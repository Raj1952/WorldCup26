# CLAUDE.md — Tempo · World Cup 2026 Match Outcome Predictor

> This file is the operating contract for Claude Code on this repository. Read it in
> full at the start of every session before writing or changing code. It defines what
> we are building, how it is structured, the rules you must follow, the design system,
> and the exact points where you must **STOP and ask the human (Raj)** instead of
> guessing or burning tokens.
>
> The project name is **Tempo** — the rhythm of the tournament, re-read every matchday.
> If the name ever changes, it changes in ONE place: the `APP_NAME` constant and the
> database filename. Do not scatter the name across the codebase.

---

## 0. Mission (read this first)

Build **Tempo** — a daily-updated system that predicts the outcome
(Home win / Draw / Away win) of every remaining FIFA World Cup 2026 match **that has
known teams**, re-evaluates as real results come in, explains *why* it made each
prediction, and presents it through a broadcast-grade dashboard themed authentically
around the World Cup 2026 — so it looks like it belongs on a sports network, not in a
homework folder.

This is a **public portfolio piece**. The owner posts predictions on LinkedIn *before*
matches kick off and the result *after*. The system must be:

1. **Real** — predictions come from a trained model on real data, never hardcoded.
2. **Fresh, not faked** — ingests actual 2026 results on a **daily batch** and
   re-evaluates forward. No "live / real-time" claims anywhere (see §0.5 and §3).
3. **Accurate & honest** — **RPS-first**, un-inflated metrics. The public sees these
   numbers; a wrong claim is worse than a modest true one.
4. **Explainable** — every prediction ships with the drivers that moved it (native
   XGBoost `pred_contribs`), reconciled to the **calibrated** probability (see §0.5).
5. **Beautiful & on-theme** — the UI is the first impression. Treat it as the product.
6. **Clean-room** — see §1. Nothing inherited from any other project.

If a change would compromise any of these, raise it before doing it.

---

## 0.5 Architectural Pivot & Technical Constraints (Post-Council Review) — AUTHORITATIVE

**This section takes precedence over anything earlier or later in this file that
conflicts with it.** It is the result of a senior data-engineering + UI/UX review.

### Overrides (these earlier ideas are now retired)
- Any "live / real-time / self-updating" phrasing → replaced by **"updates daily via batch."**
- **Accuracy** as the headline metric → replaced by **RPS** (Ranked Probability Score).
  Accuracy may appear as a secondary number, never as the headline.
- Any **donut chart** or **accuracy gauge** in the page specs → **removed** (see viz rules).
- The **Monte Carlo bracket sim is no longer optional**. It is a **required dependency**
  for displaying any knockout match.

### 1. Core metrics & validation
- **Primary metric: RPS** for the ordered 3-outcome forecast (Home/Draw/Away). RPS
  rewards being *close* (a predicted draw on a home win is less wrong than a predicted
  away rout). Report log-loss and Brier as secondary; accuracy is secondary-only.
- **Calibration story:** every evaluation includes an isotonic-calibration check and
  renders a **Reliability Diagram** (predicted vs. observed) with a **confidence
  histogram** beneath it. This is the credibility centerpiece — not a gauge.
- **Explainability alignment:** per-match `pred_contribs` must terminate at the
  **calibrated** probability shown on the card, presented as a **waterfall** from the
  base rate. If raw contribs cannot sum to the calibrated output, present them as
  *directional drivers* and label them as such — never imply they add to the displayed %.

### 2. UI/UX & visualization standards (Opta / 538 style)
- **Banned:** default Streamlit gauges, donut charts, and raw markdown tables for
  critical data.
- **Required viz:** Plotly `Scatterternary` (matches as points in Win/Draw/Loss space);
  per-match horizontal **waterfall** (base rate → calibrated output); **reliability
  diagram + histogram**; cumulative **RPS-vs-baseline** line.
- **Interactivity rule:** every chart must *filter* something or *reveal* something on
  hover. If it does neither, cut it.
- **Design system:** high negative space, minimal dark theme, hairline borders
  (`#2A2A31`), custom typography via injected CSS (`@font-face`), no default Streamlit
  footer / hamburger / Deploy chrome.
- **Layout:** plain-English headline summary + one hero match at the top (for
  scrollers); advanced technical viz below the fold (for validation).

### 3. Pipeline & scope rules
- **Data-freshness copy:** ban "live" and "real-time." Use **"updates daily via batch"**
  plus an explicit `data as of {timestamp}` asset on every page.
- **Knockout constraint:** never render placeholder or fabricated future knockout
  matchups (e.g. "Winner Group A"). Display only matches with concrete known teams
  until the Monte Carlo simulator is structurally active.
- **Monte Carlo rules (when built):** simulate the remaining group stage from predicted
  match probabilities; apply real WC2026 advancement logic (top 2 per group + **8 best
  third-placed**, ranked by points → goal difference → goals for → …); propagate into
  R32+ to produce **advancement and title odds with uncertainty**.
- **Orchestration:** a lightweight **GitHub Actions cron** workflow only. **No Airflow,
  DVC, or feature stores** (avoid infrastructure cosplay).

---

## 1. Clean-room rule (no inherited context — read carefully)

This repository is **fully standalone**. Build everything fresh.

- Do NOT import, copy, reference, or re-use code, file names, database names, schemas,
  config, prompts, helper functions, or assets from any of Raj's other projects.
- If you recognize a name or pattern from somewhere else, that is a signal to **not**
  use it here. Generate a fresh equivalent for Tempo.
- Canonical names for THIS project: app = **Tempo**, database = **`data/tempo.db`**.
  There is no `crystal_ball.db`, no `fulltime.db`, no leftover Ollama/Cursor/other-project
  wiring, no borrowed module. Anything like that is a mistake — flag and remove it.
- All scaffolding, schemas, and utilities are authored from scratch for Tempo.

---

## 2. Environment bootstrap (do this first — install everything fresh)

Assume a **clean machine**: nothing beyond a Python interpreter is guaranteed to be
installed. You are authorized to install whatever the project needs. Do it cleanly:

- Create and use a project virtual environment `.venv`; never install globally.
- Author `requirements.txt` with **pinned** versions (see §11), install into the venv,
  then **freeze** the resolved versions back into `requirements.txt`.
- Write `scripts/verify_env.py` that imports every dependency, prints its version, and
  exits non-zero if anything is missing. Run it; do not proceed to P1 until it passes.
- If an install fails (network, build tools, wheels), stop and report the exact error
  and the fix you need — don't silently skip a dependency.
- Node is only needed if we later add a JS build step; we do not by default.

This bootstrap is expected work — you do **not** need a checkpoint to install. You DO
need a checkpoint for anything requiring Raj's accounts/keys (§8: C1, C2, C7).

---

## 3. Tournament facts (ground truth — do not hallucinate these)

- 48 teams, **12 groups (A–L)** of 4. Group stage 11–27 June (72 matches).
- Knockouts: Round of 32 (28 Jun–3 Jul) → R16 (4–7 Jul) → QF (9–11 Jul) →
  SF (14–15 Jul) → 3rd place (18 Jul) → **Final 19 Jul 2026**. 104 matches total.
- Top 2 per group + 8 best third-placed teams advance to the Round of 32.
- Hosts: USA / Canada / Mexico. Knockout ties: 30 min ET then penalties.
- **The current date and matchday are NOT hardcoded.** Always derive "remaining
  matches" from the fixture feed so the repo keeps working every day to the Final.
- **Knockout fixtures have no concrete teams until the groups resolve** — per §0.5/§3,
  do not display them until the Monte Carlo simulator backs them.

---

## 4. The three-layer architecture (non-negotiable structure)

Everything lives in exactly one of three layers. No logic leaks across boundaries.
Each layer talks to the next only through a defined interface (a validated table on
disk or a typed object — never a hidden global).

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — PRESENTATION  (Streamlit, Plotly, design system)  │
│  Reads predictions + explanations. Renders. Zero ML logic.   │
└───────────────▲─────────────────────────────────────────────┘
                │  reads predictions.parquet / model registry
┌───────────────┴─────────────────────────────────────────────┐
│  LAYER 2 — INTELLIGENCE  (features, model, calibration, expl)│
│  Trains, calibrates, predicts, explains. Knows nothing of UI.│
└───────────────▲─────────────────────────────────────────────┘
                │  reads clean tables from the data store
┌───────────────┴─────────────────────────────────────────────┐
│  LAYER 1 — DATA  (ingest, validate, store, feature tables)   │
│  Fetches current + historical data. Single source of truth.  │
└─────────────────────────────────────────────────────────────┘
```

**Rule:** Layer 3 never imports scikit-learn/xgboost. Layer 1 never imports Streamlit.

### Layer 1 — Data
- **Historical**: `martj42/international-football-results-from-1872-to-2017` (use the
  maintained version extending past 2017). Internationals: date, teams, scores,
  tournament, neutral flag.
- **Current tournament (primary intended)**: `football-data.org` REST API, free tier
  (World Cup included; 10 req/min): fixtures, results, standings, scorers.
- **Current tournament (active fallback, no key)**: `openfootball/worldcup.json` on
  GitHub — public-domain JSON, refreshed ~daily. Parses as a **flat matches array**
  (not nested rounds). Seeds and cross-checks the primary feed.
- **Manual override**: `data/manual_results.csv` (human-editable) always wins over the
  feed for any match it lists — patches a stale feed instantly on a posting night.
- Pipeline: fetch → validate (schema + sanity) → normalize team names via a canonical
  alias→ID map → persist to `data/tempo.db` (SQLite) + Parquet → build features.
  Idempotent: re-running never duplicates rows.

### Layer 2 — Intelligence
- **Features (all leak-free — see §6)**: Elo per team updated match-by-match; recent
  form (weighted last-N); rolling goals for/against; rest days; neutral/host flags;
  confederation; head-to-head; tournament-stage weighting.
- **Model**: XGBoost → 3-class {Home, Draw, Away}. A simple baseline (Elo-only logistic
  / Poisson) is built FIRST and must be beaten before the complex model ships.
- **Calibration**: a **custom isotonic calibrator** (`_IsotonicCalibrator`) — sklearn's
  `CalibratedClassifierCV(cv='prefit')` was removed, so we own this. Render a reliability
  diagram every retrain.
- **Evaluation**: **RPS primary**; log-loss + Brier secondary; accuracy reported but
  never headlined (per §0.5). Promote a new model to "current" only if it doesn't
  regress on RPS.
- **Explainability**: native XGBoost `pred_contribs` (faster than and equivalent to the
  old SHAP path). **Must reconcile to the calibrated output** — present as a base-rate→
  calibrated waterfall, or label as directional drivers (per §0.5).
- **Output contract**: `predictions.parquet`, one row per upcoming **known-team** match:
  `match_id, date, home, away, p_home, p_draw, p_away, contribs[], model_version, created_at`.

### Layer 3 — Presentation
- **Streamlit** reading only Layer 2 outputs + Layer 1 standings. **Plotly** for charts.
- Pages:
  1. **Today / Upcoming** — hero match + plain-English summary on top; match cards with
     the signature probability bar; known-team matches only.
  2. **Match detail** — prediction + **per-match waterfall** of contributions
     (base rate → calibrated), head-to-head, form.
  3. **Model report** — **RPS + reliability diagram + confidence histogram** (primary),
     cumulative RPS-vs-baseline over time, called-vs-missed log. No gauge, no donut.
     This page IS the credibility proof.
  4. **Match space** — Plotly `Scatterternary` of upcoming matches in W/D/L space;
     clicking a point filters the match list.
  5. **Bracket / simulation** — Monte Carlo advancement + title odds (**required** for
     knockout display, C4).
  6. **Share card** — fixed-size, export-ready LinkedIn image (C6).

---

## 5. Repository layout

```
tempo/
├── CLAUDE.md
├── README.md                     # public story (written last, §12)
├── .env.example                  # FOOTBALL_DATA_API_KEY=...
├── requirements.txt              # pinned + frozen
├── .streamlit/config.toml        # base theme (chrome stripped via CSS too)
├── .github/workflows/refresh.yml # daily cron orchestration (no Airflow/DVC)
├── scripts/
│   └── verify_env.py
├── data/
│   ├── raw/
│   ├── manual_results.csv        # human override, wins over feed
│   └── tempo.db                  # SQLite store (NOT any prior project's db)
├── src/
│   ├── data_layer/      {ingest_historical, ingest_live, team_aliases, validate, build_features}.py
│   ├── intelligence_layer/ {elo, features, train, calibrate, predict, explain, metrics, registry}.py
│   └── presentation_layer/
│       ├── app.py
│       ├── theme.py              # ALL design tokens from §7 (single source)
│       ├── styles.py             # injected CSS (chrome strip, @font-face)
│       ├── components/           # match_card, prob_bar, factor_waterfall, share_card, geo_unit
│       ├── charts/               # ternary, reliability, rps_timeline, waterfall
│       └── pages/
├── pipelines/refresh.py          # one command: ingest → retrain → predict
├── tests/
└── artifacts/{models, reports}/
```

`python pipelines/refresh.py` is the heartbeat. The Streamlit app only ever *reads*
what refresh produced — UI is always fast and never trains on page load.

---

## 6. Engineering rules

- **No data leakage, ever.** Every feature must be computable using only info available
  *before kickoff*. Strict chronological computation; **time-based splits only**, never
  random K-fold on matches. A test asserts no future data enters a feature. This is the
  #1 way these projects are secretly wrong — guard it aggressively.
- **Honest metrics.** **RPS is the headline.** Always report against naive baselines
  (always-home, Elo-only, bookmaker-implied if available). Never headline accuracy;
  never inflate a public number.
- **Determinism**: seeds set; versions pinned; log `model_version` + `created_at` on
  every prediction row.
- **Idempotency**: ingest and refresh re-run safely with no side effects.
- **Fail loud in pipeline, fail soft in UI**: if the feed is down, show the last good
  predictions with a visible `data as of {timestamp}` stamp — never a crash.
- **Secrets** only in `.env` / Streamlit secrets, never committed. `.gitignore` covers
  `.env`, `.venv`, `data/raw/`, large model files.
- **Tests** (minimum): alias mapping, leakage guard, calibration sanity, RPS correctness
  on a known toy case, and the `predictions.parquet` schema contract.

---

## 7. Design system

Design system: see [DESIGN.md](DESIGN.md).

---

## 8. Human-in-the-loop checkpoints (STOP and ask)

At any of these, **pause, state exactly what you need, and wait.** Don't invent
credentials, don't download gated data silently, don't start long/expensive runs
without a go-ahead. Keep each ask short and specific.

- **C1 — Kaggle historical dataset.** Can't download without auth. Ask Raj to drop the
  CSV in `data/raw/` (give the exact expected filename) or provide Kaggle credentials.
- **C2 — football-data.org API key.** Ask him to register (free) and paste the key into
  `.env` as `FOOTBALL_DATA_API_KEY`. Until then, run on the openfootball fallback — say so.
- **C3 — Heavy training / tuning.** Before any long search/sweep, show the planned space
  + rough cost and confirm. Default to a small, fast config otherwise.
- **C4 — Monte Carlo simulation.** **Required for knockout display** and compute-heavy.
  Confirm scope + run size (e.g. 10k vs 50k) before running.
- **C5 — Design sign-off.** Render ONE polished screen and get explicit approval on
  tokens, type, the geo-unit, and the probability bar before building the other pages.
- **C6 — LinkedIn share card.** Before generating any public image, show the exact match,
  the numbers, and the timestamp, and confirm. Public output gets a human check.
- **C7 — Deployment.** Streamlit Cloud needs his GitHub repo + secrets. Give precise
  steps and the secrets to set; don't assume account access.

Unsure whether something is a checkpoint? Treat it as one. A short question is cheaper
than a wrong long run.

---

## 9. Build order & current remediation

Original phases P0–P5 are **done** (env, data layer, Elo + model + calibration,
`pred_contribs`, refresh pipeline, 3-page dashboard). The active work is the
**post-council remediation** below — do it **one isolated asset at a time**, validate on
real data, then move on. Touch only the files named in each step.

- **R1 — Honesty & scope (fast):** replace every "live"/"real-time" UI string with
  "updates daily via batch"; add the `data as of {timestamp}` asset to all pages; filter
  the predictions view to **known-team matches only**. (§0.5 §3)
- **R2 — RPS + reliability ("the one thing first"):** add RPS metric + reliability
  diagram with confidence histogram to the Model Report; retire the accuracy gauge. (§0.5 §1)
- **R3 — Strip Streamlit chrome:** `styles.py` injected CSS + `.streamlit/config.toml`
  (hide hamburger/footer/Deploy/padding; wire fonts via `@font-face`). (§0.5 §2)
- **R4 — Match visuals:** Plotly `Scatterternary` (click-to-filter) + per-match waterfall
  that ends at the **calibrated** probability and reconciles `pred_contribs`. (§0.5 §1–2)
- **R5 — Orchestration:** `.github/workflows/refresh.yml` daily cron running
  `pipelines/refresh.py` and committing outputs. No other infra. (§0.5 §3)
- **R6 — Monte Carlo (C4, last & biggest):** simulator per §0.5 §3; produces advancement
  + title odds with uncertainty; once active, un-filter knockout display.
  - **C4 decisions (2026-06-19):** 50k seeded runs (seed=42); conditioning starts from
    CURRENT group standings + remaining-match model probabilities, NOT a fresh 48-team
    draw; projected knockout slots displayed only on the Bracket page, labeled
    "Projected" — never injected into the Predictions/match-card flow.
  - Group-stage sim verified: Canada/Switzerland 100% R32 (Group B), Bosnia 49.7%
    (can win final match → best-third route), Qatar 20.4% — all expected. Next step:
    knockout-round bracket + road-to-final odds table.
- **R7 — Share card + README + deploy** (C6, C7).

---

## 10. Token & cost discipline

- Don't load large data files into context to "look around" — write a small script that
  prints the specific summary, run it, read the output.
- Don't paste big dataframes / full model dumps / whole files back; summarize + point to
  the artifact path.
- Prefer editing files in place over regenerating them wholesale; keep diffs minimal.
- Long/repeated experiments → propose, get a go-ahead (C3/C4), then run.

---

## 11. Tech stack (pin these; install per §2)

Python 3.11+ · pandas · numpy · scikit-learn · xgboost (use native `pred_contribs`;
**SHAP removed** — had a v0.52.0 bug, and native contribs are faster/equivalent) ·
pydantic v2 (or pandera) for validation · requests · plotly · streamlit · python-dotenv ·
pyarrow · pytest. Calibration: our own `_IsotonicCalibrator`. Orchestration: GitHub
Actions (no Airflow/DVC/feature store). Storage: SQLite (`data/tempo.db`) + Parquet.
Pin versions and `pip freeze` them into `requirements.txt`.

---

## 12. Provenance & honest framing (protects Raj — follow it)

- Public story: **"built mid-tournament, predicting forward from the day it went public."**
  Never backdate commits, never fabricate a pre-tournament track record, never imply
  predictions were logged before they actually were.
- Every prediction row + the Model Report carry a real `created_at`, and every page shows
  `data as of {timestamp}`. Credibility comes from *forward* calls checked against
  reality — that's the honest, stronger flex.
- README (written last) tells the true arc: what it does, the architecture, **RPS + the
  reliability story** so far, and how to run it. Put the **deployed link up top** —
  recruiters click links, they don't clone repos.
- If asked to produce anything that misrepresents when/how predictions were made, refuse
  and flag it.

---

## 13. Session checklist for Claude Code

1. Re-read this file and obey **§0.5 (Post-Council overrides)**. 2. Confirm clean-room
(§1) — no inherited names/assets; the db is `data/tempo.db`. 3. Identify the current
remediation step (§9). 4. Stay inside layer boundaries (§4). 5. Watch for a checkpoint
(§8). 6. Build on real data; touch only the files named. 7. For UI, run the a11y
checklist (DESIGN.md §13), keep it on-theme (DESIGN.md), and obey the viz bans (DESIGN.md §8). 8. Report briefly,
point to artifacts, don't dump large output. 9. Keep it real, daily-fresh, RPS-honest,
explainable, beautiful.