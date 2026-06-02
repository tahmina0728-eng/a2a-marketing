"""
seed_sephora_cdp.py — Build CDP customer insights from Sephora product data.

Queries BigQuery briefing_agent.sephora_products, maps hair products to
Sunglow (natural/curl/scalp care) and Boozt (volume/styling/thickening),
generates consumer insight profiles, embeds them, and stores in pgvector
customer_insights table.

Run:
  cd d:/campaignos/harness
  uv run python scripts/seed_sephora_cdp.py
"""

import os
import psycopg2
from psycopg2.extras import execute_values
from google.cloud import bigquery

PROJECT    = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
BQ_DATASET = os.getenv("BQ_DATASET",           "briefing_agent")
BQ_TABLE   = f"{PROJECT}.{BQ_DATASET}.sephora_products"

PG_HOST = os.getenv("PGVECTOR_HOST",     "127.0.0.1")
PG_PORT = int(os.getenv("PGVECTOR_PORT", "5433"))
PG_USER = os.getenv("PGVECTOR_USER",     "campaignos")
PG_PASS = os.getenv("PGVECTOR_PASSWORD", "campaignos")
PG_DB   = os.getenv("PGVECTOR_DB",       "marketing")

_model = None
def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# ── Brand mapping keywords ─────────────────────────────────────────────────

SUNGLOW_KEYWORDS = [
    "curl", "coil", "natural hair", "scalp", "moisture", "afro",
    "protective", "kinky", "wavy", "frizz", "deep condition",
    "leave-in", "co-wash", "detangle", "shrinkage", "twist",
    "define", "nourish", "hydrat", "repair", "strengthen",
]

BOOZT_KEYWORDS = [
    "volume", "volum", "lift", "root lift", "thicken", "body",
    "texture", "mousse", "bounce", "fullness", "fine hair",
    "blow dry", "root", "plump", "big hair", "fluffy",
    "weightless", "lightweight", "airy", "boost", "buildup-free",
]


def map_product_to_brand(row: dict) -> str | None:
    """Map a Sephora product to Sunglow or Boozt based on keywords."""
    text = " ".join([
        str(row.get("product_name", "") or ""),
        str(row.get("secondary_category", "") or ""),
        str(row.get("tertiary_category", "") or ""),
        str(row.get("highlights", "") or ""),
    ]).lower()

    # Check Boozt first (volume/styling is more specific)
    if any(kw in text for kw in BOOZT_KEYWORDS):
        return "Boozt"

    # Then Sunglow (broader natural/moisture hair care)
    if any(kw in text for kw in SUNGLOW_KEYWORDS):
        return "Sunglow"

    # Also check primary category
    primary = str(row.get("primary_category", "") or "").lower()
    secondary = str(row.get("secondary_category", "") or "").lower()
    if "hair" in primary or "hair" in secondary:
        return "Sunglow"  # Default hair → Sunglow

    return None


def generate_consumer_note(row: dict, brand: str) -> str:
    """Generate a consumer insight profile from a Sephora product row."""
    name      = row.get("product_name", "Unknown product")
    brand_name = row.get("brand_name", "")
    rating    = row.get("rating") or 0
    reviews   = row.get("reviews") or 0
    price     = row.get("price_usd") or 0
    loves     = row.get("loves_count") or 0
    highlights = str(row.get("highlights", "") or "")
    secondary = str(row.get("secondary_category", "") or "")
    tertiary  = str(row.get("tertiary_category", "") or "")

    # Infer consumer profile from product attributes
    is_premium  = price > 30
    is_viral    = loves > 5000
    is_trusted  = rating >= 4.0 and reviews > 50
    is_new      = row.get("new") == 1
    is_exclusive = row.get("sephora_exclusive") == 1

    lines = []

    if brand == "Sunglow":
        lines.append(f"Natural hair care buyer — purchased {brand_name} {name}.")
        if "scalp" in tertiary.lower() or "scalp" in highlights.lower():
            lines.append("Scalp health focus. Seeks targeted treatments for scalp condition.")
        if "moisture" in tertiary.lower() or "curl" in tertiary.lower():
            lines.append("Curl and moisture-driven purchases. Values hydration, definition, and frizz control.")
        if "protective" in highlights.lower():
            lines.append("Protective style practitioner. Looks for products that work under braids, twists, wigs.")
        if is_premium:
            lines.append(f"Premium buyer (${price:.0f}). Willing to invest in high-quality hair care formulations.")
        else:
            lines.append(f"Value-conscious (${price:.0f}). Seeks effective results at accessible price points.")
        if is_viral:
            lines.append(f"Attracted to viral products ({loves:,} Sephora loves). Social proof drives discovery.")
        if is_trusted:
            lines.append(f"Trust-driven buyer — {rating}/5 rating with {reviews} reviews. Reviews matter.")

    elif brand == "Boozt":
        lines.append(f"Volume and styling buyer — purchased {brand_name} {name}.")
        if "volume" in tertiary.lower() or "volumiz" in highlights.lower():
            lines.append("Core volume seeker. Primary need: visible lift at the root, instant fullness.")
        if "fine" in highlights.lower() or "thin" in highlights.lower():
            lines.append("Fine or thin hair concern. Needs lightweight formulas that add body without weighing down.")
        if "mousse" in name.lower() or "spray" in name.lower() or "powder" in name.lower():
            lines.append("Styling tool user. Part of a regular styling routine, not a one-off purchase.")
        if is_premium:
            lines.append(f"Premium styling buyer (${price:.0f}). Invests in professional-grade results.")
        else:
            lines.append(f"Accessible styling buyer (${price:.0f}). Speed and efficacy over price.")
        if is_new:
            lines.append("Early adopter — purchased new launch. Responds to 'new' and 'just launched' messaging.")
        if is_exclusive:
            lines.append("Sephora-exclusive buyer — channel loyalty signal. Responds to exclusivity messaging.")

    # Add channel preference based on product type
    if price < 20:
        lines.append("Budget-accessible range. Likely discovers via TikTok and Instagram.")
    elif price < 40:
        lines.append("Mid-range buyer. Researches via Instagram and YouTube before purchasing.")
    else:
        lines.append("Premium buyer. Discovers via editorial content, influencer reviews, and brand storytelling.")

    return " ".join(lines)


def infer_age_range_from_product(row: dict, brand: str) -> str:
    price = row.get("price_usd") or 0
    loves = row.get("loves_count") or 0
    tertiary = str(row.get("tertiary_category", "") or "").lower()

    if brand == "Boozt":
        if loves > 10000:  return "18-25"  # Viral = younger
        if price < 20:     return "18-25"
        if price < 35:     return "26-35"
        return "26-44"
    else:  # Sunglow
        if "scalp" in tertiary: return "25-44"
        if "baby" in tertiary:  return "25-40"
        if price < 20:          return "18-34"
        return "25-44"


def infer_channels(row: dict, brand: str) -> list[str]:
    loves  = row.get("loves_count") or 0
    price  = row.get("price_usd") or 0
    online = row.get("online_only") == 1

    channels = ["Instagram"]

    if brand == "Boozt":
        if loves > 5000:
            channels.append("TikTok")
        channels.append("YouTube" if price > 25 else "TikTok")
    else:  # Sunglow
        channels.append("YouTube")  # Natural hair tutorials
        if loves > 8000:
            channels.append("TikTok")
        if online:
            channels.append("Meta Ads")

    return list(set(channels))[:3]


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Seeding Sephora CDP into pgvector ===\n")

    # Query hair products from BigQuery
    bq = bigquery.Client(project=PROJECT)
    query = f"""
        SELECT *
        FROM `{BQ_TABLE}`
        WHERE LOWER(primary_category) LIKE '%hair%'
           OR LOWER(secondary_category) LIKE '%hair%'
           OR LOWER(tertiary_category) LIKE '%volume%'
           OR LOWER(tertiary_category) LIKE '%curl%'
           OR LOWER(tertiary_category) LIKE '%scalp%'
           OR LOWER(tertiary_category) LIKE '%moisture%'
           OR LOWER(highlights) LIKE '%volume%'
           OR LOWER(highlights) LIKE '%curl%'
           OR LOWER(highlights) LIKE '%natural hair%'
        ORDER BY loves_count DESC
    """
    print("Querying BigQuery for hair/beauty products...")
    rows = [dict(r) for r in bq.query(query).result()]
    print(f"Found {len(rows)} hair/beauty products\n")

    # Map to brands
    mapped = [(r, map_product_to_brand(r)) for r in rows]
    mapped = [(r, b) for r, b in mapped if b is not None]

    sunglow_rows = [(r, b) for r, b in mapped if b == "Sunglow"]
    boozt_rows   = [(r, b) for r, b in mapped if b == "Boozt"]
    print(f"Mapped: {len(sunglow_rows)} → Sunglow, {len(boozt_rows)} → Boozt")

    # Connect to pgvector
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB
    )
    cur  = conn.cursor()

    # Remove old Sunglow/Boozt Sephora records
    cur.execute("DELETE FROM customer_insights WHERE brand IN ('Sunglow', 'Boozt')")
    print(f"\nCleared existing Sunglow/Boozt records")

    model = get_model()
    print("Embedding model ready. Generating profiles...\n")

    batch = []
    fake_id = 100000  # Start IDs above Kaggle range (max ~11000)

    for i, (row, brand) in enumerate(mapped):
        note      = generate_consumer_note(row, brand)
        age_range = infer_age_range_from_product(row, brand)
        channels  = infer_channels(row, brand)
        income    = (row.get("price_usd") or 0) * 800  # proxy: spend × 800 ≈ annual income
        embedding = model.encode(note).tolist()

        batch.append((
            fake_id + i,
            brand,
            age_range,
            min(income, 120000),  # cap at £120k
            0.0,   # mnt_wines (n/a)
            0.0,   # mnt_meat (n/a)
            0,     # num_deals
            5,     # web_visits (beauty buyers are digital)
            False, # has_children
            channels,
            note,
            embedding,
        ))

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(mapped)}...")

    # Insert into pgvector
    print(f"\nInserting {len(batch)} Sephora-derived profiles into pgvector...")
    execute_values(cur,
        """INSERT INTO customer_insights
           (id, brand, age_range, income, mnt_wines, mnt_meat, num_deals,
            web_visits, has_children, top_channels, crm_notes, embedding)
           VALUES %s ON CONFLICT (id) DO UPDATE SET
             crm_notes = EXCLUDED.crm_notes,
             embedding  = EXCLUDED.embedding""",
        batch,
    )
    conn.commit()

    # Verify counts
    cur.execute("SELECT brand, COUNT(*) FROM customer_insights WHERE brand IN ('Sunglow','Boozt') GROUP BY brand")
    counts = dict(cur.fetchall())
    cur.close()
    conn.close()

    print(f"""
=== Done ===
pgvector customer_insights:
  Sunglow: {counts.get('Sunglow', 0):,} profiles
  Boozt:   {counts.get('Boozt',   0):,} profiles

Restart the harness and run a Sunglow or Boozt campaign.
The CDP Audience Intelligence card will now show real Sephora product buyers.
""")
