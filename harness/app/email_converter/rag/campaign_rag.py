class CampaignRAG:

    """
    Connect this to your existing
    BigQuery historical campaign data.
    """

    def search(
        self,
        brand_name: str = "",
        source_context: dict | None = None,
    ) -> list[dict]:

        return []