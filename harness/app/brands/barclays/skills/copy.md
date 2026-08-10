# Barclays Copy Skill

Generates brand-compliant copy for Barclays campaigns. Reads rules from `../brand.json` and injects campaign-specific direction from the active campaign profile.

## Inputs

| Field | Type | Description |
|---|---|---|
| `machine_brief` | dict | Campaign brief from the brief form |
| `campaign_profile` | dict | Active campaign JSON (e.g. wimbledon/campaign.json) |
| `copy_slot` | str | `"headline"` \| `"subline"` \| `"cta"` \| `"mid_reel"` \| `"end_frame"` |
| `max_words` | int | Word limit for the slot |

## Rules

Loaded from `../brand.json → copy_rules`:

- **Platform**: quiet confidence, human truth, never hype
- **Headline**: understated, emotionally resonant, billboard-scale standalone
- **Subline**: completes the headline's territory; ≤ 20 words; no financial jargon
- **CTA**: max 3 words; never salesy
- **Forbidden words**: see `brand.json → rules.no_financial_jargon`

## Campaign overlay

When `campaign_profile.type == "partnership"`:

- Read `campaign_profile.copy_rules.creative_direction` for allowed narrative themes
- Read `campaign_profile.copy_rules.avoid` for prohibited claims
- Never mention specific players, match results, or financial products

## Output

```json
{
  "headline": "...",
  "subline":  "...",
  "cta":      "..."
}
```

## Migration note

Current logic lives in `../__init__.py → copy_prompt_block()` and `copy_agent` block in `runner.py`. Move here when transitioning to Skills architecture.
