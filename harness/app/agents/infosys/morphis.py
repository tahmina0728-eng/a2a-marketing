"""
agents/infosys/morphis.py — MorphisAgent.

Morphis is the Infosys key-visual & ad-design agent.
It takes Helia's territory + Ideon's copy and produces a full visual production
spec: image-generation prompts (imagery layer), layout coordinates per size
(composite layer), lockup colourway, and QA notes.

Input:  {"creative_platform": HeliaAgentResponse, "copy_deck": IdeonAgentResponse}
Output: AgentResponse with artifact type "key_visual_spec"

Note: Morphis produces SPECS and IMAGE PROMPTS — actual compositing / rendering
is handled by the caller (HTML/CSS compositor, PIL, or Playwright).
The imagery prompt deliberately excludes logos, text, and brand marks;
those are composited deterministically from real approved artwork.
"""
from __future__ import annotations

import json

from app.agents.infosys.base import BaseInfosysAgent
from app.schemas.common import AgentResponse

_OUTPUT_SCHEMA = """{
  "campaign_name": "string",
  "territory": "string — territory name from Helia",
  "sub_brand": "string — e.g. Infosys Topaz",

  "template": "infosys | infosys-aster | topaz-cobalt | speaker",
  "modules": ["photoPanel | scrim | badge | partner | disclaimer — list only modules used"],

  "ground": {
    "name": "string — e.g. Sapphire Dark",
    "hex": "string — e.g. #061838",
    "white_contrast": "string — e.g. 17.57:1",
    "note": "string — accessibility reasoning"
  },

  "banner_master_1200x627": {
    "headline": "string — fits 546px column at 48px Semibold (≤18 chars/line, 2 lines max)",
    "headline_position": {"x": 126, "y": 208, "max_width": 546, "font_size": 48, "weight": "Semibold"},
    "subheading": "string (optional)",
    "subheading_position": {"y": 266, "font_size": 42},
    "body": "string (optional)",
    "body_position": {"y": 348, "font_size": 42, "variant": "Condensed"},
    "lockup_left": "string — which Infosys lockup file (e.g. Infosys-tagline_WB.png) at x=88",
    "lockup_right": "string or null — partner badge or null",
    "bar_device": "4 bars at x=0/70/1112/1182, y=262, size 18×120",
    "copy_colourway": "white on [ground]",
    "known_defects_fixed": ["string — e.g. 'copy column limited to 498px when photoPanel active'"]
  },

  "sizes": [
    {
      "name": "string — e.g. LinkedIn 1200×627",
      "dimensions": "string — e.g. 1200x627",
      "channel": "string — LinkedIn | X | Instagram | Display",
      "margin_note": "string — e.g. '~4% short edge, min 40px'",
      "copy_adjustments": "string — any copy trimming needed at this size",
      "lockup_note": "string — min 90px digital; sub-brand minimum unresolved if applicable"
    }
  ],

  "image_prompts": [
    {
      "for_sizes": ["string — list of sizes this prompt covers"],
      "aspect": "string — e.g. 16:9",
      "prompt": "string — art direction for imagery ONLY: scene, subject, mood, light, palette, composition with copy-zone negative space. NO text, NO logos, NO brand marks, NO identifiable real people, NO product screens, NO data/charts.",
      "negative_prompt": "string — elements to exclude",
      "copy_zone": "string — where to leave negative space for copy overlay",
      "label": "AI-generated concept — not for final production without rights clearance and brand/legal sign-off"
    }
  ],

  "qa_checklist": {
    "brand": ["string — each brand check to perform"],
    "accessibility": ["string — each accessibility check including feed-scale (0.46 for LinkedIn)"],
    "compliance": ["string — each compliance check"],
    "image_integrity": ["string — checks for generated imagery"]
  },

  "compliance_flags": ["string — each BLOCK: element + [APPROVED_...] token + routing"],
  "sign_off_required": ["string — brand | legal | partner (if co-brand)"],

  "display_spec": "string — complete key-visual set spec in the Morphis output format (all sections, per size)"
}"""


class MorphisAgent(BaseInfosysAgent):
    name = "morphis"
    artifact_type = "key_visual_spec"
    output_schema = _OUTPUT_SCHEMA

    def run(self, context: dict) -> AgentResponse:
        """
        context keys:
          creative_platform — HeliaAgentResponse
          copy_deck         — IdeonAgentResponse
          channels          — list[str]  (optional override, e.g. ["LinkedIn", "Display"])
          sizes             — list[str]  (optional override)
        """
        helia_output = context.get("creative_platform")
        ideon_output = context.get("copy_deck")

        platform = helia_output.artifact.content if helia_output and helia_output.artifact else {}
        copy     = ideon_output.artifact.content  if ideon_output and ideon_output.artifact else {}

        campaign_name = platform.get("campaign_name", copy.get("campaign_name", ""))
        territory     = platform.get("recommended_territory", "")
        sub_brand     = ""

        # Pull sub_brand from territory visual_cues if possible
        territories = platform.get("territories", [])
        for t in territories:
            if isinstance(t, dict) and t.get("name") == territory:
                sub_brand = t.get("visual_cues", "")[:60]
                break

        rag_query = " ".join(filter(None, [
            "Infosys banner template layout colour ground lockup",
            territory,
            context.get("channels", ["LinkedIn"])[0] if context.get("channels") else "LinkedIn",
        ]))

        channels_str = ", ".join(context.get("channels", ["LinkedIn", "Display"]))
        sizes_str    = ", ".join(context.get("sizes", [
            "LinkedIn 1200x627", "LinkedIn 1080x1080",
            "Display 300x250", "Display 728x90",
        ]))

        input_text = (
            "CREATIVE PLATFORM (from Helia — this defines the territory and visual world):\n\n"
            + json.dumps(platform, indent=2)
            + "\n\nCOPY DECK (from Ideon — use banner_copy and headline for the composite layer):\n\n"
            + json.dumps(copy, indent=2)
            + f"\n\nCHANNELS REQUIRED: {channels_str}"
            + f"\nSIZES REQUIRED: {sizes_str}"
            + "\n\nMorphis must:"
            + "\n1. Pick the correct banner master template and modules"
            + "\n2. Specify the ground colour (with hex and white contrast ratio)"
            + "\n3. Write image-generation prompts for the IMAGERY LAYER ONLY — no text, no logos"
            + "\n4. Specify the exact COMPOSITE LAYER coordinates for lockup, headline, CTA per size"
            + "\n5. Flag any known defects (panel/column overlap, sub-brand minimum) and how to fix them"
            + "\n6. Produce a QA checklist including feed-scale legibility (0.46 for LinkedIn)"
        )

        result = self._run_sync(input_text, rag_query=rag_query)
        return self._make_response(result, campaign_name=campaign_name)
