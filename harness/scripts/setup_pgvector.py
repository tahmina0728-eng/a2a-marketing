"""
setup_pgvector.py - Create schema and seed benchmark + Fan Truth data.

Run AFTER starting Docker:
  docker-compose -f docker-compose.pgvector.yml up -d
  uv run python scripts/setup_pgvector.py

For Cloud SQL (GCP):
  Set PG_HOST=<cloud-sql-ip> PG_PASSWORD=<password> before running.
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")  # use IPv4 explicitly — localhost resolves to ::1 on Windows
PG_PORT = os.getenv("PG_PORT", "5433")
PG_USER = os.getenv("PG_USER", "campaignos")
PG_PASS = os.getenv("PG_PASSWORD", "campaignos")
PG_DB   = os.getenv("PG_DB", "marketing")

DSN = f"host={PG_HOST} port={PG_PORT} user={PG_USER} password={PG_PASS} dbname={PG_DB}"


def get_embedding(text: str) -> list[float]:
    """Generate a 384-dim embedding using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()
    except ImportError:
        # Fallback: zero vector if sentence-transformers not installed
        print("  WARNING: sentence-transformers not installed — using zero vectors")
        return [0.0] * 384


def setup_schema(cur):
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fan_truths (
            id         SERIAL PRIMARY KEY,
            brand      TEXT NOT NULL,
            statement  TEXT NOT NULL,
            category   TEXT,
            verdict    TEXT CHECK (verdict IN ('PASS','FAIL')),
            specific   INT,
            shared     INT,
            special    INT,
            overall    INT,
            embedding  vector(384)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS campaign_benchmarks (
            id                SERIAL PRIMARY KEY,
            brand             TEXT,
            product_category  TEXT NOT NULL,
            market            TEXT,
            season            TEXT,
            channels          TEXT[],
            reach             BIGINT,
            ctr_pct           NUMERIC(5,2),
            roas              NUMERIC(5,2),
            engagement_pct    NUMERIC(5,2),
            budget_gbp        NUMERIC(12,2),
            notes             TEXT,
            embedding         vector(384)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS channel_benchmarks (
            id               SERIAL PRIMARY KEY,
            channel          TEXT NOT NULL,
            market           TEXT,
            audience_segment TEXT,
            ctr_pct          NUMERIC(5,2),
            cpm_gbp          NUMERIC(8,2),
            engagement_pct   NUMERIC(5,2),
            completion_pct   NUMERIC(5,2),
            avg_dwell_sec    NUMERIC(6,1),
            notes            TEXT,
            embedding        vector(384)
        );
    """)

    # HNSW indexes for fast similarity search
    cur.execute("CREATE INDEX IF NOT EXISTS ft_emb_idx ON fan_truths USING hnsw (embedding vector_cosine_ops);")
    cur.execute("CREATE INDEX IF NOT EXISTS cb_emb_idx ON campaign_benchmarks USING hnsw (embedding vector_cosine_ops);")
    cur.execute("CREATE INDEX IF NOT EXISTS ch_emb_idx ON channel_benchmarks USING hnsw (embedding vector_cosine_ops);")
    print("✓ Schema created")


def seed_fan_truths(cur):
    rows = [
        # Rnorr
        {"brand": "Rnorr", "statement": "That moment when a weeknight dinner smells like it took all day", "category": "Dry Cook-In Sauces", "verdict": "PASS", "specific": 78, "shared": 85, "special": 80, "overall": 81},
        {"brand": "Rnorr", "statement": "Real flavour shouldn't take real time", "category": "Stock Cubes", "verdict": "PASS", "specific": 70, "shared": 88, "special": 72, "overall": 77},
        {"brand": "Rnorr", "statement": "The shortcut that feels like cheating — but isn't", "category": "Stock Pots", "verdict": "PASS", "specific": 82, "shared": 75, "special": 85, "overall": 81},
        {"brand": "Rnorr", "statement": "People like good food", "category": "Generic", "verdict": "FAIL", "specific": 10, "shared": 90, "special": 20, "overall": 40},
        # McDonalds
        {"brand": "McDonalds", "statement": "Friday nights belong to McDonald's", "category": "QSR", "verdict": "PASS", "specific": 72, "shared": 85, "special": 78, "overall": 78},
        {"brand": "McDonalds", "statement": "That heat that hits you mid-bite and makes you close your eyes for a second", "category": "Burgers & Chicken", "verdict": "PASS", "specific": 88, "shared": 70, "special": 90, "overall": 83},
        {"brand": "McDonalds", "statement": "Nostalgia is the most powerful flavour", "category": "QSR", "verdict": "PASS", "specific": 65, "shared": 80, "special": 85, "overall": 77},
    ]

    for r in rows:
        text = f"{r['brand']} fan truth: {r['statement']}"
        r["embedding"] = get_embedding(text)
        print(f"  Embedding: {r['statement'][:50]}...")

    execute_values(cur,
        """INSERT INTO fan_truths
           (brand, statement, category, verdict, specific, shared, special, overall, embedding)
           VALUES %s ON CONFLICT DO NOTHING""",
        [(r["brand"], r["statement"], r["category"], r["verdict"],
          r["specific"], r["shared"], r["special"], r["overall"],
          r["embedding"]) for r in rows]
    )
    print(f"✓ Seeded {len(rows)} fan truths")


def seed_campaign_benchmarks(cur):
    rows = [
        {"brand": "Rnorr", "product_category": "Dry Cook-In Sauces", "market": "UK", "season": "Winter", "channels": ["Instagram", "TikTok"], "reach": 4200000, "ctr_pct": 1.8, "roas": 3.2, "engagement_pct": 4.1, "budget_gbp": 350000, "notes": "Strong performance with recipe-led content on TikTok"},
        {"brand": "Rnorr", "product_category": "Stock Cubes", "market": "UK", "season": "Summer", "channels": ["TikTok", "OOH"], "reach": 3800000, "ctr_pct": 2.1, "roas": 2.8, "engagement_pct": 5.2, "budget_gbp": 250000, "notes": "BBQ season activation — OOH drove 40% of awareness"},
        {"brand": "McDonalds", "product_category": "Burgers & Chicken", "market": "UK", "season": "Summer", "channels": ["Instagram", "TikTok"], "reach": 8500000, "ctr_pct": 2.4, "roas": 4.1, "engagement_pct": 6.8, "budget_gbp": 750000, "notes": "Spicy range launch — UGC drove organic amplification"},
        {"brand": "McDonalds", "product_category": "Value Range", "market": "UK", "season": "All Year", "channels": ["Meta Ads", "Google Ads"], "reach": 12000000, "ctr_pct": 1.9, "roas": 5.2, "engagement_pct": 3.1, "budget_gbp": 1200000, "notes": "Always-on value messaging — strong ROAS from search intent"},
    ]

    for r in rows:
        text = f"{r['brand']} {r['product_category']} {r['market']} {r['season']} campaign"
        r["embedding"] = get_embedding(text)
        print(f"  Embedding: {r['brand']} {r['product_category']} {r['season']}...")

    execute_values(cur,
        """INSERT INTO campaign_benchmarks
           (brand, product_category, market, season, channels, reach, ctr_pct, roas, engagement_pct, budget_gbp, notes, embedding)
           VALUES %s ON CONFLICT DO NOTHING""",
        [(r["brand"], r["product_category"], r["market"], r["season"],
          r["channels"], r["reach"], r["ctr_pct"], r["roas"],
          r["engagement_pct"], r["budget_gbp"], r["notes"], r["embedding"]) for r in rows]
    )
    print(f"✓ Seeded {len(rows)} campaign benchmarks")


def seed_channel_benchmarks(cur):
    rows = [
        {"channel": "Instagram", "market": "UK", "audience_segment": "18-34", "ctr_pct": 1.2, "cpm_gbp": 8.50, "engagement_pct": 4.5, "completion_pct": None, "avg_dwell_sec": None, "notes": "Feed images + Reels. Best for visual product shots. Peak: Thu-Sun 18:00-22:00"},
        {"channel": "TikTok", "market": "UK", "audience_segment": "18-34", "ctr_pct": 2.1, "cpm_gbp": 6.20, "engagement_pct": 8.3, "completion_pct": 62.0, "avg_dwell_sec": None, "notes": "Native UGC style drives 3x engagement. Authentic > polished"},
        {"channel": "OOH", "market": "UK", "audience_segment": "All", "ctr_pct": None, "cpm_gbp": 12.00, "engagement_pct": None, "completion_pct": None, "avg_dwell_sec": 2.5, "notes": "3-second rule. Logo + hero + headline only. Pre-approved crops required"},
        {"channel": "Meta Ads", "market": "UK", "audience_segment": "25-44", "ctr_pct": 1.8, "cpm_gbp": 9.80, "engagement_pct": 3.2, "completion_pct": 55.0, "avg_dwell_sec": None, "notes": "Carousel drives 40% more clicks than single image"},
        {"channel": "Google Ads", "market": "UK", "audience_segment": "All", "ctr_pct": 3.2, "cpm_gbp": 4.50, "engagement_pct": None, "completion_pct": None, "avg_dwell_sec": None, "notes": "Search intent = highest purchase intent. Use exact match for branded terms"},
        {"channel": "YouTube", "market": "UK", "audience_segment": "18-44", "ctr_pct": 0.8, "cpm_gbp": 7.20, "engagement_pct": 2.1, "completion_pct": 45.0, "avg_dwell_sec": None, "notes": "Pre-roll: hook in first 5s. 15s skippable recommended for awareness"},
    ]

    for r in rows:
        text = f"{r['channel']} {r['market']} {r['audience_segment']} benchmark performance"
        r["embedding"] = get_embedding(text)
        print(f"  Embedding: {r['channel']} {r['market']}...")

    execute_values(cur,
        """INSERT INTO channel_benchmarks
           (channel, market, audience_segment, ctr_pct, cpm_gbp, engagement_pct, completion_pct, avg_dwell_sec, notes, embedding)
           VALUES %s ON CONFLICT DO NOTHING""",
        [(r["channel"], r["market"], r["audience_segment"], r["ctr_pct"],
          r["cpm_gbp"], r["engagement_pct"], r["completion_pct"],
          r["avg_dwell_sec"], r["notes"], r["embedding"]) for r in rows]
    )
    print(f"✓ Seeded {len(rows)} channel benchmarks")


def seed_customer_segments(cur):
    """
    Seed customer segments derived from the Kaggle Customer Personality Analysis dataset.
    Columns: ID, Year_Birth, Education, Marital_Status, Income, Kidhome, Teenhome,
             MntWines, MntMeatProducts, MntFishProducts, MntSweetProducts, MntGoldProds,
             NumDealsPurchases, NumWebPurchases, NumStorePurchases, NumWebVisitsMonth,
             AcceptedCmp1-5, Response, Recency, Complain

    Segments are derived by clustering the Kaggle data into behavioural archetypes.
    Each segment includes CRM-style notes generated from the quantitative signals.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_segments (
            id                    SERIAL PRIMARY KEY,
            brand                 TEXT NOT NULL,
            segment_name          TEXT NOT NULL,
            size_estimate         INT,
            age_range             TEXT,
            income_band           TEXT,
            top_channels          TEXT[],
            avg_weekly_spend_gbp  NUMERIC(8,2),
            behavioural_notes     TEXT,
            fan_truth_benchmark   TEXT,
            kaggle_derivation     TEXT,
            embedding             vector(384)
        );
        CREATE INDEX IF NOT EXISTS seg_emb_idx ON customer_segments
            USING hnsw (embedding vector_cosine_ops);
    """)

    rows = [
        # ── RNORR segments (derived from Kaggle MntMeatProducts, MntFishProducts, Income) ──
        {
            "brand": "Rnorr",
            "segment_name": "Home Cook Enthusiasts",
            "size_estimate": 420000,
            "age_range": "25-44",
            "income_band": "£35k-£65k",
            "top_channels": ["Instagram", "YouTube", "Pinterest"],
            "avg_weekly_spend_gbp": 18.50,
            "behavioural_notes": (
                "High MntMeatProducts (£400+/yr) and MntFishProducts signals active home cooks. "
                "NumStorePurchases > NumWebPurchases — prefers in-store browsing. "
                "Low NumDealsPurchases — not price-driven, values quality and convenience. "
                "Recipe content performs 3× better than product-led content for this segment. "
                "Peak engagement: weekday evenings 18:00-20:00, planning the next day's dinner."
            ),
            "fan_truth_benchmark": "Fan Truth must score Specific > 70. This segment responds to precise, named moments — not generic cooking sentiment. 'That moment when a weeknight dinner smells like it took all day' scores 78/100 with this group.",
            "kaggle_derivation": "Income 35k-65k, MntMeatProducts > 200, NumStorePurchases > 6, Kidhome 0-1",
        },
        {
            "brand": "Rnorr",
            "segment_name": "Budget Family Cooks",
            "size_estimate": 680000,
            "age_range": "28-40",
            "income_band": "£20k-£40k",
            "top_channels": ["Facebook", "TikTok", "OOH"],
            "avg_weekly_spend_gbp": 9.20,
            "behavioural_notes": (
                "Kidhome > 0, high NumDealsPurchases (>5) — systematically deal-seeking. "
                "MntMeatProducts moderate (£150-250/yr) — buys in bulk when on offer. "
                "Highly responsive to value messaging and bundle promotions. "
                "Time-poor: seeks shortcuts that feel 'proper' not lazy. "
                "Facebook Groups (recipe sharing) drives discovery; TikTok for quick meal ideas."
            ),
            "fan_truth_benchmark": "Fan Truth must score Shared > 80 — this segment only engages with widely-held truths. 'Real flavour shouldn't take real time' scores 88/100. Avoid aspirational or premium-coded language.",
            "kaggle_derivation": "Income < 40k, Kidhome > 0, NumDealsPurchases > 5, MntMeatProducts 150-250",
        },
        {
            "brand": "Rnorr",
            "segment_name": "Premium Home Entertainers",
            "size_estimate": 195000,
            "age_range": "35-55",
            "income_band": "£65k+",
            "top_channels": ["Instagram", "Pinterest", "YouTube"],
            "avg_weekly_spend_gbp": 34.00,
            "behavioural_notes": (
                "High Income + high MntWines (£500+/yr) + high MntMeatProducts. "
                "Kidhome = 0, Marital_Status = Together/Married. "
                "NumCatalogPurchases highest of all segments — responds to curated, editorial presentation. "
                "Buys premium ingredients to impress guests; Rnorr is the 'insider secret' not the shortcut. "
                "Endorsement by chefs or food editors drives consideration more than discount."
            ),
            "fan_truth_benchmark": "Fan Truth must score Special > 80 — this segment wants to feel like insiders. 'The shortcut that feels like cheating — but isn't' scores 85/100. Avoid positioning as budget or convenience.",
            "kaggle_derivation": "Income > 65k, MntWines > 500, MntMeatProducts > 300, Kidhome = 0",
        },
        {
            "brand": "Rnorr",
            "segment_name": "Student Budget Cooks",
            "size_estimate": 310000,
            "age_range": "18-25",
            "income_band": "Under £20k",
            "top_channels": ["TikTok", "Instagram", "YouTube"],
            "avg_weekly_spend_gbp": 5.80,
            "behavioural_notes": (
                "Low Income, NumWebVisitsMonth highest of all segments (>7/month). "
                "NumDealsPurchases very high — coupon and promotional driven. "
                "MntMeatProducts low (£50-100/yr) — buys stock cubes as flavour booster for cheap proteins. "
                "TikTok recipe challenges drive trial; peer validation critical for brand adoption. "
                "Price sensitivity: £1-£2 per meal target. Stock cubes as 'life hack' framing resonates."
            ),
            "fan_truth_benchmark": "Fan Truth must score Specific > 65 and use student-recognisable language. 'Home-cooked meals on a budget' framing scores 72/100. Avoid aspirational or premium tone.",
            "kaggle_derivation": "Income < 20k, NumWebVisitsMonth > 7, NumDealsPurchases > 6, MntMeatProducts < 100",
        },

        # ── McDONALDS segments ──
        {
            "brand": "McDonalds",
            "segment_name": "Gen Z Digital Natives",
            "size_estimate": 2400000,
            "age_range": "16-24",
            "income_band": "Under £25k",
            "top_channels": ["TikTok", "Instagram", "Snapchat"],
            "avg_weekly_spend_gbp": 12.50,
            "behavioural_notes": (
                "NumWebVisitsMonth highest segment (8+/month). High NumWebPurchases. "
                "AcceptedCmp promotions on limited-edition / FOMO items. "
                "McDonald's as social currency — shares meals, challenges, reactions on TikTok. "
                "Peak visits: Fri-Sat 21:00-01:00 (late-night). Delivery and app orders dominate. "
                "Spicy products index 2.8× higher with this segment vs. average."
            ),
            "fan_truth_benchmark": "Fan Truth must score Specific > 72. 'Friday nights belong to McDonald's' scores 78/100. Needs a NAMED MOMENT — not generic enjoyment. Social ritual framing outperforms product taste framing.",
            "kaggle_derivation": "Age < 25, NumWebVisitsMonth > 7, Income < 25k, AcceptedCmp3 or AcceptedCmp5 high",
        },
        {
            "brand": "McDonalds",
            "segment_name": "Family Value Seekers",
            "size_estimate": 3100000,
            "age_range": "28-42",
            "income_band": "£25k-£50k",
            "top_channels": ["Facebook", "Instagram", "OOH"],
            "avg_weekly_spend_gbp": 22.00,
            "behavioural_notes": (
                "Kidhome > 0, NumDealsPurchases high — Happy Meal and combo deal-driven. "
                "Recency low — frequent visitors (every 1-2 weeks). "
                "Primary decision driver: children's preference + value. "
                "Saturday lunchtime peak. Drive-thru dominant channel. "
                "Responds to family occasion messaging and limited-time promotions."
            ),
            "fan_truth_benchmark": "Fan Truth must score Shared > 82 — must resonate across the whole family unit. 'McDonald's is the reward after a long week' scores 80/100 for this segment.",
            "kaggle_derivation": "Kidhome > 0, Income 25k-50k, NumDealsPurchases > 4, Recency < 20",
        },
        {
            "brand": "McDonalds",
            "segment_name": "Lapsed Premium Customers",
            "size_estimate": 890000,
            "age_range": "30-50",
            "income_band": "£50k+",
            "top_channels": ["Instagram", "Google Ads", "OOH"],
            "avg_weekly_spend_gbp": 8.00,
            "behavioural_notes": (
                "High Income but low Recency (>30 days) — churned or infrequent. "
                "Complain = 1 or AcceptedCmp = 0 on recent campaigns — disengaged. "
                "High MntWines elsewhere — sophisticated palate, sees McDonald's as treat not staple. "
                "Re-engagement requires quality/provenance narrative — sourcing, freshness, craft. "
                "Most responsive to premium product launches (McSpicy, Signature range)."
            ),
            "fan_truth_benchmark": "Fan Truth must score Special > 78. Nostalgia angle scores 77/100 for re-engagement. Avoid value/deal messaging — it alienates this segment.",
            "kaggle_derivation": "Income > 50k, Recency > 30, Complain = 1 or AcceptedCmp1-5 all 0",
        },
    ]

    for r in rows:
        text = (
            f"{r['brand']} {r['segment_name']} {r['age_range']} "
            f"{r['income_band']} {r['behavioural_notes'][:200]}"
        )
        r["embedding"] = get_embedding(text)
        print(f"  Embedding: {r['brand']} — {r['segment_name']}...")

    execute_values(cur,
        """INSERT INTO customer_segments
           (brand, segment_name, size_estimate, age_range, income_band,
            top_channels, avg_weekly_spend_gbp, behavioural_notes,
            fan_truth_benchmark, kaggle_derivation, embedding)
           VALUES %s ON CONFLICT DO NOTHING""",
        [(r["brand"], r["segment_name"], r["size_estimate"], r["age_range"],
          r["income_band"], r["top_channels"], r["avg_weekly_spend_gbp"],
          r["behavioural_notes"], r["fan_truth_benchmark"],
          r["kaggle_derivation"], r["embedding"]) for r in rows]
    )
    print(f"✓ Seeded {len(rows)} customer segments (Kaggle Customer Personality Analysis)")


if __name__ == "__main__":
    print(f"=== Setting up pgvector at {PG_HOST}:{PG_PORT} ===\n")
    print("Installing sentence-transformers if needed...")

    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()

    print("\n1. Creating schema...")
    setup_schema(cur)

    print("\n2. Seeding Fan Truths...")
    seed_fan_truths(cur)

    print("\n3. Seeding Campaign Benchmarks...")
    seed_campaign_benchmarks(cur)

    print("\n4. Seeding Channel Benchmarks...")
    seed_channel_benchmarks(cur)

    print("\n5. Seeding Customer Segments (Kaggle Customer Personality Analysis)...")
    seed_customer_segments(cur)

    conn.commit()
    cur.close()
    conn.close()

    print("""
=== Done ===
Add to harness/.env:
  PGVECTOR_HOST=localhost
  PGVECTOR_PORT=5432
  PGVECTOR_USER=campaignos
  PGVECTOR_PASSWORD=campaignos
  PGVECTOR_DB=marketing
  SEARCH_MODE=pgvector   ← uses pgvector instead of stubs or Vertex AI Search
""")
