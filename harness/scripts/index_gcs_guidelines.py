"""
index_gcs_guidelines.py — RAG indexer for GCS brand guidelines.

Downloads brand_guidelines.md files from GCS, chunks them into ~500-char
segments, embeds each chunk, and stores in pgvector for semantic retrieval.

Run:
  cd d:\\campaignos\\harness
  uv run python scripts/index_gcs_guidelines.py

Requires:
  - GOOGLE_CLOUD_PROJECT in .env (for GCS access via ADC)
  - pgvector running on port 5433
"""

import os
import re
import psycopg2
from psycopg2.extras import execute_values

# Load .env FIRST so defaults are set before reading config
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
except ImportError:
    pass

# ── Config ─────────────────────────────────────────────────────────────────
GCS_BUCKET    = os.getenv("GCS_BUCKET", "dauntless-karma-497108-b0-campaignos")
BRANDS_PREFIX = "brands"
PG_HOST       = os.getenv("PGVECTOR_HOST", "127.0.0.1")
PG_PORT       = int(os.getenv("PGVECTOR_PORT", "5433"))
PG_USER       = os.getenv("PGVECTOR_USER", "campaignos")
PG_PASS       = os.getenv("PGVECTOR_PASSWORD", "campaignos")
PG_DB         = os.getenv("PGVECTOR_DB", "marketing")
CHUNK_SIZE    = 500   # characters per chunk
CHUNK_OVERLAP = 100   # overlap between chunks
VECTOR_DIM    = 768   # gemini-embedding-2 via Google AI (vertexai=False)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Brands to index — McDonalds excluded (not a current brand)
ALLOWED_BRANDS = {"Rnorr", "Boozt", "Sunglow", "Glenfiddich", "UBS Bank", "Sunrise", "Haleon"}


def get_embedding(text: str) -> list[float]:
    """Embed text using gemini-embedding-2 via Google AI endpoint (matches pgvector_client.py)."""
    try:
        import google.genai as genai
        client = genai.Client(api_key=GOOGLE_API_KEY if GOOGLE_API_KEY else None, vertexai=False)
        result = client.models.embed_content(
            model   = "gemini-embedding-2",
            contents= text,
            config  = {"task_type": "RETRIEVAL_DOCUMENT", "output_dimensionality": VECTOR_DIM},
        )
        return list(result.embeddings[0].values)
    except Exception as e:
        print(f"  WARNING: embedding failed ({e}) — using zero vector")
        return [0.0] * VECTOR_DIM


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, respecting paragraph boundaries."""
    chunks = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > size and current:
            chunks.append(current.strip())
            current = current[-overlap:] + "\n\n" + para
        else:
            current = (current + "\n\n" + para).strip()
    if current:
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 50]  # drop tiny fragments


def setup_schema(cur):
    cur.execute("DROP TABLE IF EXISTS brand_guidelines_chunks CASCADE;")
    cur.execute(f"""
        CREATE TABLE brand_guidelines_chunks (
            id          SERIAL PRIMARY KEY,
            brand       TEXT NOT NULL,
            source_file TEXT,
            chunk_index INT,
            content     TEXT NOT NULL,
            embedding   vector({VECTOR_DIM})
        );
        CREATE INDEX bgc_emb_idx
            ON brand_guidelines_chunks USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX bgc_brand_idx ON brand_guidelines_chunks (brand);
    """)
    print("  Schema ready (768-dim, gemini-embedding-2)")


def index_brand(brand: str, content: str, source_file: str, cur) -> int:
    chunks = chunk_text(content)
    rows   = []

    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        print(f"    chunk {i+1}/{len(chunks)}: {chunk[:60].strip()!r}...")
        rows.append((brand, source_file, i, chunk, emb))

    if rows:
        execute_values(cur,
            """INSERT INTO brand_guidelines_chunks
               (brand, source_file, chunk_index, content, embedding)
               VALUES %s""",
            rows,
        )
    return len(rows)


if __name__ == "__main__":
    print("=== Indexing brand guidelines into pgvector RAG ===")
    print(f"    Target DB : {PG_HOST}:{PG_PORT}/{PG_DB}")
    print(f"    Brands    : {sorted(ALLOWED_BRANDS)}\n")

    # Connect to pgvector
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB
    )
    cur = conn.cursor()
    setup_schema(cur)
    conn.commit()
    print("Cleared existing brand guideline chunks\n")

    import pathlib
    total_chunks  = 0
    brands_done   = []
    local_root    = pathlib.Path(__file__).parent.parent / "bucket" / "brands"

    # Always read from local bucket/ folder — all 4 brands are present there
    for brand in sorted(ALLOWED_BRANDS):
        md_path = local_root / brand / "Guidelines" / "brand_guidelines.md"
        if not md_path.exists():
            print(f"  SKIP {brand}: no brand_guidelines.md at {md_path}")
            continue
        content = md_path.read_text(encoding="utf-8")
        print(f"  {brand}: {len(content)} chars — indexing...")
        n = index_brand(brand, content, str(md_path), cur)
        conn.commit()
        total_chunks += n
        brands_done.append(brand)
        print(f"  {brand}: {n} chunks done ✓\n")

    cur.close()
    conn.close()

    print(f"=== Done ===")
    print(f"Brands indexed : {brands_done}")
    print(f"Total chunks   : {total_chunks}")
    print(f"Stored in      : {PG_HOST}:{PG_PORT}/{PG_DB}")
