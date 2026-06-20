"""
Share Card — Fixed-size LinkedIn export image.

HTML: 600px wide preview card for in-browser display.
PNG:  1200×630px bitmap (Pillow) — 2× the HTML preview width, crisp on Retina.

§CLAUDE.md C6 checkpoint satisfied by explicit user request to build this.
"""

from __future__ import annotations

import io

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img

# ── Design tokens (hardcoded — card must self-render without Streamlit CSS) ───
_BG        = "#111114"
_SURFACE_R = "#1C1C21"
_BORDER    = "#2A2A31"
_TEXT      = "#F4F1EA"
_MUTED     = "#A7A39B"
_GOLD      = "#E8B84B"
_WIN       = "#4CA882"
_DRAW      = "#6B8ABF"
_LOSS      = "#C9645C"
_WIN_TEXT  = "#052318"
_DRAW_TEXT = "#081526"
_LOSS_TEXT = "#250907"

# PNG size — 2× the 600px HTML card width
_PNG_W, _PNG_H = 1200, 630


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default(size=size)


_BOLD = [
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_REG = [
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_MONO = [
    "C:/Windows/Fonts/cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
]


# ── HTML card ─────────────────────────────────────────────────────────────────

def share_card_css() -> str:
    """Scoped CSS for .sc-* classes — inject once per page."""
    return """<style>
.sc-card {
  width: 600px; max-width: 100%;
  background: #111114;
  border: 1px solid #2A2A31;
  border-radius: 12px;
  overflow: hidden;
  font-family: 'Inter', sans-serif;
  box-sizing: border-box;
}
.sc-rail {
  height: 4px;
  background: linear-gradient(90deg, #4CA882 0% 33.3%, #6B8ABF 33.3% 66.6%, #C9645C 66.6% 100%);
}
.sc-body { padding: 1.1rem 1.25rem 0.9rem; }
.sc-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.9rem;
}
.sc-brand-name {
  font-family: 'Archivo', sans-serif; font-weight: 900; font-size: 1.05rem;
  color: #E8B84B; letter-spacing: -0.02em; margin-right: 0.35rem;
}
.sc-brand-sub {
  font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
  text-transform: uppercase; letter-spacing: 0.1em; color: #A7A39B;
}
.sc-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
  text-transform: uppercase; letter-spacing: 0.06em; color: #A7A39B;
  background: #1C1C21; border: 1px solid #2A2A31; border-radius: 6px;
  padding: 3px 8px; white-space: nowrap;
}
.sc-teams {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.5rem; margin-bottom: 0.85rem;
}
.sc-team { display: flex; flex-direction: column; gap: 0.2rem; flex: 1; min-width: 0; }
.sc-team--away { align-items: flex-end; }
.sc-team-name {
  font-family: 'Archivo', sans-serif; font-weight: 800; font-size: 1.1rem;
  color: #F4F1EA; letter-spacing: -0.01em; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.sc-team-pct {
  font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.55rem;
  font-variant-numeric: tabular-nums;
}
.sc-team-pct--win  { color: #4CA882; }
.sc-team-pct--loss { color: #C9645C; }
.sc-center {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.2rem; padding: 0 0.4rem; flex-shrink: 0;
}
.sc-vs {
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
  color: #2A2A31; background: #1C1C21; border: 1px solid #2A2A31;
  border-radius: 4px; padding: 2px 5px;
}
.sc-draw-pct {
  font-family: 'JetBrains Mono', monospace; font-weight: 700;
  font-size: 1.1rem; color: #6B8ABF; font-variant-numeric: tabular-nums;
}
.sc-draw-lbl {
  font-family: 'JetBrains Mono', monospace; font-size: 0.56rem;
  text-transform: uppercase; color: #A7A39B;
}
.sc-bar {
  display: flex; height: 30px; gap: 2px;
  border-radius: 8px; overflow: hidden; margin-bottom: 0.3rem;
}
.sc-seg {
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
  font-weight: 700; font-variant-numeric: tabular-nums;
  min-width: 0; overflow: hidden;
}
.sc-seg--win  { background: #4CA882; color: #052318; }
.sc-seg--draw { background: #6B8ABF; color: #081526; }
.sc-seg--loss { background: #C9645C; color: #250907; }
.sc-bar-labels {
  display: flex; justify-content: space-between;
  font-family: 'JetBrains Mono', monospace; font-size: 0.58rem;
  color: #A7A39B; margin-bottom: 0.7rem;
}
.sc-favored {
  display: inline-flex; align-items: center; gap: 0.4rem;
  font-family: 'Inter', sans-serif; font-size: 0.77rem; color: #F4F1EA;
  background: rgba(232,184,75,0.06); border: 1px solid rgba(232,184,75,0.2);
  border-radius: 20px; padding: 4px 11px; margin-bottom: 0.8rem;
}
.sc-favored-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #E8B84B;
  box-shadow: 0 0 5px rgba(232,184,75,0.6); flex-shrink: 0;
}
.sc-footer {
  display: flex; justify-content: space-between; align-items: center;
  border-top: 1px solid #2A2A31; padding-top: 0.55rem;
  gap: 0.5rem; flex-wrap: wrap;
}
.sc-footer-meta, .sc-footer-model {
  font-family: 'JetBrains Mono', monospace; font-size: 0.58rem; color: #A7A39B;
}
.sc-ts {
  font-family: 'JetBrains Mono', monospace; font-size: 0.58rem;
  background: #1C1C21; color: #E8B84B;
  border: 1px solid #2A2A31; border-radius: 3px; padding: 1px 4px;
}
</style>"""


def share_html(row: pd.Series) -> str:
    home  = str(row["home_team"])
    away  = str(row["away_team"])
    p_h   = float(row["p_home"])
    p_d   = float(row["p_draw"])
    p_a   = float(row["p_away"])
    date  = str(row.get("date", ""))
    group = str(row.get("group_label", "WC"))
    kick  = str(row.get("kickoff_time", ""))
    kick_s = f" · {kick} UTC" if kick else ""
    mv    = str(row.get("model_version", ""))[:20]
    ts    = str(row.get("created_at", ""))[:16].replace("T", " ")

    hf = flag_img(get_flag_code(home), width=40, team_name=home)
    af = flag_img(get_flag_code(away), width=40, team_name=away)

    best = max(p_h, p_d, p_a)
    if best == p_h:
        fav_flag = flag_img(get_flag_code(home), width=14, team_name=home)
        fav_txt  = f"{fav_flag} {home} {p_h:.0%}"
    elif best == p_d:
        fav_txt  = f"Draw {p_d:.0%}"
    else:
        fav_flag = flag_img(get_flag_code(away), width=14, team_name=away)
        fav_txt  = f"{fav_flag} {away} {p_a:.0%}"

    wh = f"{p_h*100:.2f}%"
    wd = f"{p_d*100:.2f}%"
    wa = f"{p_a*100:.2f}%"
    sl = lambda p: f"{p:.0%}" if p >= 0.09 else ""

    return f"""<div class="sc-card">
  <div class="sc-rail"></div>
  <div class="sc-body">
    <div class="sc-header">
      <div>
        <span class="sc-brand-name">Tempo</span>
        <span class="sc-brand-sub">WC26 · AI Predictor</span>
      </div>
      <span class="sc-chip">WC26 · GRP {group} · {date}{kick_s}</span>
    </div>
    <div class="sc-teams">
      <div class="sc-team">
        {hf}
        <span class="sc-team-name">{home}</span>
        <span class="sc-team-pct sc-team-pct--win">{p_h:.0%}</span>
      </div>
      <div class="sc-center">
        <span class="sc-vs">VS</span>
        <span class="sc-draw-pct">{p_d:.0%}</span>
        <span class="sc-draw-lbl">Draw</span>
      </div>
      <div class="sc-team sc-team--away">
        {af}
        <span class="sc-team-name">{away}</span>
        <span class="sc-team-pct sc-team-pct--loss">{p_a:.0%}</span>
      </div>
    </div>
    <div class="sc-bar" role="img"
         aria-label="{home} {p_h:.0%} · Draw {p_d:.0%} · {away} {p_a:.0%}">
      <div class="sc-seg sc-seg--win"  style="width:{wh};">{sl(p_h)}</div>
      <div class="sc-seg sc-seg--draw" style="width:{wd};">{sl(p_d)}</div>
      <div class="sc-seg sc-seg--loss" style="width:{wa};">{sl(p_a)}</div>
    </div>
    <div class="sc-bar-labels">
      <span>Home win</span><span>Draw</span><span>Away win</span>
    </div>
    <div class="sc-favored">
      <span class="sc-favored-dot"></span>Favored: {fav_txt}
    </div>
    <div class="sc-footer">
      <span class="sc-footer-meta">Data as of <code class="sc-ts">{ts}</code> · Updates daily via batch</span>
      <span class="sc-footer-model">Tempo · Model <code class="sc-ts">{mv[:15]}</code></span>
    </div>
  </div>
</div>"""


# ── PNG card (Pillow, 1200×630) ───────────────────────────────────────────────

def share_png(row: pd.Series) -> bytes:
    """
    1200×630 PNG — 2× the 600px HTML card, crisp on Retina / LinkedIn feed.
    No dashboard chrome. Pure prediction card.
    """
    W, H = _PNG_W, _PNG_H
    BX   = 44          # horizontal body margin

    home  = str(row["home_team"])
    away  = str(row["away_team"])
    p_h   = float(row["p_home"])
    p_d   = float(row["p_draw"])
    p_a   = float(row["p_away"])
    date  = str(row.get("date", ""))
    group = str(row.get("group_label", "WC"))
    mv    = str(row.get("model_version", ""))
    ts    = str(row.get("created_at", ""))[:16].replace("T", " ")

    f_brand = _font(_BOLD, 38)
    f_sub   = _font(_MONO, 18)
    f_chip  = _font(_MONO, 20)
    f_abbr  = _font(_BOLD, 52)
    f_team  = _font(_BOLD, 46)
    f_pct   = _font(_BOLD, 58)
    f_dpct  = _font(_BOLD, 38)
    f_vs    = _font(_BOLD, 22)
    f_bar   = _font(_BOLD, 20)
    f_lbl   = _font(_REG,  20)
    f_fav   = _font(_REG,  21)
    f_foot  = _font(_MONO, 17)

    img  = Image.new("RGB", (W, H), _rgb(_BG))
    d    = ImageDraw.Draw(img)

    # Tri-color rail
    W3 = W // 3
    d.rectangle([0, 0, W3,    5], fill=_rgb(_WIN))
    d.rectangle([W3, 0, W3*2, 5], fill=_rgb(_DRAW))
    d.rectangle([W3*2, 0, W,  5], fill=_rgb(_LOSS))

    # Gold left accent
    d.rectangle([0, 5, 3, H], fill=_rgb(_GOLD))

    # Brand row
    d.text((BX, 16), "Tempo", font=f_brand, fill=_rgb(_GOLD))
    bw = int(d.textlength("Tempo", font=f_brand))
    d.text((BX + bw + 12, 26), "WC26 · AI Predictor", font=f_sub, fill=_rgb(_MUTED))

    # Match chip (right-aligned)
    chip = f"WC26 · GRP {group} · {date}"
    cw   = int(d.textlength(chip, font=f_chip))
    cx   = W - BX - cw
    cy   = 20
    d.rounded_rectangle([cx - 8, cy - 4, cx + cw + 8, cy + 24],
                        radius=5, fill=_rgb(_SURFACE_R))
    d.text((cx, cy), chip, font=f_chip, fill=_rgb(_MUTED))

    # Divider
    d.line([(BX, 68), (W - BX, 68)], fill=_rgb(_BORDER), width=1)

    # ── Teams section ─────────────────────────────────────────────────────────
    # Layout: home left-aligned, away right-aligned, center column at W//2
    CX = W // 2    # center x

    # Y positions
    Y_abbr = 78
    Y_name = Y_abbr + 60    # 138
    Y_pct  = Y_name + 54    # 192

    # Home (left)
    home_abbr = home[:3].upper()
    d.text((BX, Y_abbr), home_abbr, font=f_abbr, fill=_rgb(_MUTED))
    d.text((BX, Y_name), home,      font=f_team, fill=_rgb(_TEXT))
    d.text((BX, Y_pct),  f"{p_h:.0%}", font=f_pct, fill=_rgb(_WIN))

    # Away (right-aligned)
    away_abbr = away[:3].upper()
    away_s    = f"{p_a:.0%}"
    aw_a = int(d.textlength(away_abbr, font=f_abbr))
    aw_n = int(d.textlength(away,      font=f_team))
    aw_p = int(d.textlength(away_s,    font=f_pct))
    RX   = W - BX
    d.text((RX - aw_a, Y_abbr), away_abbr, font=f_abbr, fill=_rgb(_MUTED))
    d.text((RX - aw_n, Y_name), away,      font=f_team, fill=_rgb(_TEXT))
    d.text((RX - aw_p, Y_pct),  away_s,    font=f_pct,  fill=_rgb(_LOSS))

    # Center: VS + draw prob
    vs_w  = int(d.textlength("VS", font=f_vs))
    d.text((CX - vs_w // 2, Y_name + 4), "VS", font=f_vs, fill=_rgb(_BORDER))

    dp_s  = f"{p_d:.0%}"
    dp_w  = int(d.textlength(dp_s, font=f_dpct))
    d.text((CX - dp_w // 2, Y_pct + 2), dp_s, font=f_dpct, fill=_rgb(_DRAW))

    dl_w  = int(d.textlength("DRAW", font=f_chip))
    d.text((CX - dl_w // 2, Y_pct + 48), "DRAW", font=f_chip, fill=_rgb(_MUTED))

    # Divider
    DY2 = 305
    d.line([(BX, DY2), (W - BX, DY2)], fill=_rgb(_BORDER), width=1)

    # ── Probability bar ───────────────────────────────────────────────────────
    BAR_Y = 318
    BAR_H = 44
    BAR_X = BX
    BAR_W = W - 2 * BX
    GAP   = 3
    R     = 8

    w_win  = int(BAR_W * p_h)
    w_draw = int(BAR_W * p_d)
    w_loss = BAR_W - w_win - w_draw

    x = BAR_X
    d.rounded_rectangle([x, BAR_Y, x + w_win - GAP, BAR_Y + BAR_H],
                        radius=R, fill=_rgb(_WIN), corners=(True, False, False, True))
    if w_win > 60:
        t = f"{p_h:.0%}"
        tw = int(d.textlength(t, font=f_bar))
        d.text((x + (w_win - GAP) // 2 - tw // 2, BAR_Y + 12),
               t, font=f_bar, fill=_rgb(_WIN_TEXT))
    x += w_win + GAP

    d.rectangle([x, BAR_Y, x + w_draw - GAP, BAR_Y + BAR_H], fill=_rgb(_DRAW))
    if w_draw > 60:
        t = f"{p_d:.0%}"
        tw = int(d.textlength(t, font=f_bar))
        d.text((x + (w_draw - GAP) // 2 - tw // 2, BAR_Y + 12),
               t, font=f_bar, fill=_rgb(_DRAW_TEXT))
    x += w_draw + GAP

    d.rounded_rectangle([x, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H],
                        radius=R, fill=_rgb(_LOSS), corners=(False, True, True, False))
    if w_loss > 60:
        t = f"{p_a:.0%}"
        tw = int(d.textlength(t, font=f_bar))
        d.text((x + w_loss // 2 - tw // 2, BAR_Y + 12),
               t, font=f_bar, fill=_rgb(_LOSS_TEXT))

    # Bar labels
    LY = BAR_Y + BAR_H + 10
    for lbl, ax, align in [
        ("HOME WIN", BAR_X, "left"),
        ("DRAW",     CX,    "center"),
        ("AWAY WIN", RX,    "right"),
    ]:
        lw = int(d.textlength(lbl, font=f_foot))
        lx = {"left": ax, "center": ax - lw // 2, "right": ax - lw}[align]
        d.text((lx, LY), lbl, font=f_foot, fill=_rgb(_MUTED))

    # ── Favored ───────────────────────────────────────────────────────────────
    FAV_Y = LY + 36
    best  = max(p_h, p_d, p_a)
    if best == p_h:
        fav_s = f"Favored: {home} {p_h:.0%}"
    elif best == p_d:
        fav_s = f"Favored: Draw {p_d:.0%}"
    else:
        fav_s = f"Favored: {away} {p_a:.0%}"

    dot_x = BX + 1
    d.ellipse([dot_x, FAV_Y + 5, dot_x + 10, FAV_Y + 15], fill=_rgb(_GOLD))
    d.text((BX + 18, FAV_Y), fav_s, font=f_fav, fill=_rgb(_TEXT))

    # ── Footer ────────────────────────────────────────────────────────────────
    FOOT_Y = H - 44
    d.line([(BX, FOOT_Y - 12), (W - BX, FOOT_Y - 12)], fill=_rgb(_BORDER), width=1)
    foot_l = f"Data as of {ts} · Updates daily via batch"
    foot_r = f"Tempo · {mv[:15]}"   # date+time portion only
    d.text((BX, FOOT_Y), foot_l, font=f_foot, fill=_rgb(_MUTED))
    frw = int(d.textlength(foot_r, font=f_foot))
    d.text((W - BX - frw, FOOT_Y), foot_r, font=f_foot, fill=_rgb(_GOLD))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
