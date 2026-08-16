"""
Campaign RAG — retrieves historical campaign performance from BigQuery
to give the Email Composer Agent context on what worked before.

BigQuery table schema (dataset: campaignos, table: campaign_history):
  campaign_id     STRING
  brand_name      STRING
  subject_line    STRING
  open_rate       FLOAT64
  click_rate      FLOAT64
  conversion_rate FLOAT64
  template        STRING     -- "hero" | "text_first" | "product"
  audience        STRING
  send_date       DATE
  summary         STRING     -- short human description of the campaign

Wire-up:
  1. Set GOOGLE_CLOUD_PROJECT env var.
  2. Grant the service account "BigQuery Data Viewer" + "BigQuery Job User" roles.
  3. Populate via the Analytics pipeline or a Dataflow job.
"""
from __future__ import annotations
from typing import Any


class CampaignRAG:
    """
    Retrieves top-performing historical campaigns for a given brand,
    to inform the composer about what subject lines, templates, and
    content patterns drove the best open and click rates.

    Usage:
        rag = CampaignRAG(project="my-gcp-project")
        ctx = await rag.search("Haleon", top_n=3)
        # ctx = [{ subject_line, open_rate, click_rate, template, summary }, ...]
    """

    _QUERY = """
        SELECT
          subject_line, open_rate, click_rate, conversion_rate,
          template, audience, summary
        FROM `{project}.campaignos.campaign_history`
        WHERE LOWER(brand_name) = LOWER(@brand_name)
        ORDER BY open_rate DESC
        LIMIT @top_n
    """

    def __init__(self, project: str = ""):
        self._project = project
        self._client  = None   # lazy BigQuery Client

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import bigquery
                self._client = bigquery.Client(project=self._project or None)
            except ImportError:
                raise RuntimeError(
                    "google-cloud-bigquery is required for CampaignRAG. "
                    "Install: pip install google-cloud-bigquery"
                )
        return self._client

    async def search(self, brand_name: str, top_n: int = 3) -> list[dict[str, Any]]:
        """
        Return the top_n best-performing campaigns for brand_name.
        Returns an empty list on any error — the composer handles missing context.
        """
        if not brand_name:
            return []
        try:
            from google.cloud import bigquery

            client = self._get_client()
            query  = self._QUERY.format(project=self._project)
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("brand_name", "STRING", brand_name),
                    bigquery.ScalarQueryParameter("top_n",      "INT64",  top_n),
                ]
            )
            rows = client.query(query, job_config=job_config).result()
            return [dict(row) for row in rows]
        except Exception:
            return []

    async def log_campaign(self, record: dict[str, Any]) -> None:
        """Append a sent campaign to the history table (post-send hook)."""
        try:
            from google.cloud import bigquery

            client = self._get_client()
            table  = f"{self._project}.campaignos.campaign_history"
            client.insert_rows_json(table, [record])
        except Exception:
            pass
