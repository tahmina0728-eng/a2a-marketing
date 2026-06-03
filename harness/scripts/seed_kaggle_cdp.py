"""
seed_kaggle_cdp.py — Load real Kaggle Customer Personality Analysis data into pgvector.

Dataset: https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis
File:    marketing_campaign.csv  (place in this scripts/ folder)

Each row becomes a customer_insights record with:
  - Quantitative fields from the CSV
  - CRM-style notes generated from the behavioural signals
  - A 384-dim sentence embedding for semantic search

Run:
  cd d:\\campaignos\\harness
  uv run python scripts/seed_kaggle_cdp.py
"""

import os
import csv
import random
import psycopg2
from psycopg2.extras import execute_values

# Load .env file so USE_GEMINI_EMBEDDINGS and GOOGLE_API_KEY are available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5433"))
PG_USER = os.getenv("PG_USER", "campaignos")
PG_PASS = os.getenv("PG_PASSWORD", "campaignos")
PG_DB   = os.getenv("PG_DB", "marketing")

CSV_PATH = os.path.join(os.path.dirname(__file__), "marketing_campaign.csv")

# ── Embedding backend (mirrors pgvector_client.py) ────────────────────────────
USE_GEMINI = os.getenv("USE_GEMINI_EMBEDDINGS", "false").lower() == "true"
GEMINI_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
VECTOR_DIM = 768 if USE_GEMINI else 384  # gemini-embedding-2 with output_dimensionality=768, ST=384


def get_embedding(text: str) -> list[float]:
    """Single text embedding — delegates to batch function."""
    return get_embeddings_batch([text])[0]


def get_embeddings_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """
    Batch embedding — much faster than individual calls.

    Option A — Gemini text-embedding-004 (USE_GEMINI_EMBEDDINGS=true):
      Processes up to 50 texts per API call
      768 dims, ~300ms per batch vs 300ms per individual call
      Free tier: 1,500 req/day — use batches to stay within limit

    Option B — sentence-transformers (USE_GEMINI_EMBEDDINGS=false):
      384 dims, all texts processed locally in one pass
      Original code preserved:
      #   from sentence_transformers import SentenceTransformer
      #   model = SentenceTransformer("all-MiniLM-L6-v2")
      #   return [model.encode(t).tolist() for t in texts]
    """
    if USE_GEMINI:
        import google.genai as genai
        import time
        api_key = os.getenv("GOOGLE_API_KEY", "")
        client = genai.Client(api_key=api_key if api_key else None)
        all_embeddings = []
        print(f"  Rate limit: ~15 RPM free tier — adding 4s delay between batches")

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                result = client.models.embed_content(
                    model   = GEMINI_MODEL,
                    contents= batch,
                    config  = {"task_type": "RETRIEVAL_DOCUMENT", "output_dimensionality": VECTOR_DIM},
                )
                all_embeddings.extend([list(e.values) for e in result.embeddings])
            except Exception as e:
                if "429" in str(e):
                    print(f"  Rate limit hit at batch {i//batch_size+1} — waiting 60s...")
                    time.sleep(60)
                    # Retry once after waiting
                    try:
                        result = client.models.embed_content(
                            model   = GEMINI_MODEL,
                            contents= batch,
                            config  = {"task_type": "RETRIEVAL_DOCUMENT", "output_dimensionality": VECTOR_DIM},
                        )
                        all_embeddings.extend([list(e.values) for e in result.embeddings])
                        print(f"  Retry succeeded for batch {i//batch_size+1}")
                        time.sleep(4)
                        continue
                    except Exception as e2:
                        print(f"  Retry failed: {e2} — zero vectors")
                        all_embeddings.extend([[0.0] * VECTOR_DIM] * len(batch))
                else:
                    print(f"  WARNING: Gemini batch {i//batch_size+1} failed ({e}) — zero vectors")
                    all_embeddings.extend([[0.0] * VECTOR_DIM] * len(batch))
            # 4s pause between batches = ~15 RPM (free tier limit)
            time.sleep(4)

        return all_embeddings
    else:
        # ── sentence-transformers batch (original implementation) ───────────
        # from sentence_transformers import SentenceTransformer
        # model = SentenceTransformer("all-MiniLM-L6-v2")
        # return [model.encode(t).tolist() for t in texts]
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            return [model.encode(t).tolist() for t in texts]
        except ImportError:
            return [[0.0] * 384] * len(texts)


# kept for backward compat
def get_model():
    return None


# ── CRM note generation (from Kaggle columns → qualitative text) ─────────────

PREMIUM_INTROS = [
    "Account audit indicates tier-1 profile.",
    "VIP customer contact log updated.",
    "High-value portfolio review completed.",
    "Loyalty tier: Gold. High purchase frequency confirmed.",
]

BUDGET_INTROS = [
    "Value-conscious account profile.",
    "Frequent promotions user flagged.",
    "Standard tier retail customer tracker.",
    "Deal-responsive purchasing pattern noted.",
]

FRICTION_SCENARIOS = {
    "ui_bug": {
        "premium": (
            "Customer registered intense dissatisfaction regarding a persistent UI crash "
            "during checkout on premium product drops. Threatening to abandon loyalty programme "
            "due to app bugs."
        ),
        "standard": (
            "User encountered an unexpected web interface exception when attempting to apply a "
            "promo code at checkout. Abandoned basket after multiple attempts."
        ),
    },
    "support_delay": (
        "Frequent site visitor with unresolved service ticket. Logged inquiry regarding missing "
        "loyalty points adjustment. Response SLA breached."
    ),
    "shipping_issue": (
        "Delivery logistics breakdown reported. High-value grocery delivery arrived damaged. "
        "Customer expressed frustration with cold-chain reliability."
    ),
    "none": None,
}


def generate_crm_note(row: dict) -> str:
    income      = float(row.get("Income", 0) or 0)
    wines       = float(row.get("MntWines", 0) or 0)
    meat        = float(row.get("MntMeatProducts", 0) or 0)
    fish        = float(row.get("MntFishProducts", 0) or 0)
    sweets      = float(row.get("MntSweetProducts", 0) or 0)
    gold        = float(row.get("MntGoldProds", 0) or 0)
    deals       = int(row.get("NumDealsPurchases", 0) or 0)
    web_visits  = int(row.get("NumWebVisitsMonth", 0) or 0)
    web_orders  = int(row.get("NumWebPurchases", 0) or 0)
    kids        = int(row.get("Kidhome", 0) or 0)
    teens       = int(row.get("Teenhome", 0) or 0)
    complain    = int(row.get("Complain", 0) or 0)
    recency     = int(row.get("Recency", 999) or 999)
    birth_year  = int(row.get("Year_Birth", 1980) or 1980)
    age         = 2024 - birth_year

    is_premium   = income > 70000 or (wines + meat) > 700
    is_deal_seek = deals > 5 or income < 35000
    has_family   = (kids + teens) > 0
    is_digital   = web_visits > 6 or web_orders > 5
    is_churned   = recency > 60

    # Detect beauty/styling profile (proxy for Sunglow/Boozt)
    brand_detected = map_to_brand(row)
    is_beauty = brand_detected in ("Sunglow", "Boozt")

    notes = []

    # Beauty/hair care profile notes
    if is_beauty and brand_detected == "Sunglow":
        notes.append("Premium self-care buyer profile. High spend on gold/luxury products.")
        notes.append("No dependants — high personal care budget. Values quality and visible results.")
        if gold > 200:
            notes.append("Frequent luxury product buyer — premium hair treatment and care routine likely.")
        if age < 40:
            notes.append("Younger premium buyer. Social media-influenced purchases. Responds to before/after content.")
        else:
            notes.append("Established premium consumer. Brand loyalty high once trust earned.")
    elif is_beauty and brand_detected == "Boozt":
        notes.append("Young styling-conscious consumer profile. High digital engagement.")
        notes.append("Fast beauty buyer — values instant results and on-trend products.")
        if web_visits > 7:
            notes.append(f"Very high site visit frequency ({web_visits}/month). Browses before buying. Responds to reviews and demos.")
        if gold > 50:
            notes.append("Moderate luxury spend — willing to pay for proven styling results.")

    # Profile identity
    if not is_beauty and is_premium:
        notes.append(random.choice(PREMIUM_INTROS))
        if wines > 400:
            notes.append("Strong affinity for premium and curated product selections.")
        if not has_family:
            notes.append("High disposable income. Prefers quality-led messaging over price.")
        if gold > 200:
            notes.append("Luxury / gifting purchases observed — seasonal campaign sensitivity.")
    elif is_deal_seek:
        notes.append(random.choice(BUDGET_INTROS))
        notes.append("Highly responsive to discount triggers, markdown alerts, and bundle offers.")
        if has_family:
            notes.append("Household purchasing patterns indicate bulk-buy preference for family care.")
    else:
        notes.append("Mid-market steady consumer profile. Standard recurring purchasing cadence.")

    # Digital behaviour
    if is_digital:
        notes.append(
            f"High digital engagement: {web_visits} site visits/month, "
            f"{web_orders} web orders. App or web is primary purchase channel."
        )

    # Churn risk
    if is_churned:
        notes.append(
            f"Recency gap: {recency} days since last purchase. Re-engagement trigger recommended."
        )

    # Age signal
    if age < 26:
        notes.append("Gen Z profile — social-first discovery, peer validation critical.")
    elif age < 36:
        notes.append("Millennial profile — convenience and values-alignment important.")
    elif age > 50:
        notes.append("Established consumer — brand loyalty high, low switching probability.")

    # Complaint / friction
    if complain:
        notes.append(
            "Active complaint on record. Service recovery communication recommended before "
            "next promotional push."
        )
    else:
        # Assign a friction scenario probabilistically
        random.seed(int(row.get("ID", 0) or 0))
        friction_type = random.choice(["ui_bug", "support_delay", "shipping_issue", "none", "none"])
        if friction_type == "ui_bug":
            note = FRICTION_SCENARIOS["ui_bug"]["premium" if is_premium else "standard"]
            notes.append(note)
        elif friction_type == "support_delay" and web_visits > 4:
            notes.append(FRICTION_SCENARIOS["support_delay"])
        elif friction_type == "shipping_issue" and meat > 200:
            notes.append(FRICTION_SCENARIOS["shipping_issue"])

    return " ".join(notes)


def map_to_brand(row: dict) -> str:
    """
    Map a Kaggle row to the most relevant brand based on product spend profile.

    Proxy signals used (dataset has no direct hair/beauty column):
      Rnorr:    high meat/fish spend → home cooking
      McDonalds: convenience/sweets/kids/deal-seeking
      Sunglow:  premium income + high gold (luxury self-care) + no kids → Black hair care buyer proxy
      Boozt:    young (18-35) + high digital + moderate gold → styling-conscious, fast beauty
    """
    meat       = float(row.get("MntMeatProducts", 0) or 0)
    fish       = float(row.get("MntFishProducts", 0) or 0)
    sweets     = float(row.get("MntSweetProducts", 0) or 0)
    wines      = float(row.get("MntWines", 0) or 0)
    gold       = float(row.get("MntGoldProds", 0) or 0)
    income     = float(row.get("Income", 0) or 0)
    kids       = int(row.get("Kidhome", 0) or 0)
    teens      = int(row.get("Teenhome", 0) or 0)
    deals      = int(row.get("NumDealsPurchases", 0) or 0)
    web_visits = int(row.get("NumWebVisitsMonth", 0) or 0)
    web_orders = int(row.get("NumWebPurchases", 0) or 0)
    birth_year = int(row.get("Year_Birth", 1985) or 1985)
    age        = 2024 - birth_year

    # Sunglow: premium self-care buyer — high income, spends on luxury/gold products,
    # no young children (free to spend on personal care), 25-55 age range
    if income > 55000 and gold > 100 and (kids + teens) == 0 and 25 <= age <= 55:
        return "Sunglow"

    # Boozt: styling-conscious young buyer — under 35, high digital, moderate gold spend
    if age < 36 and (web_visits > 5 or web_orders > 3) and gold > 30 and income > 25000:
        return "Boozt"

    # Rnorr: home cooking — meat, fish, budget-conscious
    if (meat + fish) > 200 or (income < 50000 and (meat + fish) > 80):
        return "Rnorr"

    # McDonald's: convenience, sweets, younger, deal-seeking
    if sweets > 100 or (kids > 0 and deals > 3) or wines < 50:
        return "McDonalds"

    return "All"


def infer_age_range(row: dict) -> str:
    birth_year = int(row.get("Year_Birth", 1985) or 1985)
    age = 2024 - birth_year
    if age < 18:  return "Under 18"
    if age < 26:  return "18-25"
    if age < 36:  return "26-35"
    if age < 46:  return "36-45"
    if age < 56:  return "46-55"
    return "55+"


def infer_channels(row: dict) -> list[str]:
    web_visits = int(row.get("NumWebVisitsMonth", 0) or 0)
    web_orders = int(row.get("NumWebPurchases", 0) or 0)
    catalog    = int(row.get("NumCatalogPurchases", 0) or 0)
    store      = int(row.get("NumStorePurchases", 0) or 0)
    birth_year = int(row.get("Year_Birth", 1985) or 1985)
    age        = 2024 - birth_year

    channels = []
    if age < 26:
        # Gen Z — TikTok primary regardless of purchase channel
        channels.extend(["TikTok", "Instagram"])
    elif age < 35 and (web_visits > 5 or web_orders > 3):
        channels.extend(["Instagram", "TikTok"])
    elif web_visits > 5 or web_orders > 3:
        channels.extend(["Instagram", "Facebook"])
    if catalog > 2:
        channels.append("Email")
    if store > 6:
        channels.append("OOH")
    if not channels:
        channels = ["Instagram"]
    return list(set(channels))[:3]


# ── Schema ────────────────────────────────────────────────────────────────────

def setup_schema(cur):
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS customer_insights (
            id              INT PRIMARY KEY,
            brand           TEXT,
            age_range       TEXT,
            income          NUMERIC(10,2),
            mnt_wines       NUMERIC(8,2),
            mnt_meat        NUMERIC(8,2),
            num_deals       INT,
            web_visits      INT,
            has_children    BOOL,
            top_channels    TEXT[],
            crm_notes       TEXT,
            embedding       vector({VECTOR_DIM})
        );
        CREATE INDEX IF NOT EXISTS ci_emb_idx
            ON customer_insights USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX IF NOT EXISTS ci_brand_idx ON customer_insights (brand);
    """)
    print("  Schema ready")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: Dataset not found at {CSV_PATH}")
        print("Download from: https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis")
        print("Save as: d:\\campaignos\\harness\\scripts\\marketing_campaign.csv")
        exit(1)

    print(f"Loading {CSV_PATH} ...")
    with open(CSV_PATH, encoding="utf-8") as f:
        # Kaggle file uses tab separator
        dialect = csv.Sniffer().sniff(f.read(4096))
        f.seek(0)
        reader = csv.DictReader(f, dialect=dialect)
        rows = [r for r in reader if r.get("Income", "").strip()]

    print(f"Loaded {len(rows)} rows with valid income data")

    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB
    )
    cur = conn.cursor()
    setup_schema(cur)
    conn.commit()

    backend = f"Gemini {GEMINI_MODEL} ({VECTOR_DIM} dims)" if USE_GEMINI else "sentence-transformers all-MiniLM-L6-v2 (384 dims)"
    print(f"Embedding backend: {backend}")
    print(f"Processing {len(rows)} customers...\n")

    # Pre-generate all CRM notes
    print("Generating CRM notes...")
    records = []
    for i, row in enumerate(rows):
        records.append({
            "id":        int(row.get("ID", i)),
            "brand":     map_to_brand(row),
            "age_range": infer_age_range(row),
            "channels":  infer_channels(row),
            "crm_note":  generate_crm_note(row),
            "row":       row,
        })

    # Batch embed all CRM notes (50 texts per API call)
    crm_notes = [r["crm_note"] for r in records]
    EMBED_BATCH = 50
    total_batches = (len(crm_notes) + EMBED_BATCH - 1) // EMBED_BATCH
    print(f"Embedding {len(crm_notes)} records in {total_batches} batches of {EMBED_BATCH}...")
    all_embeddings = get_embeddings_batch(crm_notes, batch_size=EMBED_BATCH)
    print(f"Embeddings done. Building insert batch...")

    batch = []
    for i, (rec, embedding) in enumerate(zip(records, all_embeddings)):
        row = rec["row"]
        batch.append((
            rec["id"],
            rec["brand"],
            rec["age_range"],
            float(row.get("Income", 0) or 0),
            float(row.get("MntWines", 0) or 0),
            float(row.get("MntMeatProducts", 0) or 0),
            int(row.get("NumDealsPurchases", 0) or 0),
            int(row.get("NumWebVisitsMonth", 0) or 0),
            (int(row.get("Kidhome", 0) or 0) + int(row.get("Teenhome", 0) or 0)) > 0,
            rec["channels"],
            rec["crm_note"],
            embedding,
        ))

    print(f"\nInserting {len(batch)} records into pgvector...")
    execute_values(cur,
        """INSERT INTO customer_insights
           (id, brand, age_range, income, mnt_wines, mnt_meat, num_deals,
            web_visits, has_children, top_channels, crm_notes, embedding)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        batch,
    )
    conn.commit()
    cur.close()
    conn.close()

    print(f"""
=== Done ===
Inserted {len(batch)} real customer records from Kaggle dataset.

Brand distribution:
  Rnorr:      home cooking profiles (high meat/fish spend)
  McDonalds:  convenience profiles (sweets, kids, deals)
  All:        cross-brand profiles

The briefing agent can now query real customer data for audience validation.
""")
