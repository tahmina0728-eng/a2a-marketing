"""
agents/infosys/ideon.py — IdeonAgent.

Ideon is the Infosys copy agent.
Input:  {"brief": LogosAgentResponse, "creative_platform": HeliaAgentResponse}
Output: AgentResponse with artifact type "copy_deck"
        containing a CopyDeck-shaped JSON + display_deck text
"""
from __future__ import annotations

import json

from app.agents.infosys.base import BaseInfosysAgent
from app.schemas.common import AgentResponse

_OUTPUT_SCHEMA = """{
  "campaign_name": "string",
  "territory": "string — territory name from Helia",
  "big_idea_anchor": "string — big idea statement this deck executes",
  "headlines": {
    "hero_options": [
      "string (option 1 — ≤7 words, char count in brackets e.g. [21 chars])",
      "string (option 2)",
      "string (option 3)"
    ],
    "support_options": [
      "string (option 1)",
      "string (option 2)",
      "string (option 3)"
    ]
  },
  "body_copy": {
    "web": "string — hook → what it means for this CXO role → proof ([APPROVED_...]) → CTA",
    "email": "string — subject line + preview + body"
  },
  "banner_copy": {
    "linkedin_1200x627": {
      "heading": "string — fits 546px column at 48px: ≤18 chars/line, 2 lines max",
      "subheading": "string — ≤20 chars at 42px",
      "cta": "string"
    }
  },
  "cta_bank": [
    "string — specific CTA 1 (max 5 words)",
    "string — specific CTA 2",
    "string — specific CTA 3",
    "string — specific CTA 4"
  ],
  "social_captions": {
    "linkedin": "string — professional, value-first, 1-2 lines before 'see more', ≤3 hashtags",
    "x": "string — one tight idea"
  },
  "scripts": [
    {
      "format": "string — e.g. '30s social film'",
      "territory": "string",
      "scenes": [
        {
          "time": "string — e.g. '0:00–0:08'",
          "visual": "string — [image zone] description",
          "super": "string — on-screen text",
          "vo": "string — spoken voiceover"
        }
      ],
      "end_frame": "string — lockup on [colour ground]; endline SUPER: [hero line]",
      "legal_supers": ["string — [APPROVED_...] tokens shown on-screen"]
    }
  ],
  "compliance_flags": ["string — each BLOCK: element + [TOKEN] + routing"],
  "lead_picks": {
    "linkedin_banner": "string — which hero option",
    "social_caption": "string — which platform version"
  },
  "display_deck": "string — the complete copy deck in the Ideon output format (all sections, with variants, tokens, alt text, flags)"
}"""


class IdeonAgent(BaseInfosysAgent):
    name = "ideon"
    artifact_type = "copy_deck"
    output_schema = _OUTPUT_SCHEMA

    def run(self, context: dict) -> AgentResponse:
        logos_output: AgentResponse | None = context.get("brief")
        helia_output: AgentResponse | None = context.get("creative_platform")

        brief    = logos_output.artifact.content if logos_output and logos_output.artifact else {}
        platform = helia_output.artifact.content if helia_output and helia_output.artifact else {}

        campaign_name = brief.get("campaign_name", "")
        rag_query = " ".join(filter(None, [
            "Infosys copy voice tone sentence case plain english",
            brief.get("sub_brand", ""),
            platform.get("big_idea", {}).get("statement", "") if isinstance(platform.get("big_idea"), dict) else "",
        ]))

        input_text = (
            "VALIDATED BRIEF (from Logos):\n\n"
            + json.dumps(brief, indent=2)
            + "\n\nCREATIVE PLATFORM (from Helia — write inside this territory):\n\n"
            + json.dumps(platform, indent=2)
        )

        result = self._run_sync(input_text, rag_query=rag_query)
        return self._make_response(result, campaign_name=campaign_name)
