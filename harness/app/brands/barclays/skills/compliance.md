# Barclays Compliance Skill

Pre-flight check applied to all generated copy and creative before output. Barclays is a regulated financial services brand operating within the FCA framework.

## Inputs

| Field | Type | Description |
|---|---|---|
| `copy` | dict | Generated copy package (headline, subline, cta) |
| `image_prompt` | str | Final image/video generation prompt |
| `campaign_profile` | dict | Active campaign JSON |
| `channel` | str | Output channel |

## Copy checks

Loaded from `../brand.json → rules`:

- [ ] No forbidden jargon — see `brand.json → rules.no_financial_jargon`
- [ ] No rate, return, or performance claims
- [ ] No superlatives that imply superiority over competitors
- [ ] Headline works as a standalone statement (billboard test)
- [ ] Subline ≤ 20 words
- [ ] CTA ≤ 3 words

## Partnership checks

When `campaign_profile.type == "partnership"`, additionally verify:

- [ ] No specific player names or match results
- [ ] No unverified sponsorship claims beyond `campaign_profile.relationship.display_name`
- [ ] No fabricated partnership statistics or impact claims
- [ ] Avoid list enforced — see `campaign_profile.copy_rules.avoid`
- [ ] Partnership wording matches `campaign_profile.relationship.display_name` exactly when cited

## Visual / prompt checks

- [ ] No financial products, app screens, or bank branch imagery requested
- [ ] No trademarked logos or text in image generation prompt
- [ ] Campaign `visual_overrides.forbidden` list enforced
- [ ] `approved_assets.lockup.editable == false` — lockup text never reconstructed from strings

## Asset checks

- [ ] All logos sourced from `../assets.json` approved library
- [ ] Partnership lockup sourced from `approved_asset_library`, not dynamically generated
- [ ] `concepts.asset_requirements.licensed_assets` flag checked — flag for review when `true`

## Output

```json
{
  "pass": true | false,
  "flags": [
    { "rule": "...", "found": "...", "severity": "block" | "warn" }
  ]
}
```

Severity `"block"` prevents generation. Severity `"warn"` logs for human review.

## Migration note

Current compliance enforcement is implicit in `copy_prompt_block()` and `apply_overlay()`. Move here as an explicit pre-flight gate when transitioning to Skills architecture.
