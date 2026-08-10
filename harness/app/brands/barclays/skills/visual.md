# Barclays Visual Skill

Builds the final image and video generation prompts by combining brand profile, campaign profile, and concept creative direction. No brand colours or partnership claims are stored in concept files — this skill supplies them.

## Inputs

| Field | Type | Description |
|---|---|---|
| `creative_direction` | dict | Concept's `creative_direction` object from `concepts.json` |
| `campaign_profile` | dict | Active campaign JSON (e.g. wimbledon/campaign.json) |
| `channel` | str | `"instagram"` \| `"linkedin"` \| `"outdoor"` \| etc. |
| `aspect_ratio` | str | `"4:5"` \| `"1:1"` \| `"9:16"` \| `"16:9"` |
| `copy` | dict | Filled copy slots (headline, subline) |

## Brand profile

Loaded from `../brand.json`:

- **Palette**: Barclays Blue `#00AEEF`, Barclays Night `#1A2142`, White
- **Visual effects**: see `brand.json → visual.effects`
- **Subject style**: see `brand.json → visual.subject`
- **Background**: see `brand.json → visual.background`
- **Negative space**: left-side open for headline typography (T3 templates)

## Campaign visual overrides

When campaign profile is active, apply `campaign_profile.visual_overrides`:

- Restrict subjects to `visual_overrides.subjects`
- Restrict environment to `visual_overrides.environment`
- Apply `visual_overrides.lighting` and `visual_overrides.mood`
- Enforce `visual_overrides.forbidden` exclusions

## Output — image prompt

```
{creative_direction formatted block}
{brand palette instruction}
{campaign lighting / mood instruction}
{channel / aspect ratio composition note}
{negative prompt}
NO logos, NO text, NO brand marks in the generated image.
```

## Output — video prompt

For reel generation, read from `../campaigns/{id}/reel-concepts.json`:

- Apply `generation.negative_prompt` from the reel-concepts file
- One prompt per scene (`scene.visual` + `scene.camera` + `scene.audio`)
- Brand palette supplied here, not stored in scene definitions

## Composition layer (post-generation)

After model output, the composition engine adds (via `../__init__.py → apply_overlay()`):

- Barclays logo or partnership lockup (from approved asset library)
- Headline + subline typography
- Bottom bar
- Wimbledon shield (if campaign type is `partnership`)

## Migration note

Current prompt-building logic lives in `runner.py` (concept direction injection, `_BRAND_MAGIC`, `_BRAND_PALETTE_LOCK`). Move here when transitioning to Skills architecture.
