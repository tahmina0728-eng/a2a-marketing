"""
search_client.py — Vertex AI Search client.

ONE Search App, TWO datastores:
  Datastore 1 (GCS unstructured):  brand_guidelines.md
  Datastore 2 (BigQuery structured): historical_campaigns,
                                      fan_truth_library,
                                      channel_benchmarks

The ADK tools in tools.py call these methods.
This module is unchanged from the non-ADK version.
"""

import structlog
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.exceptions import GoogleAPICallError
from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()


class SearchResult:
    """Clean wrapper around a raw Vertex AI Search response."""

    def __init__(self, query: str, raw_response):
        self.query = query
        self._raw  = raw_response

    @property
    def summary(self) -> str:
        # Try AI summary first, fall back to top snippets joined together
        try:
            text = self._raw.summary.summary_text or ""
            if text:
                return text
        except Exception:
            pass
        snippets = self.top_snippets
        return "\n\n".join(snippets[:3]) if snippets else ""

    @property
    def citations(self) -> list[dict]:
        try:
            refs = self._raw.summary.summary_with_metadata.references
            return [{"title": getattr(r, "title", ""), "document": getattr(r, "document", "")} for r in refs]
        except Exception:
            return []

    @property
    def results(self) -> list[dict]:
        items = []
        for result in self._raw.results:
            doc  = result.document
            data = {}
            if doc.struct_data:
                data.update(dict(doc.struct_data))
            if doc.derived_struct_data:
                data.update(dict(doc.derived_struct_data))
            items.append({"id": doc.id, "name": doc.name, "data": data})
        return items

    @property
    def top_snippets(self) -> list[str]:
        snippets = []
        for result in self._raw.results:
            doc = result.document
            if not doc.derived_struct_data:
                continue
            derived = dict(doc.derived_struct_data)
            for answer in derived.get("extractive_answers", {}).get("values", []):
                content = answer.get("struct_value", {}).get("fields", {}).get("content", {}).get("string_value", "")
                if content:
                    snippets.append(content)
            for snippet in derived.get("snippets", {}).get("values", []):
                content = snippet.get("struct_value", {}).get("fields", {}).get("snippet", {}).get("string_value", "")
                if content:
                    snippets.append(content)
        return snippets

    def to_dict(self) -> dict:
        return {
            "query":        self.query,
            "summary":      self.summary,
            "citations":    self.citations,
            "results":      self.results,
            "top_snippets": self.top_snippets,
        }


class BriefingSearchClient:
    """Queries the CampaignOS Search App across both datastores."""

    def __init__(self):
        self.client          = discoveryengine.SearchServiceClient()
        self._serving_config = (
            f"projects/{settings.gcp_project}"
            f"/locations/{settings.search_location}"
            f"/collections/default_collection"
            f"/engines/{settings.search_engine_id}"
            f"/servingConfigs/default_config"
        )
        logger.info("search_client_init", engine_id=settings.search_engine_id)

    def _build_request(self, query: str, page_size: int | None = None) -> discoveryengine.SearchRequest:
        # Standard Edition: summary + snippets only (no extractive answers/segments)
        return discoveryengine.SearchRequest(
            serving_config=self._serving_config,
            query=query,
            page_size=page_size or settings.search_max_results,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                    summary_result_count=settings.search_summary_result_count,
                    include_citations=False,
                    ignore_adversarial_query=True,
                ),
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                ),
            ),
        )

    def search(self, query: str, page_size: int | None = None) -> SearchResult:
        log = logger.bind(query=query[:120])
        log.info("search_start")
        try:
            response = self.client.search(self._build_request(query, page_size))
            result   = SearchResult(query, response)
            log.info("search_complete", result_count=len(result.results), has_summary=bool(result.summary))
            return result
        except GoogleAPICallError as e:
            log.error("search_api_error", error=str(e))
            raise RuntimeError(f"Vertex AI Search failed: {e}") from e

    def get_brand_rules(self, product_category: str, channels: list[str]) -> SearchResult:
        channel_str = ", ".join(channels)
        return self.search(
            f"brand guidelines: logo colour font voice guardrails for "
            f"{product_category} campaign on {channel_str}. Include brand logo rules, "
            f"font weights, colour proportions, brand voice, tagline restriction, "
            f"OOH crop requirements, forbidden treatments, campaign generation rules."
        )

    def get_fan_truth_examples(self, product: str, product_category: str, audience: str) -> SearchResult:
        return self.search(
            f"Fan Truth examples for {product} ({product_category}) "
            f"targeting {audience}. Show validated examples that are Specific Shared Special. "
            f"Also show rejected generic corporate examples with rejection reasons. "
            f"Include overall_score, is_specific, is_shared, is_special, status fields."
        )

    def get_campaign_benchmarks(self, product_category: str, market: str, season: str) -> SearchResult:
        return self.search(
            f"Historical campaign performance for {product_category} "
            f"in {market} during {season}. Include reach, CTR, ROAS, conversions, "
            f"engagement rate, budget, channels, Fan Truth used, and final result."
        )

    def get_channel_benchmarks(self, channels: list[str], market: str, audience_segment: str) -> SearchResult:
        return self.search(
            f"Channel performance benchmarks for {', '.join(channels)} in {market} "
            f"targeting {audience_segment}. Include CTR, CPM, engagement rate, "
            f"completion rate, colour ratio, ad length, OOH crop rules."
        )

    def get_moment_type_rules(self, moment_type: str) -> SearchResult:
        return self.search(
            f"{moment_type} campaign rules: budget weighting, approval "
            f"requirements, logo treatment, content guidelines."
        )


_client: BriefingSearchClient | None = None


def get_search_client() -> BriefingSearchClient:
    global _client
    if _client is None:
        _client = BriefingSearchClient()
    return _client
