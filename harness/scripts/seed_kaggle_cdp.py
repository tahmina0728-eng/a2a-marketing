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

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5433"))
PG_USER = os.getenv("PG_USER", "campaignos")
PG_PASS = os.getenv("PG_PASSWORD", "campaignos")
PG_DB   = os.getenv("PG_DB", "marketing")

CSV_PATH = os.path.join(os.path.dirname(__file__), "marketing_campaign.csv")

_model = None
def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


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

    notes = []

    # Profile identity
    if is_premium:
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
    """Map a Kaggle row to the most relevant brand based on product spend profile."""
    meat   = float(row.get("MntMeatProducts", 0) or 0)
    fish   = float(row.get("MntFishProducts", 0) or 0)
    sweets = float(row.get("MntSweetProducts", 0) or 0)
    wines  = float(row.get("MntWines", 0) or 0)
    income = float(row.get("Income", 0) or 0)
    kids   = int(row.get("Kidhome", 0) or 0)
    deals  = int(row.get("NumDealsPurchases", 0) or 0)

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
    cur.execute("""
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
            embedding       vector(384)
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

    model = get_model()
    print(f"Embedding model loaded. Processing {len(rows)} customers...\n")

    batch = []
    for i, row in enumerate(rows):
        crm_note  = generate_crm_note(row)
        brand     = map_to_brand(row)
        age_range = infer_age_range(row)
        channels  = infer_channels(row)
        embedding = model.encode(crm_note).tolist()

        batch.append((
            int(row.get("ID", i)),
            brand,
            age_range,
            float(row.get("Income", 0) or 0),
            float(row.get("MntWines", 0) or 0),
            float(row.get("MntMeatProducts", 0) or 0),
            int(row.get("NumDealsPurchases", 0) or 0),
            int(row.get("NumWebVisitsMonth", 0) or 0),
            (int(row.get("Kidhome", 0) or 0) + int(row.get("Teenhome", 0) or 0)) > 0,
            channels,
            crm_note,
            embedding,
        ))

        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(rows)}...")

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
