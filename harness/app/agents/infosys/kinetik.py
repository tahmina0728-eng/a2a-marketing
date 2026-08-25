"""
agents/infosys/kinetik.py — KinetikAgent.

Kinetik is the Infosys motion & reels agent.
It turns Helia's territory + Ideon's script + Morphis's key visuals into a full
motion production spec: storyboard, footage prompts, format scaling across all
ratios and cutdowns, caption timing, end-frame spec, and compliance flags.

Input:  {
    "creative_platform": HeliaAgentResponse,
    "copy_deck":         IdeonAgentResponse,
    "key_visual_spec":   MorphisAgentResponse  (optional — used for ground + lockup)
}
Output: AgentResponse with artifact type "motion_spec"

Note: Kinetik produces SPECS and FOOTAGE PROMPTS — actual video assembly is handled
by the caller (ffmpeg, HTML motion template, Veo, etc.).
Footage prompts exclude logos, text, brand marks, and identifiable real people;
those are composited deterministically from real approved artwork.
"""
from __future__ import annotations

import json

from app.agents.infosys.base import BaseInfosysAgent
from app.schemas.common import AgentResponse

_OUTPUT_SCHEMA = """{
  "campaign_name": "string",
  "territory": "string — territory name from Helia",
  "sub_brand": "string",
  "story_spine": "string — the six-beat arc: situation → tension → stake → navigable path → Infosys alongside → outcome",

  "storyboard": [
    {
      "beat": 1,
      "time_range": "string — e.g. '0:00–0:06'",
      "visual_direction": "string — what the footage layer shows (no logos/text/brand marks)",
      "super": "string — on-screen text/title to composite",
      "vo": "string — voiceover line",
      "caption": "string — burnt-in caption text (same content as VO for accessibility)",
      "note": "string — any framing or pacing note"
    }
  ],

  "end_frame": {
    "ground": "string — e.g. Sapphire Dark #061838 (white 17.57:1)",
    "lockup": "string — which approved lockup file and colourway",
    "endline_super": "string — the hero endline",
    "cta": "string",
    "proof_tokens": ["string — [APPROVED_...] tokens shown on-screen"],
    "duration_seconds": 3,
    "accessibility_note": "string — e.g. 'CTA uses Sapphire Dark, not Infosys Blue, because Blue is 4.50:1 — fine for large endline but not small CTA'"
  },

  "format_specs": [
    {
      "ratio": "string — 9:16 | 1:1 | 4:5 | 16:9",
      "size": "string — e.g. 1080x1920",
      "channels": ["string"],
      "durations": ["string — e.g. '15s', '30s'"],
      "reframe_note": "string — how subject is repositioned vs. master",
      "safe_zone_top_pct": 14,
      "safe_zone_bottom_pct": 20,
      "bar_device_note": "string — how the 4-bar motif (18×120) is adapted for this ratio",
      "caption_note": "string — legibility and timing note"
    }
  ],

  "footage_prompts": [
    {
      "for_beats": ["string — beat numbers this prompt covers"],
      "for_ratios": ["string"],
      "prompt": "string — art direction for FOOTAGE ONLY: scene, action, mood, light, colour. NO text, NO logos, NO identifiable real people, NO product screens, NO dashboards, NO data.",
      "negative_prompt": "string",
      "framing_note": "string — protect-for-all framing instruction",
      "label": "AI-generated concept footage — rights clearance + brand/legal sign-off required; provenance metadata intact"
    }
  ],

  "music_direction": "string — tempo, mood, arc; muted version note",

  "qa_checklist": {
    "safe_zones": ["string — each zone check per ratio"],
    "caption_legibility": ["string — legibility and timing checks"],
    "brand": ["string — lockup colourway, bar device, colour set, no gradients"],
    "accessibility": ["string — captions, audio description, flashing check (≤3 flashes/sec)"],
    "compliance": ["string — each regulated element check"],
    "footage_integrity": ["string — no generated logos, text, identifiable people"]
  },

  "compliance_flags": ["string — BLOCK: element + [APPROVED_...] token + routing"],
  "sign_off_required": ["string — brand | legal | partner (co-brand) | rights clearance (footage/likeness)"],

  "display_spec": "string — complete motion set spec in the Kinetik output format (all sections, storyboard + format grid)"
}"""


class KinetikAgent(BaseInfosysAgent):
    name = "kinetik"
    artifact_type = "motion_spec"
    output_schema = _OUTPUT_SCHEMA

    def run(self, context: dict) -> AgentResponse:
        """
        context keys:
          creative_platform — HeliaAgentResponse (required)
          copy_deck         — IdeonAgentResponse (required — uses scripts block)
          key_visual_spec   — MorphisAgentResponse (optional — ground + lockup reference)
          formats           — list[str]  (optional override, e.g. ["9:16", "1:1", "16:9"])
          durations         — list[str]  (optional override, e.g. ["15s", "30s"])
        """
        helia_output  = context.get("creative_platform")
        ideon_output  = context.get("copy_deck")
        morphis_output = context.get("key_visual_spec")

        platform = helia_output.artifact.content  if helia_output and helia_output.artifact  else {}
        copy     = ideon_output.artifact.content   if ideon_output and ideon_output.artifact   else {}
        kv_spec  = morphis_output.artifact.content if morphis_output and morphis_output.artifact else {}

        campaign_name = platform.get("campaign_name", copy.get("campaign_name", ""))

        rag_query = " ".join(filter(None, [
            "Infosys video motion reel format safe margins caption end-frame",
            platform.get("recommended_territory", ""),
        ]))

        formats_str   = ", ".join(context.get("formats", ["9:16", "1:1", "4:5", "16:9"]))
        durations_str = ", ".join(context.get("durations", ["15s", "30s"]))

        input_parts = [
            "CREATIVE PLATFORM (from Helia — territory, story spine, big idea):\n\n"
            + json.dumps(platform, indent=2),

            "\n\nCOPY DECK SCRIPTS (from Ideon — use the scripts block for VO, supers, captions):\n\n"
            + json.dumps(copy.get("scripts", copy), indent=2),
        ]

        if kv_spec:
            input_parts.append(
                "\n\nKEY VISUAL SPEC (from Morphis — reuse the ground, lockup, and bar device):\n\n"
                + json.dumps({
                    "ground":      kv_spec.get("ground"),
                    "template":    kv_spec.get("template"),
                    "end_frame_reference": kv_spec.get("banner_master_1200x627", {}).get("lockup_left"),
                }, indent=2)
            )

        input_parts += [
            f"\n\nFORMATS REQUIRED: {formats_str}",
            f"DURATIONS REQUIRED: {durations_str}",
            "\n\nKinetik must:",
            "1. Beat out the story spine with VO, supers, and burnt-in captions for every beat",
            "2. Specify footage prompts (imagery layer only — no text, logos, identifiable people)",
            "3. Specify safe margins and reframe notes for each ratio",
            "4. Carry the 4-bar device across all ratios (flush edges, 18×120)",
            "5. Specify the end-frame: lockup + endline + CTA on Sapphire Dark #061838",
            "6. Flag every regulated element as [APPROVED_...] token",
            "7. Include a QA checklist with a no-flashing check (≤3 flashes/sec)",
        ]

        input_text = "".join(input_parts)

        result = self._run_sync(input_text, rag_query=rag_query)
        return self._make_response(result, campaign_name=campaign_name)
