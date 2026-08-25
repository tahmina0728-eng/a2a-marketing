"""
agents/infosys/logos.py — LogosAgent.

Logos is the Infosys campaign-briefing agent.
Input:  a raw campaign brief dict
Output: AgentResponse with artifact type "validated_brief"
        containing a ValidatedBrief-shaped JSON + display_brief text
"""
from __future__ import annotations

from app.agents.infosys.base import BaseInfosysAgent
from app.schemas.common import AgentResponse

_OUTPUT_SCHEMA = """{
  "campaign_name": "string",
  "brand": "string",
  "sub_brand": "string — which Infosys entity fronts the campaign, e.g. 'Infosys Topaz', 'Infosys Cobalt', 'Infosys Aster', 'Infosys Finacle', 'Infosys'",
  "co_brand": "string or null — partner name and approved lockup if applicable",
  "market": "string — country",
  "locale": "string — IETF tag e.g. en-GB",
  "objective": "string — one measurable campaign objective",
  "kpi": "string — specific number + timeframe, e.g. '180 MQLs from BFSI CIOs in 8 weeks'",
  "audience": {
    "segment": "string — named segment",
    "role": "string — CXO title",
    "industry": "string",
    "insight": "string — the pressure or situation this segment faces right now"
  },
  "buyer_truth": {
    "statement": "string — the real human tension the campaign stands on",
    "scores": {
      "true": 1,
      "human": 1,
      "relevant": 1,
      "ownable": 1,
      "actionable": 1
    },
    "weighted_total": 0,
    "verdict": "GO | SHARPEN | REWORK"
  },
  "proposition": "string — single-minded proposition",
  "reasons_to_believe": ["string — use [APPROVED_CLIENT_REF] or [APPROVED_ANALYST_CITATION] tokens for unverified claims"],
  "tone": "string — e.g. 'Credible, specific, plain about limits'",
  "channels": ["string"],
  "formats": ["string — with real specs, e.g. 'LinkedIn 1200×627 (banner master)'"],
  "mandatories": ["string — lockup, legal line, accessibility, partner rules"],
  "timing": "string — flight dates",
  "budget": "string — budget band",
  "success_metric": "string — how success is judged post-launch",
  "status": "READY FOR CREATIVE | SHARPEN | REWORK",
  "gate": {
    "overall": "PASS | BLOCK",
    "flags": [
      {
        "area": "disclosure | partner | accessibility | people",
        "status": "PASS | BLOCK",
        "element": "string or null — what triggered the flag",
        "rule": "string or null",
        "token": "string or null — [APPROVED_...] replacement token",
        "routes_to": "string or null — e.g. 'legal', 'brand_team', 'partner'"
      }
    ]
  },
  "quiet_period_check": "string — notes any collision with Infosys results quiet period",
  "display_brief": "string — the complete formatted brief in the Logos output format (all sections, as it would appear in the brand document)"
}"""


class LogosAgent(BaseInfosysAgent):
    name = "logos"
    artifact_type = "validated_brief"
    output_schema = _OUTPUT_SCHEMA

    def run(self, request: dict) -> AgentResponse:
        campaign_name = request.get("campaign_name", "")
        rag_query = " ".join(filter(None, [
            request.get("sub_brand", "Infosys"),
            request.get("objective", ""),
            request.get("audience", ""),
            request.get("product_area", ""),
        ]))

        input_lines = [f"CAMPAIGN BRIEF REQUEST — to be validated by Logos\n"]
        for key, val in request.items():
            if val:
                input_lines.append(f"{key}: {val}")
        input_text = "\n".join(input_lines)

        result = self._run_sync(input_text, rag_query=rag_query)
        return self._make_response(result, campaign_name=campaign_name)
