"""
agents/infosys/helia.py — HeliaAgent.

Helia is the Infosys creative strategist.
Input:  AgentResponse from Logos (artifact.content = ValidatedBrief)
Output: AgentResponse with artifact type "creative_platform"
        containing a CreativePlatform-shaped JSON + display_platform text
"""
from __future__ import annotations

import json

from app.agents.infosys.base import BaseInfosysAgent
from app.schemas.common import AgentResponse

_OUTPUT_SCHEMA = """{
  "campaign_name": "string",
  "brief_summary": "string — one paragraph restating objective, segment, buyer truth, proposition",
  "big_idea": {
    "statement": "string — one sentence: the single organising creative thought",
    "what_it_unlocks": "string — short paragraph on what this idea enables creatively",
    "scores": {
      "rooted": 1,
      "single_minded": 1,
      "ownable": 1,
      "elastic": 1,
      "inspiring": 1
    },
    "weighted_total": 0,
    "verdict": "proceed | sharpen | rework"
  },
  "hero_message": {
    "hero_line": "string — memorable endline, short, on-platform, no position claim",
    "hero_line_char_count": 0,
    "fits_banner_column": true,
    "support_line": "string — expands the promise for the segment",
    "reason_to_believe": "string — proof, using [APPROVED_...] tokens for unverified claims",
    "cta": "string — plain, specific next step"
  },
  "territories": [
    {
      "name": "string",
      "premise": "string — the world in a phrase",
      "feeling": "string — emotion it leaves",
      "verbal_tone": "string — how copy sounds within the Infosys voice",
      "visual_cues": "string — colour set name, ground hex, contrast ratio (e.g. 'Sapphire Dark #061838, white 17.57:1'), template modules (photoPanel | scrim | badge | partner | disclaimer)",
      "story_spine": "string — narrative arc: tension → stake → navigable path → Infosys alongside → outcome",
      "sample_execution": "string — one hero line + one format described in words",
      "extends": "string — how it scales across formats, industries, and time"
    }
  ],
  "recommended_territory": "string — name of the recommended territory",
  "recommendation_reason": "string — why this territory best serves the objective and truth",
  "dos": ["string — 3-4 how-to-keep-executions-on-idea rules"],
  "donts": ["string — 3-4 pitfalls to avoid"],
  "compliance_flags": ["string — each BLOCK item: 'BLOCK → route to legal: [element] replaced by [TOKEN]'"],
  "display_platform": "string — the complete creative platform in the Helia output format (all sections)"
}"""


class HeliaAgent(BaseInfosysAgent):
    name = "helia"
    artifact_type = "creative_platform"
    output_schema = _OUTPUT_SCHEMA

    def run(self, logos_output: AgentResponse) -> AgentResponse:
        brief = (
            logos_output.artifact.content
            if logos_output.artifact else {}
        )
        campaign_name = brief.get("campaign_name", "")
        rag_query = " ".join(filter(None, [
            "Infosys creative platform big idea territory",
            brief.get("sub_brand", ""),
            brief.get("objective", ""),
            brief.get("proposition", ""),
        ]))

        input_text = (
            "VALIDATED BRIEF (output from Logos — use this as the foundation for everything):\n\n"
            + json.dumps(brief, indent=2)
        )

        result = self._run_sync(input_text, rag_query=rag_query)
        return self._make_response(result, campaign_name=campaign_name)
