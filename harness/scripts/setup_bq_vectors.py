"""
setup_bq_vectors.py — Create BigQuery tables with embedding columns and seed all benchmark data.

Run this ONCE (or to rebuild) to set up the BigQuery vector search tables used by
bq_vector_client.py when SEARCH_MODE=bigquery.

What it does:
  1. Creates (or recreates) 5 tables in the `briefing_agent` dataset:
       fan_truth_library       — fan truths + Gemini embeddings
       historical_campaigns    — campaign benchmarks + embeddings
       channel_benchmarks      — per-channel benchmarks + embeddings
       customer_segments       — synthetic audience profiles + embeddings
       brand_guidelines_chunks — chunked brand guidelines + embeddings
  2. Generates Gemini text-embedding-004 embeddings (768 dims) for every row.
  3. Creates BigQuery vector indexes for ANN search (effective at 5K+ rows).

Usage:
  cd d:\\campaignos\\harness
  uv run python scripts/setup_bq_vectors.py

  # Skip embedding re-generation for tables that already exist:
  uv run python scripts/setup_bq_vectors.py --skip-existing

Requires:
  - GOOGLE_CLOUD_PROJECT (or GCP_PROJECT) set in settings / environment
  - GOOGLE_API_KEY for Gemini embedding API
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Load .env so API keys and project ID are available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
except ImportError:
    pass

from google.cloud import bigquery

# ── Config ──────────────────────────────────────────────────────────────────────
GCP_PROJECT      = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT", "")
DATASET          = os.getenv("BQ_DATASET", "briefing_agent")
BQ_LOCATION      = "US"
EMBEDDING_MODEL  = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIM    = 768


def _embed(text: str, max_retries: int = 8) -> list[float]:
    import re
    import google.genai as genai
    api_key = os.getenv("GOOGLE_API_KEY", "")
    client  = genai.Client(api_key=api_key if api_key else None, vertexai=False)

    for attempt in range(max_retries):
        try:
            result = client.models.embed_content(
                model    = EMBEDDING_MODEL,
                contents = text,
                config   = {"task_type": "RETRIEVAL_DOCUMENT", "output_dimensionality": EMBEDDING_DIM},
            )
            return list(result.embeddings[0].values)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                # Parse suggested retry delay from error message
                m = re.search(r"retry in (\d+(?:\.\d+)?)s", err)
                wait = float(m.group(1)) + 2 if m else min(10 * (attempt + 1), 60)
                print(f"  Rate-limited (attempt {attempt + 1}/{max_retries}) — waiting {wait:.0f}s...")
                time.sleep(wait)
            else:
                print(f"  WARNING: embedding failed ({e}) — using zero vector")
                return [0.0] * EMBEDDING_DIM

    print("  WARNING: quota exhausted after retries — using zero vector")
    return [0.0] * EMBEDDING_DIM


def _client() -> bigquery.Client:
    return bigquery.Client(project=GCP_PROJECT)


def _full(table: str) -> str:
    return f"{GCP_PROJECT}.{DATASET}.{table}"


# ── Table creation ───────────────────────────────────────────────────────────────

def _create_table(bq: bigquery.Client, table_id: str, schema: list[bigquery.SchemaField]) -> None:
    table_ref = bq.dataset(DATASET).table(table_id)
    table     = bigquery.Table(table_ref, schema=schema)
    bq.create_table(table, exists_ok=True)
    print(f"  Table ready: {_full(table_id)}")


def _drop_create_table(bq: bigquery.Client, table_id: str, schema: list[bigquery.SchemaField]) -> None:
    """Drop and recreate a table to ensure the embedding column is present."""
    table_ref = bq.dataset(DATASET).table(table_id)
    bq.delete_table(table_ref, not_found_ok=True)
    table = bigquery.Table(table_ref, schema=schema)
    bq.create_table(table)
    print(f"  Table (re)created: {_full(table_id)}")


def _create_vector_index(bq: bigquery.Client, table_id: str, column: str = "embedding") -> None:
    idx_name = f"idx_{table_id}_emb"
    try:
        bq.query(f"""
            CREATE VECTOR INDEX IF NOT EXISTS `{idx_name}`
            ON `{_full(table_id)}`({column})
            OPTIONS (distance_type='COSINE', index_type='IVF')
        """).result()
        print(f"  Vector index ready: {idx_name}")
    except Exception as e:
        # Indexes fail silently on small tables (< 5K rows) — that is fine;
        # VECTOR_SEARCH falls back to a full scan automatically.
        print(f"  Vector index skipped (will use full scan on small table): {e}")


# ── Fan truth library ────────────────────────────────────────────────────────────

FAN_TRUTH_SCHEMA = [
    bigquery.SchemaField("brand",     "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("statement", "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("category",  "STRING"),
    bigquery.SchemaField("verdict",   "STRING"),
    bigquery.SchemaField("specific",  "INTEGER"),
    bigquery.SchemaField("shared",    "INTEGER"),
    bigquery.SchemaField("special",   "INTEGER"),
    bigquery.SchemaField("overall",   "INTEGER"),
    bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
]

FAN_TRUTHS = [
    {"brand": "Rnorr",      "statement": "That moment when a weeknight dinner smells like it took all day",            "category": "Dry Cook-In Sauces", "verdict": "PASS", "specific": 78, "shared": 85, "special": 80, "overall": 81},
    {"brand": "Rnorr",      "statement": "Real flavour shouldn't take real time",                                       "category": "Stock Cubes",        "verdict": "PASS", "specific": 70, "shared": 88, "special": 72, "overall": 77},
    {"brand": "Rnorr",      "statement": "The shortcut that feels like cheating - but isn't",                          "category": "Stock Pots",         "verdict": "PASS", "specific": 82, "shared": 75, "special": 85, "overall": 81},
    {"brand": "Rnorr",      "statement": "People like good food",                                                      "category": "Generic",            "verdict": "FAIL", "specific": 10, "shared": 90, "special": 20, "overall": 40},
    {"brand": "McDonalds",  "statement": "Friday nights belong to McDonald's",                                         "category": "QSR",                "verdict": "PASS", "specific": 72, "shared": 85, "special": 78, "overall": 78},
    {"brand": "McDonalds",  "statement": "That heat that hits you mid-bite and makes you close your eyes for a second","category": "Burgers & Chicken",  "verdict": "PASS", "specific": 88, "shared": 70, "special": 90, "overall": 83},
    {"brand": "McDonalds",  "statement": "Nostalgia is the most powerful flavour",                                     "category": "QSR",                "verdict": "PASS", "specific": 65, "shared": 80, "special": 85, "overall": 77},
    {"brand": "Boozt",      "statement": "That first sip when you need to switch on - that's a Boozt moment",          "category": "Energy Drinks",      "verdict": "PASS", "specific": 82, "shared": 74, "special": 79, "overall": 78},
    {"brand": "Boozt",      "statement": "Peak performance isn't a personality - it's a decision you make every day",  "category": "Energy Drinks",      "verdict": "PASS", "specific": 76, "shared": 80, "special": 83, "overall": 80},
    {"brand": "Boozt",      "statement": "The can that turns 'I can't' into 'watch me'",                               "category": "Energy Drinks",      "verdict": "PASS", "specific": 85, "shared": 70, "special": 88, "overall": 81},
    {"brand": "Boozt",      "statement": "Zero limits. Pure energy. One can.",                                         "category": "Energy Drinks",      "verdict": "PASS", "specific": 72, "shared": 76, "special": 80, "overall": 76},
    {"brand": "Boozt",      "statement": "I just need energy",                                                         "category": "Generic",            "verdict": "FAIL", "specific": 15, "shared": 82, "special": 18, "overall": 38},
    {"brand": "Sunglow",    "statement": "The first look in the mirror after wash day - that's your glow",             "category": "Hair Care",          "verdict": "PASS", "specific": 84, "shared": 72, "special": 80, "overall": 79},
    {"brand": "Sunglow",    "statement": "Your crown is not a problem to manage, it's a conversation to have",         "category": "Hair Care",          "verdict": "PASS", "specific": 78, "shared": 76, "special": 88, "overall": 81},
    {"brand": "Sunglow",    "statement": "Good hair day isn't luck - it's science built for you from the start",       "category": "Hair Care",          "verdict": "PASS", "specific": 80, "shared": 74, "special": 75, "overall": 76},
    {"brand": "Sunglow",    "statement": "My hair looks nice",                                                         "category": "Generic",            "verdict": "FAIL", "specific": 12, "shared": 85, "special": 14, "overall": 37},
    {"brand": "Glenfiddich","statement": "The first sip of a whisky that's older than most of your friendships",       "category": "Single Malt Scotch", "verdict": "PASS", "specific": 86, "shared": 74, "special": 85, "overall": 82},
    {"brand": "Glenfiddich","statement": "Good whisky doesn't rush you - and neither should the best moments",         "category": "Premium Spirits",    "verdict": "PASS", "specific": 80, "shared": 82, "special": 78, "overall": 80},
    {"brand": "Glenfiddich","statement": "Some bottles are too good to open - until the moment is finally right",      "category": "Single Malt Scotch", "verdict": "PASS", "specific": 83, "shared": 76, "special": 88, "overall": 82},
    {"brand": "Glenfiddich","statement": "When you gift a Glenfiddich, you're not giving a bottle - you're giving thought", "category": "Gifting",     "verdict": "PASS", "specific": 78, "shared": 80, "special": 90, "overall": 83},
    {"brand": "Glenfiddich","statement": "136 years of one family making one whisky in one valley",                    "category": "Heritage",           "verdict": "PASS", "specific": 88, "shared": 70, "special": 92, "overall": 83},
    {"brand": "Glenfiddich","statement": "People enjoy whisky",                                                        "category": "Generic",            "verdict": "FAIL", "specific":  8, "shared": 88, "special": 10, "overall": 35},
    {"brand": "sunrise",    "statement": "That moment when the call holds and the signal doesn't drop",                "category": "Mobile & Connectivity","verdict": "PASS","specific": 82, "shared": 78, "special": 76, "overall": 79},
    {"brand": "sunrise",    "statement": "Technology disappears when it works perfectly - and that silence is Sunrise","category": "Digital Services",   "verdict": "PASS", "specific": 80, "shared": 74, "special": 84, "overall": 79},
    {"brand": "sunrise",    "statement": "The pause before you press call - you know it'll connect, because it always does", "category": "Mobile & Connectivity","verdict":"PASS","specific": 76,"shared": 82,"special": 78,"overall": 79},
    {"brand": "sunrise",    "statement": "Staying connected isn't a luxury - it's the quiet infrastructure of every good day", "category": "Digital Services","verdict":"PASS","specific": 78,"shared": 80,"special": 72,"overall": 77},

    # Haleon — Consumer Healthcare (Sensodyne, Voltaren, Panadol, Centrum)
    {"brand": "Haleon", "statement": "That wince when you bite into something cold and know your teeth are telling you something", "category": "Oral Health",        "verdict": "PASS", "specific": 86, "shared": 82, "special": 78, "overall": 82},
    {"brand": "Haleon", "statement": "The moment pain stops being background noise and starts taking over the day",               "category": "Pain Relief",         "verdict": "PASS", "specific": 82, "shared": 85, "special": 76, "overall": 81},
    {"brand": "Haleon", "statement": "You don't think about your health until it's the only thing you can think about",         "category": "Consumer Healthcare",  "verdict": "PASS", "specific": 78, "shared": 88, "special": 80, "overall": 82},
    {"brand": "Haleon", "statement": "Taking a vitamin feels like a promise you make to the future version of yourself",        "category": "Vitamins & Supplements","verdict": "PASS", "specific": 80, "shared": 76, "special": 84, "overall": 80},
    {"brand": "Haleon", "statement": "When the joint ache stops, you remember what moving freely actually felt like",           "category": "Pain Relief",         "verdict": "PASS", "specific": 84, "shared": 78, "special": 82, "overall": 81},
    {"brand": "Haleon", "statement": "Healthcare is fine",                                                                      "category": "Generic",             "verdict": "FAIL", "specific":  9, "shared": 85, "special": 12, "overall": 35},

    # Barclays — UK Banking & Financial Services
    {"brand": "Barclays", "statement": "The moment your mortgage is approved and the house finally feels like it could be yours", "category": "Mortgages & Home",   "verdict": "PASS", "specific": 88, "shared": 80, "special": 84, "overall": 84},
    {"brand": "Barclays", "statement": "Watching your savings grow month by month — proof that small decisions compound",        "category": "Savings & Investment","verdict": "PASS", "specific": 82, "shared": 76, "special": 80, "overall": 79},
    {"brand": "Barclays", "statement": "The quiet confidence of knowing your bank understands your business, not just your balance", "category": "Business Banking","verdict": "PASS", "specific": 80, "shared": 74, "special": 86, "overall": 80},
    {"brand": "Barclays", "statement": "Money anxiety doesn't disappear when you earn more — it just changes shape",            "category": "Personal Finance",    "verdict": "PASS", "specific": 84, "shared": 82, "special": 78, "overall": 81},
    {"brand": "Barclays", "statement": "We offer banking services",                                                             "category": "Generic",             "verdict": "FAIL", "specific":  7, "shared": 88, "special":  9, "overall": 35},

    # Infosys — Global IT Services & Consulting (Navigate your next.)
    {"brand": "Infosys", "statement": "The moment a client realises the transformation they feared is the one that saves them", "category": "Digital Transformation","verdict": "PASS", "specific": 84, "shared": 76, "special": 86, "overall": 82},
    {"brand": "Infosys", "statement": "The organisations that navigate uncertainty fastest aren't lucky — they're better wired", "category": "Technology Consulting", "verdict": "PASS", "specific": 80, "shared": 78, "special": 84, "overall": 81},
    {"brand": "Infosys", "statement": "AI doesn't replace strategy — it amplifies the quality of the people who set it",        "category": "AI & Automation",      "verdict": "PASS", "specific": 82, "shared": 74, "special": 88, "overall": 81},
    {"brand": "Infosys", "statement": "The CIO who chose the right partner five years ago is still ahead of the one who chose the cheapest", "category": "Enterprise IT",  "verdict": "PASS", "specific": 86, "shared": 70, "special": 90, "overall": 82},
    {"brand": "Infosys", "statement": "We provide IT services",                                                                "category": "Generic",               "verdict": "FAIL", "specific":  6, "shared": 85, "special":  8, "overall": 33},
]


def seed_fan_truths(bq: bigquery.Client) -> None:
    print("\nSeeding fan_truth_library...")
    _drop_create_table(bq, "fan_truth_library", FAN_TRUTH_SCHEMA)
    rows = []
    for r in FAN_TRUTHS:
        text = f"{r['brand']} fan truth: {r['statement']}"
        emb  = _embed(text)
        print(f"  Embedded: {r['statement'][:60]}...")
        rows.append({**r, "embedding": emb})
    errors = bq.insert_rows_json(_full("fan_truth_library"), rows)
    if errors:
        print(f"  Insert errors: {errors}")
    else:
        print(f"  Inserted {len(rows)} fan truths")
    _create_vector_index(bq, "fan_truth_library")


# ── Campaign benchmarks ──────────────────────────────────────────────────────────

CAMPAIGN_SCHEMA = [
    bigquery.SchemaField("brand",            "STRING"),
    bigquery.SchemaField("product_category", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("market",           "STRING"),
    bigquery.SchemaField("season",           "STRING"),
    bigquery.SchemaField("channels",         "STRING", mode="REPEATED"),
    bigquery.SchemaField("reach",            "INTEGER"),
    bigquery.SchemaField("ctr_pct",          "FLOAT64"),
    bigquery.SchemaField("roas",             "FLOAT64"),
    bigquery.SchemaField("engagement_pct",   "FLOAT64"),
    bigquery.SchemaField("budget_gbp",       "FLOAT64"),
    bigquery.SchemaField("notes",            "STRING"),
    bigquery.SchemaField("embedding",        "FLOAT64", mode="REPEATED"),
]

CAMPAIGN_BENCHMARKS = [
    {"brand": "Rnorr",      "product_category": "Dry Cook-In Sauces",          "market": "UK",          "season": "Winter",   "channels": ["Instagram","TikTok"],               "reach": 4200000, "ctr_pct": 1.8, "roas": 3.2, "engagement_pct": 4.1, "budget_gbp": 350000, "notes": "Strong performance with recipe-led content on TikTok"},
    {"brand": "Rnorr",      "product_category": "Stock Cubes",                  "market": "UK",          "season": "Summer",   "channels": ["TikTok","OOH"],                      "reach": 3800000, "ctr_pct": 2.1, "roas": 2.8, "engagement_pct": 5.2, "budget_gbp": 250000, "notes": "BBQ season activation - OOH drove 40% of awareness"},
    {"brand": "McDonalds",  "product_category": "Burgers & Chicken",            "market": "UK",          "season": "Summer",   "channels": ["Instagram","TikTok"],               "reach": 8500000, "ctr_pct": 2.4, "roas": 4.1, "engagement_pct": 6.8, "budget_gbp": 750000, "notes": "Spicy range launch - UGC drove organic amplification"},
    {"brand": "McDonalds",  "product_category": "Value Range",                  "market": "UK",          "season": "All Year", "channels": ["Meta Ads","Google Ads"],             "reach":12000000, "ctr_pct": 1.9, "roas": 5.2, "engagement_pct": 3.1, "budget_gbp":1200000, "notes": "Always-on value messaging - strong ROAS from search intent"},
    {"brand": "Boozt",      "product_category": "Energy Drinks",                "market": "UK",          "season": "Summer",   "channels": ["Instagram","TikTok","OOH"],          "reach": 5000000, "ctr_pct": 2.5, "roas": 3.0, "engagement_pct": 5.8, "budget_gbp": 400000, "notes": "Festival season activation - UGC athletes and gym-goers drove TikTok reach"},
    {"brand": "Boozt",      "product_category": "Energy Drinks",                "market": "UK",          "season": "All Year", "channels": ["TikTok","YouTube","Meta Ads"],       "reach": 4200000, "ctr_pct": 2.8, "roas": 2.6, "engagement_pct": 6.4, "budget_gbp": 300000, "notes": "Always-on gaming and sport audience targeting - YouTube pre-roll strong for awareness"},
    {"brand": "Sunglow",    "product_category": "Hair Care - Scalp Oil",        "market": "UK",          "season": "Spring",   "channels": ["Instagram","TikTok"],               "reach": 3200000, "ctr_pct": 2.2, "roas": 2.9, "engagement_pct": 6.1, "budget_gbp": 220000, "notes": "Launch campaign for Black hair scalp oil - TikTok tutorials and wash-day content drove 68% of reach"},
    {"brand": "Sunglow",    "product_category": "Hair Care",                    "market": "UK",          "season": "Summer",   "channels": ["Instagram","TikTok","Meta Ads"],     "reach": 2800000, "ctr_pct": 2.6, "roas": 3.1, "engagement_pct": 7.2, "budget_gbp": 180000, "notes": "Summer glow campaign - user testimonial content outperformed brand content 3:1 on TikTok"},
    {"brand": "Glenfiddich","product_category": "Single Malt Scotch Whisky",    "market": "UK",          "season": "Christmas","channels": ["OOH","Instagram","YouTube"],          "reach": 6800000, "ctr_pct": 1.4, "roas": 4.2, "engagement_pct": 3.8, "budget_gbp": 680000, "notes": "Christmas gifting campaign - OOH in airports and premium retail drove 55% of awareness. Heritage storytelling outperformed product-led content 2:1"},
    {"brand": "Glenfiddich","product_category": "Single Malt Scotch Whisky",    "market": "UK",          "season": "All Year", "channels": ["Instagram","YouTube","Meta Ads"],    "reach": 4200000, "ctr_pct": 1.8, "roas": 3.6, "engagement_pct": 4.5, "budget_gbp": 320000, "notes": "Always-on premium spirits awareness - YouTube whisky education content drove highest dwell time and purchase intent"},
    {"brand": "sunrise",    "product_category": "Mobile Subscriptions",         "market": "Switzerland", "season": "All Year", "channels": ["Instagram","Facebook","Website"],    "reach": 2800000, "ctr_pct": 2.1, "roas": 3.4, "engagement_pct": 4.2, "budget_gbp": 420000, "notes": "Always-on consumer mobile - human lifestyle imagery outperformed tech-led creative 2:1. de-CH copy outperformed en-Global by 38% CTR"},
    {"brand": "sunrise",    "product_category": "Home Internet & TV",           "market": "Switzerland", "season": "Winter",   "channels": ["Instagram","YouTube","Email"],       "reach": 1900000, "ctr_pct": 1.8, "roas": 4.1, "engagement_pct": 3.6, "budget_gbp": 310000, "notes": "Winter home connectivity push - warm family moments in Swiss homes drove 62% of conversions"},
    {"brand": "sunrise",    "product_category": "Business Connectivity",        "market": "Switzerland", "season": "Spring",   "channels": ["LinkedIn","Google Ads","Email"],     "reach":  480000, "ctr_pct": 2.6, "roas": 5.2, "engagement_pct": 3.1, "budget_gbp": 180000, "notes": "B2B SME campaign - outcome-first messaging outperformed feature-led. LinkedIn drove 70% of qualified leads"},

    # Haleon — Consumer Healthcare
    {"brand": "Haleon", "product_category": "Sensodyne Toothpaste",        "market": "UK", "season": "All Year", "channels": ["TV","YouTube","Instagram"],           "reach": 9200000, "ctr_pct": 1.6, "roas": 3.8, "engagement_pct": 3.2, "budget_gbp": 820000, "notes": "Always-on oral care — dentist endorsement creative drove 2.4x purchase intent vs lifestyle imagery. YouTube 30s drove highest brand recall"},
    {"brand": "Haleon", "product_category": "Voltaren Pain Relief",        "market": "UK", "season": "Winter",   "channels": ["TV","Meta Ads","OOH"],                "reach": 7400000, "ctr_pct": 1.4, "roas": 4.1, "engagement_pct": 2.8, "budget_gbp": 640000, "notes": "Winter joint pain activation — functional proof messaging (show the pain, show the relief) outperformed emotional storytelling 2:1 for this category"},
    {"brand": "Haleon", "product_category": "Centrum Vitamins",            "market": "UK", "season": "January",  "channels": ["Instagram","Google Ads","YouTube"],   "reach": 5100000, "ctr_pct": 2.2, "roas": 3.2, "engagement_pct": 4.6, "budget_gbp": 390000, "notes": "New Year health reset activation — aspirational wellness content drove 58% of conversions. Search intent spikes 340% in January for vitamins"},
    {"brand": "Haleon", "product_category": "Panadol Pain Relief",        "market": "UK", "season": "All Year", "channels": ["TV","Meta Ads","Pharmacy OOH"],       "reach": 8600000, "ctr_pct": 1.2, "roas": 4.5, "engagement_pct": 2.4, "budget_gbp": 750000, "notes": "Always-on pain category — fast-acting efficacy proof is table stakes. Pharmacy-adjacent OOH drives point-of-purchase conversion"},

    # Barclays — UK Banking & Financial Services
    {"brand": "Barclays", "product_category": "Mortgages",                "market": "UK", "season": "Spring",   "channels": ["TV","Google Ads","Meta Ads"],         "reach": 6800000, "ctr_pct": 1.8, "roas": 5.4, "engagement_pct": 2.6, "budget_gbp": 720000, "notes": "Spring homebuying season — emotional 'home as a dream' creative outperformed rate-comparison ads 3:1. Google search drove 62% of qualified applications"},
    {"brand": "Barclays", "product_category": "Business Banking",         "market": "UK", "season": "All Year", "channels": ["LinkedIn","Google Ads","Email"],      "reach": 1200000, "ctr_pct": 2.8, "roas": 6.2, "engagement_pct": 3.4, "budget_gbp": 380000, "notes": "SME business banking — outcome-first messaging (grow faster, bank smarter) outperformed product feature ads. LinkedIn drove 74% of qualified SME leads"},
    {"brand": "Barclays", "product_category": "Personal Current Account", "market": "UK", "season": "All Year", "channels": ["TV","Instagram","OOH"],               "reach":11400000, "ctr_pct": 1.1, "roas": 2.8, "engagement_pct": 2.2, "budget_gbp":1100000, "notes": "Brand awareness — 'This is Barclays' campaign. OOH and TV drive brand salience; digital retargeting closes. Younger audience (18-30) responds to digital-first, app-led messaging"},

    # Infosys — Global IT Services & Consulting
    {"brand": "Infosys", "product_category": "Digital Transformation Services", "market": "Global", "season": "All Year", "channels": ["LinkedIn","YouTube","Google Ads"],   "reach": 3200000, "ctr_pct": 1.4, "roas": 8.2, "engagement_pct": 2.8, "budget_gbp": 2400000, "notes": "Thought leadership campaign — 'Navigate your next.' Long-form YouTube content and LinkedIn articles drove highest qualified C-suite engagement. ROI measured in pipeline, not click-through"},
    {"brand": "Infosys", "product_category": "AI & Automation (Infosys Topaz)", "market": "Global", "season": "All Year", "channels": ["LinkedIn","Programmatic","Events"],  "reach": 1800000, "ctr_pct": 1.8, "roas": 9.4, "engagement_pct": 3.6, "budget_gbp": 1800000, "notes": "Infosys Topaz AI launch — decision-maker targeting on LinkedIn drove 74% of pipeline. Executive roundtable events + digital amplification outperformed pure digital by 3x on qualified leads"},
    {"brand": "Infosys", "product_category": "Cloud Services",                  "market": "US",     "season": "Spring",   "channels": ["LinkedIn","Google Ads","Webinars"],   "reach":  980000, "ctr_pct": 2.1, "roas": 7.6, "engagement_pct": 3.2, "budget_gbp": 1200000, "notes": "US enterprise cloud migration campaign — outcome-first messaging (reduce cost, accelerate time-to-value) outperformed feature-led by 2.4x. Webinar leads converted at 4x the rate of programmatic leads"},
]


def seed_campaign_benchmarks(bq: bigquery.Client) -> None:
    print("\nSeeding historical_campaigns...")
    _drop_create_table(bq, "historical_campaigns", CAMPAIGN_SCHEMA)
    rows = []
    for r in CAMPAIGN_BENCHMARKS:
        text = f"{r['brand']} {r['product_category']} {r['market']} {r['season']} campaign"
        emb  = _embed(text)
        print(f"  Embedded: {r['brand']} {r['product_category']} {r['season']}...")
        rows.append({**r, "embedding": emb})
    errors = bq.insert_rows_json(_full("historical_campaigns"), rows)
    if errors:
        print(f"  Insert errors: {errors}")
    else:
        print(f"  Inserted {len(rows)} campaign benchmarks")
    _create_vector_index(bq, "historical_campaigns")


# ── Channel benchmarks ───────────────────────────────────────────────────────────

CHANNEL_SCHEMA = [
    bigquery.SchemaField("channel",          "STRING", mode="REQUIRED"),
    bigquery.SchemaField("market",           "STRING"),
    bigquery.SchemaField("audience_segment", "STRING"),
    bigquery.SchemaField("ctr_pct",          "FLOAT64"),
    bigquery.SchemaField("cpm_gbp",          "FLOAT64"),
    bigquery.SchemaField("engagement_pct",   "FLOAT64"),
    bigquery.SchemaField("completion_pct",   "FLOAT64"),
    bigquery.SchemaField("avg_dwell_sec",    "FLOAT64"),
    bigquery.SchemaField("notes",            "STRING"),
    bigquery.SchemaField("embedding",        "FLOAT64", mode="REPEATED"),
]

CHANNEL_BENCHMARKS = [
    {"channel": "Instagram",  "market": "UK", "audience_segment": "18-34", "ctr_pct": 1.2, "cpm_gbp":  8.50, "engagement_pct": 4.5, "completion_pct": None, "avg_dwell_sec": None, "notes": "Feed images + Reels. Best for visual product shots. Peak: Thu-Sun 18:00-22:00"},
    {"channel": "TikTok",     "market": "UK", "audience_segment": "18-34", "ctr_pct": 2.1, "cpm_gbp":  6.20, "engagement_pct": 8.3, "completion_pct": 62.0, "avg_dwell_sec": None, "notes": "Native UGC style drives 3x engagement. Authentic > polished"},
    {"channel": "OOH",        "market": "UK", "audience_segment": "All",   "ctr_pct": None,"cpm_gbp": 12.00, "engagement_pct": None,"completion_pct": None, "avg_dwell_sec": 2.5,  "notes": "3-second rule. Logo + hero + headline only. Pre-approved crops required"},
    {"channel": "Meta Ads",   "market": "UK", "audience_segment": "25-44", "ctr_pct": 1.8, "cpm_gbp":  9.80, "engagement_pct": 3.2, "completion_pct": 55.0, "avg_dwell_sec": None, "notes": "Carousel drives 40% more clicks than single image"},
    {"channel": "Google Ads", "market": "UK", "audience_segment": "All",   "ctr_pct": 3.2, "cpm_gbp":  4.50, "engagement_pct": None,"completion_pct": None, "avg_dwell_sec": None, "notes": "Search intent = highest purchase intent. Use exact match for branded terms"},
    {"channel": "YouTube",    "market": "UK", "audience_segment": "18-44", "ctr_pct": 0.8, "cpm_gbp":  7.20, "engagement_pct": 2.1, "completion_pct": 45.0, "avg_dwell_sec": None, "notes": "Pre-roll: hook in first 5s. 15s skippable recommended for awareness"},
    {"channel": "LinkedIn",   "market": "UK", "audience_segment": "25-54", "ctr_pct": 0.5, "cpm_gbp": 22.00, "engagement_pct": 0.8, "completion_pct": None, "avg_dwell_sec": None, "notes": "B2B and professional audiences. Sponsored InMail performs for high-intent B2B leads"},
    {"channel": "Email",      "market": "UK", "audience_segment": "All",   "ctr_pct": 2.5, "cpm_gbp":  1.20, "engagement_pct": 22.0,"completion_pct": None, "avg_dwell_sec": None, "notes": "Open rate ~22%. Personalisation drives +30% CTR. Subject line accounts for 47% of opens"},
    {"channel": "Instagram",  "market": "Switzerland", "audience_segment": "25-44", "ctr_pct": 1.5, "cpm_gbp": 9.50, "engagement_pct": 3.8, "completion_pct": None, "avg_dwell_sec": None, "notes": "Swiss French and German language segmentation required. Multilingual content lifts CTR 25%"},
]


def seed_channel_benchmarks(bq: bigquery.Client) -> None:
    print("\nSeeding channel_benchmarks...")
    _drop_create_table(bq, "channel_benchmarks", CHANNEL_SCHEMA)
    rows = []
    for r in CHANNEL_BENCHMARKS:
        text = f"{r['channel']} {r['market']} {r['audience_segment']} benchmark performance"
        emb  = _embed(text)
        print(f"  Embedded: {r['channel']} {r['market']}...")
        rows.append({**r, "embedding": emb})
    errors = bq.insert_rows_json(_full("channel_benchmarks"), rows)
    if errors:
        print(f"  Insert errors: {errors}")
    else:
        print(f"  Inserted {len(rows)} channel benchmarks")
    _create_vector_index(bq, "channel_benchmarks")


# ── Customer segments ────────────────────────────────────────────────────────────

SEGMENT_SCHEMA = [
    bigquery.SchemaField("brand",                "STRING", mode="REQUIRED"),
    bigquery.SchemaField("segment_name",         "STRING", mode="REQUIRED"),
    bigquery.SchemaField("size_estimate",        "INTEGER"),
    bigquery.SchemaField("age_range",            "STRING"),
    bigquery.SchemaField("income_band",          "STRING"),
    bigquery.SchemaField("top_channels",         "STRING", mode="REPEATED"),
    bigquery.SchemaField("avg_weekly_spend_gbp", "FLOAT64"),
    bigquery.SchemaField("behavioural_notes",    "STRING"),
    bigquery.SchemaField("fan_truth_benchmark",  "STRING"),
    bigquery.SchemaField("embedding",            "FLOAT64", mode="REPEATED"),
]

CUSTOMER_SEGMENTS = [
    # Rnorr segments
    {
        "brand": "Rnorr", "segment_name": "Home Cook Enthusiasts", "size_estimate": 420000,
        "age_range": "25-44", "income_band": "GBP35k-GBP65k",
        "top_channels": ["Instagram", "YouTube", "Pinterest"], "avg_weekly_spend_gbp": 18.50,
        "behavioural_notes": "High MntMeatProducts (GBP400+/yr) and MntFishProducts signals active home cooks. NumStorePurchases > NumWebPurchases. Low NumDealsPurchases - not price-driven, values quality. Recipe content performs 3x better than product-led. Peak engagement: weekday evenings 18:00-20:00.",
        "fan_truth_benchmark": "Fan Truth must score Specific > 70. 'That moment when a weeknight dinner smells like it took all day' scores 78/100 with this group.",
    },
    {
        "brand": "Rnorr", "segment_name": "Budget Family Cooks", "size_estimate": 680000,
        "age_range": "28-40", "income_band": "GBP20k-GBP40k",
        "top_channels": ["Facebook", "TikTok", "OOH"], "avg_weekly_spend_gbp": 9.20,
        "behavioural_notes": "Kidhome > 0, high NumDealsPurchases (>5) - systematically deal-seeking. Time-poor: seeks shortcuts that feel 'proper' not lazy. Facebook Groups (recipe sharing) drives discovery.",
        "fan_truth_benchmark": "Fan Truth must score Shared > 80. 'Real flavour shouldn't take real time' scores 88/100. Avoid aspirational or premium-coded language.",
    },
    {
        "brand": "Rnorr", "segment_name": "Premium Home Entertainers", "size_estimate": 195000,
        "age_range": "35-55", "income_band": "GBP65k+",
        "top_channels": ["Instagram", "Pinterest", "YouTube"], "avg_weekly_spend_gbp": 34.00,
        "behavioural_notes": "High MntWines + MntMeatProducts signals dinner party hosting. Low NumDealsPurchases - quality over price. Pinterest for recipe inspiration; Instagram for food aesthetics.",
        "fan_truth_benchmark": "Fan Truth must score Special > 80. 'The shortcut that feels like cheating - but isn't' scores 85/100. Aspirational and quality signals land well.",
    },
    # Boozt segments
    {
        "brand": "Boozt", "segment_name": "Fitness & Performance Seekers", "size_estimate": 380000,
        "age_range": "18-30", "income_band": "GBP20k-GBP45k",
        "top_channels": ["TikTok", "Instagram", "YouTube"], "avg_weekly_spend_gbp": 12.50,
        "behavioural_notes": "Daily gym-goers, weekend athletes. Decision-driven by performance outcomes not relaxation. Peak consumption: pre-workout (06:00-08:00) and post-work (17:00-19:00). Gaming audience overlap is significant.",
        "fan_truth_benchmark": "Fan Truth must score Special > 80. 'The can that turns I can't into watch me' scores 88/100. Authenticity over polish; peer proof over brand authority.",
    },
    {
        "brand": "Boozt", "segment_name": "Festival & Social Energy Seekers", "size_estimate": 520000,
        "age_range": "18-25", "income_band": "GBP15k-GBP30k",
        "top_channels": ["TikTok", "Instagram", "OOH"], "avg_weekly_spend_gbp": 8.80,
        "behavioural_notes": "Event-driven consumption: festivals, clubs, house parties. FOMO-motivated. Social sharing of 'moments' is core behaviour. UGC from events drives massive organic reach.",
        "fan_truth_benchmark": "Fan Truth must score Shared > 75. 'That first sip when you need to switch on' scores 74/100 with this group. Social context matters more than personal performance.",
    },
    # Sunglow segments
    {
        "brand": "Sunglow", "segment_name": "Natural Hair Community", "size_estimate": 290000,
        "age_range": "22-38", "income_band": "GBP25k-GBP50k",
        "top_channels": ["Instagram", "TikTok", "YouTube"], "avg_weekly_spend_gbp": 22.00,
        "behavioural_notes": "Deeply engaged in natural hair community online. Wash-day routine is a ritual. Ingredient-conscious - reads labels. TikTok tutorials and community validation drive purchasing. Micro-influencer trust > brand advertising.",
        "fan_truth_benchmark": "Fan Truth must score Special > 85. 'Your crown is not a problem to manage, it's a conversation to have' scores 88/100. Cultural identity and community affirmation land strongest.",
    },
    # Glenfiddich segments
    {
        "brand": "Glenfiddich", "segment_name": "Premium Gifters", "size_estimate": 420000,
        "age_range": "35-60", "income_band": "GBP60k+",
        "top_channels": ["Instagram", "OOH", "YouTube"], "avg_weekly_spend_gbp": 45.00,
        "behavioural_notes": "Purchase Glenfiddich primarily as a considered gift. Decision is emotionally significant - 'what does this say about me?' High dwell time on heritage and craft content. Premium retail and airport duty-free key touchpoints.",
        "fan_truth_benchmark": "Fan Truth must score Overall > 80. 'When you gift a Glenfiddich, you're not giving a bottle - you're giving thought' scores 83/100. Heritage narrative is a permission for premium price.",
    },
    {
        "brand": "Glenfiddich", "segment_name": "Single Malt Enthusiasts", "size_estimate": 185000,
        "age_range": "40-65", "income_band": "GBP50k+",
        "top_channels": ["YouTube", "Instagram", "Email"], "avg_weekly_spend_gbp": 38.00,
        "behavioural_notes": "Educated whisky consumers who read tasting notes and follow distilleries. YouTube whisky education (tasting, craft) drives highest purchase intent. Long-form content and email newsletters work well.",
        "fan_truth_benchmark": "Fan Truth must score Specific > 80. '136 years of one family making one whisky in one valley' scores 88/100. Provenance and heritage specificity converts this segment.",
    },
    # Sunrise segments
    {
        "brand": "sunrise", "segment_name": "Swiss Family Connectivity Seekers", "size_estimate": 640000,
        "age_range": "28-48", "income_band": "CHF70k-CHF120k",
        "top_channels": ["Instagram", "Facebook", "YouTube"], "avg_weekly_spend_gbp": 55.00,
        "behavioural_notes": "Family households prioritising reliable home connectivity. Streaming, remote work, and children's education driving demand. Warm lifestyle imagery outperforms tech specs. Multilingual household - German-dominant.",
        "fan_truth_benchmark": "Fan Truth must score Shared > 78. 'Staying connected isn't a luxury - it's the quiet infrastructure of every good day' scores 80/100. Invisible-infrastructure framing resonates.",
    },
    # Haleon segments
    {
        "brand": "Haleon", "segment_name": "Active Pain Sufferers", "size_estimate": 3200000,
        "age_range": "35-65", "income_band": "GBP25k-GBP60k",
        "top_channels": ["TV", "YouTube", "Meta Ads"], "avg_weekly_spend_gbp": 8.50,
        "behavioural_notes": "Chronic or recurring pain (joint, back, head) manages conditions as part of daily routine. Trust in clinically validated brands is high. Pharmacist recommendation is a primary purchase driver. Functional proof (how fast, how effective) outweighs emotional messaging. Heavy TV viewers.",
        "fan_truth_benchmark": "Fan Truth must score Specific > 80. 'When the joint ache stops, you remember what moving freely actually felt like' scores 84/100. Specificity of the pain experience, not the product, is what lands.",
    },
    {
        "brand": "Haleon", "segment_name": "Proactive Wellness Seekers", "size_estimate": 2800000,
        "age_range": "25-45", "income_band": "GBP30k-GBP70k",
        "top_channels": ["Instagram", "YouTube", "Google Ads"], "avg_weekly_spend_gbp": 14.00,
        "behavioural_notes": "Preventative health mindset — vitamins, supplements, oral care as daily rituals. Highly informed, reads ingredient labels. Instagram and YouTube for wellness content discovery. January is highest intent month. Responds to science-backed claims with accessible language.",
        "fan_truth_benchmark": "Fan Truth must score Special > 78. 'Taking a vitamin feels like a promise you make to the future version of yourself' scores 84/100. Aspirational self-investment framing beats product efficacy claims with this segment.",
    },
    {
        "brand": "Haleon", "segment_name": "Family Health Decision Makers", "size_estimate": 4100000,
        "age_range": "28-50", "income_band": "GBP28k-GBP55k",
        "top_channels": ["TV", "Facebook", "OOH"], "avg_weekly_spend_gbp": 22.00,
        "behavioural_notes": "Primary healthcare purchaser for household. Seeks trusted, familiar brands — Panadol, Sensodyne, Centrum. Brand loyalty is high once established. Pharmacist and GP recommendations are key influence points. Facebook and TV reach this segment most effectively.",
        "fan_truth_benchmark": "Fan Truth must score Shared > 82. 'You don't think about your health until it's the only thing you can think about' scores 88/100. Universal health anxiety resonates across the entire household-management role.",
    },

    # Barclays segments
    {
        "brand": "Barclays", "segment_name": "First-Time Buyers", "size_estimate": 1400000,
        "age_range": "26-38", "income_band": "GBP28k-GBP55k",
        "top_channels": ["Instagram", "Google Ads", "YouTube"], "avg_weekly_spend_gbp": 0,
        "behavioural_notes": "Anxious about the mortgage process — overwhelmed by jargon, fees, and criteria. High search intent ('how much can I borrow', 'first-time buyer schemes'). Peer social proof and simplicity are key. Instagram and YouTube for discovery; Google Search at moment of high intent. Trust in institution matters as much as rate.",
        "fan_truth_benchmark": "Fan Truth must score Specific > 84. 'The moment your mortgage is approved and the house finally feels like it could be yours' scores 88/100. Emotional specificity of the milestone moment outperforms rational finance messaging.",
    },
    {
        "brand": "Barclays", "segment_name": "SME Business Owners", "size_estimate": 820000,
        "age_range": "30-55", "income_band": "GBP45k-GBP120k",
        "top_channels": ["LinkedIn", "Google Ads", "Email"], "avg_weekly_spend_gbp": 0,
        "behavioural_notes": "Time-poor decision-makers managing cash flow, payroll, and growth. Value expertise and partnership over product features. LinkedIn professional content and Google business search are primary touchpoints. Email newsletters from trusted sources influence decisions. Want a bank that understands their sector.",
        "fan_truth_benchmark": "Fan Truth must score Special > 82. 'The quiet confidence of knowing your bank understands your business, not just your balance' scores 86/100. Partnership and sector understanding resonate strongly vs generic business banking messaging.",
    },
    {
        "brand": "Barclays", "segment_name": "Mass Affluent Savers", "size_estimate": 2200000,
        "age_range": "35-60", "income_band": "GBP50k-GBP120k",
        "top_channels": ["TV", "Google Ads", "Email"], "avg_weekly_spend_gbp": 0,
        "behavioural_notes": "Financially engaged, monitors investments and savings rates actively. Moves money based on rate comparisons but values brand trust and stability. TV for brand salience; Google search and email for rate-driven decisions. Anxiety about long-term financial security is a core driver.",
        "fan_truth_benchmark": "Fan Truth must score Overall > 79. 'Watching your savings grow month by month — proof that small decisions compound' scores 79/100. Tangible, incremental progress framing beats aspirational wealth messaging.",
    },

    # Infosys segments
    {
        "brand": "Infosys", "segment_name": "C-Suite Digital Transformation Leaders", "size_estimate": 42000,
        "age_range": "42-58", "income_band": "USD200k+",
        "top_channels": ["LinkedIn", "YouTube", "Events"], "avg_weekly_spend_gbp": 0,
        "behavioural_notes": "CIOs, CTOs and CDOs accountable for enterprise transformation programmes. Consume long-form thought leadership (reports, whitepapers, executive briefings). Peer validation and analyst recognition (Gartner, Forrester) are primary trust signals. LinkedIn is the dominant professional channel; in-person events build the relationship that closes the deal.",
        "fan_truth_benchmark": "Fan Truth must score Special > 84. 'The CIO who chose the right partner five years ago is still ahead of the one who chose the cheapest' scores 90/100. Strategic partner framing — not vendor framing — is the only language that lands with this segment.",
    },
    {
        "brand": "Infosys", "segment_name": "Enterprise IT Decision Influencers", "size_estimate": 180000,
        "age_range": "32-50", "income_band": "USD80k-USD150k",
        "top_channels": ["LinkedIn", "Google Ads", "Webinars"], "avg_weekly_spend_gbp": 0,
        "behavioural_notes": "VPs, Directors and senior managers who evaluate, shortlist and recommend technology partners. Heavily research-driven — reads case studies, attends webinars, compares analyst ratings. Google search is high-intent at shortlist stage. LinkedIn for brand awareness and thought leadership earlier in the journey.",
        "fan_truth_benchmark": "Fan Truth must score Specific > 80. 'The organisations that navigate uncertainty fastest aren't lucky — they're better wired' scores 80/100. Specificity about business outcomes (speed, resilience, advantage) outperforms generic capability claims.",
    },
    {
        "brand": "Infosys", "segment_name": "AI & Innovation Agenda Owners", "size_estimate": 95000,
        "age_range": "35-52", "income_band": "USD120k-USD250k",
        "top_channels": ["LinkedIn", "YouTube", "Programmatic"], "avg_weekly_spend_gbp": 0,
        "behavioural_notes": "Chief AI Officers, heads of innovation and digital labs. Actively tracking AI developments — reads tech press, follows AI researchers on LinkedIn, attends AI-specific conferences. Highly sceptical of vendor hype; responds to demonstrated capability and honest limitation acknowledgement. YouTube for deep-dive technical content.",
        "fan_truth_benchmark": "Fan Truth must score Special > 86. 'AI doesn't replace strategy — it amplifies the quality of the people who set it' scores 88/100. Human-amplification framing consistently outperforms automation/replacement messaging with this audience.",
    },

    # Generic segments for any brand
    {
        "brand": "All", "segment_name": "Digital Natives (18-28)", "size_estimate": 2800000,
        "age_range": "18-28", "income_band": "GBP15k-GBP35k",
        "top_channels": ["TikTok", "Instagram", "YouTube"], "avg_weekly_spend_gbp": 7.50,
        "behavioural_notes": "Mobile-first, short-form content consumers. Authenticity is non-negotiable. Peer influence over brand authority. TikTok trends accelerate or kill campaigns within 48 hours. UGC is the highest-trust format.",
        "fan_truth_benchmark": "Fan Truth must score Shared > 72 AND Special > 74. Generic statements fail completely with this segment. Cultural specificity and genuine insight are table stakes.",
    },
]


def seed_customer_segments(bq: bigquery.Client) -> None:
    print("\nSeeding customer_segments...")
    _drop_create_table(bq, "customer_segments", SEGMENT_SCHEMA)
    rows = []
    for r in CUSTOMER_SEGMENTS:
        text = f"{r['brand']} {r['segment_name']} {r['age_range']} {' '.join(r['top_channels'])} customer segment"
        emb  = _embed(text)
        print(f"  Embedded: {r['brand']} — {r['segment_name']}...")
        rows.append({**r, "embedding": emb})
    errors = bq.insert_rows_json(_full("customer_segments"), rows)
    if errors:
        print(f"  Insert errors: {errors}")
    else:
        print(f"  Inserted {len(rows)} customer segments")
    _create_vector_index(bq, "customer_segments")


# ── Brand guidelines chunks ──────────────────────────────────────────────────────

GUIDELINES_SCHEMA = [
    bigquery.SchemaField("brand",       "STRING", mode="REQUIRED"),
    bigquery.SchemaField("content",     "STRING", mode="REQUIRED"),
    bigquery.SchemaField("source_file", "STRING"),
    bigquery.SchemaField("chunk_index", "INTEGER"),
    bigquery.SchemaField("embedding",   "FLOAT64", mode="REPEATED"),
]

CHUNK_SIZE    = 500   # characters per chunk
CHUNK_OVERLAP = 100   # overlap between chunks


def _chunk_text(text: str) -> list[str]:
    chunks = []
    start  = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start = end - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 50]


def _load_local_guidelines(brand: str) -> tuple[str, str]:
    """Load brand guidelines from local bucket path. Returns (content, source_file)."""
    import pathlib
    bucket_root = pathlib.Path(__file__).parent.parent / "bucket" / "brands" / brand / "Guidelines"
    for filename in ("brand_guidelines.md", "brand_guidelines.txt"):
        path = bucket_root / filename
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace"), filename
    return "", ""


# Brands that live only in GCS (not in local bucket): map brand name → GCS blob path
GCS_ONLY_BRANDS = {
    "Infosys": "brands/Infosys/Guidelines/Guideline.md",
}


def _load_gcs_guidelines(brand: str, blob_path: str) -> tuple[str, str]:
    """Download brand guidelines from GCS. Returns (content, source_file)."""
    try:
        from google.cloud import storage as _gcs
        gcs_bucket = (
            os.getenv("GCS_BUCKET")
            or os.getenv("BUCKET_NAME")
            or f"{GCP_PROJECT}-campaignos"
        )
        if not gcs_bucket:
            print(f"  WARNING: GCS_BUCKET not set — cannot load {brand} from GCS")
            return "", ""
        client = _gcs.Client(project=GCP_PROJECT)
        blob   = client.bucket(gcs_bucket).blob(blob_path)
        content = blob.download_as_text(encoding="utf-8")
        return content, blob_path.rsplit("/", 1)[-1]
    except Exception as e:
        print(f"  WARNING: GCS load failed for {brand} ({e})")
        return "", ""


def seed_brand_guidelines_chunks(bq: bigquery.Client) -> None:
    """Chunk and embed brand guidelines (local + GCS-only brands) into BigQuery."""
    print("\nSeeding brand_guidelines_chunks...")
    _drop_create_table(bq, "brand_guidelines_chunks", GUIDELINES_SCHEMA)

    import pathlib
    brands_root = pathlib.Path(__file__).parent.parent / "bucket" / "brands"

    all_rows     = []
    brands_found = 0

    # ── Local brands ──────────────────────────────────────────────────────────
    if brands_root.exists():
        for brand_dir in brands_root.iterdir():
            if not brand_dir.is_dir():
                continue
            brand = brand_dir.name
            content, source_file = _load_local_guidelines(brand)
            if not content:
                continue
            brands_found += 1
            chunks = _chunk_text(content)
            print(f"  {brand}: {len(chunks)} chunks from {source_file} (local)")
            for i, chunk in enumerate(chunks):
                emb = _embed(f"{brand} brand guidelines {chunk}")
                all_rows.append({
                    "brand": brand, "content": chunk,
                    "source_file": source_file, "chunk_index": i, "embedding": emb,
                })
                time.sleep(0.05)
    else:
        print(f"  No local bucket at {brands_root}")

    # ── GCS-only brands ───────────────────────────────────────────────────────
    for brand, blob_path in GCS_ONLY_BRANDS.items():
        content, source_file = _load_gcs_guidelines(brand, blob_path)
        if not content:
            continue
        brands_found += 1
        chunks = _chunk_text(content)
        print(f"  {brand}: {len(chunks)} chunks from {source_file} (GCS)")
        for i, chunk in enumerate(chunks):
            emb = _embed(f"{brand} brand guidelines {chunk}")
            all_rows.append({
                "brand": brand, "content": chunk,
                "source_file": source_file, "chunk_index": i, "embedding": emb,
            })
            time.sleep(0.05)

    if not all_rows:
        print("  No brand guidelines found. Table created (empty).")
        return

    # Insert in batches of 100 (BQ streaming insert limit ~10MB per request)
    batch_size = 100
    for i in range(0, len(all_rows), batch_size):
        batch  = all_rows[i: i + batch_size]
        errors = bq.insert_rows_json(_full("brand_guidelines_chunks"), batch)
        if errors:
            print(f"  Batch {i//batch_size + 1} errors: {errors[:2]}")
    print(f"  Inserted {len(all_rows)} chunks for {brands_found} brands")
    _create_vector_index(bq, "brand_guidelines_chunks")


# ── Main ─────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Set up BigQuery vector tables for CampaignOS")
    parser.add_argument("--skip-guidelines", action="store_true",
                        help="Skip seeding brand_guidelines_chunks (useful if running index_gcs_guidelines.py separately)")
    args = parser.parse_args()

    if not GCP_PROJECT:
        print("ERROR: GOOGLE_CLOUD_PROJECT (or GCP_PROJECT) must be set", file=sys.stderr)
        sys.exit(1)

    print(f"BigQuery Vector Setup")
    print(f"  Project:  {GCP_PROJECT}")
    print(f"  Dataset:  {DATASET}")
    print(f"  Embedder: {EMBEDDING_MODEL} ({EMBEDDING_DIM} dims)")
    print()

    bq = _client()

    # Ensure dataset exists
    dataset_ref = bq.dataset(DATASET)
    try:
        bq.create_dataset(bigquery.Dataset(dataset_ref), exists_ok=True)
        print(f"Dataset ready: {GCP_PROJECT}.{DATASET}\n")
    except Exception as e:
        print(f"WARNING: Could not verify dataset ({e})")

    seed_fan_truths(bq)
    seed_campaign_benchmarks(bq)
    seed_channel_benchmarks(bq)
    seed_customer_segments(bq)

    if not args.skip_guidelines:
        seed_brand_guidelines_chunks(bq)
    else:
        print("\nSkipped brand_guidelines_chunks (--skip-guidelines)")

    print("\nBigQuery vector setup complete.")
    print("Set SEARCH_MODE=bigquery in your environment to activate.")


if __name__ == "__main__":
    main()
