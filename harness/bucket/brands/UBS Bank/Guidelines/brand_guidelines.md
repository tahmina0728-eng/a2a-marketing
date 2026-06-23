---
name: ubs-brand-guidelines
description: Brand design assistant for UBS digital advertising and campaigns. Use whenever the user wants to design, review, or produce UBS-branded digital assets — Instagram posts, Stories/Reels, display banners (300×250, 728×90, 160×600), video pre-roll, campaign concepts, taglines, or on-brand copy — or asks for UBS colors, fonts, logo rules, accessibility specs, or a brand-compliant layout. Trigger this even when the user only says "make a UBS ad," "is this on-brand for UBS," "UBS social post," or names a UBS pillar (Wealth Management, Asset Management, Investment Bank), so every recommendation traces back to the brand brief instead of guesswork.
---

# UBS — Brand Guidelines for Digital Advertising

A working brand-guideline and campaign skill for UBS digital advertising. Every recommendation below traces back to the brand brief. Use real values (HEX/RGB, font names, exact pixel dimensions) — never vague advice.

> Scope note: This is an illustrative working guideline built from the supplied brief and publicly known UBS brand attributes (Swiss red, the three-keys logo, Frutiger typography). For any client-facing or production deliverable, validate final values against UBS's official brand portal and legal/compliance team. The font files (`Frutiger.ttf`, `Frutiger_bold.ttf`) were provided by the user; do not redistribute them — embed only where licensing permits, and fall back to Arial otherwise.

---

## How to use this skill

When asked to design or review a UBS digital asset, work through these four areas in order and tie each choice back to the brief:

1. **Brand brief** — confirm audience, the brand promise, personality, competitors, and the core feeling the ad must leave.
2. **Core identity** — apply the logo, color, type, imagery, iconography, and voice rules below.
3. **Digital advertising layer** — use exact platform specs, safe margins, motion, and accessibility rules.
4. **Sample campaign** — when proving the system, execute one idea across ≥3 formats with a right/wrong example.

Behavioral rules:
- Give specific, usable values, not vague guidance. "Frutiger Bold 64px, UBS Red `#E60000`, 64px margin" — not "use a bold font and red."
- Trace every recommendation to the brief. If a choice doesn't serve **trust, clarity, or precision**, reconsider it.
- Red is an **accent**, never a wash. Long copy is black on white/stone, or white on black.
- Always include the risk disclaimer on any asset that mentions investing, returns, or performance (see Voice & Tone).
- Offer to produce a downloadable document, layout spec, or pre-flight checklist when it would help.
- If the user hasn't said which pillar (Wealth / Asset Management / Investment Bank) or audience the asset targets, ask before finalizing copy and imagery.

---

## 1. Brand brief

**One-line positioning:** UBS is a global financial partner delivering integrated wealth and investment solutions to help clients achieve a clearer, more secure financial future.

**Core promise / north-star line:** *"Helping you discover a clearer financial future."*

**Audience:**
- High-net-worth individuals and families
- Entrepreneurs and business leaders
- Institutional investors
- Corporate clients

**Personality (5 adjectives):** Trusted · Expert · Precise · Reassuring · Global.
(Underlying brand values, expressed through the three-keys logo: confidence, security, success.)

**Brand pillars:**
1. **Wealth Management** — end-to-end planning, investing, philanthropy.
2. **Asset Management** — broad capabilities across traditional and alternative assets.
3. **Investment Bank** — advice, execution, and tailored solutions for institutions.

**Competitors (positioning reference):** Morgan Stanley Wealth Management, J.P. Morgan Private Bank, Goldman Sachs Private Wealth, Julius Baer, Deutsche Bank Wealth, BlackRock (asset management). *Note: Credit Suisse is now part of UBS — do not reference it as a competitor.*

**Competitive edge:** Integrated offering across wealth, asset, and investment banking; personalized long-term advisory; global reach with local expertise; Swiss heritage of trust and precision.

**Core feeling every ad must leave:** *"I have a precise, trustworthy expert who makes my financial future feel clear and within reach — calm, controlled confidence, never hype."*

---

## 2. Core identity

### 2.1 Logo system

The UBS logo is the **three keys** symbol (the keys of Zürich, representing confidence, security, success) set to the left of the **"UBS" wordmark** — used together as a horizontal lockup.

- **Clear space:** keep a minimum clear area equal to the **height of the three-keys symbol** (≈ the cap height of the "U") on all four sides. Nothing — text, image edge, or other logo — enters this zone.
- **Minimum size (digital):** keys-plus-wordmark lockup **24px tall** minimum on screen; **88px wide** minimum for the full lockup. For favicons/app tiles, use the keys symbol alone at **16px** minimum.
- **Color versions:** UBS Red `#E60000` keys + Black `#000000` wordmark on light backgrounds; all-white reversed lockup on Red, Black, or dark imagery. One-color black is allowed where color is unavailable.
- **Placement:** typically top-left or bottom-right of an ad; right-align in horizontal banners. Always on a clean, high-contrast area.

**Logo misuse — never:**
- Recolor the keys or wordmark to off-brand colors, gradients, or photos.
- Stretch, condense, rotate, or skew.
- Add drop shadows, outlines, bevels, or glows.
- Place on busy imagery or low-contrast backgrounds where clear space or contrast is lost.
- Recreate, re-typeset, or rearrange the keys/wordmark relationship.
- Box the logo or crowd it past its clear-space rule.

### 2.2 Color palette

| Role | Name | HEX | RGB |
|---|---|---|---|
| Primary | UBS Red | `#E60000` | 230, 0, 0 |
| Primary | Black | `#000000` | 0, 0, 0 |
| Secondary | White | `#FFFFFF` | 255, 255, 255 |
| Secondary | Stone (warm off-white) | `#F4F3EF` | 244, 243, 239 |

**Functional digital extensions** (label clearly when used; keep secondary to the four above):
| Role | HEX | RGB | Use |
|---|---|---|---|
| Secondary text / captions | `#595959` | 89, 89, 89 | Sub-copy, captions, disclaimers on white (≈7:1 contrast) |
| Hairlines / dividers | `#D8D6D0` | 216, 214, 208 | 1px rules, table borders on stone/white |

**Usage rules:**
- **Red = accent.** Use for the single emphasis element per layout (keyline, underline, CTA, the keys). Do not fill large backgrounds with red as a default; reserve full-bleed red for hero moments where one strong word/CTA sits on it.
- **Stone `#F4F3EF`** is the default calm background for editorial/advisory layouts; **white** for clean data and product layouts; **black** for premium/contrast moments.
- Backgrounds carry the structure; red carries the eye. Aim for roughly 70% neutral / 25% black type / 5% red.

### 2.3 Typography

| Level | Font | Web-safe fallback | Notes |
|---|---|---|---|
| Headline / display | **Frutiger Bold** | Arial Bold | Tight, confident, sentence case |
| Subhead | **Frutiger Regular** | Arial | |
| Body | **Frutiger Regular** | Arial | |
| CTA / button | **Frutiger Bold** | Arial Bold | |
| Legal / disclaimer | Frutiger Regular | Arial | Smaller, but must stay legible |

- **Web/email font stack:** `font-family: "Frutiger", Arial, Helvetica, sans-serif;`
- **Where Frutiger is not licensed for embedding (most web/email/3rd-party ad servers):** ship **Arial** as the live face — it is the designated secondary font, not a degraded fallback.
- **Case:** sentence case for headlines and body (advisory, human). Avoid all-caps for long strings; small caps acceptable for short labels.
- **Alignment:** left-aligned, ragged right. No justified body text.

**Digital type scale (square/1080-class assets):**
| Use | Size | Line height |
|---|---|---|
| Display headline | 64–88px Frutiger Bold | 1.05–1.1 |
| Subhead | 32–40px Frutiger Regular | 1.2 |
| Body | 24–28px Frutiger Regular | 1.4 |
| CTA label | 24–28px Frutiger Bold | 1.2 |
| Legal/disclaimer | 12–14px (min 12px) | 1.3 |

For small display banners, scale down proportionally (see §3) but never below the minimum legible sizes in §3.4.

### 2.4 Imagery & art direction

- **Mood:** calm, optimistic, precise. Controlled confidence — never aspirational excess or hype.
- **People:** real, credible clients and advisors; natural light; genuine moments (planning, conversation, looking ahead). Avoid clichéd stock — no staged handshakes, no money/gold imagery, no fist-pumps.
- **Composition:** Swiss-precision grid, generous neutral/stone space, strong horizon and alignment, clear single focal point.
- **Data visuals:** clean, minimal, honest. Thin lines, one red accent line/point, ample whitespace, no 3D, no decorative gradients. Charts must be readable and never misleading.
- **Signature device:** "blur-to-sharp" — imagery or data that resolves from soft focus into crisp clarity (visual metaphor for "a clearer financial future").

### 2.5 Iconography

- Geometric line icons, **consistent 2px stroke**, rounded-to-square terminals matching Frutiger's tone.
- Single weight per set; monochrome (black on light, white on dark); red only for an active/emphasis state.
- Functional and literal — clarity over decoration. The three-keys motif may inspire a recurring graphic device but is not an icon for reuse.

### 2.6 Voice & tone

- **Professional and advisory** — speaks as a trusted expert partner.
- **Clear, structured, insightful** — short sentences, no jargon, confident.
- **Reassuring and long-term** — calm, secure, never hype or pressure.

On-brand line examples: *"Discover a clearer financial future." / "Advice tailored to your needs." / "A total wealth solution."*

**Mandatory risk disclaimer** — include on any asset mentioning investing, returns, or performance:
> *"The value of investments can go down as well as up. You may not get back the amount you invested."*
Plus the required entity/regulatory line per market. Place legibly (see §3.4) — small is fine, illegible is not.

---

## 3. Digital advertising layer

### 3.1 Platform specs

| Format | Dimensions | Ratio | Notes |
|---|---|---|---|
| Instagram feed | 1080×1080 | 1:1 | Primary social unit |
| Instagram Stories / Reels | 1080×1920 | 9:16 | Full-screen vertical |
| Display — MPU | 300×250 | — | Standard rectangle |
| Display — Leaderboard | 728×90 | — | Top-of-page horizontal |
| Display — Skyscraper | 160×600 | — | Vertical sidebar |
| Video | 1920×1080 (16:9) + 1:1 + 9:16 cuts | — | Bumper 6s, standard 15s / 30s |

### 3.2 Layout & safe margins

- **1080×1080:** 64px outer margin all sides. Logo top-left or bottom-right within margin; one headline, one CTA.
- **1080×1920 Stories:** 64px side margins. Reserve **top ~250px** and **bottom ~340px** for platform UI/CTA sticker — keep logo, headline, and disclaimer inside the central safe zone.
- **728×90:** 16px padding; logo lockup right-aligned, headline + CTA left/center. One message only.
- **300×250:** 20px padding; stacked headline → CTA → logo. Keep to a single idea.
- **160×600:** 16px padding; vertical stack, logo at top or bottom, generous spacing.
- **Video 1920×1080:** keep text within **title-safe (90%)** and graphics within **action-safe (93%)**; hold an end card ≥2s with logo + disclaimer.
- Across all formats: align to a grid, lead with one headline, never crowd the logo's clear space.

### 3.3 Motion guidelines

- **Easing:** `cubic-bezier(0.4, 0.0, 0.2, 1)` (ease-in-out) — calm and precise. No bounce/elastic.
- **Durations:** micro-interactions 200–300ms; scene transitions 400–600ms; pre-roll 6s / 15s / 30s.
- **Signature motion:** the "blur-to-sharp" focus resolve as the headline lands; red enters as an underline/keyline reveal — never a full-screen flash.
- **Accessibility:** no content flashing more than 3 times per second (WCAG 2.3.1). Captions/subtitles on all video; legible end-card disclaimer held ≥2s.
- **Pacing:** unhurried and confident; let whitespace and a single message breathe.

### 3.4 Accessibility (WCAG 2.1 AA)

**Contrast minimum 4.5:1 for normal text, 3:1 for large text (≥24px regular / ≥18.66px bold).** Verified pairs for the UBS palette:

| Foreground / Background | Ratio | Normal text | Large text |
|---|---|---|---|
| Black `#000000` on White `#FFFFFF` | 21:1 | ✅ | ✅ |
| Black on Stone `#F4F3EF` | ~19:1 | ✅ | ✅ |
| White `#FFFFFF` on Red `#E60000` | ~4.8:1 | ✅ (just) | ✅ |
| Red `#E60000` on White | ~4.8:1 | ✅ (just) | ✅ |
| Red `#E60000` on **Black** | ~4.4:1 | ❌ **fails** | ✅ only |
| Black `#000000` on **Red** | ~4.4:1 | ❌ **fails** | ✅ only |
| `#595959` on White | ~7:1 | ✅ | ✅ |

**Practical rules from the above:**
- **Never set body/small text in red on black, or black on red** — both fall below 4.5:1. Use red on black only for large display words (≥24px), and prefer **white on red** or **black on white/stone** for anything readable.
- Red-on-white and white-on-red pass but only just (~4.8:1) — don't shrink red copy below body size.
- Use `#595959` for secondary/legal copy on white when full black is too heavy; it stays AA-safe.

**Minimum legible mobile font sizes:**
- Body: **16px** minimum (prefer 18–24px on social).
- Captions/secondary: 14px minimum.
- Legal/disclaimer: **12px** minimum on social/large units; **11px** absolute floor on small display banners — never sacrifice legibility to fit.
- Tap targets ≥44×44px; don't rely on color alone to convey meaning (pair red with text/underline).

---

## 4. Sample campaign — "Clearer."

**Concept:** A "blur-to-sharp" system. Each asset opens soft/out-of-focus and resolves into crisp clarity exactly as the headline lands — the literal expression of *"a clearer financial future."* Swiss-precision grid, stone whitespace, red as the single accent (an underline that draws under the key word).

**Tagline:** *"A clearer financial future, tailored to you."*
Supporting lines: *"See what's possible." / "Clarity, by design."*

**Why it's on-brand:** clarity + precision (Swiss heritage), tailored = client-focused advisory, calm confidence = reassuring tone. Red stays an accent; neutral structure carries trust.

### Executions (≥3 formats)

**A. Instagram feed — 1080×1080**
- Background: Stone `#F4F3EF`. 64px margins.
- Frame 1 (motion): client portrait soft/blurred. Frame 2: snaps sharp as headline appears.
- Headline (Frutiger Bold ~72px, Black): "A clearer financial future" with **"clearer"** underlined in UBS Red `#E60000`.
- Subline (Frutiger Regular 32px, `#595959`): "Advice tailored to your needs."
- CTA (Frutiger Bold 26px, white on a red `#E60000` pill): "Speak to an advisor".
- Logo bottom-right (white-area, clear space respected). Disclaimer 12px along the bottom margin.

**B. Instagram Story — 1080×1920**
- Full-bleed image, dark gradient lower third; content inside central safe zone (top 250 / bottom 340 reserved).
- Headline mid-frame (Frutiger Bold 80px, white): "See what's possible." — red underline reveal.
- CTA sticker zone left for the platform "Learn more" swipe; logo top-left (reversed white). Disclaimer 12px above the bottom safe margin.

**C. Display MPU — 300×250**
- White background, 20px padding.
- Headline (Frutiger Bold 26px, Black, two lines): "A clearer financial future." Red underline under "clearer."
- CTA button (Frutiger Bold 14px, white on red): "Find out more".
- Logo bottom-right (Red keys + Black wordmark). Legal 11px single line at the very bottom.
- *(Optional 4th: 728×90 leaderboard — logo right, headline + red-underline left, CTA center.)*

### Right vs. wrong

| Element | ✅ Right | ❌ Wrong |
|---|---|---|
| Red usage | Red as a single underline/CTA accent | Full red background flooded with red text |
| Contrast | Black headline on stone; white CTA text on red | Red body text on a black panel (≈4.4:1 — fails AA) |
| Type | Frutiger Bold headline, sentence case, left-aligned | All-caps, justified, mixed fonts, centered blocks |
| Logo | Clear space respected, correct lockup, bottom-right | Stretched, recolored, drop-shadowed, crowded |
| Layout | One message, grid-aligned, generous stone space | Multiple competing messages, cluttered, no margins |
| Compliance | Risk disclaimer present and legible (≥12px) | Disclaimer omitted or shrunk to an illegible size |
| Tone | "Advice tailored to your needs." | "Get rich fast — guaranteed returns!" |

---

## 5. Pre-flight checklist (use before shipping any UBS asset)

- [ ] Choice traces to the brief (trust / clarity / precision; correct pillar + audience).
- [ ] Correct dimensions and safe margins for the placement (§3.1–3.2).
- [ ] Logo: correct lockup, clear space respected, ≥ minimum size, no misuse.
- [ ] Colors from the approved palette; red used as accent (~5% of layout).
- [ ] Frutiger (or Arial fallback) only; sizes ≥ minimum legible (§3.4); left-aligned, sentence case.
- [ ] All text/background pairs meet AA contrast — **no red-on-black or black-on-red body text**.
- [ ] Risk disclaimer present and legible wherever investing/returns are mentioned.
- [ ] Motion: ease-in-out, no flashing >3×/sec, captions on video, end card ≥2s.
- [ ] One clear message; calm, confident, reassuring tone.

---

## 6. Quick reference

- **Promise:** "Helping you discover a clearer financial future."
- **Colors:** Red `#E60000` (230,0,0) · Black `#000000` · White `#FFFFFF` · Stone `#F4F3EF` (244,243,239).
- **Type:** Frutiger Bold (headlines) / Frutiger Regular (body) → Arial fallback. Stack: `"Frutiger", Arial, Helvetica, sans-serif`.
- **Accessibility floor:** 4.5:1 normal text; body ≥16px; legal ≥12px (≥11px small banners).
- **Red rule:** accent only — never body text on black, never a default background wash.
