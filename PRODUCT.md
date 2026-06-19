# Product

## Register

product

## Users

Football fans and recruiters/technical reviewers who find Tempo via LinkedIn posts. Access is overwhelmingly mobile — they tap a LinkedIn link after seeing a prediction posted before a match, or a result posted after. A secondary audience arrives via direct URL on desktop to evaluate it as a portfolio piece. Both groups are time-limited: the fan wants the prediction fast; the reviewer wants to see the methodology fast. Neither wants to read documentation.

## Product Purpose

Tempo is a daily-updated AI predictor for FIFA World Cup 2026 match outcomes (Home win / Draw / Away win). It ingests real results each day, re-evaluates all remaining matches, explains why it made each prediction (XGBoost feature contributions → calibrated probability waterfall), and posts predictions on LinkedIn before matches kick off. The public track record — forward calls checked against real results — is the credibility proof. The dashboard is the artifact; the predictions are the product.

## Brand Personality

Authoritative, transparent, broadcast-grade.

Tempo should feel like a sports network's data team built it — not a side project, not a homework folder, not a generic SaaS tool. It knows football. It shows its math. It admits uncertainty as probability rather than hiding it.

Three words: **credible, precise, alive**.

## Anti-references

- Generic AI portfolio dashboards (SaaS cream backgrounds, identical card grids, accuracy gauges)
- "Homework project" aesthetic (default Streamlit chrome, raw markdown tables, matplotlib plots)
- Over-decorated sports apps (neon gradients, glassmorphism, particle backgrounds)
- Any interface that buries the prediction behind complexity — the number and the confidence bar should hit within 2 seconds of opening the page

## Design Principles

1. **Prediction first.** Every page leads with the forecast, not metadata about the model. The number is the product; everything else supports it.
2. **Earn credibility, don't claim it.** Show the calibration diagram. Show RPS vs. baselines. Show when we were wrong. Transparency is the brand.
3. **Mobile from the first pixel.** LinkedIn traffic is overwhelmingly mobile. The probability bar must be legible at 375px. Team names must not overflow. Touch targets must be ≥44×44px.
4. **Honest copy, always.** No "live", no "real-time", no inflated accuracy claims. "Updates daily via batch" + exact timestamp. RPS is the headline metric; accuracy is secondary and labeled as such.
5. **Broadcast, not blog.** The visual language is sports media — dark surfaces, high contrast, tight typography, color as signal not decoration. It looks like it belongs on screen during a match broadcast.

## Trademark & IP Guardrail

This is a public portfolio piece. Do NOT reproduce: FIFA emblem, the stylized "26" wordmark, the World Cup trophy image, the mascots (Maple, Zayu, Clutch), the "Trionda" ball graphic, or the official FIFA typeface. Use only: Tempo's own geometric square + quarter-circle motif, the committed palette, plain-text team names, and public-domain country flags. When in doubt, make it ourselves.

## Accessibility & Inclusion

WCAG 2.2 AA minimum. Mobile-first (375px no horizontal scroll). Focus rings required on all interactive elements (`--gold` outline). `prefers-reduced-motion` honored. No emoji as icons — inline SVG only. All probability data must have text alternatives (aria-label on the prob bar).
