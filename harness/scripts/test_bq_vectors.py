"""
Quick smoke test for BigQuery vector search.

Run from the harness directory:
  uv run python scripts/test_bq_vectors.py
"""
import os
import sys
import pathlib

# Add harness root to path so `app` package is importable
_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root))

# Load .env so GOOGLE_API_KEY and GOOGLE_CLOUD_PROJECT are available
try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env", override=False)
except ImportError:
    pass

os.environ["SEARCH_MODE"] = "bigquery"

from app.bq_vector_client import (
    search_fan_truths,
    search_campaign_benchmarks,
    search_channel_benchmarks,
    search_audience_insights,
    search_brand_guidelines,
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def check(label: str, result: str) -> None:
    ok = bool(result and "No " not in result[:20] and "found" not in result[:30])
    status = PASS if ok else FAIL
    print(f"[{status}] {label}")
    if ok:
        # Print first 200 chars of result
        preview = result.replace("\n", " ")[:200]
        print(f"       {preview}...")
    else:
        print(f"       Got: {result[:100]}")
    print()


print("BigQuery Vector Search — smoke test")
print("=" * 50)
print()

check(
    "Fan truths (Rnorr / weeknight dinner)",
    search_fan_truths("Rnorr", "cook-in sauces", "weeknight dinner", top_k=2),
)

check(
    "Campaign benchmarks (McDonalds / burgers / UK)",
    search_campaign_benchmarks("McDonalds", "burgers", "UK", "Summer", top_k=2),
)

check(
    "Channel benchmarks (Instagram + TikTok / UK)",
    search_channel_benchmarks(["Instagram", "TikTok"], "UK", "18-34", top_k=3),
)

check(
    "Audience insights (Rnorr / home cooks)",
    search_audience_insights("Rnorr", "home cooks", "25-44", ["Instagram"], top_k=2),
)

check(
    "Brand guidelines RAG (Glenfiddich / heritage)",
    search_brand_guidelines("Glenfiddich", "heritage tone of voice", top_k=2),
)
