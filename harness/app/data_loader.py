"""
data_loader.py -- BigQuery audit log for CampaignOS pipeline outputs.

Brief outputs are stored via the ADK artifact service (tools.py).
This module writes structured rows to BigQuery for analytics and audit trail.
"""

import json
import structlog
from datetime import datetime, timezone
from google.cloud import bigquery
from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()


def log_brief_to_bigquery(campaign_id: str, brief_input: dict, machine_brief: dict) -> None:
    """Append brief to BigQuery audit log. Non-fatal if it fails."""
    if not settings.bq_logging_enabled:
        logger.debug("bq_logging_disabled", campaign_id=campaign_id)
        return
    try:
        client   = bigquery.Client(project=settings.gcp_project)
        table_id = f"{settings.gcp_project}.{settings.bq_output_dataset}.{settings.bq_output_table}"
        row = {
            "campaign_id":       campaign_id,
            "campaign_name":     brief_input.get("campaign_name"),
            "brand":             brief_input.get("brand"),
            "market":            brief_input.get("market"),
            "product_category":  brief_input.get("product_category"),
            "season":            brief_input.get("season"),
            "channels":          ",".join(brief_input.get("channels", [])),
            "moment_type":       brief_input.get("moment_type"),
            "validation_score":  machine_brief.get("validation", {}).get("score"),
            "validation_status": machine_brief.get("validation", {}).get("status"),
            "fan_truth_score":   machine_brief.get("fan_truth_score", {}).get("overall"),
            "fan_truth_verdict": machine_brief.get("fan_truth_score", {}).get("verdict"),
            "flag_count":        len(machine_brief.get("flags", [])),
            "brief_json":        json.dumps(machine_brief, default=str),
            "created_at":        datetime.now(timezone.utc).isoformat(),
        }
        errors = client.insert_rows_json(table_id, [row])
        if errors:
            logger.error("bq_log_failed", errors=errors)
        else:
            logger.info("brief_logged_bq", campaign_id=campaign_id)
    except Exception as e:
        logger.error("log_bq_failed", campaign_id=campaign_id, error=str(e))
