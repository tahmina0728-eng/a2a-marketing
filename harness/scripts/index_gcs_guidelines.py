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
from google.cloud import storage

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

_model = None
def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS brand_guidelines_chunks (
            id          SERIAL PRIMARY KEY,
            brand       TEXT NOT NULL,
            source_file TEXT,
            chunk_index INT,
            content     TEXT NOT NULL,
            embedding   vector(384)
        );
        CREATE INDEX IF NOT EXISTS bgc_emb_idx
            ON brand_guidelines_chunks USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX IF NOT EXISTS bgc_brand_idx ON brand_guidelines_chunks (brand);
    """)
    print("  Schema ready")


def index_brand(brand: str, content: str, source_file: str, cur) -> int:
    model  = get_model()
    chunks = chunk_text(content)
    rows   = []

    for i, chunk in enumerate(chunks):
        emb = model.encode(chunk).tolist()
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
    print("=== Indexing GCS brand guidelines into pgvector RAG ===\n")

    # Connect to GCS
    gcs_client = storage.Client()
    bucket     = gcs_client.bucket(GCS_BUCKET)

    # Connect to pgvector
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB
    )
    cur = conn.cursor()
    setup_schema(cur)
    conn.commit()

    # Delete existing chunks to allow re-indexing
    cur.execute("DELETE FROM brand_guidelines_chunks")
    conn.commit()
    print("Cleared existing brand guideline chunks\n")

    # List all brand guideline files in GCS
    total_chunks = 0
    blobs = list(bucket.list_blobs(prefix=f"{BRANDS_PREFIX}/"))
    guideline_blobs = [b for b in blobs if "Guidelines/" in b.name and b.name.endswith(".md")]

    if not guideline_blobs:
        print(f"No .md files found in gs://{GCS_BUCKET}/{BRANDS_PREFIX}/*/Guidelines/")
        print("Falling back to local bucket/ folder...")

        import pathlib
        local_root = pathlib.Path(__file__).parent.parent / "bucket" / "brands"
        guideline_blobs = list(local_root.glob("*/Guidelines/*.md"))

        for path in guideline_blobs:
            brand   = path.parent.parent.name
            content = path.read_text(encoding="utf-8")
            n       = index_brand(brand, content, str(path), cur)
            conn.commit()
            total_chunks += n
            print(f"  {brand}: {n} chunks indexed from local file")
    else:
        for blob in guideline_blobs:
            # Extract brand name from path: brands/{BrandName}/Guidelines/file.md
            parts  = blob.name.split("/")
            brand  = parts[1] if len(parts) > 1 else "Unknown"
            content = blob.download_as_text()
            n      = index_brand(brand, content, blob.name, cur)
            conn.commit()
            total_chunks += n
            print(f"  {brand}: {n} chunks indexed from gs://{GCS_BUCKET}/{blob.name}")

    cur.close()
    conn.close()

    print(f"""
=== Done ===
Total chunks indexed: {total_chunks}
Brands indexed: {len(guideline_blobs)}

The briefing agent can now semantically search brand guidelines.
Add search_brand_guidelines() call to pgvector_client.py to use it.
""")
