"""
migrate_boozt_data.py - Insert Boozt energy drink fan truths and campaign benchmarks.

Run from the harness directory:
  uv run python scripts/migrate_boozt_data.py

Safe to run multiple times — uses ON CONFLICT DO NOTHING.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

import psycopg2
from psycopg2.extras import execute_values

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = os.getenv("PG_PORT", "5433")
PG_USER = os.getenv("PG_USER", "campaignos")
PG_PASS = os.getenv("PG_PASSWORD", "campaignos")
PG_DB   = os.getenv("PG_DB", "marketing")

DSN = f"host={PG_HOST} port={PG_PORT} user={PG_USER} password={PG_PASS} dbname={PG_DB}"

USE_GEMINI = os.getenv("USE_GEMINI_EMBEDDINGS", "false").lower() == "true"
GEMINI_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")

print(f"Embedding backend: {'Gemini ' + GEMINI_MODEL if USE_GEMINI else 'sentence-transformers all-MiniLM-L6-v2'}")


def get_embedding(text: str) -> list[float]:
    if USE_GEMINI:
        try:
            import google.genai as genai
            api_key = os.getenv("GOOGLE_API_KEY", "")
            client = genai.Client(api_key=api_key if api_key else None, vertexai=False)
            resp = client.models.embed_content(
                model=GEMINI_MODEL,
                contents=text,
                config={"task_type": "RETRIEVAL_DOCUMENT", "output_dimensionality": 768},
            )
            return list(resp.embeddings[0].values)
        except Exception as e:
            print(f"  WARNING: Gemini embedding failed ({e}) — using zero vector")
            return [0.0] * 768
    else:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            return model.encode(text).tolist()
        except ImportError:
            print("  WARNING: sentence-transformers not installed — using zero vectors")
            return [0.0] * 384


FAN_TRUTHS = [
    {"brand": "Boozt", "statement": "That first sip when you need to switch on — that's a Boozt moment", "category": "Energy Drinks", "verdict": "PASS", "specific": 82, "shared": 74, "special": 79, "overall": 78},
    {"brand": "Boozt", "statement": "Peak performance isn't a personality — it's a decision you make every day", "category": "Energy Drinks", "verdict": "PASS", "specific": 76, "shared": 80, "special": 83, "overall": 80},
    {"brand": "Boozt", "statement": "The can that turns 'I can't' into 'watch me'", "category": "Energy Drinks", "verdict": "PASS", "specific": 85, "shared": 70, "special": 88, "overall": 81},
    {"brand": "Boozt", "statement": "Zero limits. Pure energy. One can.", "category": "Energy Drinks", "verdict": "PASS", "specific": 72, "shared": 76, "special": 80, "overall": 76},
    {"brand": "Boozt", "statement": "I just need energy", "category": "Generic", "verdict": "FAIL", "specific": 15, "shared": 82, "special": 18, "overall": 38},
]

CAMPAIGN_BENCHMARKS = [
    {"brand": "Boozt", "product_category": "Energy Drinks", "market": "UK", "season": "Summer", "channels": ["Instagram", "TikTok", "OOH"], "reach": 5000000, "ctr_pct": 2.5, "roas": 3.0, "engagement_pct": 5.8, "budget_gbp": 400000, "notes": "Festival season activation — UGC athletes and gym-goers drove TikTok reach"},
    {"brand": "Boozt", "product_category": "Energy Drinks", "market": "UK", "season": "All Year", "channels": ["TikTok", "YouTube", "Meta Ads"], "reach": 4200000, "ctr_pct": 2.8, "roas": 2.6, "engagement_pct": 6.4, "budget_gbp": 300000, "notes": "Always-on gaming and sport audience targeting — YouTube pre-roll strong for awareness"},
]


def run():
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()

    # --- Fan Truths ---
    print("\nInserting Boozt fan truths...")
    ft_rows = []
    for r in FAN_TRUTHS:
        text = f"{r['brand']} fan truth: {r['statement']}"
        emb = get_embedding(text)
        ft_rows.append((
            r["brand"], r["statement"], r["category"], r["verdict"],
            r["specific"], r["shared"], r["special"], r["overall"], emb
        ))
        print(f"  Embedded: {r['statement'][:55]}...")

    execute_values(cur,
        """INSERT INTO fan_truths
           (brand, statement, category, verdict, specific, shared, special, overall, embedding)
           VALUES %s ON CONFLICT DO NOTHING""",
        ft_rows
    )
    print(f"  Done — {cur.rowcount} rows inserted (0 = already existed)")

    # --- Campaign Benchmarks ---
    print("\nInserting Boozt campaign benchmarks...")
    cb_rows = []
    for r in CAMPAIGN_BENCHMARKS:
        text = f"{r['brand']} {r['product_category']} {r['market']} {r['season']} campaign"
        emb = get_embedding(text)
        cb_rows.append((
            r["brand"], r["product_category"], r["market"], r["season"],
            r["channels"], r["reach"], r["ctr_pct"], r["roas"],
            r["engagement_pct"], r["budget_gbp"], r["notes"], emb
        ))
        print(f"  Embedded: {r['brand']} {r['product_category']} {r['season']}...")

    execute_values(cur,
        """INSERT INTO campaign_benchmarks
           (brand, product_category, market, season, channels, reach, ctr_pct, roas, engagement_pct, budget_gbp, notes, embedding)
           VALUES %s ON CONFLICT DO NOTHING""",
        cb_rows
    )
    print(f"  Done — {cur.rowcount} rows inserted (0 = already existed)")

    conn.commit()
    cur.close()
    conn.close()
    print("\nMigration complete")


if __name__ == "__main__":
    run()
