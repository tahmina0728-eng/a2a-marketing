"""
agents/infosys/aether.py — AetherAgent.

Aether is the Infosys market & cultural intelligence agent.
It sits BEFORE Logos in the pipeline — its market intelligence briefing
feeds directly into the brief request so Logos scores a well-evidenced
buyer truth rather than a raw hunch.

Input:  a research scope dict (brand, segment, industry, market, objective, timeframe)
Output: AgentResponse with artifact type "market_intelligence"
        containing a MarketIntelligenceBriefing + candidate buyer truths for Logos
"""
from __future__ import annotations

from app.agents.infosys.base import BaseInfosysAgent
from app.schemas.common import AgentResponse

_OUTPUT_SCHEMA = """{
  "brand": "string",
  "segment": "string — named buyer segment, e.g. 'CIOs in European banking'",
  "industry": "string",
  "market": "string",
  "timeframe": "string",
  "objective": "string",

  "executive_summary": "string — 3-5 lines: the headline signal and the right-buyer-right-moment recommendation",

  "category_signals": [
    {
      "signal": "string — what is shifting in this category",
      "so_what": "string — implication for Infosys and this sub-brand",
      "confidence": "Observed | Reported | Inferred",
      "source": "string — source name and date"
    }
  ],

  "buyer_insight": {
    "accountabilities": ["string — what this CXO is accountable for right now"],
    "jobs_to_be_done": ["string"],
    "information_diet": ["string — where they get information"],
    "unspoken_tensions": ["string — pressures they carry but don't say out loud"]
  },

  "analyst_landscape": [
    {
      "firm": "string — Gartner | Forrester | IDC | Everest | HFS",
      "position": "string — how they frame the category and Infosys within it",
      "as_of": "string — date of this position",
      "citation_status": "source_only — must be [APPROVED_ANALYST_CITATION] before use in copy"
    }
  ],

  "moments_and_timing": {
    "align_with": ["string — event / cycle / deadline + date"],
    "avoid": ["string — periods to avoid, e.g. results quiet period"],
    "quiet_period_note": "string — note any Infosys results quiet period collision",
    "receptivity": "string — when and why this buyer is most open to this message"
  },

  "competitor_context": {
    "what_rivals_own": "string — what TCS, Accenture, Cognizant, Wipro etc. are saying",
    "whitespace": "string — the territory Infosys can credibly own that rivals don't"
  },

  "candidate_buyer_truths": [
    {
      "rank": 1,
      "statement": "string — one-sentence tension the segment already feels",
      "evidence": "string — sources / signals supporting this",
      "moment": "string — which timing signal makes this land right now",
      "confidence": "Observed | Reported | Inferred"
    }
  ],

  "right_buyer_right_moment": "string — the recommended buyer + timing recommendation for Logos and Helia",

  "sources": ["string — source name, URL or publication, date"],
  "confidence_and_gaps": "string — what is solid, what needs validation before the brief",
  "flags": ["string — confidentiality | disclosure | analyst citation | partner checks needed"],

  "display_briefing": "string — the complete market intelligence briefing in the Aether output format (all sections)"
}"""


class AetherAgent(BaseInfosysAgent):
    name = "aether"
    artifact_type = "market_intelligence"
    output_schema = _OUTPUT_SCHEMA

    def run(self, scope: dict) -> AgentResponse:
        """
        scope keys (all optional except brand):
          brand, sub_brand, segment, industry, market, objective, timeframe
        """
        rag_query = " ".join(filter(None, [
            "Infosys market trends buyer insight enterprise technology",
            scope.get("sub_brand", ""),
            scope.get("segment", ""),
            scope.get("industry", ""),
            scope.get("objective", ""),
        ]))

        input_lines = ["RESEARCH SCOPE — what Aether needs to investigate:\n"]
        for key, val in scope.items():
            if val:
                input_lines.append(f"{key}: {val}")
        input_lines.append(
            "\nAether should search for current enterprise tech signals, buyer behaviour, "
            "analyst positions, timing moments, and competitor whitespace for this scope. "
            "Return 2-4 candidate buyer truths ranked by evidence strength for Logos to score."
        )
        input_text = "\n".join(input_lines)

        result = self._run_sync(input_text, rag_query=rag_query)
        return self._make_response(result, campaign_name=scope.get("campaign_name", ""))
