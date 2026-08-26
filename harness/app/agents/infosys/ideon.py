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
  "content_type": "string — e.g. 'Campaign Ad'",
  "channel": "string — e.g. 'LinkedIn'",
  "territory": "string — territory name from Helia",
  "big_idea_anchor": "string — big idea statement this deck executes",

  "audience": {
    "insight": "string — core tension or unmet need driving this audience"
  },
  "strategic_context": {
    "key_message": "string — the one message this territory is built on"
  },

  "recommended_variant": 0,

  "variants": [
    {
      "tone": "string — 2-4 word tone label e.g. 'confident and thoughtful'",
      "approach": "string — 1-sentence rationale for this angle",
      "headline": "string — ≤7 words, sentence case, no period",
      "subheadline": "string — 1 support line expanding the promise",
      "body": "string — 2-3 sentence body copy: hook → role implication → proof token → CTA",
      "cta": "string — ≤5 words, plain action verb",
      "quality_score": 0.0,
      "scores": {
        "brand_voice": 0.0,
        "strategy_alignment": 0.0,
        "message_clarity": 0.0,
        "audience_relevance": 0.0,
        "originality": 0.0,
        "channel_suitability": 0.0,
        "grammar_readability": 0.0
      }
    }
  ],

  "banner_copy": {
    "linkedin_1200x627": {
      "heading": "string — from recommended variant: fits 546px column at 48px, ≤18 chars/line, 2 lines max",
      "subheading": "string — from recommended variant, ≤20 chars at 42px",
      "cta": "string — from recommended variant CTA"
    }
  },
  "body_copy": {
    "web": "string — hook → what it means for this CXO role → proof ([APPROVED_...]) → CTA",
    "email": "string — subject line + preview + body"
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
  "compliance_flags": ["string — each BLOCK: element + [TOKEN] + routing"],
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

        # preferred_headline is pre-injected by the runner BEFORE Logos runs,
        # so it survives Logos rewriting the objective. Only use it if explicitly set —
        # never try to extract from the Logos-processed text (risk of false positives).
        _required_headline = brief.get("preferred_headline", "")

        _headline_rule = (
            "\n\nREQUIRED HEADLINE: The user has specified an exact headline to use: "
            f'"{_required_headline}". '
            "ALL variants MUST use this exact string as their headline field, verbatim — "
            "every variant[].headline must be identical to this string. "
            "Variants differentiate through tone, subheadline, body copy, and CTA only. "
            "Do NOT alter, paraphrase, or replace this headline in any variant."
            if _required_headline else ""
        )

        input_text = (
            "VALIDATED BRIEF (from Logos):\n\n"
            + json.dumps(brief, indent=2)
            + "\n\nCREATIVE PLATFORM (from Helia — write inside this territory):\n\n"
            + json.dumps(platform, indent=2)
            + "\n\nCRITICAL COPY RULE: Never use a forward slash (/) inside any headline, "
            "subheadline, or endline string. Each headline is a single clean phrase — "
            "no slashes, no separators, no stylistic / devices. Slashes are NOT permitted "
            "anywhere in variants[].headline or variants[].subheadline."
            + _headline_rule
        )

        result = self._run_sync(input_text, rag_query=rag_query)

        # Strip any "/" that slipped into headline/subheadline strings.
        # The SKILL.md example used "/" to separate option listings; the LLM
        # sometimes treats it as a creative device within the headline itself.
        for variant in result.get("variants", []):
            for field in ("headline", "subheadline", "subline"):
                if field in variant and isinstance(variant[field], str):
                    variant[field] = variant[field].replace(" / ", " ").replace("/", " ").strip()

        return self._make_response(result, campaign_name=campaign_name)
