# DESIGN.md — Tempo · WC2026 AI Predictor

> Single source of truth for all visual decisions in the Tempo presentation layer.
> When DESIGN.md conflicts with code, the code is wrong.
> When CLAUDE.md §7 is trimmed to a one-line pointer, this file becomes the sole visual specification.
>
> Re-read this file at the start of every UI work step.

---

## 0. Document Status

Created: 2026-06-20. Elevated (impeccable pass): 2026-06-20. Branch: `ui/overhaul`.

**Step 1 ✓** — donut ban enforced in `today.py`; dead `_prob_donut` removed from `match_detail.py`.

**Path A scope (~85%):** Streamlit app visual overhaul — tokens, components, charts, copy rules.
Excluded: Bracket/simulation page (pending R6), share card (C6 checkpoint), README (written last).

---

## 1. Mission & Register

**Register:** App / dashboard — design serves the product. Prediction data is the product; design makes it legible, credible, and beautiful.

**Product:** Tempo — a daily-updated AI match-outcome predictor for FIFA World Cup 2026, presented through a broadcast-grade sports dashboard.

**Audience:** Recruiters, technical reviewers, football fans. Heavy mobile traffic from LinkedIn.
Mobile-first is mandatory — no horizontal scroll at 375px.

**Physical scene:** A football fan or recruiter opens this on their phone after clicking a LinkedIn post. Dark ambient light — commute, evening, stadium. The interface must read immediately, show predictions clearly, and feel like it belongs on a sports network, not a homework folder.

**Theme:** Dark primary. Sports dashboards are universally dark; the ambient-light argument is strong. Light theme is a supported toggle. Dark is the design identity.

---

## 2. Color System

All tokens live in `src/presentation_layer/theme.py` as Python constants and are injected as CSS custom properties via `apply_global_css()`. **Never use raw hex values in components — always `var(--token-name)`.**

### 2a. Dark palette (default)

| Token | Value | Semantic role |
|---|---|---|
| `--bg` | `#0B0B0D` | Page background (warm near-black) |
| `--surface` | `#141417` | Card background |
| `--surface-raised` | `#1C1C21` | Elevated / hover / dropdown |
| `--border` | `#2A2A31` | Hairlines, dividers |
| `--text` | `#F4F1EA` | Primary text (~15:1 on `--bg` ✓) |
| `--text-muted` | `#A7A39B` | Secondary text (~6:1 on `--bg` ✓) |
| `--gold` | `#E8B84B` | Signature accent: large numbers, favored pick, active nav, focus ring |
| `--gold-bright` | `#FFD66B` | Gold hover / active |
| `--win` | `#1FB479` | Home / favored outcome (Mexico green / Wave 1) |
| `--draw` | `#3E7BFA` | Draw outcome (USA blue / Wave 2) |
| `--loss` | `#E4564A` | Away / underdog outcome (Canada red / Wave 3) |

### 2b. Win / Draw / Loss = Host-Nation Triad

This mapping is **deliberate and semantic** — green/blue/red = Mexico/USA/Canada. The probability bar reads as "World Cup" instantly. Never swap these colors.

### 2c. Gold usage rules

Gold (`--gold`) is permitted for:
- Large numerals (metric values, confidence %)
- The favored-pick indicator and dot
- Active nav item text and border
- Focus rings (`outline: 2px solid var(--gold)`)
- Primary buttons (background)

Gold is **not** for body copy, section headings, or decoration.

### 2d. Segment text on probability fills

Text inside `--win`/`--draw`/`--loss` fills uses dark tints — never `--text` or white:
- On `--win` fill: `#0a3d27`
- On `--draw` fill: `#0d1e52`
- On `--loss` fill: `#4a0f0a`

These pass ≥4.5:1 contrast on the respective fill colors.

### 2e. Light palette (toggle)

Same token names; lighter values defined in `_LightPalette`. Both themes must pass WCAG 2.2 AA contrast for all text. Verify before shipping any light-mode change.

### 2f. Color strategy

**Strategy: Full palette.** Four named roles, each used deliberately. The palette is closed — never add a fifth color without removing one.

| Role | Tokens | Purpose |
|---|---|---|
| **Neutral** | `--bg` `--surface` `--surface-raised` `--border` `--text` `--text-muted` | Foundation — never decorative |
| **Gold** | `--gold` `--gold-bright` | Identity accent — see §2c rationing |
| **Outcome triad** | `--win` `--draw` `--loss` | Data viz only — color as signal, not decoration |

Color here is data. The probability bar and ternary carry the palette. Everywhere else is neutral.

---

## 3. Typography

### 3a. Font stack

| Role | Family | Weights | Use |
|---|---|---|---|
| Display | Archivo | 800, 900 | Page h1, team names, sidebar brand, section headings |
| Body | Inter | 400, 500, 600 | Prose, labels, sidebar nav, chip text, factor chips |
| Mono | JetBrains Mono | 400, 600 | All stats / %, scores, timestamps, code, match chips |

All three fonts load from Google Fonts via `styles.py`. `font-variant-numeric: tabular-nums` on all mono elements.

### 3b. Scale

| Context | Size | Family | Weight |
|---|---|---|---|
| Page h1 | 2rem (32px) | Archivo | 900 |
| Team name (card) | 0.98rem | Archivo | 800 |
| Team name (hero) | 1.25–1.3rem | Archivo | 800 |
| Sidebar brand | 1.55rem | Archivo | 900 |
| Metric value | 1.65–1.75rem | JetBrains Mono | 700 |
| Body / prose | 1rem (16px) | Inter | 400 |
| Subtitle | 0.87rem | Inter | 400 |
| Section heading | 0.78rem | Archivo | 800 |
| Widget label | 0.75rem | Inter | 600 |
| Prob bar label | 0.62–0.72rem | JetBrains Mono | 400–700 |
| Chip / stamp | 0.66–0.68rem | JetBrains Mono | 400 |

### 3c. Typography rules

- Body line length: cap at 65–75ch. Never full-width prose blocks.
- Display letter-spacing: `-0.02em` on h1. Floor is `-0.03em` — tighter reads cramped.
- `text-transform: uppercase` only on section headings (`.sec-heading`) and mono chips — never on primary text.
- Minimum readable text: 16px body, 0.66rem (10.6px) for chips/stamps only.
- `text-wrap: balance` on h1–h3 for even line lengths where supported.
- `text-wrap: pretty` on body prose paragraphs (≥3 lines) to prevent orphaned last words.

---

## 4. Spacing & Layout

### 4a. Scale

`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64px` — 4pt base, 8pt rhythm.

### 4b. Layout rules

- Max content width: 1400px (enforced in `styles.py` / `apply_global_css`).
- Main padding: 2rem horizontal, 1.5rem top, 3rem bottom.
- Mobile (≤480px): 0.75rem horizontal, respect iOS safe-area insets.
- Match card grid: `st.columns(2)`. Single column on mobile (Streamlit responsive).
- Section dividers: `border-bottom: 1px solid var(--border)` on `.sec-heading`. Full `<hr>` only as a visual separator between major sections.

---

## 5. Radius, Shadow & Motion

### 5a. Radius tokens

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | 8px | Buttons, inputs, chips, inner elements |
| `--radius-md` | 12px | Match cards, dropdowns, metric containers |
| `--radius-lg` | 16px | No-data state, large containers only |

**Match cards must use `--radius-md` (12px).** The current code uses `--radius-lg` (16px) — over-rounded for a broadcast panel. Fix in Step 2.

### 5b. Shadow rules

- Default card state: **no `box-shadow`**. Border only.
- Hover state only: `0 8px 32px rgba(0,0,0,0.45)` + `0 0 0 1px rgba(232,184,75,0.08)`.
- Never pair `border: 1px solid X` + wide drop-shadow (blur > 8px) in the default (non-hover) state.

### 5c. Motion tokens

| Token | Value | Use |
|---|---|---|
| `--anim-fast` | 150ms | Button hover, border transitions |
| `--anim-normal` | 200ms | Card hover, metric updates |
| `--anim-slow` | 300ms | Page-level (rare) |

- Easing (use explicit `cubic-bezier()`, not the `ease` keyword):
  - `--anim-fast` (150ms): `cubic-bezier(0.25, 0, 0, 1)` — ease-out-quart
  - `--anim-normal` (200ms): `cubic-bezier(0.16, 1, 0.3, 1)` — expo-out
  - `--anim-slow` (300ms): `cubic-bezier(0.12, 0, 0.39, 0)` — ease-out-quint
- No bounce, no elastic. No x control-points outside [0, 1].
- Animated properties: `transform`, `opacity`, `border-color`, `box-shadow` only.
- `@media (prefers-reduced-motion: reduce)` disables all — maintained in `styles.py`. Keep it.

### 5d. Z-Index scale

Semantic named layers — never arbitrary values like 999 or 9999.

| Layer | Value | Use |
|---|---|---|
| `--z-base` | 0 | Normal document flow |
| `--z-sticky` | 100 | Sticky headers, floating clear-selection button |
| `--z-dropdown` | 200 | Streamlit dropdowns, multiselect popovers |
| `--z-modal-backdrop` | 300 | Overlay scrim |
| `--z-modal` | 400 | Modal dialogs |
| `--z-toast` | 500 | Toast / snackbar notifications |
| `--z-tooltip` | 600 | Plotly tooltips, custom tooltips (topmost) |

In Streamlit: apply to `.stPopover`, `.stTooltipContent`, and custom HTML overlays only. Never set arbitrary z-index on Streamlit-managed elements.

---

## 6. Signature Elements

### 6a. Probability Bar (primary signature — every match)

One horizontal bar per match, split: Home Win / Draw / Away Win.

- Colors: `--win` / `--draw` / `--loss` (host-nation triad).
- Label text: shown inside segment if ≥9%. JetBrains Mono 0.72rem bold. Dark-tint text per §2d.
- Below bar: three labels "Home win · Draw · Away win" in `--text-muted` 0.62rem mono.
- Track height: 28px. Gap between segments: 2px.
- Border-radius: `--radius-sm` on track; left-cap only on home segment, right-cap only on away.
- `role="img"` + `aria-label` with full spoken sentence on the track element.

### 6b. Tri-Color Accent Rail

- 3px horizontal bar at top of each page (`.accent-rail`) and top of each match card (`.match-card-rail`).
- `linear-gradient(90deg, var(--win) 0%→33%, var(--draw) 33%→66%, var(--loss) 66%→100%)`.
- **This is the single branded decoration. Do not add more decorative rails or lines.**

### 6c. Match Chip

- Pattern: `WC26 · Grp A · Fri 20 Jun · 20:00 UTC`.
- Style: JetBrains Mono 0.66rem, uppercase, `--text-muted` on `--surface-raised`, `1px solid var(--border)`, `border-radius: 6px`.

### 6d. Favored Chip

- Gold dot + "Favored: [flag] [Team] [confidence%]".
- Background: `rgba(--gold, 0.08)`, border: `rgba(--gold, 0.2)`, `border-radius: 20px`.
- Gold dot: `box-shadow: 0 0 6px rgba(232,184,75,0.6)`.

### 6e. Factor Chips

- Positive: green-tint bg + green text + green border.
- Negative: red-tint bg + red text + red border.
- Size: 0.67rem Inter 500, `border-radius: 5px`, `padding: 3px 8px`.

### 6f. Geo-Unit

- Square + quarter-circle SVG at ~6% opacity as card background texture.
- Never a primary visual. Never used as a logo or hero.

---

## 7. Component Inventory

### 7a. Sidebar Navigation (`app.py`)

**Anatomy:** Brand block → Radio nav → Legend block.

**States:**

| State | Background | Text color | Border |
|---|---|---|---|
| Default | transparent | `--text-muted` | transparent |
| Hover | `--surface-raised` | `--text` | transparent |
| Active | `rgba(--gold, 0.08)` | `--gold` | `rgba(--gold, 0.2)` |
| Focus | — | — | `outline: 2px solid var(--gold)` |

**Rules:**
- Radio circle hidden — label styling only.
- Brand name: Archivo 900, `--gold`, 1.55rem, `letter-spacing: -0.03em`.
- Brand sub: JetBrains Mono uppercase 0.68rem, `--text-muted`, `letter-spacing: 0.12em`.
- Legend: 0.68rem mono, `--text-muted`, color swatches + model info.

---

### 7b. Match Card (Fixture Ticket)

**Anatomy (top to bottom):**
1. `.match-card-rail` — 3px tri-color rail
2. `.match-card-body` — padding: `1.1rem 1.25rem`
3. `.match-chip` — group + date chip
4. `.match-teams` — home flag + name / VS divider / away flag + name
5. `.prob-bar-track` + `.prob-bar-labels` — probability bar
6. `.favored-chip` — gold favored indicator
7. `.factors-row` — up to 3 factor chips

**States:**

| State | Border | Shadow |
|---|---|---|
| Default | `1px solid var(--border)` | none |
| Hover | `rgba(--gold, 0.4)` | `0 8px 32px rgba(0,0,0,0.45)` + gold glow |

**Rules:**
- Border-radius: `--radius-md` (12px). Not `--radius-lg` (16px).
- No default `box-shadow`. Hover only.
- Team names: Archivo 800. `0.98rem` in 2-col grid, `1.25rem` in hero.
- VS divider: `--border` color, JetBrains Mono 0.72rem, border + `border-radius: 4px`.

---

### 7c. Metric Cards (`st.metric`)

- Background: `--surface`, border: `1px solid var(--border)`, radius: `--radius-md`.
- Label: 0.72rem uppercase Inter 600 in `--text-muted`.
- Value: 1.75rem JetBrains Mono 700 in `--gold`.
- Hover: border tints toward `rgba(--gold, 0.3)`.
- **RPS is always labeled the primary metric.** Accuracy labeled secondary.

---

### 7d. Section Heading (`.sec-heading`)

- Archivo 800, 0.78rem, uppercase, `--text-muted`, `letter-spacing: 0.1em`.
- `border-bottom: 1px solid var(--border)`, `padding-bottom: 0.4rem`.
- **One per section. No numbered markers (01/02/03). No eyebrow text above every section.**

---

### 7e. Data Stamp (`.data-stamp`)

- 0.68rem JetBrains Mono, `--text-muted`.
- Timestamp in `<code>` chip: `--surface-raised` bg, `--gold` text, `--border` border.
- Required on every page, at the bottom.
- Wording: `Data as of {timestamp} · Updates daily via batch`.
- **Never "live". Never "real-time".**

---

### 7f. No-Data State (`.no-data`)

- `border: 1px dashed var(--border)`, `border-radius: var(--radius-lg)`.
- Centered: Archivo 800 heading + Inter body + code chip for CLI command.
- No background fill.

---

### 7g. Icon Vocabulary

- **Library:** Lucide (inline SVG). Heroicons is acceptable where Lucide lacks coverage.
- **No emoji as icons** — see §9.
- **Sizes:** 16×16px (inline label), 20×20px (standard UI), 24×24px (section heading accent).
- **Stroke width:** 1.5px at all sizes.
- **Color:** `currentColor` — never hardcoded hex.
- **Touch targets:** icon-only interactive elements need a 44×44px tap target via padding or `min-width`/`min-height`.

---

### 7h. Loading & Skeleton States

When predictions are loading (pipeline not yet run, or `predictions.parquet` being written):

- **Match card skeleton:** `--surface-raised` background with animated shimmer sweeping left-to-right.
  ```css
  background: linear-gradient(90deg, var(--surface-raised) 0%, var(--border) 50%, var(--surface-raised) 100%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.4s cubic-bezier(0.16, 1, 0.3, 1) infinite;
  ```
  `@media (prefers-reduced-motion)`: animation off; static `--surface-raised` fill only.
- **Metric card skeleton:** `--surface` background, `--border` border, `--text-muted` "—" value.
- **Rule:** never mix real and placeholder rows. Show skeleton (loading) or no-data state (§7f, pipeline not run) — never both at once.

---

## 8. Visualization Rules

### 8a. Required charts (per CLAUDE.md §0.5)

| Chart | Page | Purpose |
|---|---|---|
| `Scatterternary` | Match Space | Matches in W/D/L space; click-to-filter |
| Per-match waterfall | Match Space detail, Match Detail | Base rate → calibrated probability |
| Reliability diagram + confidence histogram | Model Report | Credibility centrepiece |
| Cumulative RPS-vs-baseline line | Model Report | Model performance over time |

### 8b. Banned visualizations (per CLAUDE.md §0.5/§2)

- **Donut / pie charts** — banned everywhere, no exceptions.
- **Accuracy gauge** — banned. RPS is the headline.
- **Raw markdown tables** for critical prediction data — use `st.dataframe` or styled HTML.

### 8c. Violations — resolved (Step 1 ✓)

~~`today.py` rendered `_group_donut(upcoming)` — a banned donut chart in the "Outlook" section.~~
**Fixed:** replaced with 3-stat outcome summary (triad colors, tabular-mono counts).

~~`match_detail.py` contained a dead `_prob_donut` function.~~
**Fixed:** dead code removed.

No active visualization violations remain.

### 8d. Plotly style rules

- All charts: `template="plotly_dark"`, `paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`.
- Labels: `'Inter', sans-serif`. Tick values: `'JetBrains Mono', monospace`.
- Grid lines: `#2A2A31`. Axis labels: `--text-muted` (#A7A39B).
- Every chart must filter or reveal on interaction — never decorative.

---

## 9. Accessibility Requirements

**Target: WCAG 2.2 AA.**

### Contrast

| Element | Foreground | Background | Pass? |
|---|---|---|---|
| Body text | `--text` #F4F1EA | `--bg` #0B0B0D | ✓ ~15:1 |
| Muted text | `--text-muted` #A7A39B | `--bg` #0B0B0D | ✓ ~6:1 |
| Gold on bg (large) | `--gold` #E8B84B | `--bg` #0B0B0D | ✓ large text only |
| Prob bar text | dark tints (§2d) | `--win/draw/loss` | must verify per fill |
| Muted text on surface | `--text-muted` #A7A39B | `--surface` #141417 | ✓ ~5:1 |
| Muted text on surface-raised | `--text-muted` #A7A39B | `--surface-raised` #1C1C21 | ✓ ~4.8:1 |

### Keyboard & interaction

- Focus ring: `outline: 2px solid var(--gold); outline-offset: 2px` on all interactive elements.
- Touch targets: ≥44×44px, ≥8px spacing.
- No emoji as icons — inline SVG only. Flags from `flags.py` (SVG) are acceptable.

### Animation

- 150–300ms, `transform`/`opacity`/`border-color`/`box-shadow` only.
- `prefers-reduced-motion` disables all — maintained in `styles.py`.

### Aria

- Prob bar track: `role="img"` + `aria-label` with full spoken description.
- Icon-only buttons: `aria-label` required.

---

## 10. Content & Tone Rules

- **Data freshness:** "Updates daily via batch" + `data as of {timestamp}`. Never "live", never "real-time".
- **RPS:** Headline metric on Model Report. Accuracy shown as secondary — label it explicitly.
- **Predictions:** "Favored:" not "Winner". Never claim certainty.
- **Knockout matches:** Concrete teams only on Predictions page. Bracket slots only on Bracket page, labeled "Projected".
- **No hardcoded match data** — always from `predictions.parquet` or `data/tempo.db`.

---

## 11. Anti-Patterns

Match-and-refuse when reviewing code.

1. **Donut / pie charts** — banned everywhere.
2. **Accuracy gauge** — banned.
3. **"Live" / "real-time" copy** — use "updates daily via batch".
4. **Gradient text** (`background-clip: text` + gradient) — banned.
5. **Side-stripe borders** (colored `border-left` > 1px as card accent) — banned.
6. **Glassmorphism as default decoration** — banned.
7. **Numbered eyebrow section markers** (01 / 02 / 03) — banned.
8. **Multiple decorative horizontal lines** — only the tri-color accent rail permitted.
9. **Default `box-shadow` on cards** — hover state only.
10. **Raw hex in component HTML** — all `var(--token)`.
11. **`border-radius` > 12px on match cards** — 12px (`--radius-md`) max.
12. **Placeholder knockout matchups on Predictions page** — only concrete teams shown.

---

## 12. Path A — UI Overhaul Steps

Steps executed one at a time. App must be runnable after each. Each step committed separately.

| Step | File(s) to touch | Change |
|---|---|---|
| **0 ✓** | `DESIGN.md`, branch `ui/overhaul` | This file. Source of truth established. |
| **1 ✓** | `today.py`, `match_detail.py` | Remove banned `_group_donut`; replace "Outlook" with 3-stat outcome summary; remove dead `_prob_donut` |
| **2** | `theme.py` (CSS in `apply_global_css`) | Fix match card `border-radius` to `--radius-md`; tighten h1 letter-spacing |
| **3** | `today.py` | Match card chip and team layout polish |
| **4** | `model_report.py` | RPS headline prominence; baseline row; section heading cleanup |
| **5** | `match_space.py` | Detail panel layout; prob display using prob-bar classes |
| **6** | `match_detail.py` | Tighten layout (dead code already removed in Step 1) |
| **7** | `app.py`, `styles.py` | Sidebar polish: brand spacing, legend, nav refinements |

Steps beyond Step 2 are subject to explicit approval before starting.

---

## 13. QA Checklist

Run before marking any step done:

- [ ] `streamlit run src/presentation_layer/app.py` launches without Python errors
- [ ] All four pages render (with real `predictions.parquet` present)
- [ ] No raw hex values in component HTML — all `var(--token)`
- [ ] No donut / pie charts on any page
- [ ] No "live" or "real-time" copy on any page
- [ ] Probability bar: segments sum to 100%, labels visible where ≥9%, aria-label present
- [ ] Gold used only for: numerals, favored chip, active nav, focus ring, primary button
- [ ] Body text contrast ≥4.5:1 (spot-check with browser devtools)
- [ ] Focus ring visible on keyboard tab navigation
- [ ] `data as of {timestamp}` stamp present on every page
- [ ] Mobile: no horizontal scroll at 375px viewport
- [ ] `prefers-reduced-motion` honored
- [ ] No trademark-protected assets rendered (§14)

---

## 14. Trademark & IP Guardrail

This is a public portfolio piece. Evoke the tournament; never copy protected assets.

**Never reproduce:**
- The FIFA emblem
- The stylized "26" wordmark
- The World Cup trophy image
- The mascots (Maple, Zayu, Clutch)
- The "Trionda" ball graphic
- The official FIFA typeface

**Use only:**
- Tempo's own geometric square + quarter-circle motif (the geo-unit — §6f)
- The palette from §2
- Plain-text team names
- Public-domain country flags (rendered via `flags.py`, SVG)

When in doubt, make it ourselves. The geo-unit is Tempo's visual identity — it evokes the tournament without replicating any protected mark.
