"""
index_gcs_guidelines.py — RAG indexer for GCS brand guidelines.

Downloads brand_guidelines.md / brand_guidelines.txt files, chunks them into
~500-char segments, embeds each chunk with gemini-embedding-2, and stores in
pgvector for semantic retrieval.

Source priority (per brand):
  1. Local  bucket/brands/{brand}/Guidelines/brand_guidelines.md   (most brands)
  2. Local  bucket/brands/{brand}/Guidelines/brand_guidelines.txt
  3. GCS    gs://{GCS_BUCKET}/brands/{brand}/Guidelines/brand_guidelines.txt
  4. GCS    gs://{GCS_BUCKET}/brands/{brand}/Guidelines/brand_guidelines.md

Barclays (and any future cloud-only brand) is handled by options 3/4.

Run:
  cd d:\\campaignos\\harness
  uv run python scripts/index_gcs_guidelines.py

  # Index a single brand without rebuilding the whole table:
  uv run python scripts/index_gcs_guidelines.py --brand Barclays

Requires:
  - GOOGLE_CLOUD_PROJECT + GOOGLE_API_KEY in .env
  - pgvector running on port 5433
"""

import argparse
import os
import pathlib
import sys

import psycopg2
from psycopg2.extras import execute_values

# Load .env FIRST so defaults are set before reading config
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
except ImportError:
    pass

# Force UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Config ─────────────────────────────────────────────────────────────────────
GCS_BUCKET    = os.getenv("GCS_BUCKET", "dauntless-karma-497108-b0-campaignos")
GCP_PROJECT   = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
PG_HOST       = os.getenv("PGVECTOR_HOST", "127.0.0.1")
PG_PORT       = int(os.getenv("PGVECTOR_PORT", "5433"))
PG_USER       = os.getenv("PGVECTOR_USER", "campaignos")
PG_PASS       = os.getenv("PGVECTOR_PASSWORD", "campaignos")
PG_DB         = os.getenv("PGVECTOR_DB", "marketing")
CHUNK_SIZE    = 500   # characters per chunk
CHUNK_OVERLAP = 100   # overlap between chunks
VECTOR_DIM    = 768   # gemini-embedding-2

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# All brands — local brands read from bucket/, cloud-only brands read from GCS
ALLOWED_BRANDS = {
    "Rnorr", "Boozt", "Sunglow", "Glenfiddich", "UBS Bank", "Sunrise", "Haleon",
    "Barclays",
}

# Ordered list of Guidelines filenames to try (local then GCS, .md then .txt)
_GUIDELINE_FILENAMES = ["brand_guidelines.md", "brand_guidelines.txt"]


# ── Embedding ──────────────────────────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """Embed text using gemini-embedding-2 via Google AI endpoint."""
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


# ── Text loading ───────────────────────────────────────────────────────────────

def _load_local(brand: str, local_root: pathlib.Path) -> tuple[str, str] | tuple[None, None]:
    """Try to load guidelines from the local bucket/ directory. Returns (content, path)."""
    for fname in _GUIDELINE_FILENAMES:
        p = local_root / brand / "Guidelines" / fname
        if p.exists():
            return p.read_text(encoding="utf-8"), str(p)
    return None, None


def _load_gcs(brand: str) -> tuple[str, str] | tuple[None, None]:
    """Download guidelines from GCS. Returns (content, gcs_uri)."""
    try:
        from google.cloud import storage
        client = storage.Client(project=GCP_PROJECT)
        bucket = client.bucket(GCS_BUCKET)
        for fname in _GUIDELINE_FILENAMES:
            blob_path = f"brands/{brand}/Guidelines/{fname}"
            blob = bucket.blob(blob_path)
            if blob.exists():
                text = blob.download_as_text(encoding="utf-8")
                if text.strip():
                    return text, f"gs://{GCS_BUCKET}/{blob_path}"
        return None, None
    except Exception as e:
        print(f"  WARNING: GCS download failed for {brand} ({e})")
        return None, None


def load_guidelines(brand: str, local_root: pathlib.Path) -> tuple[str, str] | tuple[None, None]:
    """Load guidelines: try local first, then GCS. Returns (content, source)."""
    content, source = _load_local(brand, local_root)
    if content:
        return content, source
    print(f"  {brand}: not in local bucket — trying GCS...")
    return _load_gcs(brand)


# ── Chunking ───────────────────────────────────────────────────────────────────

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
    return [c for c in chunks if len(c) > 50]


# ── DB ─────────────────────────────────────────────────────────────────────────

def _connect():
    if PG_HOST.startswith("/"):
        return psycopg2.connect(host=PG_HOST, user=PG_USER, password=PG_PASS, dbname=PG_DB)
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB
    )


def setup_schema(cur):
    """Create (or recreate) the brand_guidelines_chunks table."""
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
    print(f"  Schema ready ({VECTOR_DIM}-dim, gemini-embedding-2)")


def delete_brand_chunks(cur, brand: str):
    """Delete existing chunks for a single brand (used in --brand mode)."""
    cur.execute("DELETE FROM brand_guidelines_chunks WHERE brand = %s", (brand,))
    deleted = cur.rowcount
    if deleted:
        print(f"  Deleted {deleted} existing chunks for {brand}")


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


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", help="Index only this brand (upsert mode — doesn't rebuild table)")
    args = parser.parse_args()

    target_brands = {args.brand} if args.brand else ALLOWED_BRANDS

    print("=== Indexing brand guidelines into pgvector RAG ===")
    print(f"    Target DB     : {PG_HOST}:{PG_PORT}/{PG_DB}")
    print(f"    Brands        : {sorted(target_brands)}")
    print(f"    Mode          : {'single-brand upsert' if args.brand else 'full rebuild'}\n")

    local_root = pathlib.Path(__file__).parent.parent / "bucket" / "brands"
    conn       = _connect()
    cur        = conn.cursor()

    if args.brand:
        # Upsert mode: delete only this brand's chunks, leave others intact
        try:
            delete_brand_chunks(cur, args.brand)
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            print("  Table doesn't exist yet — running full setup...")
            setup_schema(cur)
        conn.commit()
    else:
        # Full rebuild: drop and recreate table
        setup_schema(cur)
        conn.commit()
        print("Cleared existing brand guideline chunks\n")

    total_chunks = 0
    brands_done  = []

    for brand in sorted(target_brands):
        content, source = load_guidelines(brand, local_root)
        if not content:
            print(f"  SKIP {brand}: no guidelines found (local or GCS)\n")
            continue

        print(f"  {brand}: {len(content)} chars from {source} — indexing...")
        n = index_brand(brand, content, source, cur)
        conn.commit()
        total_chunks += n
        brands_done.append(brand)
        print(f"  {brand}: {n} chunks done ✓\n")

    cur.close()
    conn.close()

    print("=== Done ===")
    print(f"Brands indexed : {brands_done}")
    print(f"Total chunks   : {total_chunks}")
    print(f"Stored in      : {PG_HOST}:{PG_PORT}/{PG_DB}")
