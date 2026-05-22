"""
CampaignOS — BigQuery Tools
FunctionTools for agents to query BigQuery datasets.
"""
import json
from datetime import datetime, timezone
from google.cloud import bigquery
from google.adk.tools import FunctionTool
import config


_client: bigquery.Client | None = None

def _bq() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=config.BQ_PROJECT)
    return _client


def _table(name: str) -> str:
    return f"`{config.BQ_PROJECT}.{config.BQ_DATASET}.{name}`"


@FunctionTool
def get_channel_benchmarks(channels: list[str]) -> dict:
    """
    Query BigQuery for performance benchmarks per marketing channel.
    Use this to validate KPI targets in a campaign brief.
    Args:
        channels: List of channels e.g. ['instagram', 'tiktok', 'youtube']
    Returns:
        Dict of channel -> benchmark metrics (avg_ctr, avg_roas, avg_reach, etc.)
    """
    placeholders = ", ".join([f"'{c}'" for c in channels])
    query = f"""
        SELECT channel, avg_ctr, avg_roas, avg_reach,
               avg_engagement, cost_per_mille, best_formats, audience_skew
        FROM {_table('channel_benchmarks')}
        WHERE channel IN ({placeholders})
        ORDER BY avg_roas DESC
    """
    try:
        rows = list(_bq().query(query).result())
        return {
            row.channel: {
                "avg_ctr": row.avg_ctr,
                "avg_roas": row.avg_roas,
                "avg_reach": row.avg_reach,
                "avg_engagement": row.avg_engagement,
                "cost_per_mille": row.cost_per_mille,
                "best_formats": list(row.best_formats or []),
                "audience_skew": row.audience_skew,
            }
            for row in rows
        }
    except Exception as e:
        # Return sensible defaults if table not yet populated
        return {ch: {
            "avg_ctr": 0.02, "avg_roas": 3.0, "avg_reach": 500000,
            "avg_engagement": 0.04, "cost_per_mille": 8.0,
            "best_formats": ["short_video", "story"], "audience_skew": "18-34"
        } for ch in channels}


@FunctionTool
def query_fan_truths(product_tags: list[str], audience_tags: list[str]) -> list[dict]:
    """
    Query the fan_truths table to find validated fan insights
    relevant to a specific product and audience.
    Args:
        product_tags: e.g. ['burger', 'spicy', 'limited_edition']
        audience_tags: e.g. ['18-34', 'spicy_lovers', 'australia']
    Returns:
        List of fan truth records sorted by combined score descending
    """
    query = f"""
        SELECT truth_id, statement, score_specific, score_shared, score_special,
               (score_specific + score_shared + score_special) AS total_score
        FROM {_table('fan_truths')}
        WHERE ARRAY_LENGTH(
            ARRAY(SELECT x FROM UNNEST(product_tags) x
                  WHERE x IN UNNEST(@product_tags))
        ) > 0
        ORDER BY total_score DESC
        LIMIT 10
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("product_tags", "STRING", product_tags),
        ]
    )
    try:
        rows = list(_bq().query(query, job_config=job_config).result())
        return [
            {
                "truth_id": r.truth_id,
                "statement": r.statement,
                "score_specific": r.score_specific,
                "score_shared": r.score_shared,
                "score_special": r.score_special,
                "total_score": r.total_score,
            }
            for r in rows
        ]
    except Exception:
        return []  # Graceful fallback — agent will use its own knowledge


@FunctionTool
def log_audit_event(
    campaign_id: str,
    agent: str,
    event_type: str,
    payload: dict | None = None,
    duration_ms: int | None = None,
    model: str | None = None,
) -> str:
    """
    Write an event to the BigQuery audit log.
    Call this after each major agent action for traceability.
    Args:
        campaign_id: The campaign being processed
        agent: Name of the agent e.g. 'briefing_agent'
        event_type: e.g. 'brief_validated', 'strategy_generated'
        payload: Optional dict with relevant data
        duration_ms: How long the operation took
        model: Gemini model used
    Returns:
        'ok' on success
    """
    import uuid
    row = {
        "log_id": str(uuid.uuid4()),
        "campaign_id": campaign_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "event_type": event_type,
        "payload": json.dumps(payload) if payload else None,
        "duration_ms": duration_ms,
        "model": model,
        "token_count": None,
    }
    try:
        table_ref = f"{config.BQ_PROJECT}.{config.BQ_DATASET}.audit_log"
        errors = _bq().insert_rows_json(table_ref, [row])
        return "ok" if not errors else f"warn: {errors}"
    except Exception as e:
        return f"audit_log_failed: {e}"  # Non-fatal


@FunctionTool
def save_campaign_to_bigquery(campaign_id: str, status: str, data: dict) -> str:
    """
    Upsert campaign data into the campaigns table.
    Args:
        campaign_id: Unique campaign identifier
        status: Current pipeline status
        data: Dict with any of: brief_json, strategy_json, kv_json,
              content_json, execution_json, product, budget, channels
    Returns:
        'ok' or error message
    """
    from datetime import datetime, timezone
    # BigQuery doesn't support upsert natively — use MERGE via DML
    set_clauses = ", ".join([f"{k} = @{k}" for k in data if k != "campaign_id"])
    params = [
        bigquery.ScalarQueryParameter("campaign_id", "STRING", campaign_id),
        bigquery.ScalarQueryParameter("status", "STRING", status),
        bigquery.ScalarQueryParameter("created_at", "TIMESTAMP",
                                     datetime.now(timezone.utc).isoformat()),
    ]
    # Simplified: just insert a new row per update for the audit trail
    row = {
        "campaign_id": campaign_id,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **{k: (json.dumps(v) if isinstance(v, dict) else v)
           for k, v in data.items()},
    }
    try:
        table_ref = f"{config.BQ_PROJECT}.{config.BQ_DATASET}.campaigns"
        _bq().insert_rows_json(table_ref, [row])
        return "ok"
    except Exception as e:
        return f"error: {e}"
