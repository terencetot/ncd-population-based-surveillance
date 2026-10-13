"""
NCD Surveillance Intelligence Platform - WHO African Region
Report builder: CSS, JavaScript, HTML assembly
"""
import base64
import json
import re
from html import escape as html_escape
import pandas as pd
from pathlib import Path
import re
import json as _json
from src.config import (C, FONT, TIER_COLORS, TIER_LABELS, SURVEY_META,
                        CURRENT_YEAR, CYCLE_YEARS, CURRENT_CYCLE_START,
                        REPORT_DATE, ASSETS_DIR, CYCLE_STATUS_LABELS, CYCLE_STATUS_COLORS,
                        CYCLE_STATUS_INK, CYCLE_STATUS_ON, CYCLE_STATUS_PATTERN,
                        CYCLE_STATUS_PATTERN_FG, TIER_INK, TIER_ON, BRAND,
                        RECENCY_STEPS, RECENCY_NONE, recency_color, tier_of, TIER_CUTS,
                        FS, RADIUS, DUR, EASE)
from src.charts import (fig_tier_donut, fig_spi_bar, fig_spi_choropleth,
                        fig_spi_components, fig_current_cycle,
                        fig_last_year_heatmap, fig_priority_scatter,
                        fig_timeline, fig_gap_bar, fig_survey_type_comparison)

# ── Embed assets as base64 ─────────────────────────────────────────────────────
def _b64(path: Path) -> str:
    """Return base64-encoded PNG as data URI string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""

_LOGOS_DIR = ASSETS_DIR / "logos"
_MAPS_DIR  = ASSETS_DIR / "maps"

def _png_wh(path: Path):
    """Intrinsic (width, height) from a PNG header, or None."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            import struct
            return struct.unpack(">II", head[16:24])
    except OSError:
        pass
    return None


def _wh_attr(path: Path, h: int) -> str:
    wh = _png_wh(path)
    return f'width="{round(wh[0] * h / wh[1])}" height="{h}"' if wh else f'height="{h}"'


WHO_LOGO_B64 = _b64(_LOGOS_DIR / "who_logo.png")
DPC_LOGO_B64 = _b64(_LOGOS_DIR / "dpc_logo.png")
FAV_LOGO_B64 = _b64(_LOGOS_DIR / "favicon.png")

# Load all country maps: {ISO3: base64_string}
COUNTRY_MAPS: dict = {}
if _MAPS_DIR.exists():
    for mp in sorted(_MAPS_DIR.glob("*.png")):
        COUNTRY_MAPS[mp.stem] = _b64(mp)

# ── Shared formatting helpers ──────────────────────────────────────────────────
def fmt_years(n, prefix: str = "") -> str:
    """'1 yr' / '2 yrs' - every year-count rendering routes through this."""
    v = int(round(float(n)))
    return f"{prefix}{v} yr" if v == 1 else f"{prefix}{v} yrs"


def fmt_spi(v, decimals: int = 1) -> str:
    """Single formatter for the regional/country SPI score, so every display
    (hero badge, Performance tab, tables) renders the same precision."""
    return f"{float(v):.{decimals}f}"



# ── Header: tile map of the AFRO region ────────────────────────────────────────
# One tile per Member State, built from the dashboard's own country silhouettes
# (assets/maps/*.png - the same images as the scorecard thumbnails). Tiles sit
# on an approximate geographic grid (col, row); the empty south-west is the
# Atlantic, where the SPI card overlaps. Zanzibar is not drawn (it shares TZA).
TILE_POS = {
    # rows run north -> south; within a row, west -> east (e.g. GHA, TGO, BEN, NGA, CMR)
    "CPV": (0, 0), "MRT": (3, 0), "DZA": (4, 0),
    "GMB": (1, 1), "SEN": (2, 1), "MLI": (3, 1), "BFA": (4, 1), "NER": (5, 1), "TCD": (6, 1), "ERI": (10, 1),
    "GNB": (0, 2), "GIN": (1, 2), "CIV": (2, 2), "GHA": (3, 2), "TGO": (4, 2), "BEN": (5, 2), "NGA": (6, 2),
    "CMR": (7, 2), "CAF": (8, 2), "SSD": (9, 2), "ETH": (10, 2),
    "SLE": (1, 3), "LBR": (2, 3), "STP": (6, 3), "GNQ": (7, 3), "COG": (8, 3), "COD": (9, 3), "UGA": (10, 3), "KEN": (11, 3),
    "GAB": (7, 4), "AGO": (8, 4), "BDI": (9, 4), "RWA": (10, 4), "TZA": (11, 4), "SYC": (13, 4),
    "NAM": (8, 5), "ZMB": (9, 5), "MWI": (10, 5), "MOZ": (11, 5), "COM": (12, 5),
    "BWA": (9, 6), "ZWE": (10, 6), "MDG": (12, 6), "MUS": (13, 6),
    "ZAF": (9, 7), "SWZ": (10, 7),
    "LSO": (9, 8),
}
TILE_COLS = 1 + max(c for c, _ in TILE_POS.values())
TILE_ROWS = 1 + max(r for _, r in TILE_POS.values())

WHO_MAP_DISCLAIMER = ("The boundaries and names shown and the designations used on this map do not imply the "
                      "expression of any opinion whatsoever on the part of the World Health Organization concerning "
                      "the legal status of any country, territory, city or area or of its authorities, or concerning "
                      "the delimitation of its frontiers or boundaries.")


def country_map_css() -> str:
    """Each silhouette is embedded ONCE, as a CSS custom property shared by the
    scorecard thumbnails and the header tile map."""
    return ":root{" + "".join(f'--map-{k}:url("data:image/png;base64,{v}");' for k, v in COUNTRY_MAPS.items()) + "}\n"


def hero_tile_map(spi_df) -> str:
    tiles = []
    for r in spi_df.itertuples():
        if r.country == "Zanzibar" or r.iso3 not in TILE_POS or r.iso3 not in COUNTRY_MAPS:
            continue
        c, row = TILE_POS[r.iso3]
        t = int(r.tier)
        label = f"{r.country} · SPI {r.spi:.1f}"
        tiles.append(f'<div class="tm-tile t{t}" style="grid-column:{c + 1};grid-row:{row + 1}" role="img" '
                     f'aria-label="{html_escape(label)}, {TIER_LABELS[t]}" title="{html_escape(label)}">'
                     f'<span style="--m:var(--map-{r.iso3})"></span></div>')
    return (f'<div class="tm-grid" style="--cols:{TILE_COLS};--rows:{TILE_ROWS}" role="group" '
            f'aria-label="Countries by SPI tier">{"".join(tiles)}</div>')


# ── Colour system → CSS / JS (single source: src/config.py) ───────────────────
def _slug(label: str) -> str:
    return re.sub(r"[^a-z]+", "-", label.lower()).strip("-")


def palette_css() -> str:
    """Emit the evidence colour system as custom properties plus the two
    component classes (status badge, tier badge) every view uses, so no
    template ever hard-codes a semantic hex again."""
    v = [f"--brand:{BRAND['navy']};--who-blue:{BRAND['who_blue']};--tint:{BRAND['tint']};--rule:{BRAND['rule']};"]
    cls = []
    for lbl in CYCLE_STATUS_LABELS:
        k = _slug(lbl)
        v.append(f"--st-{k}:{CYCLE_STATUS_COLORS[lbl]};--st-{k}-ink:{CYCLE_STATUS_INK[lbl]};--st-{k}-on:{CYCLE_STATUS_ON[lbl]};")
        cls.append(f".st-badge.st-{k}{{background-color:var(--st-{k});color:var(--st-{k}-on)}}"
                   f".st-ink-{k}{{color:var(--st-{k}-ink)}}")
    for t in (1, 2, 3, 4):
        v.append(f"--tier-{t}:{TIER_COLORS[t]};--tier-{t}-ink:{TIER_INK[t]};--tier-{t}-on:{TIER_ON[t]};")
        cls.append(f".tier-badge.t{t}{{background-color:var(--tier-{t});color:var(--tier-{t}-on)}}")
    for i, (_hi, fill, ink, _l) in enumerate(RECENCY_STEPS):
        v.append(f"--rec-{i}:{fill};--rec-{i}-ink:{ink};")
    v.append(f"--rec-none:{RECENCY_NONE};")
    # In-progress texture: same cue as the Plotly bar patterns (hatch / dots)
    fg_att = CYCLE_STATUS_PATTERN_FG["Attempt to update"]
    cls.append(".st-badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:var(--fs-xs);"
               "font-weight:700;line-height:1.5;white-space:nowrap;-webkit-print-color-adjust:exact;print-color-adjust:exact}"
               f".st-badge.st-attempt-to-update{{background-image:repeating-linear-gradient(135deg,{fg_att}40 0 1.5px,transparent 1.5px 6px)}}"
               ".st-badge.st-first-attempt{background-image:radial-gradient(rgba(255,255,255,.35) 1px,transparent 1.3px);background-size:5px 5px}")
    return ":root{" + "".join(v) + "}\n" + "\n".join(cls) + "\n"


def palette_js() -> str:
    return json.dumps({
        "status": CYCLE_STATUS_COLORS, "statusInk": CYCLE_STATUS_INK, "statusOn": CYCLE_STATUS_ON,
        "statusPattern": CYCLE_STATUS_PATTERN, "statusPatternFg": CYCLE_STATUS_PATTERN_FG,
        "tier": TIER_COLORS, "tierInk": TIER_INK, "tierOn": TIER_ON,
        "recency": [[hi, fill, ink] for hi, fill, ink, _ in RECENCY_STEPS], "recencyNone": RECENCY_NONE,
        "brand": BRAND,
    })


# ── Shared Plotly theme (Our World in Data reference) ─────────────────────────
# One dict styles every chart on the page: the server-built figures through
# _theme_fig() inside R(), and every client-side chart through the JS
# _themed() wrapper, which receives this same dict as JSON. Styling only:
# traces, values, chart types and sort orders are never touched.
#   - no chart borders, no axis lines; light dashed gridlines on the value
#     axis only, where the chart already asked for a grid
#   - dashboard fonts: Source Serif 4 titles, Source Sans 3 everywhere else
#   - recessive axis text, quiet sentence-case axis titles
#   - legends sit top-left under the title, borderless (direct-label style)
#   - one white hover card with a hairline border
#   - one margin rule: title band on top, 24px right/bottom, automargin left
_SANS = "'Source Sans 3','Segoe UI',system-ui,sans-serif"
_SERIF = "'Source Serif 4',Georgia,serif"
PLOTLY_THEME = {
    "font": {"family": _SANS, "size": 13, "color": BRAND["text"]},
    "title": {"font": {"family": _SERIF, "size": 18, "color": BRAND["ink"]},
              "x": 0, "xanchor": "left", "xref": "container",
              "y": 1, "yanchor": "top", "yref": "container", "pad": {"t": 14, "l": 4}},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "axis": {"showline": False, "ticks": "", "ticklen": 0, "automargin": True,
             "gridcolor": "#e3e7ee", "griddash": "dash", "gridwidth": 1,
             "zerolinecolor": BRAND["rule"], "zerolinewidth": 1,
             "tickfont": {"family": _SANS, "size": 12, "color": BRAND["muted"]},
             "title": {"font": {"family": _SANS, "size": 13, "color": BRAND["muted"]}, "standoff": 10}},
    "legend": {"orientation": "h", "x": 0, "xanchor": "left", "y": 1.0, "yanchor": "bottom",
               "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0, "itemsizing": "constant",
               "traceorder": "normal", "itemwidth": 30,
               "font": {"family": _SANS, "size": 13, "color": BRAND["text"]}},
    "hoverlabel": {"bgcolor": "#ffffff", "bordercolor": BRAND["rule"], "align": "left",
                   "namelength": -1,
                   "font": {"family": _SANS, "size": 13, "color": BRAND["ink"]}},
    "colorbar": {"outlinewidth": 0, "thickness": 10, "ticks": "",
                 "tickfont": {"family": _SANS, "size": 12, "color": BRAND["muted"]},
                 "title": {"font": {"family": _SANS, "size": 12, "color": BRAND["muted"]}}},
    "modebar": {"bgcolor": "rgba(0,0,0,0)", "color": "#9aa3b2", "activecolor": BRAND["navy"]},
    "margin": {"r": 24, "b": 24, "l": 8, "pad": 0},
    "bar_gap_line": {"color": "#ffffff", "width": 2},   # 2px surface gap between stacked fills
}


def _theme_margin_top(title_text: str, has_legend: bool) -> int:
    lines = (title_text.count("<br>") + 1) if title_text else 0
    return (16 if not lines else 28 + 24 * lines) + (32 if has_legend else 0)


def _theme_fig(fig):
    """Apply PLOTLY_THEME to a server-built figure (styling only)."""
    T = PLOTLY_THEME
    title_text = re.sub(r"</?b>", "", (fig.layout.title.text or ""))
    multi = sum(1 for t in fig.data if t.type not in ("heatmap", "choropleth")) > 1
    has_legend = multi and fig.layout.showlegend is not False and not any(t.type == "pie" for t in fig.data)
    below = any((a.yref == "paper" and (a.y or 0) < 0) for a in (fig.layout.annotations or []))
    m = fig.layout.margin
    fig.update_layout(
        font=T["font"], paper_bgcolor=T["paper_bgcolor"], plot_bgcolor=T["plot_bgcolor"],
        hoverlabel=T["hoverlabel"], modebar=T["modebar"],
        margin=dict(t=_theme_margin_top(title_text, has_legend),
                    r=max(T["margin"]["r"], m.r or 0),
                    b=(m.b if below and m.b else T["margin"]["b"]),
                    l=T["margin"]["l"], pad=0),
    )
    if title_text:
        fig.update_layout(title=dict(text=title_text, **T["title"]))
    if has_legend:
        fig.update_layout(legend=T["legend"])
    for upd in (fig.update_xaxes, fig.update_yaxes):
        upd(**{k: v for k, v in T["axis"].items() if k != "title"})
        upd(title_font=T["axis"]["title"]["font"], title_standoff=T["axis"]["title"]["standoff"])
    if fig.layout.geo:
        fig.update_geos(bgcolor="rgba(0,0,0,0)")
    for tr in fig.data:
        if tr.type in ("heatmap", "choropleth"):
            tr.update(colorbar=T["colorbar"])
        if tr.type == "bar" and fig.layout.barmode == "stack":
            tr.update(marker_line=T["bar_gap_line"])
    return fig


# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --primary:#003d82;--secondary:#006eb6;--accent:#009ade;
  --success:#1f5fa8;--warning:#8a5a00;--danger:#b13a24;
  --navy-deep:#00285a;   /* the one dark surface: nav, hero panel, briefing, footer */
  --light:#f4f7fb;--white:#fff;--dark:#0d1f4e;
  --text:#1e2a4a;--muted:#5b6577;--border:#e4e7ef;
  /* Editorial type system - one superfamily, two voices.
     Source Sans 3 carries UI chrome, body copy, tables and charts: a sober
     humanist sans with true tabular/lining figures and full Latin Extended
     coverage for the Francophone and Lusophone Member States.
     Source Serif 4 (optical-size axis) is reserved for headline moments: the
     hero title, section titles and every "big number" a reader's eye should
     land on first. Shared metrics keep the two voices on one baseline. */
  --font:'Source Sans 3','Segoe UI',system-ui,-apple-system,sans-serif;
  --font-serif:'Source Serif 4',Georgia,'Times New Roman',serif;
  /* Role scale (px, not fluid: a dense data surface must stay spatially
     predictable). Source Sans runs ~13% narrower than the old geometric
     sans, so each step sits one notch up at roughly the same line length. */
  --fs-xs:13px;    /* metadata, micro caps labels, dense table cells */
  --fs-sm:14px;    /* UI controls, tabs, captions, secondary copy */
  --fs-base:16px;  /* body prose */
  --fs-md:18px;    /* card titles, emphasised figures */
  /* Spacing scale (4px base) and the three rhythm roles built from it.
     Tight inside a group, medium between blocks, generous above a new
     section: the contrast between them is what carries the hierarchy. */
  --sp-1:4px;--sp-2:8px;--sp-3:12px;--sp-4:16px;--sp-5:24px;--sp-6:32px;--sp-7:48px;--sp-8:64px;
  --gap-card:var(--sp-4);      /* siblings in one group (cards in a row)   */
  --gap-block:var(--sp-5);     /* between blocks inside a tab              */
  --gap-section:var(--sp-7);   /* above a new labelled section             */
  --pad-card:var(--sp-5);      /* inside every card                        */
  /* Motion: a dashboard opened many times a day should feel crisp, not
     performed. One strong ease-out, short durations, nothing over 300ms. */
  --ease-out:cubic-bezier(.23,1,.32,1);
  --dur-press:140ms;   /* button press feedback        */
  --dur-ui:180ms;      /* hover colour, small state     */
  --dur-enter:240ms;   /* content entering, bars        */
  /* Layered shadows (tight contact shadow + soft diffuse ambient shadow)
     read as real depth rather than a single flat drop-shadow. */
  --shadow-sm:0 1px 2px rgba(15,23,42,.04),0 3px 8px rgba(15,23,42,.05);
  --shadow-md:0 2px 6px rgba(15,23,42,.05),0 10px 24px rgba(15,23,42,.09);
  --shadow-lg:0 4px 10px rgba(15,23,42,.06),0 20px 48px rgba(15,23,42,.14);
  --radius:16px;
}
html{scroll-behavior:smooth;overflow-x:hidden;color-scheme:light;
  scroll-padding-top:128px;          /* focused/anchored content never hides under the sticky nav + tabs */
  accent-color:var(--primary);       /* native checkboxes, radios, range sliders */
  scrollbar-color:#c3ccd9 transparent;scrollbar-width:thin}
input,textarea{caret-color:var(--primary)}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:#c3ccd9;border-radius:10px;border:2px solid transparent;background-clip:content-box}
::-webkit-scrollbar-track{background:transparent}
/* ── Focus visibility - every interactive element gets a consistent,
   high-contrast ring on keyboard focus (never on mouse click, via
   :focus-visible), so keyboard users navigating the 6 tabs, filter
   controls, and 48-row tables are never left invisible to themselves. */
a:focus-visible,button:focus-visible,select:focus-visible,input:focus-visible,
.tab-btn:focus-visible,[tabindex]:focus-visible{
  outline:3px solid var(--who-blue);outline-offset:2px;border-radius:4px;
}
.skip-link{position:absolute;left:-9999px;top:0;z-index:10000;background:var(--primary);color:#fff;
  padding:10px 18px;border-radius:0 0 8px 0;font-weight:700;font-size:var(--fs-base);text-decoration:none}
.skip-link:focus{left:0;}
/* ── Interaction: press feedback on every button ── */
button,.tab-btn,.filter-reset,.prio-pill,#back-to-top{
  transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),
             border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);
}
button:active,.tab-btn:active,.filter-reset:active,.prio-pill:active,#back-to-top:active{transform:scale(.97)}
.footer-logo{opacity:.85;transition:opacity var(--dur-ui) var(--ease-out)}
/* Reduced motion = no movement, but keep short opacity fades that aid
   comprehension (content appearing, chevrons) instead of killing all feedback. */
@media(prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .reveal,.reveal.will-animate{transform:none!important;transition:opacity 150ms linear}
  .inst-bar{animation:barFade 150ms linear both}
  button:active,.tab-btn:active,.filter-reset:active,.prio-pill:active,#back-to-top:active{transform:none}
  .chart-about>summary i,.profile-section-head .sec-chevron{transition:opacity 150ms linear}
}
@keyframes barFade{from{opacity:0}to{opacity:1}}
body{font-family:var(--font);background:#f6f7fb;color:var(--text);line-height:1.6;font-size:var(--fs-base);overflow-x:hidden;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;font-optical-sizing:auto;font-kerning:normal}
h1,h2,h3,h4{text-wrap:balance}
p,li{text-wrap:pretty}
/* Figures: every number a reader compares - KPIs, table columns, badges,
   pills, chart ticks - is set tabular + lining so digits stack in columns
   and values do not jitter when filters change them. Prose keeps the
   font's proportional default. */
table,.num-cell,.rank-cell,
.kpi-value,.kpi-delta,.hero-stat-val,.stat-val,.signal-val,.tier-card-val,.stat-hl-val,
.profile-kpi-value,.profile-kpi-ci,.profile-kpi-trend,.profile-kpi-sex span,.inst-pct,
.tier-badge,.prio-pill,.profile-survey-pill,.profile-iso-badge,.hero-qs,.footer-badge,
.section-num,.filter-count,
.js-plotly-plot svg text,#js-plotly-tester text{font-variant-numeric:tabular-nums lining-nums}
::selection{background:rgba(0,110,182,.18);color:var(--dark)}
@keyframes barGrow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
/* ── Reading progress ── */
#reading-progress{position:fixed;top:0;left:0;height:3px;background:var(--who-blue);width:100%;transform:scaleX(0);transform-origin:left center;z-index:9999;will-change:transform}
/* ── Back to top ── */
#back-to-top{position:fixed;bottom:32px;right:32px;width:46px;height:46px;background:var(--primary);color:#fff;border:none;border-radius:50%;font-size:var(--fs-md);cursor:pointer;display:none;align-items:center;justify-content:center;box-shadow:var(--shadow-lg);transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);z-index:999}
/* ── Top nav ── */
.topnav{position:sticky;top:0;z-index:1000;background:var(--navy-deep);box-shadow:0 2px 12px rgba(0,10,50,.35);height:70px;border-bottom:1px solid rgba(255,255,255,.1)}
.topnav::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--who-blue)}
.topnav-inner{max-width:1400px;margin:0 auto;padding:0 32px;height:100%;display:flex;align-items:center;gap:20px}
.nav-logos{display:flex;align-items:center;gap:18px;flex-shrink:0}
.nav-logos img{height:40px;object-fit:contain;filter:brightness(1.05)}
.nav-divider{width:1px;height:34px;background:rgba(255,255,255,.18)}
/* ── Hero ── */
.hero{background:#fff;padding:0;position:relative;overflow:hidden;border-bottom:1px solid var(--border)}
/* Subtle dot-grid on the left panel */
/* Dot-grid texture on right panel */
/* A 48-node network - one point per AFRO country/territory, nearest-
   neighbour lines - as the platform's own signature motif: a literal
   "surveillance network" rendered as quiet linework behind the headline
   numbers, rather than generic decoration. */
/* Each badge staggered entrance */
/* SPI progress bar */
/* Hero left */
/* Quick-stat pills below subtitle */
/* ── Reveal animation (hidden only when JS adds .will-animate) ── */
.reveal{transition:opacity var(--dur-enter) var(--ease-out),transform var(--dur-enter) var(--ease-out)}
.reveal.will-animate{opacity:0;transform:translateY(8px)}
.reveal.visible{opacity:1;transform:translateY(0)}
/* ── Container ── */
.container{max-width:1400px;margin:0 auto;padding:0 28px;position:relative}
/* ── Wide-screen centering (>1400px): all frame elements stay centered ── */
@media(min-width:1500px){
  .topnav-inner,.tab-nav-inner,.footer-inner{max-width:1480px}
  .container{max-width:1480px}
}
@media(min-width:1800px){
  .topnav-inner,.tab-nav-inner,.footer-inner{max-width:1600px}
  .container{max-width:1600px}
}
/* ── Layout ──
   CSS Grid instead of flex+calc(): a 12-column grid divides its gutters
   exactly, so a col-8+col-4 row and a col-6+col-6 row always share the same
   vertical edges (the old flex version's calc(33.333% - 14px) etc. was off
   by a few px on every fractional column - 20px*(n-1)/n, not a flat 10-15px). */
.row{display:grid;grid-template-columns:repeat(12,1fr);gap:var(--gap-card);margin-bottom:var(--gap-block)}
.col-12{grid-column:span 12}.col-8{grid-column:span 8}.col-7{grid-column:span 7}.col-6{grid-column:span 6}.col-5{grid-column:span 5}.col-4{grid-column:span 4}.col-3{grid-column:span 3}
/* ── Section ── */
.section{padding:var(--sp-7) 0 var(--sp-8)}
.section-header{margin-bottom:var(--sp-6)}
.section-header-inner{display:flex;align-items:baseline;gap:var(--sp-3);margin-bottom:var(--sp-2)}
.section-num{display:none}
.section-title{font-family:var(--font-serif);font-size:1.85rem;font-weight:600;color:var(--dark);letter-spacing:-.015em;line-height:1.15;display:block}
.section-subtitle{color:var(--muted);font-size:var(--fs-base);margin:0;max-width:80ch;line-height:1.55}
hr.section-divider{border:none;border-top:1px solid var(--border);margin:var(--gap-section) 0}
/* ── Cards ── */
.chart-card{background:#fff;border-radius:var(--radius);padding:var(--pad-card);box-shadow:var(--shadow-sm);border:1px solid var(--border);height:100%;position:relative;overflow:hidden}
.chart-card::before{content:'';position:absolute;inset:0;border-radius:var(--radius);opacity:0;background:none;pointer-events:none}
.chart-commentary{margin-top:var(--sp-4);padding:var(--sp-3) var(--sp-4);background:var(--tint);border-radius:10px;font-size:var(--fs-sm);color:var(--text);line-height:1.6}
/* Captions read as a caption column, not a 170ch banner across a wide chart */
.chart-commentary{max-width:100ch}
/* Progressive disclosure: one takeaway line, full validated text one click away */
.chart-note{margin-top:var(--sp-4);margin-bottom:var(--gap-block);max-width:100ch}
.chart-card .chart-note,.method-card .chart-note{margin-bottom:0}
.chart-takeaway{font-size:var(--fs-base);line-height:1.5;color:var(--text);margin:0 0 var(--sp-1)}
.chart-about>summary{display:inline-flex;align-items:center;gap:var(--sp-1);cursor:pointer;list-style:none;
  font-size:var(--fs-sm);font-weight:600;color:var(--secondary);padding:var(--sp-1) 0;border-radius:4px;user-select:none}
.chart-about>summary::-webkit-details-marker{display:none}
.chart-about>summary i{font-size:14px;transition:transform 160ms cubic-bezier(.23,1,.32,1)}
.chart-about[open]>summary i{transform:rotate(90deg)}
.chart-about>.chart-commentary,.chart-about>div{margin-top:var(--sp-2)}
@media print{.chart-about>summary{display:none}}
/* ── Insight boxes ── */
.insight-box{display:flex;align-items:flex-start;gap:var(--sp-3);padding:var(--sp-3) var(--sp-4);border-radius:10px;margin-bottom:var(--gap-block);border:1px solid var(--rule);font-size:var(--fs-base);line-height:1.6}
.insight-icon{font-size:var(--fs-md);flex-shrink:0;margin-top:2px}
/* ── KPI cards ── */
.kpi-row{display:flex;flex-wrap:wrap;gap:var(--gap-card);margin-bottom:var(--gap-block)}
.kpi-card{flex:1;min-width:145px;background:#fff;border-radius:var(--radius);padding:20px 18px 17px;box-shadow:var(--shadow-sm);border:1px solid var(--border);position:relative;overflow:hidden}
.kpi-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:currentColor;opacity:.3}
.kpi-icon{font-size:22px;margin-bottom:9px}
.kpi-value{font-family:var(--font-serif);font-size:2rem;font-weight:600;line-height:1;margin-bottom:5px;letter-spacing:-.01em}
.kpi-label{font-size:var(--fs-xs);font-weight:600;text-transform:uppercase;letter-spacing:.9px;color:var(--muted)}
.kpi-delta{font-size:var(--fs-xs);margin-top:6px;font-weight:600;display:flex;align-items:center;gap:4px}
/* ── Instrument cards ── */
.instrument-grid{display:flex;flex-wrap:wrap;gap:var(--gap-card);margin-bottom:var(--gap-block)}
.instrument-card{flex:1;min-width:200px;background:#fff;border-radius:var(--radius);padding:20px;box-shadow:var(--shadow-sm);border:1px solid var(--border);}
.inst-type{font-family:var(--font-serif);font-size:22px;font-weight:600;letter-spacing:-.01em;margin-bottom:4px}
.inst-full{font-size:var(--fs-xs);color:var(--muted);line-height:1.5;margin-bottom:10px;min-height:34px}
.inst-meta{display:flex;flex-direction:column;gap:3px;margin-bottom:12px}
.inst-meta span{font-size:var(--fs-xs);color:var(--muted);display:flex;align-items:center;gap:5px}
.inst-stats{display:flex;gap:14px;margin-bottom:12px}
.inst-stat{display:flex;flex-direction:column;align-items:center}
.stat-val{font-family:var(--font-serif);font-size:1.4rem;font-weight:600;line-height:1;color:var(--dark)}
.stat-lbl{font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.6px;color:var(--muted)}
.inst-bar-wrap{height:6px;background:#f0f0f0;border-radius:6px;overflow:hidden;margin-bottom:5px}
.inst-bar{height:6px;border-radius:6px;transform-origin:left center;animation:barGrow var(--dur-enter) var(--ease-out) both}
.inst-pct{font-size:var(--fs-xs);font-weight:700}
/* ── Recommendations ── */
.rec-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:var(--gap-card);margin-top:var(--sp-2)}
.rec-card{background:#fff;border-radius:var(--radius);padding:22px 24px;box-shadow:var(--shadow-sm);border:1px solid var(--border);display:flex;gap:18px;align-items:flex-start;}
.rec-num{width:34px;height:34px;background:var(--primary);color:#fff;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:var(--fs-md);font-weight:800;flex-shrink:0}
.rec-content h4{font-size:var(--fs-base);font-weight:700;color:var(--dark);margin-bottom:7px}
.rec-content p{font-size:var(--fs-sm);color:var(--muted);line-height:1.6}
/* ── Methods ── */
.methods-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:var(--gap-card);align-items:start}
.method-card{background:#fff;border-radius:var(--radius);padding:var(--pad-card);box-shadow:var(--shadow-sm);border:1px solid var(--border)}
.method-card h3{font-size:var(--fs-base);font-weight:700;color:var(--dark);margin-bottom:12px;display:flex;align-items:center;gap:8px}
.method-card ul{list-style:none;padding:0}
.method-card li{font-size:var(--fs-sm);color:var(--muted);padding:4px 0;border-bottom:1px solid #f5f5f5;line-height:1.65}
.method-card li:last-child{border-bottom:none}
.method-card li code{background:#f0f4ff;padding:1px 6px;border-radius:6px;font-family:ui-monospace,'Cascadia Mono',Consolas,monospace;font-size:var(--fs-xs);color:var(--primary)}
/* ── Footer ── */
.footer{background:var(--navy-deep);color:rgba(255,255,255,.7);padding:0;margin-top:40px}
.footer-inner{max-width:1400px;margin:0 auto;padding:28px 32px;display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
.footer-badge{display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:9999px;padding:3px 11px;font-size:var(--fs-xs);margin:2px;color:rgba(255,255,255,.8)}
/* ══ TABS ════════════════════════════════════════════════════════════════════ */
.tab-nav{background:#fff;border-bottom:2px solid var(--border);position:sticky;top:70px;z-index:990;box-shadow:0 4px 18px rgba(0,20,80,.09);overflow-x:auto}
.tab-nav-inner{max-width:1400px;margin:0 auto;padding:0 16px;display:flex;gap:0}
.tab-btn{background:none;border:none;padding:13px 22px;font-family:var(--font);font-size:var(--fs-sm);font-weight:600;color:var(--muted);cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;gap:8px;letter-spacing:0;position:relative;border-radius:0}
.tab-btn::before{content:'';position:absolute;bottom:6px;top:6px;left:8px;right:8px;border-radius:10px;background:rgba(0,61,130,.06);opacity:0;transition:opacity var(--dur-ui) var(--ease-out)}
.tab-btn::after{content:'';position:absolute;bottom:-2px;left:18px;right:18px;height:3px;background:var(--primary);border-radius:3px 3px 0 0;opacity:0}
.tab-btn.active{color:var(--primary);font-weight:800}
.tab-btn.active::before{opacity:1}
.tab-btn.active::after{opacity:1;left:8px;right:8px}
.tab-btn i{font-size:var(--fs-sm);opacity:.65}
.tab-btn.active i{opacity:1;color:var(--accent)}
.tab-pane{display:none}
.tab-pane.active{display:block}
/* ══ FILTER BAR ═════════════════════════════════════════════════════════════ */
.filter-bar{background:#fff;border:1px solid var(--border);border-radius:var(--radius);padding:var(--sp-3) var(--sp-4);margin-bottom:var(--gap-block);display:flex;flex-wrap:wrap;gap:var(--sp-3) var(--sp-4);align-items:center;box-shadow:var(--shadow-sm)}
.filter-label{font-size:var(--fs-xs);font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;white-space:nowrap}
.filter-select{border:1px solid var(--border);border-radius:10px;padding:7px 12px;font-family:var(--font);font-size:var(--fs-sm);color:var(--text);background:#fafbff;cursor:pointer;outline:none;transition:border-color var(--dur-ui) var(--ease-out),box-shadow var(--dur-ui) var(--ease-out)}
.filter-select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(74,144,226,.12)}
.filter-input{border:1px solid var(--border);border-radius:10px;padding:7px 13px;font-family:var(--font);font-size:var(--fs-sm);color:var(--text);background:#fafbff;outline:none;width:175px;transition:border-color var(--dur-ui) var(--ease-out),box-shadow var(--dur-ui) var(--ease-out)}
.filter-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(74,144,226,.12)}
.filter-reset{background:var(--primary);color:#fff;border:none;border-radius:10px;padding:8px 16px;font-family:var(--font);font-size:var(--fs-sm);font-weight:600;cursor:pointer;display:flex;align-items:center;gap:6px}
.filter-count{font-size:var(--fs-xs);color:var(--muted);margin-left:auto;font-style:italic;white-space:nowrap}
/* ══ TABLES ═════════════════════════════════════════════════════════════════ */
.rank-cell{font-weight:700;color:var(--muted);font-size:var(--fs-sm);text-align:center}
.num-cell{text-align:center;font-variant-numeric:tabular-nums}
/* Country map thumbnail */
.country-map{display:inline-block;flex-shrink:0;background-repeat:no-repeat;background-position:center;background-size:contain;background-origin:content-box;width:40px;height:28px;opacity:.85;border-radius:6px;background:#f5f8ff;padding:2px;border:1px solid #e8eef8;vertical-align:middle;margin-right:8px;transition:opacity var(--dur-ui) var(--ease-out)}
/* ══ EXECUTIVE SIGNALS ══════════════════════════════════════════════════════ */
.signal-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--gap-card);margin-bottom:var(--gap-block)}
.signal-card{background:#fff;border-radius:var(--radius);padding:var(--pad-card);box-shadow:var(--shadow-sm);border:1px solid var(--border);position:relative;overflow:hidden;}
.signal-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:currentColor;opacity:.5;border-radius:var(--radius) var(--radius) 0 0}
.signal-card::after{content:'';position:absolute;bottom:-30px;right:-20px;width:100px;height:100px;border-radius:50%;background:currentColor;opacity:.04}
.signal-val{font-family:var(--font-serif);font-size:2.8rem;font-weight:600;line-height:1;letter-spacing:-.015em}
.signal-lbl{font-size:var(--fs-xs);font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-top:8px}
.signal-sub{font-size:var(--fs-xs);color:var(--muted);margin-top:5px;line-height:1.55}
/* ══ EXECUTIVE MESSAGE ══════════════════════════════════════════════════════ */
/* ══ TIER BADGE ═════════════════════════════════════════════════════════════ */
.tier-badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:var(--fs-xs);font-weight:700;vertical-align:middle;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.schema-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:var(--gap-card);margin-bottom:var(--gap-block)}
.schema-card{background:#fff;border-radius:10px;border:1px solid var(--border);overflow:hidden;box-shadow:0 4px 12px rgba(0,20,80,.06)}
.schema-card-head{padding:11px 16px;font-weight:700;font-size:var(--fs-sm);color:#fff;display:flex;align-items:center;gap:8px}
.schema-card table{width:100%;border-collapse:collapse;font-size:var(--fs-sm)}
.schema-card table tr{border-bottom:1px solid var(--border)}
.schema-card table td{padding:7px 14px;color:var(--muted)}
.schema-card table td:first-child{color:var(--text);font-weight:500;font-family:ui-monospace,'Cascadia Mono',Consolas,monospace;font-size:var(--fs-xs)}
@media(max-width:920px){
  .col-6,.col-4,.col-3,.col-8,.col-7,.col-5{grid-column:span 12}
  /* Reflow the headline numbers under the title instead of dropping them:
     48 countries / 5 instruments / regional SPI are the whole point of the
     hero, not decoration to discard on a phone. */
}
@media(max-width:1100px){.signal-grid[style*="repeat(5"]{grid-template-columns:repeat(3,1fr)!important}}
@media(max-width:700px){.signal-grid[style*="repeat(5"]{grid-template-columns:repeat(2,1fr)!important}}
/* ══ TIER SUMMARY CARDS ══════════════════════════════════════════════════ */
.tier-row{display:flex;flex-wrap:wrap;gap:var(--gap-card);margin-bottom:var(--gap-block);}
.tier-card{flex:1;min-width:130px;background:#fff;border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow-sm);border:1px solid var(--border);border-top-width:4px;}
.tier-card-val{font-family:var(--font-serif);font-size:2.2rem;font-weight:600;line-height:1;letter-spacing:-.01em;}
.tier-card-lbl{font-size:var(--fs-xs);font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-top:6px;}
.tier-card-sub{font-size:var(--fs-xs);color:var(--muted);margin-top:3px;}
/* ══ STAT HIGHLIGHT ROW ══════════════════════════════════════════════════ */
.stat-highlight-row{display:flex;flex-wrap:wrap;gap:var(--gap-card);background:#fff;border-radius:var(--radius);padding:var(--pad-card);box-shadow:var(--shadow-sm);border:1px solid var(--border);margin-bottom:var(--gap-block);align-items:center;}
.stat-highlight-item{display:flex;flex-direction:column;align-items:center;padding:0 16px;border-right:1px solid var(--border);last-child:border-right:none;}
.stat-highlight-item:last-child{border-right:none;}
.stat-hl-val{font-family:var(--font-serif);font-size:2rem;font-weight:600;letter-spacing:-.01em;line-height:1;}
.stat-hl-lbl{font-size:var(--fs-xs);font-weight:700;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin-top:5px;}
/* ══ SECTION DIVIDER LABEL ═══════════════════════════════════════════════ */
.section-divider-label{display:flex;align-items:center;gap:var(--sp-3);margin:var(--gap-section) 0 var(--sp-4);font-size:var(--fs-xs);font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);}
.section-divider-label::before,.section-divider-label::after{content:'';flex:1;height:1px;background:var(--border);}
/* ══ COUNTRY PROFILE TAB ═════════════════════════════════════════════════ */
.profile-header-card{background:var(--tint);border:1px solid var(--border);border-radius:var(--radius);padding:var(--pad-card);margin-bottom:var(--gap-card);box-shadow:var(--shadow-sm);position:relative;overflow:hidden;}
.profile-iso-badge{display:inline-flex;align-items:center;justify-content:center;width:60px;height:44px;background:var(--primary);color:#fff;border-radius:10px;font-size:var(--fs-xs);font-weight:800;letter-spacing:.5px;flex-shrink:0;box-shadow:0 4px 12px rgba(0,61,130,.25);}
.profile-kpi-row{display:flex;flex-wrap:wrap;gap:var(--gap-card);margin-bottom:var(--gap-block);}
.profile-kpi-card{flex:1;min-width:150px;background:#fff;border-radius:var(--radius);padding:18px 16px 14px;box-shadow:var(--shadow-sm);border:1px solid var(--border);position:relative;overflow:hidden;}
.profile-kpi-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:currentColor;opacity:.25;}
.profile-kpi-icon{font-size:22px;margin-bottom:8px;}
.profile-kpi-value{font-family:var(--font-serif);font-size:1.9rem;font-weight:600;line-height:1;letter-spacing:-.01em;margin-bottom:4px;}
.profile-kpi-ci{font-size:var(--fs-xs);color:var(--muted);font-weight:600;margin-bottom:2px;}
.profile-kpi-label{font-size:var(--fs-xs);font-weight:700;text-transform:uppercase;letter-spacing:.9px;color:var(--muted);}
.profile-kpi-trend{font-size:var(--fs-sm);margin-top:6px;font-weight:700;}
.profile-kpi-sex{display:flex;gap:6px;margin-top:8px;}
.profile-kpi-sex span{font-size:var(--fs-xs);font-weight:600;padding:2px 8px;border-radius:10px;}
.profile-section-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:var(--gap-card);margin-bottom:var(--gap-block);align-items:start;}
.profile-section-card{background:#fff;border-radius:var(--radius);box-shadow:var(--shadow-sm);border:1px solid var(--border);overflow:hidden;}
.profile-section-head{padding:10px 15px;display:flex;align-items:center;gap:8px;cursor:pointer;list-style:none;user-select:none;}
.profile-section-head::-webkit-details-marker{display:none;}
.profile-section-head span.sec-title{font-size:var(--fs-sm);font-weight:700;color:#fff;flex:1;}
.profile-section-head span.sec-step{font-size:var(--fs-xs);color:rgba(255,255,255,.65);font-style:italic;}
.profile-section-head .sec-chevron{color:rgba(255,255,255,.85);font-size:var(--fs-sm);transition:transform 200ms;}
details.profile-section-card[open] .sec-chevron{transform:rotate(180deg);}
.profile-ind-table{width:100%;table-layout:fixed;border-collapse:collapse;font-size:var(--fs-xs);}
.profile-ind-table th{padding:8px 6px;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;font-weight:700;background:#f7f9ff;border-bottom:1px solid var(--border);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.profile-ind-table td{padding:8px 6px;border-bottom:1px solid #f3f5fb;vertical-align:middle;line-height:1.5;word-wrap:break-word;overflow-wrap:break-word;}
.profile-ind-table tbody tr:last-child td{border-bottom:none;}
.profile-no-data{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:64px 20px;color:var(--muted);text-align:center;gap:16px;}
.profile-no-data i{font-size:36px;opacity:.28;}
.profile-survey-pill{display:inline-flex;align-items:center;gap:5px;background:rgba(0,61,130,.08);border:1px solid rgba(0,61,130,.18);border-radius:9999px;padding:3px 11px;font-size:var(--fs-xs);font-weight:600;color:var(--primary);}

/* ══ PRINT ═══════════════════════════════════════════════════════════════
   This dashboard gets printed/PDF-exported for meetings. Default browser
   printing of this page would previously: only show whichever one tab was
   active on screen (the other five are display:none), burn ink on the dark
   navbar/hero/footer gradients, turn box-shadows into grey smears, and let
   Plotly charts split mid-figure across a page break. */
@media print{
  .topnav,.tab-nav,#reading-progress,#back-to-top,.skip-link,
  .filter-reset,#btn-export-spi,#btn-export-profile,.js-plotly-plot .modebar{display:none!important;}
  body{background:#fff!important;overflow-x:visible!important;}
  .hero{border-bottom:2px solid #000;}
  .footer{background:#fff!important;color:#000!important;border:1px solid #999;}
  .footer-badge{color:#000!important;}
  /* Unfold every tab so the full report prints, one section per page */
  .tab-pane{display:block!important;break-after:page;}
  .tab-pane:last-of-type{break-after:auto;}
  .reveal{opacity:1!important;transform:none!important;}
  .chart-card,.kpi-card,.signal-card,.instrument-card,.rec-card,.tier-card,
  .profile-kpi-card,.profile-section-card,.method-card,.schema-card{
    box-shadow:none!important;border:1px solid #999!important;break-inside:avoid;
  }
  a[href]::after{content:none!important;}
  .print-selection{display:inline!important;}
  .js-plotly-plot,.st-badge,.tier-badge,.tier-card,.signal-card,.hero-spi-fill{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
}
.print-selection{display:none;font-weight:700;}

/* ══ PHONE & TABLET ════════════════════════════════════════════════════════
   Platform baseline: no grey tap flash, no font inflation, no 300ms click
   wait, controls not text-selectable on long-press. */
html{-webkit-tap-highlight-color:transparent;-webkit-text-size-adjust:100%;text-size-adjust:100%}
button,a,summary,select,input,[role=button],.tab-btn{touch-action:manipulation}
button,.tab-btn,.prio-pill,.filter-reset,summary{-webkit-user-select:none;user-select:none}
.topnav-inner{padding-left:max(32px,env(safe-area-inset-left));padding-right:max(32px,env(safe-area-inset-right))}
#back-to-top{bottom:calc(24px + env(safe-area-inset-bottom,0px));right:calc(24px + env(safe-area-inset-right,0px))}
/* Touch input: 44px targets, 16px form text (stops iOS zoom-on-focus), and
   the Plotly toolbar off (it sits on the titles; pinch-zoom replaces it). */
@media (pointer:coarse){
  input,select,textarea{font-size:16px!important}
  .tab-btn,.prio-pill,.filter-reset,#back-to-top,.chart-about>summary,.profile-section-head{min-height:44px}
  .chart-about>summary{padding:var(--sp-2) 0}
  .js-plotly-plot .modebar-container{display:none!important}
}
@media(max-width:900px){
  .stat-highlight-row{justify-content:center}
  .stat-highlight-row .stat-tiers{flex:1 1 100%!important;justify-content:stretch!important}
  .stat-highlight-row .stat-tiers .tier-card{flex:1 1 calc(50% - 10px);min-width:0!important}
}
@media(max-width:640px){
  .container{padding:0 16px}
  .topnav{height:56px}
  html{scroll-padding-top:112px}
  .tab-nav{top:56px}
  .nav-logos{gap:12px}
  .nav-logos img{height:30px!important}
  .nav-brand-text,.nav-logos .nav-divider:last-of-type{display:none}   /* the hero H1 carries the name */
  .tab-nav-inner{scroll-snap-type:x proximity;padding:0 8px}
  .tab-btn{scroll-snap-align:start;padding:12px 14px}
  .section{padding:var(--sp-6) 0 var(--sp-7)}
  .chart-card{padding:var(--sp-4)}
  /* Dense charts (48 ranked rows, 48x5 matrix, labelled scatter) keep a
     readable minimum width and scroll sideways inside their card. */
  .chart-wide{overflow-x:auto;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch;margin:0 calc(-1 * var(--sp-4));padding:0 var(--sp-4)}
  .chart-wide>div,.chart-wide>.plotly-graph-div{min-width:560px}
  .prio-sliders{flex-direction:column;align-items:stretch!important;gap:var(--sp-3)!important}
  .prio-sliders>div{width:100%}
  .prio-sliders .slider-sep{display:none}
  .prio-sliders input[type=range]{flex:1;width:auto!important;min-height:32px}
  .prio-sliders .slider-hint{margin-left:0!important}
  .stat-highlight-item{border-right:none!important;padding:0 var(--sp-3)!important}
}
/* ══ WORST-CASE CONTENT (long names, empty cells, narrow screens) ══════════ */
.prof-id>div:last-child{min-width:0}
.prof-id>div:last-child>div:first-child{overflow-wrap:break-word;line-height:1.15}
.status-table .st-badge{white-space:nowrap}
@media(max-width:640px){
  /* Profile header: badge sits above the name instead of squeezing a long
     name ("Democratic Republic of the Congo") into a 3-line column */
  .prof-id{flex-direction:column;gap:var(--sp-3)!important}
  .profile-iso-badge{width:52px;height:36px}
  /* Per-instrument status table: all four columns fit at 375px */
  .status-table th,.status-table td{padding:8px 6px!important;font-size:var(--fs-xs)!important;letter-spacing:0!important}
  .status-table td:first-child{overflow-wrap:break-word;min-width:88px}
  .status-table .st-badge{padding:2px 7px}
  /* Scorecard: the country column stays pinned while the metrics scroll,
     and the caption wraps inside the screen instead of the table width */
  .scorecard-wrap{overscroll-behavior-x:contain}
  #scorecard-table caption{position:sticky;left:0;width:calc(100vw - 72px);white-space:normal}
  #scorecard-table th:nth-child(2),#scorecard-table td:nth-child(2){position:sticky;left:0;z-index:1;min-width:150px;max-width:170px;
    background:#fff;box-shadow:1px 0 0 var(--border)}
  #scorecard-table thead th:nth-child(2){background:var(--primary);z-index:2}
  #scorecard-table td:nth-child(2) strong{overflow-wrap:break-word}
}

/* ══ HEADER (design/header_v3) ═════════════════════════════════════════════
   Top bar (logos + compile date) -> hero (title, facts, tile map, SPI card,
   tier legend, WHO disclaimer) -> tabs. Schibsted Grotesk is scoped to the
   header; every colour is a dashboard token. */
:root{--topnav-h:58px;--hdr-font:'Schibsted Grotesk','Source Sans 3',system-ui,sans-serif;--hdr-gutter:64px}
.topnav{height:var(--topnav-h);background:var(--dark);box-shadow:none;border-bottom:0}
.topnav::after{display:none}
.topnav-inner{max-width:none;padding:0 var(--hdr-gutter)!important;gap:22px}
.nav-logos{gap:22px}
.nav-logos a:first-of-type .nav-logo{height:31px!important}
.nav-logos a:last-of-type .nav-logo{height:27px!important}
.nav-divider{height:26px;background:rgba(255,255,255,.2)}
.hero{position:relative;overflow:hidden;background:#fff;border-bottom:1px solid var(--border);font-family:var(--hdr-font);color:var(--dark)}
.hero::before{content:'';position:absolute;right:-120px;top:-60px;width:820px;height:820px;border-radius:50%;pointer-events:none;
  background:radial-gradient(closest-side,rgba(0,110,182,.10),rgba(0,110,182,.03) 60%,transparent);z-index:0}
.hero-grid{position:relative;z-index:1;display:grid;grid-template-columns:minmax(0,1fr) 580px;column-gap:24px;min-height:520px;padding:0 var(--hdr-gutter)}
.hero-copy{align-self:center;padding:52px 0;min-width:0}
.hero h1{font-family:var(--hdr-font);font-weight:800;font-size:56px;line-height:1;letter-spacing:-.038em;max-width:600px;color:var(--dark);margin:0;text-wrap:balance}
.hero-sub{margin:26px 0 0;font-size:18px;line-height:1.55;color:var(--muted);max-width:540px;font-weight:400}
.hero-sub strong{color:var(--dark);font-weight:600}
.hero-facts{display:flex;gap:44px;margin-top:44px}
.hero-fact b{display:block;font-size:40px;font-weight:700;letter-spacing:-.03em;line-height:1;font-variant-numeric:lining-nums proportional-nums}
.hero-fact span{display:block;margin-top:8px;font-size:14px;color:var(--muted);line-height:1.35}
.hero-fact.is-current b{color:var(--st-on-cycle-ink)}
.hero-visual{position:relative;min-width:0;display:flex;flex-direction:column;justify-content:flex-end;padding:8px 0 22px}
/* tile map */
.tm-wrap{position:relative;margin-left:auto;width:560px}
.tm-grid{display:grid;grid-template-columns:repeat(var(--cols),minmax(0,1fr));grid-template-rows:repeat(var(--rows),auto);gap:3px}
.tm-tile{aspect-ratio:1;border-radius:6px;background:color-mix(in srgb,var(--tc) 16%,#fff);display:flex;padding:3px;position:relative}
.tm-tile span{flex:1;background:var(--tc);-webkit-mask:var(--m) center/contain no-repeat;mask:var(--m) center/contain no-repeat}
.tm-tile.t1{--tc:var(--tier-1)}.tm-tile.t2{--tc:var(--tier-2)}.tm-tile.t3{--tc:var(--tier-3)}.tm-tile.t4{--tc:var(--tier-4)}
/* SPI card (glass) over the empty Atlantic of the grid */
.spi-card{position:absolute;left:-52px;bottom:-6px;width:284px;padding:22px 24px 20px;border-radius:20px;
  background:rgba(255,255,255,.8);-webkit-backdrop-filter:blur(14px) saturate(1.4);backdrop-filter:blur(14px) saturate(1.4);
  border:1px solid rgba(255,255,255,.9);box-shadow:0 1px 1px rgba(13,31,78,.04),0 20px 50px -14px rgba(13,31,78,.28)}
.spi-card-t{font-size:14px;font-weight:600;color:var(--muted)}
.spi-card-v{display:flex;align-items:baseline;gap:10px;margin-top:6px}
.spi-card-v b{font-size:60px;font-weight:800;letter-spacing:-.045em;line-height:1;color:var(--dark);font-variant-numeric:lining-nums proportional-nums}
.spi-card-v small{font-size:17px;color:var(--muted);font-weight:500}
.spi-card-tag{margin-left:auto;align-self:center;white-space:nowrap;font-size:13px;font-weight:700;padding:5px 10px;border-radius:8px}
.t1-tag{color:var(--tier-1-ink);background:color-mix(in srgb,var(--tier-1) 16%,#fff)}
.t2-tag{color:var(--tier-2-ink);background:color-mix(in srgb,var(--tier-2) 22%,#fff)}
.t3-tag{color:var(--tier-3-ink);background:color-mix(in srgb,var(--tier-3) 20%,#fff)}
.t4-tag{color:var(--tier-4-ink);background:color-mix(in srgb,var(--tier-4) 16%,#fff)}
.spi-track{position:relative;display:flex;gap:3px;height:8px;margin-top:18px}
.spi-track span{border-radius:4px}
.spi-track .t1{background:var(--tier-1)}.spi-track .t2{background:var(--tier-2)}.spi-track .t3{background:var(--tier-3)}.spi-track .t4{background:var(--tier-4)}
.spi-track i{position:absolute;top:-6px;width:4px;height:20px;border-radius:2px;background:var(--dark);box-shadow:0 0 0 2.5px #fff;transform:translateX(-50%)}
.spi-ticks{position:relative;height:14px;margin-top:8px;font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.spi-ticks span{position:absolute;transform:translateX(-50%)}
.spi-ticks span:first-child{transform:none}.spi-ticks span:last-child{transform:translateX(-100%)}
/* legend + disclaimer */
.tm-legend{display:flex;flex-wrap:wrap;justify-content:flex-end;align-items:center;gap:6px 16px;margin-top:22px;font-size:13px;color:var(--muted)}
.tm-legend span{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.tm-legend i{width:10px;height:10px;border-radius:3px}
.tm-legend i.t1{background:var(--tier-1)}.tm-legend i.t2{background:var(--tier-2)}.tm-legend i.t3{background:var(--tier-3)}.tm-legend i.t4{background:var(--tier-4)}
.tm-legend b{color:var(--dark);font-weight:700;font-variant-numeric:tabular-nums}
.tm-legend-cap{font-size:12.5px}
.tm-disclaimer{margin:10px 0 0 auto;max-width:560px;font-size:10.5px;line-height:1.45;color:var(--muted);text-align:right;font-family:var(--font)}
/* tabs: underline style, same buttons/ARIA/handlers */
.tab-nav{top:var(--topnav-h);background:#fff;box-shadow:none;border-bottom:1px solid var(--border)}
.tab-nav-inner{max-width:none;gap:36px;padding:0 var(--hdr-gutter)!important}
.tab-btn{font-family:var(--hdr-font);font-size:15px;font-weight:600;color:var(--muted);padding:18px 0 16px!important;margin:0;
  border-radius:0;border-bottom:2.5px solid transparent;background:none}
.tab-btn::before,.tab-btn::after{display:none}
.tab-btn.active{color:var(--dark);font-weight:600;border-bottom-color:var(--secondary);background:none}
@media print{.hero::before{display:none}.tm-tile,.tm-tile span,.spi-track span{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .spi-card{position:static;margin-top:12px;box-shadow:none;border:1px solid #999}}
/* tablet: visual drops under the copy */
@media(max-width:1180px){
  .hero-grid{grid-template-columns:1fr;row-gap:8px}
  .hero-copy{padding:40px 0 8px}
  .tm-wrap{margin:0 auto}
  .tm-legend{justify-content:center}
  .tm-disclaimer{margin:10px auto 0;text-align:center}
}
/* phone: map under the title, SPI card full-width under the map */
@media(max-width:640px){
  :root{--hdr-gutter:16px}
  .nav-logos{gap:12px}
  .nav-logos a:first-of-type .nav-logo{height:26px!important}
  .nav-logos a:last-of-type .nav-logo{height:22px!important}
  .hero h1{font-size:36px;letter-spacing:-.03em}
  .hero-sub{font-size:16px;margin-top:16px}
  .hero-facts{gap:24px;margin-top:28px}
  .hero-fact b{font-size:32px}
  .hero-fact span{font-size:13px}
  .tm-wrap{width:100%}
  .tm-grid{gap:2px}
  .tm-tile{border-radius:3px;padding:1px}
  .spi-card{position:static;width:100%;margin-top:16px;padding:18px 18px 16px}
  .spi-card-v b{font-size:48px}
  .tm-legend{justify-content:flex-start;gap:6px 12px}
  .tm-disclaimer{text-align:left;margin-left:0}
  .tab-nav-inner{gap:22px}
  .tab-btn{font-size:14px;padding:14px 0 12px!important}
}

/* Hover only where a real hover-capable pointer exists (no sticky hover on touch) */
@media (hover:hover) and (pointer:fine){
  #back-to-top:hover{background:var(--dark)}
  .chart-about>summary:hover{color:var(--primary);text-decoration:underline;text-underline-offset:3px}
  .tab-btn:hover{color:var(--primary)}
  .tab-btn:hover::before{opacity:.6}
  .tab-btn:hover::after{opacity:.3}
  .tab-btn:hover i{opacity:.9}
  .filter-reset:hover{background:var(--dark)}
  .country-map:hover{opacity:1}
  .profile-ind-table tbody tr:hover td{background:#f0f5ff;}
  .footer-logo:hover{opacity:1}
}
"""

# ── JavaScript ─────────────────────────────────────────────────────────────────
JS = """
(function(){
  const bar=document.getElementById('reading-progress');
  // Printing keeps the full validated text: open every "About" note for the
  // print, then restore what the reader had open.
  var _openBeforePrint=[];
  window.addEventListener('beforeprint',function(){
    document.querySelectorAll('details.chart-about').forEach(function(d){ if(!d.open){d.open=true;_openBeforePrint.push(d);} });
  });
  window.addEventListener('afterprint',function(){ _openBeforePrint.forEach(function(d){d.open=false;}); _openBeforePrint=[]; });
  const btn=document.getElementById('back-to-top');
  if(bar&&btn){
    // Cache the scrollable height instead of reading
    // document.documentElement.scrollHeight (a forced layout reflow) on
    // every single scroll event; only recompute it when the layout can
    // actually have changed (resize, or content revealed by tab/profile
    // switches which already dispatch a 'resize' event elsewhere).
    let scrollable=document.documentElement.scrollHeight-window.innerHeight;
    const recompute=()=>{scrollable=Math.max(1,document.documentElement.scrollHeight-window.innerHeight);};
    window.addEventListener('resize',recompute,{passive:true});
    let ticking=false;
    window.addEventListener('scroll',()=>{
      if(ticking)return;
      ticking=true;
      requestAnimationFrame(()=>{
        const p=window.scrollY/scrollable*100;
        bar.style.transform='scaleX('+(p/100)+')';
        btn.style.display=window.scrollY>300?'flex':'none';
        ticking=false;
      });
    },{passive:true});
    btn.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
  }
  // Mark reveal elements for animation only when JS is running
  document.querySelectorAll('.reveal').forEach(el=>el.classList.add('will-animate'));
  const ro=new IntersectionObserver((es)=>{
    es.forEach((e,i)=>{if(e.isIntersecting){setTimeout(()=>e.target.classList.add('visible'),Math.min(i*30,120));ro.unobserve(e.target);}});
  },{threshold:0.04});
  document.querySelectorAll('.reveal').forEach(el=>ro.observe(el));
  // Figures are data: they render at their true value immediately. A count-up
  // shows readers wrong numbers mid-flight (and in screenshots), so none here.
  function animCount(el,target,dur){
    el.textContent=target%1!==0?target.toFixed(1):target.toLocaleString('en-US'); return;
    const isF=target%1!==0,t0=performance.now();
    const step=now=>{const p=Math.min((now-t0)/dur,1),e2=1-Math.pow(1-p,3),v=target*e2;
      el.textContent=isF?v.toFixed(1):Math.round(v).toLocaleString('en-US');
      if(p<1)requestAnimationFrame(step);else el.textContent=isF?target.toFixed(1):target.toLocaleString('en-US');
    };requestAnimationFrame(step);
  }
  const ko=new IntersectionObserver((es)=>{
    es.forEach(e=>{if(e.isIntersecting&&!e.target.dataset.counted){
      e.target.dataset.counted='1';
      e.target.querySelectorAll('[data-count]').forEach(el=>animCount(el,parseFloat(el.dataset.count),1400));
    }});
  },{threshold:0.15});
  document.querySelectorAll('.signal-grid,.kpi-row').forEach(el=>ko.observe(el));
  // Instrument bars grow via CSS (transform: scaleX, compositor-only) - no JS width tweening.

  function activateTab(id){
    document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>{
      b.classList.remove('active');
      b.setAttribute('aria-selected','false');
      b.setAttribute('tabindex','-1');
    });
    const pane=document.getElementById(id);
    const btn=document.querySelector('.tab-btn[data-tab="'+id+'"]');
    if(pane)pane.classList.add('active');
    // Deep link as #view=tab-x: matches no element id, so the browser never
    // jumps/focuses on load. Written only on a user switch, never at start-up.
    if(pane&&!window.__tabInit&&location.hash!=='#view='+id){try{history.replaceState(null,'','#view='+id);}catch(e){}}
    if(btn){
      btn.classList.add('active');
      btn.setAttribute('aria-selected','true');
      btn.setAttribute('tabindex','0');
    }
    // Scroll just past the sticky navbar + tab bar, measured from their
    // actual rendered heights rather than a guessed constant (62 landed
    // content partly under the tab bar since navbar is 70px + tab bar
    // ~46px on its own).
    if(window.scrollY>0){
      var navEl=document.querySelector('.topnav'), tabNavEl=document.querySelector('.tab-nav');
      var offset=(navEl?navEl.offsetHeight:0)+(tabNavEl?tabNavEl.offsetHeight:0);
      window.scrollTo({top:offset,behavior:'auto'});
    }
    if(pane){
      pane.querySelectorAll('.reveal').forEach(el=>{el.classList.remove('will-animate');el.classList.add('visible');});
      pane.querySelectorAll('.signal-grid,.kpi-row').forEach(el=>{
        if(!el.dataset.counted){el.dataset.counted='1';el.querySelectorAll('[data-count]').forEach(e=>animCount(e,parseFloat(e.dataset.count),1400));}
      });
      window.dispatchEvent(new Event('resize'));
      setTimeout(function(){
        window.dispatchEvent(new Event('resize'));
        if(typeof Plotly==='undefined')return;
        pane.querySelectorAll('.plotly-graph-div').forEach(function(el){
          try{Plotly.relayout(el,{autosize:true});}catch(e){}
        });
      },250);
    }
  }
  document.querySelectorAll('.tab-btn').forEach(btn=>btn.addEventListener('click',()=>activateTab(btn.dataset.tab)));
  // Open the tab named in the URL (#tab-profile ...) so links and reloads land where the reader was.
  const _hm=location.hash.match(/^#(?:view=)?(tab-[a-z]+)$/);
  const _hashTab=_hm&&document.querySelector('.tab-btn[data-tab="'+_hm[1]+'"]');
  const firstTab=_hashTab||document.querySelector('.tab-btn');
  window.__tabInit=true; if(firstTab)activateTab(firstTab.dataset.tab); window.__tabInit=false;

  // ── ARIA tabs: Left/Right/Home/End keyboard navigation ────────────────────
  (function(){
    const tabs=Array.from(document.querySelectorAll('.tab-btn'));
    tabs.forEach((btn,i)=>btn.addEventListener('keydown',e=>{
      let j=null;
      if(e.key==='ArrowRight')j=(i+1)%tabs.length;
      else if(e.key==='ArrowLeft')j=(i-1+tabs.length)%tabs.length;
      else if(e.key==='Home')j=0;
      else if(e.key==='End')j=tabs.length-1;
      if(j===null)return;
      e.preventDefault();
      tabs[j].focus();
      activateTab(tabs[j].dataset.tab);
    }));
  })();

  function applyFilters(tableId,searchId,tierSelId,gapSelId,cycleSelId,regSelId,topSelId,countId){
    const tbl=document.getElementById(tableId);if(!tbl)return;
    const search=((document.getElementById(searchId)||{}).value||'').toLowerCase();
    const tier=((document.getElementById(tierSelId)||{}).value||'');
    const gap=((document.getElementById(gapSelId)||{}).value||'');
    const cycle=((document.getElementById(cycleSelId)||{}).value||'');
    const reg=((document.getElementById(regSelId)||{}).value||'').toLowerCase();
    const top=parseInt(((document.getElementById(topSelId)||{}).value||'0'))||0;
    let vis=0;
    const rows=tbl.querySelectorAll('tbody tr');
    rows.forEach(tr=>{
      let show=true;
      if(search&&!(tr.dataset.country||'').includes(search))show=false;
      if(tier&&(tr.dataset.tier||'')!==tier)show=false;
      if(gap&&(tr.dataset.gap||'')!==gap)show=false;
      if(cycle&&(tr.dataset.cycle||'')!==cycle)show=false;
      if(reg&&!(tr.dataset.reg||'').toLowerCase().includes(reg))show=false;
      tr.style.display=show?'':'none';
      if(show)vis++;
    });
    if(top>0){let n=0;rows.forEach(tr=>{if(tr.style.display!=='none'){n++;if(n>top)tr.style.display='none';}});vis=Math.min(vis,top);}
    const cnt=document.getElementById(countId);
    if(cnt)cnt.textContent='Showing '+vis+' of '+rows.length+' countries';
  }
  function bindFilters(tId,sId,trId,gId,cId,rgId,topId,rId,cntId){
    [sId,trId,gId,cId,rgId,topId].forEach(id=>{
      const el=document.getElementById(id);
      if(el){el.addEventListener('input',()=>applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId));
              el.addEventListener('change',()=>applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId));}
    });
    const rb=document.getElementById(rId);
    if(rb)rb.addEventListener('click',()=>{
      // Reset to each control's own declared default (a <select>'s first
      // <option>, e.g. "All countries"/value=0 for sc-top) rather than a
      // blanket value='' - sc-top has no empty option, so that used to
      // leave it at selectedIndex=-1 and render as an empty box.
      [sId,trId,gId,cId,rgId,topId].forEach(id=>{
        const el=document.getElementById(id);
        if(!el)return;
        el.value = (el.tagName==='SELECT' && el.options.length) ? el.options[0].value : '';
      });
      applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId);
    });
    applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId);
  }
  bindFilters('scorecard-table','sc-search','sc-tier','sc-gap','sc-cycle','sc-reg','sc-top','sc-reset','sc-count');

  // ── Strategic Priority tables: live country-name search ───────────────────
  function bindPrioritySearch(inputId,countId){
    const input=document.getElementById(inputId);
    if(!input)return;
    function apply(){
      const q=(input.value||'').toLowerCase().trim();
      let vis=0,total=0;
      document.querySelectorAll('.survey-detail-section tbody tr').forEach(tr=>{
        total++;
        const country=(tr.children[0]&&tr.children[0].textContent||'').toLowerCase();
        const show=!q||country.includes(q);
        tr.style.display=show?'':'none';
        if(show)vis++;
      });
      const cnt=document.getElementById(countId);
      if(cnt)cnt.textContent=q?('Matching '+vis+' rows across all instrument tables'):'';
    }
    input.addEventListener('input',apply);
  }
  bindPrioritySearch('pr-search','pr-count');

  // ── Executive Overview dynamic filter ────────────────────────────────────
  const EXEC_DATA = __EXEC_DATA_PLACEHOLDER__;

  // ── Cycle & Gap - Historical Activity Timeline ────────────────────────────
  const TIMELINE_DATA = __TIMELINE_DATA_PLACEHOLDER__;

  // ── Strategic Priority - overall SPI scores per country ──────────────────
  const SPI_SCORES = __SPI_SCORES_PLACEHOLDER__;

  const _FONT = "'Source Sans 3','Segoe UI',system-ui,sans-serif";
  // Shared Plotly theme - the same PLOTLY_THEME dict the server figures use.
  const _THEME = __PLOTLY_THEME_PLACEHOLDER__;
  // Plotly titles do not wrap. On narrow charts, break the plain-text part
  // across lines at word boundaries (tags are never split) and grow the top
  // margin to match; restore the original when the chart is wide again.
  function _fitTitle(gd){
    if(!gd||!gd.layout||!gd.layout.title||typeof Plotly==='undefined')return;
    var orig=gd._origTitle; if(orig===undefined){orig=gd._origTitle=gd.layout.title.text||''; gd._origMarginT=(gd.layout.margin||{}).t||60;}
    if(!orig)return;
    var maxC=Math.max(18,Math.floor((gd.clientWidth-24)/9));
    // Each original line is tokenised into plain runs and <span ...>text</span>
    // runs; words wrap across both, closing and reopening a span at a break.
    function wrapLine(line){
      var segs=[], re=/(<span[^>]*>)(.*?)(<\/span>)/g, last=0, m;
      while((m=re.exec(line))){ if(m.index>last)segs.push({o:'',t:line.slice(last,m.index),c:''}); segs.push({o:m[1],t:m[2],c:m[3]}); last=re.lastIndex; }
      if(last<line.length)segs.push({o:'',t:line.slice(last),c:''});
      var out='', n=0;
      segs.forEach(function(sg){
        var words=sg.t.replace(/&nbsp;/g,' ').split(/\s+/).filter(Boolean), cur=[];
        var budget=sg.o?Math.round(maxC*1.25):maxC;   // span runs are smaller text
        words.forEach(function(w){
          if(n+w.length+1>budget&&n>0){ out+=(cur.length?sg.o+cur.join(' ')+sg.c:'')+'<br>'; cur=[]; n=0; }
          cur.push(w); n+=w.length+1;
        });
        if(cur.length)out+=sg.o+cur.join(' ')+sg.c+' ';
      });
      return out.trim();
    }
    var wrapped=(gd.clientWidth>=640)?orig:orig.split('<br>').map(wrapLine).join('<br>');
    // Top band = title lines + however many rows the legend wraps into at this width
    var nLeg=(gd.layout.showlegend!==false)?(gd.data||[]).filter(function(d){return d.showlegend!==false&&d.type!=='heatmap';}).length:0;
    if(nLeg<2)nLeg=0;
    var perRow=Math.max(1,Math.floor((gd.clientWidth-16)/150));
    var legRows=nLeg?Math.ceil(nLeg/perRow):0;
    var nLines=wrapped.split('<br>').length;
    var t=(gd.clientWidth>=640)?gd._origMarginT:Math.max(gd._origMarginT,28+24*nLines+(legRows?legRows*22+8:0));
    if(wrapped!==gd.layout.title.text||t!==(gd.layout.margin||{}).t){Plotly.relayout(gd,{'title.text':wrapped,'margin.t':t});}
  }
  function _fitAllTitles(root){ (root||document).querySelectorAll('.js-plotly-plot').forEach(function(gd){ if(gd.offsetParent!==null)_fitTitle(gd); }); }
  window._fitAllTitles=_fitAllTitles;
  var _fitT; window.addEventListener('resize',function(){clearTimeout(_fitT);_fitT=setTimeout(function(){_fitAllTitles();},150);});
  window.addEventListener('load',function(){setTimeout(function(){_fitAllTitles();},300);});
  function _themed(L, nTraces){
    var T=_THEME, m=L.margin||{};
    var title=L.title?(typeof L.title==='string'?{text:L.title}:L.title):null;
    var tText=title&&title.text?title.text.replace(/<\/?b>/g,''):'';
    var hasLegend=(nTraces||1)>1 && L.showlegend!==false;
    var below=(L.annotations||[]).some(function(a){return a.yref==='paper'&&a.y<0;});
    var lines=tText?(tText.split('<br>').length):0;
    L.font=Object.assign({},T.font);
    L.paper_bgcolor=T.paper_bgcolor; L.plot_bgcolor=T.plot_bgcolor;
    L.hoverlabel=JSON.parse(JSON.stringify(T.hoverlabel));
    L.modebar=Object.assign({},T.modebar);
    if(tText){ L.title=Object.assign({},T.title,{text:tText}); }
    if(hasLegend){ L.legend=JSON.parse(JSON.stringify(T.legend)); }
    L.margin={t:(lines?28+24*lines:16)+(hasLegend?32:0), r:Math.max(T.margin.r,m.r||0),
              b:(below&&m.b)?m.b:T.margin.b, l:T.margin.l, pad:0};
    ['xaxis','yaxis'].forEach(function(k){
      var a=L[k]||{}, at=a.title?(typeof a.title==='string'?{text:a.title}:a.title):null;
      var o=Object.assign({},a,{showline:T.axis.showline,ticks:T.axis.ticks,ticklen:0,automargin:true,
        gridcolor:T.axis.gridcolor,griddash:T.axis.griddash,gridwidth:T.axis.gridwidth,
        zerolinecolor:T.axis.zerolinecolor,zerolinewidth:T.axis.zerolinewidth,
        tickfont:Object.assign({},T.axis.tickfont)});
      if(at){ o.title={text:at.text,font:Object.assign({},T.axis.title.font),standoff:T.axis.title.standoff}; }
      L[k]=o;
    });
    return L;
  }
  // Plotly loads from a CDN - on an offline workstation or behind a
  // restrictive proxy (common across the Region) it never arrives. Show a
  // clear reason instead of leaving a blank rectangle where a chart should be.
  function _plotlyOffline(el){
    if(!el||el.dataset.plotlyOfflineMsg)return;
    el.dataset.plotlyOfflineMsg='1';
    el.innerHTML='<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;min-height:160px;color:var(--muted);text-align:center;padding:20px;gap:8px;">'+
      '<i class="ti ti-wifi" aria-hidden="true" style="font-size:22px;opacity:.35;"></i>'+
      '<div style="font-size:var(--fs-sm);font-weight:600;">Chart unavailable - Plotly failed to load from the CDN</div>'+
      '<div style="font-size:var(--fs-xs);">This usually means no internet access or a blocked script host. Other page content still works.</div>'+
      '</div>';
  }
  // Shared Plotly config for every dynamically-rendered chart: keep a
  // trimmed modebar (zoom/pan/reset + "download as PNG") instead of hiding
  // it outright - users pulling these charts into a slide deck need
  // toImage, they just don't need lasso/select/compare-hover clutter.
  var _PLOTLY_CFG = {
    responsive:true, displayModeBar:true, displaylogo:false,
    modeBarButtonsToRemove:['select2d','lasso2d','autoScale2d','hoverClosestCartesian',
      'hoverCompareCartesian','toggleSpikelines','zoomIn2d','zoomOut2d'],
  };
  function _hexA(hex,a){
    var h=hex.replace('#','');
    var r=parseInt(h.substring(0,2),16),g=parseInt(h.substring(2,4),16),b=parseInt(h.substring(4,6),16);
    return 'rgba('+r+','+g+','+b+','+a+')';
  }
  // Single source of truth for status colour, generated from src/config.py's
  // STATUS_COLORS so the server-rendered badges/tables and every JS chart
  // (donut, scatter, KPI cards) always agree - see Phase 3/4 colour-system fix.
  const _STATUS_LABELS = __STATUS_LABELS_PLACEHOLDER__;
  const _STATUS_CLR = __STATUS_COLORS_PLACEHOLDER__;
  // Full evidence colour system (fills, inks, on-fill text, patterns, recency)
  const _PAL = __PALETTE_PLACEHOLDER__;
  function _recency(g, ink){
    if(g===null||g===undefined) return ink?'#5b6475':_PAL.recencyNone;
    for(var i=0;i<_PAL.recency.length;i++){ if(g<=_PAL.recency[i][0]) return _PAL.recency[i][ink?2:1]; }
    return _PAL.recency[_PAL.recency.length-1][ink?2:1];
  }
  function _statusPattern(s){
    var sh=_PAL.statusPattern[s];
    return sh?{shape:sh,fgcolor:_PAL.statusPatternFg[s],fgopacity:sh==='.'?0.3:0.4,size:sh==='.'?9:7,solidity:sh==='.'?0.15:0.25,fillmode:'overlay'}:undefined;
  }

  // Compares the selected instrument's status mix against the all-instruments
  // system-wide mix, so this chart adds a dimension the KPI cards above it
  // don't (relative standing), instead of re-displaying the same 4-5 numbers
  // a second time in a different chart type.
  function updateExecDonut(d) {
    var divId='exec-donut-chart';
    var el=document.getElementById(divId);
    if(!el)return;
    if(typeof Plotly==='undefined'){_plotlyOffline(el);return;}
    var g=EXEC_DATA['global']||d;
    var selMap={
      'On Cycle':d.n_on_cycle,'Attempt to update':d.n_attempt_to_update,
      'Off Cycle':d.n_off_cycle,'First Attempt':d.n_first_attempt,'Never Conducted':d.n_never
    };
    var gloMap={
      'On Cycle':g.n_on_cycle,'Attempt to update':g.n_attempt_to_update,
      'Off Cycle':g.n_off_cycle,'First Attempt':g.n_first_attempt,'Never Conducted':g.n_never
    };
    var selTotal=d.n_total, gloTotal=g.n_total;
    var selPct=_STATUS_LABELS.map(function(s){return Math.round(selMap[s]/selTotal*1000)/10;});
    var gloPct=_STATUS_LABELS.map(function(s){return Math.round(gloMap[s]/gloTotal*1000)/10;});
    var colors=_STATUS_LABELS.map(function(s){return _STATUS_CLR[s];});
    var traces=_STATUS_LABELS.map(function(s,i){
      return {
        type:'bar', orientation:'h',
        y:['All 5 Instruments (system-wide)','Selected Instrument'],
        x:[gloPct[i],selPct[i]],
        customdata:[[gloMap[s],gloTotal],[selMap[s],selTotal]],
        name:s, marker:{color:colors[i],pattern:_statusPattern(s),line:_THEME.bar_gap_line},
        text:[gloPct[i]+'%',selPct[i]+'%'],
        textposition:'inside', insidetextanchor:'middle',
        textfont:{size:12,color:_PAL.statusOn[s],family:_FONT},
        hovertemplate:'<b>%{y}</b> - '+s+': <b>%{customdata[0]}</b> of %{customdata[1]} countries (%{x}%)<extra></extra>',
      };
    });
    Plotly.react(divId,traces,_themed({
      barmode:'stack', bargap:0.28,
      height:236,
      xaxis:{range:[0,100],ticksuffix:'%',showgrid:false,zeroline:false},
      yaxis:{automargin:true},
    },traces.length),_PLOTLY_CFG);
  }

  function updateGapChart(surveyKey) {
    var divId='exec-gap-chart';
    var el=document.getElementById(divId);
    if(!el)return;
    if(typeof Plotly==='undefined'){_plotlyOffline(el);return;}
    var d=EXEC_DATA[surveyKey];
    if(!d||!d.countries_gap)return;
    var withData=d.countries_gap.filter(function(c){return c.gap!==null;});
    withData.sort(function(a,b){return a.gap-b.gap;});
    var noDataCount=d.countries_gap.length-withData.length;
    var names=withData.map(function(c){return c.country;});
    var gaps=withData.map(function(c){return c.gap;});
    var clrs=gaps.map(function(g){
      return _recency(g);
    });
    var hov=withData.map(function(c){
      return'<b>'+c.country+'</b><br>Last '+surveyKey+': <b>'+c.last_year+'</b><br>Gap: <b>'+c.gap+' year'+(c.gap===1?'':'s')+'</b>';
    });
    var maxGap=gaps.length>0?Math.max.apply(null,gaps):20;
    var noNote=noDataCount>0?'  <span style="font-size:13px;font-family:'+_FONT+';color:'+_THEME.axis.tickfont.color+'">('+noDataCount+' countries with no completed '+surveyKey+' not shown)</span>':'';
    // Below ~768px, 48 rotated x-axis labels collide - switch to horizontal
    // bars (one row per country) and size height to the row count instead
    // of a fixed 500px that's either cramped or excessive depending on how
    // many countries have data for the selected instrument.
    var narrow=window.innerWidth<768;
    var trace, layout;
    if(narrow){
      var namesR=names.slice().reverse(), gapsR=gaps.slice().reverse(), clrsR=clrs.slice().reverse(), hovR=hov.slice().reverse();
      trace={type:'bar',orientation:'h',y:namesR,x:gapsR,
        marker:{color:clrsR},
        text:gapsR.map(function(g){return g+' yr'+(g===1?'':'s');}),
        textposition:'outside',textfont:{size:11,family:_FONT,color:_THEME.axis.tickfont.color},
        hovertext:hovR,hoverinfo:'text',cliponaxis:false};
      layout={height:Math.max(360,namesR.length*22+140),margin:{r:50},bargap:0.25,
        xaxis:{title:{text:'Years since last survey'},range:[0,maxGap+4],dtick:5,showgrid:true,zeroline:true},
        yaxis:{showgrid:false},
        shapes:[
          {type:'line',y0:0,y1:1,x0:5.5,x1:5.5,xref:'x',yref:'paper',line:{color:_recency(6,true),dash:'dash',width:1.5}},
          {type:'line',y0:0,y1:1,x0:12.5,x1:12.5,xref:'x',yref:'paper',line:{color:_recency(13,true),dash:'dash',width:1.5}},
        ]};
    }else{
      trace={type:'bar',x:names,y:gaps,
        marker:{color:clrs},
        text:gaps.map(function(g){return g+' yr'+(g===1?'':'s');}),
        textposition:'outside',textfont:{size:10,family:_FONT,color:_THEME.axis.tickfont.color},
        hovertext:hov,hoverinfo:'text',cliponaxis:false};
      layout={height:500,margin:{r:56},bargap:0.25,
        xaxis:{tickangle:-50,showgrid:false},
        yaxis:{
          title:{text:'Years since last survey (relative to 2026)'},
          range:[0,maxGap+4],dtick:5,showgrid:true,zeroline:true,
        },
        shapes:[
          {type:'line',x0:0,x1:1,y0:5.5,y1:5.5,xref:'paper',yref:'y',line:{color:_recency(6,true),dash:'dash',width:1.5}},
          {type:'line',x0:0,x1:1,y0:12.5,y1:12.5,xref:'paper',yref:'y',line:{color:_recency(13,true),dash:'dash',width:1.5}},
        ],
        annotations:[
          {x:1.01,y:5.5,xref:'paper',yref:'y',text:'<b>5 yr</b>',showarrow:false,font:{size:11,color:_recency(6,true),family:_FONT},xanchor:'left'},
          {x:1.01,y:12.5,xref:'paper',yref:'y',text:'<b>12 yr</b>',showarrow:false,font:{size:11,color:_recency(13,true),family:_FONT},xanchor:'left'},
        ]};
    }
    layout.title={text:'Years Since Most Recent '+surveyKey+' Survey'+noNote};
    Plotly.react(divId,[trace],_themed(layout,1),_PLOTLY_CFG).then(function(gd){gd._origTitle=undefined;_fitTitle(gd);});
    if(narrow){ /* smaller tick text for 48 stacked country rows */
      Plotly.relayout(divId,{'yaxis.tickfont.size':11});
    }
  }

  function updateTimeline(surveyKey) {
    var divId='cycle-timeline-chart';
    var el=document.getElementById(divId);
    if(!el)return;
    if(typeof Plotly==='undefined'){_plotlyOffline(el);return;}
    var rows=TIMELINE_DATA[surveyKey]||[];
    if(rows.length===0){Plotly.purge(divId);return;}
    var years=rows.map(function(r){return r.year;});
    var counts=rows.map(function(r){return r.n;});
    var maxN=Math.max.apply(null,counts);
    // Colour bars by period: current cycle wears On Cycle blue; older years are neutral
    var barColors=years.map(function(y){
      if(y>=2021)return _PAL.status['On Cycle'];
      if(y>=2000)return '#9fb3cc';
      return _PAL.recencyNone;
    });
    var meta=EXEC_DATA[surveyKey]||{};
    var fullName=meta.full_name||surveyKey;
    var textLabels=counts.map(function(n){return n>0?String(n):'';});
    try{
      Plotly.react(divId,[{
        type:'bar',x:years,y:counts,
        marker:{color:barColors},
        text:textLabels,
        textposition:'outside',
        textfont:{size:12,family:_FONT,color:_THEME.axis.tickfont.color},
        cliponaxis:false,
        hovertemplate:'<b>Year %{x}</b><br>Countries completed '+surveyKey+': <b>%{y}</b><extra></extra>',
      }],_themed({
        height:400,bargap:0.25,
        title:{
          text:'Historical Activity - '+surveyKey+'&nbsp;&nbsp;<span style="font-size:14px;font-family:'+_FONT+';color:'+_THEME.axis.tickfont.color+'">'+fullName+'</span><br><span style="font-size:13px;font-family:'+_FONT+';color:'+_THEME.axis.tickfont.color+'">Number of countries completing the survey each year</span>',
        },
        xaxis:{
          title:{text:'Survey Year'},
          dtick:2,showgrid:false,
        },
        yaxis:{
          title:{text:'Number of Countries'},
          range:[0,maxN+4],dtick:2,showgrid:true,zeroline:true,
        },
        shapes:[
          {type:'rect',xref:'x',yref:'paper',x0:2020.5,x1:2026.5,y0:0,y1:1,
           fillcolor:'rgba(31,95,168,0.06)',line:{width:0}},
          {type:'line',xref:'x',yref:'paper',x0:2020.5,x1:2020.5,y0:0,y1:1,
           line:{color:_PAL.status['On Cycle'],dash:'dot',width:1.5}},
        ],
        annotations:[
          {x:2021,y:1.04,xref:'x',yref:'paper',text:'<b>Current 5-yr cycle</b>',
           showarrow:false,font:{size:11,color:_PAL.statusInk['On Cycle'],family:_FONT},xanchor:'left'},
        ],
      },1),_PLOTLY_CFG).then(function(gd){gd._origTitle=undefined;_fitTitle(gd);});
    }catch(e){console.warn('Timeline render error:',e);}
  }

  function filterSurveyDetail(code) {
    document.querySelectorAll('.survey-detail-section').forEach(function(el){
      el.style.display = el.dataset.survey === code ? '' : 'none';
    });
    // update active state on filter pills
    document.querySelectorAll('.survey-pill').forEach(function(btn){
      var active = btn.dataset.survey === code;
      btn.style.background    = active ? btn.dataset.color : '#f4f7fb';
      btn.style.color         = active ? '#ffffff' : 'var(--muted)';
      btn.style.borderColor   = active ? btn.dataset.color : 'var(--border)';
    });
  }

  var _prioCurSurvey = 'STEPS';

  function filterPriority(surveyKey) {
    _prioCurSurvey = surveyKey;
    var d = EXEC_DATA[surveyKey];
    if(!d) return;
    var n = d.n_total;
    // Read movable threshold values
    var gapEl=document.getElementById('prio-gap-cut');
    var spiEl=document.getElementById('prio-spi-cut');
    var gapCut=gapEl?Math.max(1,parseInt(gapEl.value)||5):5;
    var spiCut=spiEl?Math.max(1,Math.min(99,parseInt(spiEl.value)||50)):50;
    var gv=document.getElementById('prio-gap-val'); if(gv)gv.textContent=gapCut;
    var sv=document.getElementById('prio-spi-val'); if(sv)sv.textContent=spiCut;
    // Pill active states
    document.querySelectorAll('.prio-pill').forEach(function(btn){
      var active=btn.dataset.survey===surveyKey;
      btn.style.background  =active?btn.dataset.color:'#f4f7fb';
      btn.style.color       =active?'#ffffff':'var(--muted)';
      btn.style.borderColor =active?btn.dataset.color:'var(--border)';
      btn.style.boxShadow   ='none';
    });
    // Survey detail sections
    document.querySelectorAll('.survey-detail-section').forEach(function(sec){
      sec.style.display=sec.dataset.survey===surveyKey?'':'none';
    });
    // Scatter chart
    var divId='prio-scatter-chart';
    var chartEl=document.getElementById(divId);
    if(!chartEl)return;
    if(typeof Plotly==='undefined'){_plotlyOffline(chartEl);return;}
    var cgap=d.countries_gap||[];
    var MAXGAP=40;
    var _SYMBOL={'On Cycle':'circle','Attempt to update':'triangle-up','Off Cycle':'square','First Attempt':'diamond','Never Conducted':'circle-open'};
    var _SIZE  ={'On Cycle':15,'Attempt to update':14,'Off Cycle':13,'First Attempt':13,'Never Conducted':12};
    var statusCfg={};
    _STATUS_LABELS.forEach(function(s){
      var isOpen=s==='Never Conducted';
      statusCfg[s]={color:isOpen?_PAL.statusInk[s]:'#ffffff',fill:isOpen?_PAL.statusInk[s]:_STATUS_CLR[s],   // open symbols stroke with marker.color
                    symbol:_SYMBOL[s],sz:_SIZE[s],lw:isOpen?2:1.5};
    });
    var traceData={};
    Object.keys(statusCfg).forEach(function(s){traceData[s]={x:[],y:[],text:[]};});
    cgap.forEach(function(c){
      var st=c.status||'Never Conducted';
      var xVal=(c.gap!==null&&c.gap!==undefined)?c.gap:MAXGAP-2;
      var yVal=SPI_SCORES[c.country]!==undefined?SPI_SCORES[c.country]:0;
      if(traceData[st]){traceData[st].x.push(xVal);traceData[st].y.push(yVal);traceData[st].text.push(c.country);}
    });
    var traces=Object.keys(statusCfg).map(function(st){
      var cfg=statusCfg[st];
      var td=traceData[st];
      return{
        x:td.x,y:td.y,text:td.text,
        type:'scatter',mode:'markers+text',
        textposition:'top center',
        textfont:{size:10,family:_FONT,color:_THEME.axis.tickfont.color},
        name:st,
        marker:{
          color:cfg.fill, size:cfg.sz, opacity:0.92, symbol:cfg.symbol,
          line:{color:cfg.color,width:cfg.lw}
        },
        hovertemplate:'<b>%{text}</b><br>'+surveyKey+' gap: <b>%{x} yrs</b><br>Overall SPI: <b>%{y:.1f}</b><extra><b style="color:'+cfg.color+'">'+st+'</b></extra>'
      };
    });
    var hL=gapCut/2, mR=gapCut+(MAXGAP-gapCut)/2;
    var mBot=spiCut/2, mTop=spiCut+(100-spiCut)/2;
    var shapes=[
      // Quadrant fills
      {type:'rect',x0:gapCut,x1:MAXGAP,y0:0,    y1:spiCut,xref:'x',yref:'y',fillcolor:'rgba(196,67,43,.07)',line:{width:0}},
      {type:'rect',x0:gapCut,x1:MAXGAP,y0:spiCut,y1:100,  xref:'x',yref:'y',fillcolor:'rgba(224,147,46,.09)',line:{width:0}},
      {type:'rect',x0:-2,    x1:gapCut,y0:spiCut,y1:100,  xref:'x',yref:'y',fillcolor:'rgba(31,95,168,.06)',  line:{width:0}},
      {type:'rect',x0:-2,    x1:gapCut,y0:0,    y1:spiCut,xref:'x',yref:'y',fillcolor:'rgba(134,182,224,.12)',line:{width:0}},
      // Threshold lines - dotted navy
      {type:'line',x0:gapCut,x1:gapCut,y0:-6,y1:106,xref:'x',yref:'y',line:{color:_THEME.axis.tickfont.color,width:1.5,dash:'dot'}},
      {type:'line',x0:-2,x1:MAXGAP,y0:spiCut,y1:spiCut,xref:'x',yref:'y',line:{color:_THEME.axis.tickfont.color,width:1.5,dash:'dot'}}
    ];
    var annotations=[
      // Large watermark labels
      {x:mR,   y:mBot, text:'URGENT',   showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(177,58,36,.20)',family:_FONT}},
      {x:mR,   y:mTop, text:'REINVEST', showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(138,90,0,.20)',family:_FONT}},
      {x:hL,   y:mTop, text:'SUSTAIN',  showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(31,95,168,.20)',  family:_FONT}},
      {x:hL,   y:mBot, text:'DEVELOP',  showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(47,107,168,.20)',family:_FONT}},
      // Threshold value labels on lines
      {x:gapCut, y:104, text:'\u25bc Gap\u2009=\u2009'+gapCut+' yr', showarrow:false,
       xref:'x',yref:'y',xanchor:'center',font:{size:12,color:_PAL.brand.ink,family:_FONT},
       bgcolor:'rgba(255,255,255,.92)',borderpad:3,borderwidth:0},
      {x:MAXGAP-0.5,y:spiCut,text:'\u25c4 SPI\u2009=\u2009'+spiCut,showarrow:false,
       xref:'x',yref:'y',xanchor:'right',yanchor:'bottom',font:{size:12,color:_PAL.brand.ink,family:_FONT},
       bgcolor:'rgba(255,255,255,.92)',borderpad:3,borderwidth:0},
      // Never-conducted note
      {x:MAXGAP-2,y:-5,xref:'x',yref:'y',text:'\u25cb\u2009=\u2009Never conducted (plotted at far right)',
       showarrow:false,font:{size:12,color:_THEME.axis.tickfont.color,family:_FONT}}
    ];
    var layout={
      xaxis:{
        title:{text:'Years Since Last '+surveyKey+' Survey'},
        range:[-2,MAXGAP+1],showgrid:true,zeroline:false,
        dtick:5
      },
      yaxis:{
        title:{text:'Overall SPI Score (0\u2013100)'},
        range:[-8,108],showgrid:true,zeroline:false,
        dtick:25
      },
      shapes:shapes, annotations:annotations,
    };
    try{Plotly.react(divId,traces,_themed(layout,traces.length),_PLOTLY_CFG);}
    catch(e){console.warn('Prio scatter error:',e);}
  }

  function updateExecKPIs(surveyKey) {
    var d=EXEC_DATA[surveyKey];
    if(!d)return;
    var n=d.n_total;
    var updates=[
      ['exec-n-oncycle',  d.n_on_cycle,          d.n_on_cycle+' of '+n+' countries',          'Completed \u2264\u20095 years ago - current, usable evidence'],
      ['exec-n-implement',d.n_attempt_to_update, d.n_attempt_to_update+' of '+n+' countries', 'Prior evidence exists - actively updating with new survey'],
      ['exec-n-offcycle', d.n_off_cycle,         d.n_off_cycle+' of '+n+' countries',         'Has prior evidence but surveillance is idle - off-cycle'],
      ['exec-n-firstattempt',d.n_first_attempt,  d.n_first_attempt+' of '+n+' countries',     'No prior evidence, but a first-ever survey is in progress now'],
      ['exec-n-never',    d.n_never,             d.n_never+' of '+n+' countries',             'Never completed nor attempted - no policy-usable evidence exists'],
    ];
    updates.forEach(function(u){
      var id=u[0],val=u[1],sub=u[2],def=u[3];
      var elV=document.getElementById(id);if(elV)elV.textContent=val;
      var elS=document.getElementById(id+'-sub');if(elS)elS.textContent=sub;
      var elD=document.getElementById(id+'-def');if(elD)elD.textContent=def;
    });
    var badge=document.getElementById('exec-survey-badge');
    if(badge)badge.textContent=surveyKey+' - '+d.full_name;
    setTimeout(function(){updateExecDonut(d);},50);
    setTimeout(function(){updateGapChart(surveyKey);},60);
  }

  var execFilter=document.getElementById('exec-survey-filter');
  if(execFilter){
    execFilter.addEventListener('change',function(){updateExecKPIs(execFilter.value||'STEPS');});
  }
  var execReset=document.getElementById('exec-filter-reset');
  if(execReset){
    execReset.addEventListener('click',function(){
      if(execFilter)execFilter.value='STEPS';
      updateExecKPIs('STEPS');
    });
  }
  window.addEventListener('load',function(){
    updateExecKPIs('STEPS');
    filterSurveyDetail('STEPS');
    window.dispatchEvent(new Event('resize'));
    setTimeout(function(){
      window.dispatchEvent(new Event('resize'));
      if(typeof Plotly==='undefined')return;
      document.querySelectorAll('.tab-pane.active .plotly-graph-div').forEach(function(el){
        try{Plotly.relayout(el,{autosize:true});}catch(e){}
      });
    },300);
  });
  document.querySelectorAll('.tab-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      setTimeout(function(){ if(window._fitAllTitles)window._fitAllTitles(); },450);
      if(btn.dataset.tab==='tab-exec'){
        setTimeout(function(){
          var filt=document.getElementById('exec-survey-filter');
          updateExecKPIs((filt&&filt.value)?filt.value:'STEPS');
        },80);
      }
      if(btn.dataset.tab==='tab-cycle'){
        setTimeout(function(){
          var filt=document.getElementById('cycle-timeline-filter');
          updateTimeline((filt&&filt.value)?filt.value:'STEPS');
        },80);
      }
      if(btn.dataset.tab==='tab-priority'){
        setTimeout(function(){filterPriority(_prioCurSurvey);},80);
      }
      if(btn.dataset.tab==='tab-profile'){
        setTimeout(function(){
          var s=document.getElementById('profile-country-select');
          if(s&&s.value) renderCountryProfile(s.value, _profileSurvey);
        },80);
      }
    });
  });
  // ── Strategic Priority: pill & slider event listeners ─────────────────────
  document.querySelectorAll('.prio-pill').forEach(function(btn){
    btn.addEventListener('click',function(){filterPriority(btn.dataset.survey);});
  });
  ['prio-gap-cut','prio-spi-cut'].forEach(function(id){
    var el=document.getElementById(id);
    if(el) el.addEventListener('input',function(){filterPriority(_prioCurSurvey);});
  });

  // ════════════════════════════════════════════════════════════════════════════
  // COUNTRY PROFILE TAB
  // ════════════════════════════════════════════════════════════════════════════
  var STEPS_PROFILE_DATA = __STEPS_PROFILE_PLACEHOLDER__;
  var GYTS_PROFILE_DATA  = __GYTS_PROFILE_PLACEHOLDER__;
  var GATS_PROFILE_DATA  = __GATS_PROFILE_PLACEHOLDER__;
  var COUNTRY_SURVEYS_MAP = __COUNTRY_SURVEYS_PLACEHOLDER__ || {};
  var _profileCurrent = '';
  var _profileSurvey  = 'STEPS';

  var _SECTION_ORDER = ['S1_TOB','S1_ALC','S1_DIT','S1_PAC','S2_BPR','S2_ANT','S3_GLU','S3_CHO','S_RISK'];
  var _RADAR_CFG = [
    {code:'tobacco_current_smoke_pct',     label:'Tobacco'},
    {code:'alcohol_current_drinker_pct',   label:'Alcohol'},
    {code:'diet_less5_servings_pct',       label:'Diet'},
    {code:'pa_low_activity_pct',           label:'Inactivity'},
    {code:'bp_raised_140_pct',             label:'Hypertension'},
    {code:'bmi_obese_pct',                 label:'Obesity'},
    {code:'glucose_raised_7_pct',          label:'Diabetes'},
    {code:'cholesterol_raised_5_pct',      label:'Cholesterol'},
    {code:'risk_3plus_pct',                label:'Multi-Risk'},
  ];
  var _KPI_CFG = [
    {code:'tobacco_current_smoke_pct',  icon:'ti-smoking',            label:'Tobacco Use',          col:'#003d82'},
    {code:'alcohol_binge_pct',          icon:'ti-glass-full',     label:'Heavy/Binge Drinking',  col:'#003d82'},
    {code:'bp_raised_140_pct',          icon:'ti-heartbeat',          label:'Raised Blood Pressure', col:'#003d82'},
    {code:'bmi_obese_pct',              icon:'ti-weight',             label:'Obesity (BMI\u226530)', col:'#003d82'},
    {code:'glucose_raised_7_pct',       icon:'ti-droplet',               label:'Raised Glucose',        col:'#003d82'},
    {code:'risk_3plus_pct',             icon:'ti-alert-circle', label:'3+ Risk Factors',       col:'#003d82'},
  ];
  var _GYTS_KPI_CFG = [
    {code:'gyts_current_any_tobacco',      icon:'ti-smoking',            label:'Current Tobacco Use',        col:'#003d82'},
    {code:'gyts_current_ecig',             icon:'ti-bolt',                label:'Current E-Cigarette Use',    col:'#003d82'},
    {code:'gyts_shs_home',                 icon:'ti-wind',                label:'SHS Exposure at Home',       col:'#003d82'},
    {code:'gyts_noticed_ads_pos',          icon:'ti-building-store',               label:'Noticed Tobacco Ads (POS)',  col:'#003d82'},
    {code:'gyts_susceptible_future_use',   icon:'ti-alert-triangle',label:'Susceptible Never-Users',    col:'#003d82'},
    {code:'gyts_favor_ban_enclosed',       icon:'ti-brain',               label:'Favor Indoor Smoking Ban',   col:'#003d82'},
  ];
  var _GATS_KPI_CFG = [
    {code:'gats_current_tobacco_users',    icon:'ti-smoking',            label:'Current Tobacco Use',        col:'#003d82'},
    {code:'gats_current_cigarette_smokers',icon:'ti-flame',                label:'Current Cigarette Smoking',  col:'#003d82'},
    {code:'gats_current_ecig',             icon:'ti-bolt',                label:'Current E-Cigarette Use',    col:'#003d82'},
    {code:'gats_exposed_workplace',        icon:'ti-wind',                label:'SHS Exposure at Workplace',  col:'#003d82'},
    {code:'gats_smokers_planning_quit',    icon:'ti-first-aid-kit',   label:'Smokers Planning to Quit',   col:'#003d82'},
    {code:'gats_belief_smoking_illness',   icon:'ti-brain',               label:'Believe Smoking Causes Illness', col:'#003d82'},
  ];
  var _KPI_CFG_BY_SURVEY  = {STEPS: _KPI_CFG,  GYTS: _GYTS_KPI_CFG, GATS: _GATS_KPI_CFG};
  var _SURVEY_LABEL = {STEPS:'STEPS - NCD Risk Factor Surveillance', GYTS:'GYTS - Global Youth Tobacco Survey', GATS:'GATS - Global Adult Tobacco Survey'};
  function _profileDataFor(surveyType){
    if(surveyType==='GYTS') return GYTS_PROFILE_DATA;
    if(surveyType==='GATS') return GATS_PROFILE_DATA;
    return STEPS_PROFILE_DATA;
  }
  var _TIER_CLR = _PAL.tierInk;   // text/border use: ink, never the light fill

  function _trendArrow(cur, prev, hib) {
    if(cur===null||cur===undefined||prev===null||prev===undefined) return '';
    var diff=cur-prev, abs=Math.abs(diff);
    if(abs<0.5) return '<span style="color:var(--muted);font-size:var(--fs-sm);">\u2248</span>';
    var up=diff>0;
    var good= hib===null||hib===undefined ? null : (hib?up:!up);
    var clr= good===null?'#5b6577':(good?_PAL.tierInk[1]:_PAL.tierInk[4]);
    return '<span style="color:'+clr+';font-weight:700;">'+(up?'\u2191':'\u2193')+' '+abs.toFixed(1)+'</span>';
  }


  function renderCountryProfile(country, surveyType) {
    surveyType = surveyType || _profileSurvey || 'STEPS';
    _profileSurvey = surveyType;
    var PROFILE_DATA = _profileDataFor(surveyType);
    if(!PROFILE_DATA||!PROFILE_DATA.profiles){
      document.getElementById('country-profile-content').innerHTML=
        '<div class="profile-no-data"><i class="ti ti-database" aria-hidden="true"></i><p>No '+surveyType+' indicator data available.</p></div>';
      return;
    }
    _profileCurrent=country;
    var p=PROFILE_DATA.profiles[country];
    if(!p||!p.surveys||p.surveys.length===0){
      document.getElementById('country-profile-content').innerHTML=
        '<div class="profile-no-data"><i class="ti ti-info-circle" aria-hidden="true"></i><p>No '+surveyType+' data available for <strong>'+country+'</strong>.</p></div>';
      return;
    }
    var ind=PROFILE_DATA.indicators||{};
    var sec=PROFILE_DATA.sections||{};
    var reg=PROFILE_DATA.regional||{};
    var sectionOrder = surveyType==='STEPS' ? _SECTION_ORDER : Object.keys(sec);
    var kpiCfg = _KPI_CFG_BY_SURVEY[surveyType] || _KPI_CFG;
    var surveys=p.surveys;
    var latYr=surveys[surveys.length-1].year;
    var latData=p.data[String(latYr)]||{};
    var hasMulti=surveys.length>=2;
    var prevYr=hasMulti?surveys[surveys.length-2].year:null;
    var prevData=prevYr?(p.data[String(prevYr)]||{}):{};
    var tc=_TIER_CLR[p.tier]||'#003d82';
    var latS=surveys[surveys.length-1];
    var yrsStr=surveys.map(function(s){return s.year;}).join(' \u00b7 ');
    var nStr=latS.n?latS.n.toLocaleString('en-US'):'N/A';

    // ── Header ─────────────────────────────────────────────────────────────
    var hdr='<div class="profile-header-card reveal">';
    hdr+='<div class="prof-head" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:18px;">';
    hdr+='<div class="prof-id" style="display:flex;align-items:flex-start;gap:18px;min-width:0;">';
    hdr+='<div class="profile-iso-badge">'+(p.iso3||'???')+'</div>';
    hdr+='<div>';
    hdr+='<div style="font-family:var(--font-serif);font-size:24px;font-weight:600;color:var(--dark);letter-spacing:-.005em;">'+country+'</div>';
    hdr+='<div style="font-size:var(--fs-sm);color:var(--muted);margin-top:5px;display:flex;flex-wrap:wrap;gap:10px;">';
    hdr+='<span class="profile-survey-pill"><i class="ti ti-flask" aria-hidden="true"></i>&nbsp;'+surveyType+' surveys: <strong>'+yrsStr+'</strong></span>';
    hdr+='<span class="profile-survey-pill"><i class="ti ti-percentage" aria-hidden="true"></i>&nbsp;Response rate: '+(latS.rr?latS.rr+'%':'not recorded')+'</span>';
    if(surveyType==='STEPS'){
      hdr+='<span class="profile-survey-pill" style="background:var(--tint);color:var(--tier-1-ink);" title="Sourced from the WHO validated STEPS database">'+
           '<i class="ti ti-shield-check" aria-hidden="true"></i>&nbsp;Validated database source</span>';
    }else{
      var srcTip='Extracted programmatically from a published '+surveyType+' country fact-sheet PDF via automated table parsing; not independently re-verified against the source document'+
                 (p.source_file?(' (file: '+p.source_file+')'):'');
      hdr+='<span class="profile-survey-pill" style="background:#fbf3e6;color:var(--warning);border-color:#ecd3a6;" title="'+srcTip.replace(/"/g,'&quot;')+'">'+
           '<i class="ti ti-alert-triangle" aria-hidden="true"></i>&nbsp;Auto-extracted from PDF - unverified</span>';
    }
    hdr+='</div></div></div>';
    hdr+='<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">';
    if(p.spi!==null&&p.spi!==undefined){
      hdr+='<div style="text-align:center;padding:12px 20px;background:#fff;border:1px solid '+tc+';border-radius:10px;min-width:90px;">';
      hdr+='<div style="font-family:var(--font-serif);font-size:1.75rem;font-weight:600;color:'+tc+';line-height:1;">'+p.spi.toFixed(1)+'</div>';
      hdr+='<div style="font-size:var(--fs-xs);font-weight:700;text-transform:uppercase;letter-spacing:1px;color:'+tc+';margin-top:3px;">SPI Score</div>';
      hdr+='<div style="font-size:var(--fs-xs);color:'+tc+';font-weight:600;margin-top:2px;">'+( p.tier_label||'')+'</div></div>';
    }
    if(hasMulti){
      hdr+='<div style="padding:12px 20px;background:#fff;border:1px solid var(--rule);border-radius:10px;text-align:center;min-width:90px;">';
      hdr+='<div style="font-family:var(--font-serif);font-size:1.5rem;font-weight:600;color:var(--brand);">'+surveys.length+'</div>';
      hdr+='<div style="font-size:var(--fs-xs);font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--brand);">'+surveyType+' Rounds</div>';
      hdr+='<div style="font-size:var(--fs-xs);color:var(--muted);margin-top:1px;">Rounds recorded</div></div>';
    }
    hdr+='</div></div></div>';

    // ── KPI Cards ──────────────────────────────────────────────────────────
    var kpi='<div class="profile-kpi-row">';
    kpiCfg.forEach(function(k){
      var d=latData[k.code]||{};
      var pd=prevData[k.code]||{};
      var ki=ind[k.code]||{};
      var v=d.b!==undefined?d.b:null;
      var pv=pd.b!==undefined?pd.b:null;
      var unit=ki.unit||'%';
      var valStr=v!==null?v.toFixed(1)+unit:'N/A';
      var arrow=_trendArrow(v,pv,ki.hib);
      var mV=d.m!==undefined?d.m:null, fV=d.f!==undefined?d.f:null;
      var hasCI=(d.lo!==null&&d.lo!==undefined&&d.hi!==null&&d.hi!==undefined);
      var loStr=hasCI?' title="95% CI: '+d.lo.toFixed(1)+'\u2013'+d.hi.toFixed(1)+unit+'"':'';
      kpi+='<div class="profile-kpi-card" style="color:'+k.col+';">';
      kpi+='<div class="profile-kpi-icon"><i class="ti '+k.icon+'" aria-hidden="true" style="color:'+k.col+';"></i></div>';
      kpi+='<div class="profile-kpi-value" style="color:'+k.col+';"'+loStr+'>'+valStr+'</div>';
      if(hasCI){kpi+='<div class="profile-kpi-ci">95% CI '+d.lo.toFixed(1)+'\u2013'+d.hi.toFixed(1)+unit+'</div>';}
      var kConf=(d.conf!==undefined&&d.conf!==null&&d.conf<0.7)
        ? ' <i class="ti ti-alert-triangle" aria-hidden="true" style="color:var(--warning);font-size:var(--fs-xs);cursor:help;" title="Low-confidence label match from PDF extraction (score '+d.conf.toFixed(2)+'/1.00) - verify before citing"></i>' : '';
      kpi+='<div class="profile-kpi-label">'+k.label+kConf+'</div>';
      if(arrow){kpi+='<div class="profile-kpi-trend">'+arrow+'<span style="font-size:var(--fs-xs);color:var(--muted);font-weight:400;"> vs '+prevYr+'</span></div>';}
      if(mV!==null||fV!==null){
        kpi+='<div class="profile-kpi-sex">';
        if(mV!==null) kpi+='<span style="background:var(--tint);color:var(--text);">M: '+mV.toFixed(1)+'</span>';
        if(fV!==null) kpi+='<span style="background:var(--tint);color:var(--text);">F: '+fV.toFixed(1)+'</span>';
        kpi+='</div>';
      }
      kpi+='</div>';
    });
    kpi+='</div>';

    // ── Store state for re-render on toggle ────────────────────────────────
    _profileState = {
      latData: latData, prevData: prevData, latYr: latYr, prevYr: prevYr,
      ind: ind, sec: sec, reg: reg, hasMulti: hasMulti, tier: p.tier,
      country: country, sectionOrder: sectionOrder
    };
    // ── Section divider label ──────────────────────────────────────────────
    var sdiv='<div class="section-divider-label" style="margin:28px 0 18px;">Detailed Indicator Dashboard - All '+surveyType+' Sections <span style="font-weight:400;font-size:var(--fs-xs);color:var(--muted);text-transform:none;letter-spacing:0;">(click a section to expand)</span></div>';
    if(surveyType!=='STEPS'){
      sdiv+='<div style="font-size:var(--fs-xs);color:var(--muted);margin:-10px 0 14px;"><i class="ti ti-alert-triangle" aria-hidden="true" style="color:var(--warning);"></i>&nbsp;Indicators marked with this icon were matched to their label with lower confidence during automated PDF extraction - verify against the source fact sheet before citing.</div>';
    }
    sdiv+='<div id="profile-section-detail-grid"></div>';

    document.getElementById('country-profile-content').innerHTML=
      hdr+kpi+sdiv;

    _renderSectionDetail();

    setTimeout(function(){
      document.querySelectorAll('#country-profile-content .reveal').forEach(function(el){
        el.classList.add('visible');
      });
      window.dispatchEvent(new Event('resize'));
    },80);
  }

  // ── Section state ───────────────────────────────────────────────────────────
  var _profileState = {};

  function _renderSectionDetail() {
    var el = document.getElementById('profile-section-detail-grid');
    if(!el) return;
    var s   = _profileState;
    var latData  = s.latData  || {};
    var prevData = s.prevData || {};
    var latYr    = s.latYr;
    var prevYr   = s.prevYr;
    var ind      = s.ind  || {};
    var sec      = s.sec  || {};
    var reg      = s.reg  || {};
    var sectionOrder = s.sectionOrder || _SECTION_ORDER;

    var grid = '<div class="profile-section-grid">';
    sectionOrder.forEach(function(sc, sIdx){
      var sv = sec[sc]; if(!sv) return;
      var secInds = Object.entries(ind).filter(function(e){return e[1].sec===sc;});

      // First section (usually the KPI-strip's own domain) opens expanded;
      // the rest start collapsed so the page keeps a scannable top-to-bottom
      // hierarchy instead of nine equal-weight blocks fighting for attention.
      grid += '<details class="profile-section-card"'+(sIdx===0?' open':'')+'>';
      grid += '<summary class="profile-section-head" style="background:'+sv.color+';">';
      grid += '<i class="ti '+sv.icon+'" aria-hidden="true" style="color:rgba(255,255,255,.9);font-size:var(--fs-base);"></i>';
      grid += '<span class="sec-title">'+sv.name+'</span>';
      grid += '<span class="sec-step">'+sv.step+'</span>';
      grid += '<i class="ti ti-chevron-down sec-chevron" aria-hidden="true"></i>';
      grid += '</summary>';

      grid += '<div style="overflow-x:auto;">';
      grid += '<table class="profile-ind-table">';
      grid += '<caption style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);">'+sv.name+' indicators for the selected country and survey round</caption>';
      grid += '<thead><tr>';
      grid += '<th scope="col" style="text-align:left;width:34%;">Indicator</th>';
      grid += '<th scope="col" style="text-align:center;width:24%;">Both</th>';
      grid += '<th scope="col" style="text-align:center;width:11%;color:var(--text);" title="Male"><span aria-hidden="true">M</span><span style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);">Male</span></th>';
      grid += '<th scope="col" style="text-align:center;width:11%;color:var(--text);" title="Female"><span aria-hidden="true">F</span><span style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);">Female</span></th>';
      grid += '<th scope="col" style="text-align:center;width:20%;">Trend</th>';
      grid += '</tr></thead><tbody>';

      secInds.forEach(function(entry, idx){
        var code = entry[0], i2 = entry[1];
        var d  = latData[code]  || {};
        var pd = prevData[code] || {};
        var bV  = d.b  !== undefined ? d.b  : null;
        var mV  = d.m  !== undefined ? d.m  : null;
        var fV  = d.f  !== undefined ? d.f  : null;
        var pbV = pd.b !== undefined ? pd.b : null;
        var unit = i2.unit || '%';
        var hib  = i2.hib;
        var bg   = idx % 2 === 0 ? '#fff' : '#f9fafb';
        var lbl  = i2.label.length > 58 ? i2.label.substring(0, 57) + '\u2026' : i2.label;
        var conf = d.conf;
        var confFlag = (conf !== undefined && conf !== null && conf < 0.7)
          ? ' <i class="ti ti-alert-triangle" aria-hidden="true" style="color:var(--warning);font-size:var(--fs-xs);cursor:help;" title="Low-confidence label match from PDF extraction (score '+conf.toFixed(2)+'/1.00) - verify this indicator against the source fact sheet before citing it"></i>'
          : '';
        lbl = lbl + confFlag;
        var hasCI = (d.lo !== null && d.lo !== undefined && d.hi !== null && d.hi !== undefined);
        var ciAttr = hasCI ? ' title="95% CI: ' + d.lo.toFixed(1) + '\u2013' + d.hi.toFixed(1) + unit + '"' : '';
        var ciInline = hasCI
          ? '<br><span style="font-size:var(--fs-xs);color:var(--muted);font-weight:400;">CI ' + d.lo.toFixed(1) + '\u2013' + d.hi.toFixed(1) + '</span>' : '';

        var bStr = bV !== null
          ? '<strong' + ciAttr + '>' + bV.toFixed(1) + '</strong>'
            + '<span style="font-size:var(--fs-xs);color:var(--muted);">' + unit + '</span>' + ciInline
          : '<span style="color:#ccc;">-</span>';
        var mStr = mV !== null ? mV.toFixed(1)  : '<span style="color:#ccc;">-</span>';
        var fStr = fV !== null ? fV.toFixed(1)  : '<span style="color:#ccc;">-</span>';
        var tArr = _trendArrow(bV, pbV, hib);

        grid += '<tr style="background:' + bg + ';">';
        grid += '<td style="color:var(--text);word-break:break-word;font-size:var(--fs-xs);">' + lbl + '</td>';
        grid += '<td style="text-align:center;">' + bStr + '</td>';
        grid += '<td style="text-align:center;">' + mStr + '</td>';
        grid += '<td style="text-align:center;">' + fStr + '</td>';
        grid += '<td style="text-align:center;">' + (tArr || '<span style="color:#ccc;">-</span>') + '</td>';
        grid += '</tr>';
      });
      grid += '</tbody></table></div></details>';
    });
    grid += '</div>';
    el.innerHTML = grid;
  }

  // ── Profile tab: event listeners ────────────────────────────────────────────
  // All three survey types are always listed (never filtered out of the
  // dropdown), so GYTS/GATS stay discoverable even when the currently
  // selected country happens to lack usable data for them - picking one
  // with no data just shows the existing "no data available" message
  // instead of hiding the option entirely.
  var _ALL_SURVEYS = ['STEPS','GYTS','GATS'];
  function _populateSurveyDropdown(country, preferred){
    var sel = document.getElementById('profile-survey-select');
    if(!sel) return null;
    var avail = COUNTRY_SURVEYS_MAP[country] || [];
    var chosen = preferred || 'STEPS';
    sel.innerHTML = _ALL_SURVEYS.map(function(s){
      var has = avail.indexOf(s) !== -1;
      var label = (_SURVEY_LABEL[s]||s) + (has ? '' : ' - no data for this country');
      return '<option value="'+s+'"'+(s===chosen?' selected':'')+'>'+label+'</option>';
    }).join('');
    return chosen;
  }

  var _profSel=document.getElementById('profile-country-select');
  var _profSurveySel=document.getElementById('profile-survey-select');
  if(_profSel){
    _profSel.addEventListener('change',function(){
      var chosen=_populateSurveyDropdown(this.value, _profileSurvey);
      renderCountryProfile(this.value, chosen);
    });
    var _initChosen=_populateSurveyDropdown(_profSel.value, 'STEPS');
    _profileSurvey = _initChosen || 'STEPS';
  }
  if(_profSurveySel){
    _profSurveySel.addEventListener('change',function(){
      renderCountryProfile(_profileCurrent||(_profSel?_profSel.value:''), this.value);
    });
  }

  // CSV with a UTF-8 BOM opens cleanly in Excel on any locale with no
  // warning. The previous export named a file "*.xls" but the content was
  // actually XML Spreadsheet 2003 markup - Excel always flagged "the file
  // format and extension don't match" and made the user click through it.
  function _toCSV(rows) {
    return rows.map(function(row) {
      return row.map(function(cell) {
        var s = (cell === null || cell === undefined) ? '' : String(cell);
        if (/[",\\n\\r]/.test(s)) s = '"' + s.split('"').join('""') + '"';
        return s;
      }).join(',');
    }).join('\\r\\n');
  }

  function _slug(s) {
    // Handles apostrophes/commas that the old naive split(' ').join('_')
    // let through verbatim (e.g. "Côte d'Ivoire", "Tanzania, United
    // Republic of" produced awkward, sometimes filesystem-unfriendly names).
    return String(s).normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'export';
  }

  function _saveCSV(filename, rows) {
    var csv  = '\uFEFF' + _toCSV(rows);
    var blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
    var url  = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.style.display = 'none';
    link.setAttribute('download', filename);
    link.setAttribute('href', url);
    document.body.appendChild(link);
    link.click();
    setTimeout(function() { document.body.removeChild(link); URL.revokeObjectURL(url); }, 500);
  }

  // Inline export feedback next to the triggering button instead of a
  // browser alert() dialog.
  function _exportNote(btn, msg, isError) {
    if (!btn) return;
    var note = btn.parentElement.querySelector('.export-note');
    if (!note) {
      note = document.createElement('span');
      note.className = 'export-note';
      note.style.cssText = 'margin-left:10px;font-size:var(--fs-xs);font-weight:600;';
      btn.insertAdjacentElement('afterend', note);
    }
    note.style.color = isError ? 'var(--danger)' : 'var(--brand)';
    note.textContent = msg;
    clearTimeout(note._t);
    note._t = setTimeout(function() { note.textContent = ''; }, 4000);
  }

  // ── SPI export ────────────────────────────────────────────────────────────────
  var _SPI_TABLE = __SPI_TABLE_PLACEHOLDER__;
  var _REPORT_DATE = __REPORT_DATE_PLACEHOLDER__;

  function _doExportSPI(btn) {
    var rows = [
      ['NCD AFRO Surveillance Intelligence Platform - SPI Rankings Export'],
      ['Data compiled', _REPORT_DATE],
      ['Source', 'WHO Noncommunicable Diseases Country Tracking / gtssacademy.org'],
      [],
      ['Rank','Country','ISO3','SPI Score','Tier','Tier Label',
                 'Breadth (%)','Currency (%)','Regularity (%)','Last Survey Year',
                 'Gap (years)','Completed Surveys','Instrument Types Used']];
    (_SPI_TABLE || []).forEach(function(r, i) {
      rows.push([
        i + 1, r.country, r.iso3 || '', r.spi, r.tier, r.tier_label,
        r.d_coverage, r.d_recency,
        (r.d_regularity !== null && r.d_regularity !== undefined) ? r.d_regularity : '',
        (r.last_year    !== null && r.last_year    !== undefined) ? r.last_year    : '',
        (r.gap_years    !== null && r.gap_years    !== undefined) ? r.gap_years    : '',
        r.n_done, r.types_done
      ]);
    });
    _saveCSV('NCD_AFRO_SPI_Rankings.csv', rows);
    _exportNote(btn, 'Downloaded NCD_AFRO_SPI_Rankings.csv');
  }

  // ── Country Profile export ────────────────────────────────────────────────────
  function _doExportProfile(btn) {
    if (!_profileCurrent) {
      _exportNote(btn, 'Select a country first', true);
      return;
    }
    var PROFILE_DATA = _profileDataFor(_profileSurvey);
    if (!PROFILE_DATA || !PROFILE_DATA.profiles) return;
    var p = PROFILE_DATA.profiles[_profileCurrent]; if (!p) return;
    var ind = PROFILE_DATA.indicators || {};
    var sec = PROFILE_DATA.sections   || {};
    var provenance = _profileSurvey==='STEPS' ? 'Validated database' : 'Auto-extracted from PDF (unverified)';
    var rows = [
      ['NCD AFRO Surveillance Intelligence Platform - Country Profile Export'],
      ['Data compiled', _REPORT_DATE],
      ['Data provenance', provenance + (p.source_file ? (' - ' + p.source_file) : '')],
      [],
      ['Country','ISO3','Survey Type','Survey Year','Section','Indicator Code',
                 'Indicator','Unit','Both Sexes','Males','Females',
                 '95% CI Lower','95% CI Upper','Label Match Confidence']];
    p.surveys.forEach(function(sv) {
      var yrData = p.data[String(sv.year)] || {};
      Object.keys(yrData).sort().forEach(function(code) {
        var vals = yrData[code];
        var i2 = ind[code] || {};
        var sc = sec[i2.sec] || {};
        rows.push([
          _profileCurrent, p.iso3 || '', _profileSurvey, sv.year,
          sc.name || i2.sec || '', code, i2.label || code, i2.unit || '%',
          (vals.b  !== undefined && vals.b  !== null) ? vals.b  : '',
          (vals.m  !== undefined && vals.m  !== null) ? vals.m  : '',
          (vals.f  !== undefined && vals.f  !== null) ? vals.f  : '',
          (vals.lo !== undefined && vals.lo !== null) ? vals.lo : '',
          (vals.hi !== undefined && vals.hi !== null) ? vals.hi : '',
          (vals.conf !== undefined && vals.conf !== null) ? vals.conf : ''
        ]);
      });
    });
    var fname = _slug(_profileCurrent) + '_' + _profileSurvey + '.csv';
    _saveCSV(fname, rows);
    _exportNote(btn, 'Downloaded ' + fname);
  }

  // ── Wire buttons via addEventListener (NOT onclick) ───────────────────────────
  (function() {
    var btnSPI  = document.getElementById('btn-export-spi');
    var btnProf = document.getElementById('btn-export-profile');
    if (btnSPI)  btnSPI.addEventListener('click',  function(){ _doExportSPI(btnSPI); });
    if (btnProf) btnProf.addEventListener('click',  function(){ _doExportProfile(btnProf); });
  })();
})();
"""

# ── Font Awesome icon map ──────────────────────────────────────────────────────
_FA = {
    "globe":    "ti-world",   "clipboard": "ti-clipboard-list",
    "check":    "ti-circle-check",   "sync":      "ti-refresh",
    "times":    "ti-circle-x",   "flask":     "ti-flask",
    "calendar": "ti-calendar",   "trophy":    "ti-trophy",
    "chart":    "ti-chart-bar",      "map":       "ti-map-pin",
    "star":     "ti-star",           "gauge":     "ti-gauge",
    "users":    "ti-users",          "exclaim":   "ti-alert-triangle",
}


def kpi_card(fa_key, value, label, delta=None, color=None, bg=None):
    color = color or C["primary"]
    bg    = bg    or "#f0f6ff"
    fa    = _FA.get(fa_key, "ti-circle")
    try:
        num = float(str(value).replace(",", "").replace("%", ""))
        val_html = (f'<div class="kpi-value" style="color:{color};" '
                    f'data-count="{num}">{value}</div>')
    except ValueError:
        val_html = f'<div class="kpi-value" style="color:{color};">{value}</div>'
    delta_html = ""
    if delta:
        delta_html = (f'<div class="kpi-delta" style="color:{color};">'
                      f'<i class="ti ti-arrow-up" aria-hidden="true" style="font-size:var(--fs-xs);"></i> {delta}</div>')
    return f"""
<div class="kpi-card reveal" style="color:{color};background:{bg};">
  <div class="kpi-icon"><i class="ti {fa}" aria-hidden="true" style="color:{color};"></i></div>
  {val_html}
  <div class="kpi-label">{label}</div>
  {delta_html}
</div>"""


def section_header(anchor, num, title, subtitle=""):
    sub = f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""
    return f"""
<div class="section-header" id="{anchor}">
  <div class="section-header-inner">
    <span class="section-num">{num}</span>
    <h2 class="section-title">{title}</h2>
  </div>
  {sub}
</div>"""


def insight_box(text, kind="info"):
    fa_map  = {"info":"ti-info-circle","warning":"ti-alert-triangle",
               "success":"ti-circle-check","critical":"ti-alert-circle"}
    colors  = {
        "info":     (BRAND["text"], BRAND["tint"], BRAND["rule"]),
        "warning":  (TIER_INK[3], "#fbf3e6", "#ecd3a6"),
        "success":  (TIER_INK[1], BRAND["tint"], BRAND["rule"]),
        "critical": (TIER_INK[4], "#fbefec", "#eec3b9"),
    }
    fg, bg, border = colors.get(kind, colors["info"])
    fa = fa_map.get(kind, "ti-info-circle")
    return f"""
<div class="insight-box reveal" style="background:{bg};border-color:{border};color:{fg};">
  <span class="insight-icon"><i class="ti {fa}" aria-hidden="true"></i></span>
  <span>{text}</span>
</div>"""


def chart_card(chart_html, commentary="", span=12):
    comm = f'<div class="chart-commentary">{commentary}</div>' if commentary else ""
    return f"""
<div class="col-{span}">
  <div class="chart-card reveal">
    {chart_html}
    {comm}
  </div>
</div>"""


def instrument_cards(A):
    st_sum = A["survey_type_summary"].set_index("survey_type")
    cards = ""
    for code, meta in SURVEY_META.items():
        if code not in st_sum.index:
            continue
        row = st_sum.loc[code]
        pct = row["pct_done"]
        bc  = C["success"] if pct >= 70 else C["warning"] if pct >= 40 else C["danger"]
        cards += f"""
<div class="instrument-card reveal" style="border-top:4px solid {meta['color']};">
  <div class="inst-type" style="color:{meta['color']};">{code}</div>
  <div class="inst-full">{meta['full']}</div>
  <div class="inst-meta">
    <span><i class="ti ti-users" aria-hidden="true" style="font-size:var(--fs-xs);margin-right:4px;"></i>{meta['target']}</span>
    <span><i class="ti ti-tag" aria-hidden="true" style="font-size:var(--fs-xs);margin-right:4px;"></i>{meta['domain']}</span>
  </div>
  <div class="inst-stats">
    <div class="inst-stat"><span class="stat-val">{int(row['total'])}</span><span class="stat-lbl">Surveys</span></div>
    <div class="inst-stat"><span class="stat-val">{int(row['done'])}</span><span class="stat-lbl">Completed</span></div>
    <div class="inst-stat"><span class="stat-val">{int(row['countries'])}</span><span class="stat-lbl">Countries</span></div>
  </div>
  <div class="inst-bar-wrap">
    <div class="inst-bar" style="width:{pct}%;background:{bc};"></div>
  </div>
  <span class="inst-pct" style="color:{bc};">{pct}% completion rate</span>
</div>"""
    return f'<div class="instrument-grid">{cards}</div>'


def scorecard_table(spi):
    rows = ""
    for i, (_, r) in enumerate(spi.iterrows(), 1):
        tc, ti = TIER_COLORS[r["tier"]], TIER_INK[r["tier"]]
        gap_s  = fmt_years(r["gap_years"]) if pd.notna(r["gap_years"]) else "-"
        last_s = str(int(r["last_year"])) if pd.notna(r["last_year"]) and r["last_year"] else "-"
        cycle_val = 1 if r["recent_done"] > 0 else 0
        cycle_s = (f"{int(r['recent_done'])} done" if r["recent_done"] > 0
                   else (f"{int(r['recent_inprog'])} in prog." if r["recent_inprog"] > 0 else "-"))
        bw = int(r["spi"])
        map_img = (f'<span class="country-map" role="img" aria-label="{r["iso3"]}" '
                   f'style="background-image:var(--map-{r["iso3"]})"></span>'
                   if r["iso3"] in COUNTRY_MAPS else "")
        _NO_INTERVAL = '<span style="color:var(--muted);cursor:help;" title="No renewal interval yet - fewer than 2 completed rounds">n/a</span>'
        reg_s  = (f"{r['d_regularity']:.1f}" if r["n_renewable"] > 0 else
                   f'<span style="color:var(--muted);cursor:help;" title="Fewer than 2 completed rounds means renewal regularity cannot yet be assessed. This scores as 0.0, not excluded - it still counts at full weight in the SPI average below.">0.0</span>')
        avg_iv = (fmt_years(r["avg_cycle_interval"], prefix="~")
                  if pd.notna(r["avg_cycle_interval"]) else _NO_INTERVAL)
        rows += f"""
<tr data-country="{r['country'].lower()}" data-tier="{r['tier']}" data-gap="{r['gap_cat']}" data-cycle="{cycle_val}" data-reg="{r['reg_cat']}">
  <td class="rank-cell" style="padding:8px 10px;">{i}</td>
  <td style="padding:8px 10px;">
    <div style="display:flex;align-items:center;">{map_img}<strong>{r['country']}</strong></div>
  </td>
  <td style="padding:8px 10px;">
    <div style="display:flex;align-items:center;gap:7px;">
      <div style="background:{tc};height:5px;border-radius:6px;width:{bw}px;max-width:80px;flex-shrink:0;"></div>
      <strong style="color:{ti}">{r['spi']:.1f}</strong>
      <span class="tier-badge t{r['tier']}" style="padding:1px 7px;">{r['tier_label']}</span>
    </div>
  </td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{r['d_coverage']:.1f}%</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{r['d_recency']:.1f}%</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{reg_s}</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;font-size:var(--fs-xs);color:var(--muted);">{avg_iv}</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{last_s}</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{gap_s}</td>
</tr>"""
    return f"""
<div class="scorecard-wrap" style="overflow-x:auto;">
<table id="scorecard-table" style="width:100%;border-collapse:collapse;font-size:var(--fs-sm);">
<caption style="text-align:left;font-size:var(--fs-xs);color:var(--muted);font-style:italic;padding-bottom:10px;">
  Country Surveillance Scorecard - SPI ranking and dimension scores. The <strong>Last Survey</strong> and <strong>Gap</strong> columns span
  <strong>all five instruments</strong> (most recent completed survey of any type); see the Strategic Priority tab for instrument-specific recency.
  SPI is a point estimate with no confidence interval; adjacent ranks separated by a fraction of a point should not be read as a meaningful difference.
</caption>
<thead><tr style="background:{C['primary']};color:#fff;">
  <th scope="col" style="padding:9px 10px;text-align:left;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;">#</th>
  <th scope="col" style="padding:9px 10px;text-align:left;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;">Country</th>
  <th scope="col" style="padding:9px 10px;text-align:left;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;">SPI / Tier</th>
  <th scope="col" style="padding:9px 10px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;" title="Breadth - count of instrument types completed ≥1 time, out of 5">Breadth</th>
  <th scope="col" style="padding:9px 10px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;" title="Currency - mean exponential-decay recency score (5-yr half-life, matching the WHO cycle) over all 5 instruments">Currency</th>
  <th scope="col" style="padding:9px 10px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;" title="Regularity - coverage-adjusted average renewal interval score. Scores 0.0 (not excluded) if no instrument yet has ≥2 completed rounds">Regularity</th>
  <th scope="col" style="padding:9px 10px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;" title="Average years between consecutive survey rounds, across all instruments with ≥2 rounds">Avg Interval</th>
  <th scope="col" style="padding:9px 10px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;" title="Most recent completed survey across ALL five instruments - not instrument-specific">Last Survey (any instrument)</th>
  <th scope="col" style="padding:9px 10px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.5px;">Gap</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>"""


def schema_cards():
    tables = [
        ("#003d82", "ti-world",          "dim_country",
         [("country_id","PK · INTEGER"),("country_name","TEXT UNIQUE"),
          ("iso3","TEXT"),("is_zanzibar","INTEGER"),("sub_region","TEXT")]),
        (BRAND["navy"], "ti-flask",          "dim_survey_type",
         [("survey_type_id","PK · INTEGER"),("survey_code","TEXT UNIQUE"),
          ("survey_full_name","TEXT"),("target_population","TEXT"),
          ("domain","TEXT"),("cycle_years","INTEGER DEFAULT 5")]),
        (BRAND["navy"], "ti-circle-check",   "dim_status",
         [("status_id","PK · INTEGER"),("status_code","TEXT UNIQUE"),
          ("is_completed","INTEGER"),("completion_weight","REAL")]),
        (BRAND["navy"], "ti-calendar",   "dim_year",
         [("year_id","PK = year value"),("year","INTEGER UNIQUE"),
          ("decade","TEXT"),("five_yr_period","TEXT"),("cycle_label","TEXT")]),
        (BRAND["navy"], "ti-table",          "fact_surveys",
         [("survey_id","PK · INTEGER"),("country_id","FK → dim_country"),
          ("survey_type_id","FK → dim_survey_type"),("year_id","FK → dim_year"),
          ("status_id","FK → dim_status"),("survey_year","INTEGER")]),
        (BRAND["muted"], "ti-layers-intersect",    "dim_indicator (future)",
         [("indicator_id","PK · INTEGER"),("indicator_code","TEXT UNIQUE"),
          ("indicator_name","TEXT"),("survey_type_id","FK → dim_survey_type"),
          ("unit","TEXT"),("direction","TEXT")]),
        (BRAND["muted"], "ti-chart-line",     "fact_indicators (future)",
         [("fact_id","PK · INTEGER"),("country_id","FK → dim_country"),
          ("indicator_id","FK → dim_indicator"),("year_id","FK → dim_year"),
          ("value","REAL"),("ci_lower / ci_upper","REAL")]),
    ]
    html = '<div class="schema-grid">'
    for color, icon, name, cols in tables:
        trows = "".join(f"<tr><td>{c}</td><td>{t}</td></tr>" for c, t in cols)
        html += f"""
<div class="schema-card">
  <div class="schema-card-head" style="background:{color};">
    <i class="ti {icon}" aria-hidden="true"></i> {name}
  </div>
  <table>{trows}</table>
</div>"""
    html += "</div>"
    return html


def per_survey_sections(A):
    """
    Generate per-instrument section cards for the Survey Analysis tab.

    Row status badges and header pills are derived from the SAME source
    (exec_kpis' per-country status, the canonical 4-category vocabulary:
    On Cycle / Attempt to update / Off Cycle / Never Conducted) so the two
    can never contradict each other. The finer Overdue/Critical distinction
    that used to compete as its own status is now shown as a sub-qualifier
    next to the gap value instead (e.g. "Off Cycle · 9 yrs").
    """
    kpis = A["exec_kpis"]
    cm   = A["cycle_matrix"]

    html = ""
    for code, meta in SURVEY_META.items():
        if code not in kpis:
            continue
        k = kpis[code]
        country_status = {g["country"]: g["status"] for g in k["countries_gap"]}
        sub = cm[cm["survey_type"] == code].sort_values("order").reset_index(drop=True)

        # ── Build-time integrity check: table rows must reconcile with pills ──
        status_tally = {s: 0 for s in CYCLE_STATUS_LABELS}
        for c in country_status.values():
            status_tally[c] += 1
        pill_tally = {
            "On Cycle": k["n_on_cycle"], "Attempt to update": k["n_attempt_to_update"],
            "Off Cycle": k["n_off_cycle"], "First Attempt": k["n_first_attempt"],
            "Never Conducted": k["n_never"],
        }
        assert status_tally == pill_tally, (
            f"{code}: per-country status tally {status_tally} != header pill tally {pill_tally}")
        assert sum(status_tally.values()) == k["n_total"] == len(sub), (
            f"{code}: status rows do not total {k['n_total']} countries")

        rows_html = ""
        for i, (_, row) in enumerate(sub.iterrows(), 1):
            status = country_status.get(row["country"], "Never Conducted")
            last_s = str(int(row["last_year"])) if pd.notna(row["last_year"]) and row["last_year"] else "Never"
            if pd.notna(row["gap"]):
                qualifier = f" &middot; {row['cycle_status']}" if row["cycle_status"] in ("Overdue", "Critical") else ""
                gap_s = fmt_years(row["gap"]) + qualifier
            else:
                gap_s = "-"
            bg     = "#fafbff" if i % 2 == 0 else "#ffffff"
            rows_html += f"""<tr style="background:{bg};">
  <td style="padding:9px 12px;font-size:var(--fs-sm);">{row['country']}</td>
  <td style="padding:9px 12px;text-align:center;">
    <span class="st-badge st-{_slug(status)}">{status}</span>
  </td>
  <td style="padding:9px 12px;text-align:center;font-size:var(--fs-sm);">{last_s}</td>
  <td style="padding:9px 12px;text-align:center;font-size:var(--fs-sm);">{gap_s}</td>
</tr>"""

        html += f"""
<div class="chart-card reveal survey-detail-section" data-survey="{code}" style="border-top:4px solid {meta['color']};margin-bottom:var(--gap-block);">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
    <div>
      <h3 style="font-size:var(--fs-md);font-weight:700;color:{meta['color']};margin:0 0 2px;">{code}</h3>
      <div style="font-size:var(--fs-xs);color:var(--muted);">{meta['full']} - {meta['target']} - <span style="font-style:italic;">last {code} survey per country</span></div>
    </div>
    <div style="display:flex;gap:7px;flex-wrap:wrap;">
      <span style="background:{CYCLE_STATUS_INK['On Cycle']}14;color:{CYCLE_STATUS_INK['On Cycle']};padding:3px 10px;border-radius:10px;font-size:var(--fs-xs);font-weight:700;">{k['n_on_cycle']} On Cycle</span>
      <span style="background:{CYCLE_STATUS_INK['Attempt to update']}14;color:{CYCLE_STATUS_INK['Attempt to update']};padding:3px 10px;border-radius:10px;font-size:var(--fs-xs);font-weight:700;">{k['n_attempt_to_update']} Attempt to update</span>
      <span style="background:{CYCLE_STATUS_INK['Off Cycle']}14;color:{CYCLE_STATUS_INK['Off Cycle']};padding:3px 10px;border-radius:10px;font-size:var(--fs-xs);font-weight:700;">{k['n_off_cycle']} Off Cycle</span>
      <span style="background:{CYCLE_STATUS_INK['First Attempt']}14;color:{CYCLE_STATUS_INK['First Attempt']};padding:3px 10px;border-radius:10px;font-size:var(--fs-xs);font-weight:700;">{k['n_first_attempt']} First Attempt</span>
      <span style="background:{CYCLE_STATUS_INK['Never Conducted']}14;color:{CYCLE_STATUS_INK['Never Conducted']};padding:3px 10px;border-radius:10px;font-size:var(--fs-xs);font-weight:700;">{k['n_never']} Never Conducted</span>
    </div>
  </div>
  <p style="font-size:var(--fs-sm);color:var(--muted);margin-bottom:12px;line-height:1.7;"><strong>Action priority for {code}:</strong> {k['n_off_cycle']} {'country needs' if k['n_off_cycle'] == 1 else 'countries need'} re-engagement - prior evidence exists but no update is currently in progress. {k['n_attempt_to_update'] + k['n_first_attempt']} {'country is' if (k['n_attempt_to_update'] + k['n_first_attempt']) == 1 else 'countries are'} already in motion (a round is underway, whether renewing or first-ever) and should be supported through to completion. {k['n_never']} {'country has' if k['n_never'] == 1 else 'countries have'} no {code} evidence and nothing in progress - the highest-priority gap for new technical and financial investment.</p>
  <div class="status-table-wrap" style="overflow-x:auto;max-height:420px;overflow-y:auto;">
  <table class="status-table" style="width:100%;border-collapse:collapse;">
  <caption style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);">{code} surveillance status by country</caption>
  <thead><tr style="background:{meta['color']};color:#fff;position:sticky;top:0;z-index:1;">
    <th scope="col" style="padding:7px 12px;text-align:left;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.4px;">Country</th>
    <th scope="col" style="padding:7px 12px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.4px;">Status</th>
    <th scope="col" style="padding:7px 12px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.4px;" title="Last {code} survey - instrument-specific, not the all-instrument recency shown in the Scorecard">Last {code} Survey</th>
    <th scope="col" style="padding:7px 12px;text-align:center;font-size:var(--fs-xs);text-transform:uppercase;letter-spacing:.4px;">Gap</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
  </table>
  </div>
</div>"""

    return html


def build_html(A: dict) -> str:
    # All figures use include_plotlyjs=False - Plotly CDN is loaded once in <head>
    def R(fig):
        _theme_fig(fig)
        return fig.to_html(full_html=False,
                           include_plotlyjs=False,
                           config={"displayModeBar": True, "responsive": True,
                                   "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                                   "displaylogo": False})

    ch_tier        = R(fig_tier_donut(A))
    ch_spi_bar     = R(fig_spi_bar(A))
    ch_spi_map     = R(fig_spi_choropleth(A))
    ch_components  = R(fig_spi_components(A))
    ch_curr        = R(fig_current_cycle(A))
    ch_heatmap     = R(fig_last_year_heatmap(A))
    ch_prio        = R(fig_priority_scatter(A))
    ch_timeline    = R(fig_timeline(A))
    ch_gap         = R(fig_gap_bar(A))
    ch_survey_cmp  = R(fig_survey_type_comparison(A))
    survey_sections = per_survey_sections(A)

    spi      = A["spi"]
    top5     = spi.head(5)["country"].tolist()
    n_crit   = A["n_critical"]
    n_strong = A["n_strong"]
    reg_spi  = A["regional_spi"]
    n_ent    = A["n_entities"]
    spi_tier_color = TIER_COLORS[tier_of(reg_spi)]   # fill (bar, hairline)
    spi_tier_ink   = TIER_INK[tier_of(reg_spi)]      # text
    # Header - every number and colour read from the data (nothing copied
    # from the reference design).
    _t_reg   = tier_of(reg_spi)
    _tier_n  = {t: int((spi["tier"] == t).sum()) for t in (1, 2, 3, 4)}
    n_instr  = len(SURVEY_META)
    hero_map = hero_tile_map(spi)
    _bands   = [(0, TIER_CUTS[2], 4), (TIER_CUTS[2], TIER_CUTS[1], 3), (TIER_CUTS[1], TIER_CUTS[0], 2), (TIER_CUTS[0], 100, 1)]
    _segs    = "".join(f'<span class="t{t}" style="flex:{hi - lo}"></span>' for lo, hi, t in _bands)
    _ticks   = "".join(f'<span style="left:{v}%">{v}</span>' for v in [0] + sorted(TIER_CUTS) + [100])
    hero_spi_card = (
        f'<div class="spi-card"><div class="spi-card-t">Regional SPI score</div>'
        f'<div class="spi-card-v"><b>{fmt_spi(reg_spi)}</b><small>/100</small>'
        f'<span class="spi-card-tag t{_t_reg}-tag">{TIER_LABELS[_t_reg]}</span></div>'
        f'<div class="spi-track" role="img" aria-label="Regional SPI {fmt_spi(reg_spi)} of 100, {TIER_LABELS[_t_reg]} tier">'
        f'{_segs}<i style="left:{min(max(reg_spi, 0), 100):.1f}%"></i></div>'
        f'<div class="spi-ticks" aria-hidden="true">{_ticks}</div></div>')
    hero_legend = ('<div class="tm-legend"><span class="tm-legend-cap">Countries by SPI tier</span>' +
                   "".join(f'<span><i class="t{t}"></i><b>{_tier_n[t]}</b>{TIER_LABELS[t]}</span>' for t in (4, 3, 2, 1)) +
                   '</div>')
    # One-line takeaways for the "About this chart" pattern. Static charts get a
    # data-driven sentence computed from the same objects the chart plots;
    # filter-driven charts get a reading guide (their numbers change).
    _k   = A["exec_kpis"]
    _sts = [st for st in SURVEY_META if st in _k]
    _best_on    = max(_sts, key=lambda st: _k[st]["n_on_cycle"])
    _most_never = max(_sts, key=lambda st: _k[st]["n_never"])
    tk_status = (f"{_best_on} has the most countries on cycle ({_k[_best_on]['n_on_cycle']} of {_k[_best_on]['n_total']}); "
                 f"{_most_never} has the most that have never conducted it ({_k[_most_never]['n_never']}).")
    _lym  = A["last_year_matrix"]
    _cur  = int(((CURRENT_YEAR - _lym) <= 5).sum().sum())
    _none = int(_lym.isna().sum().sum())
    tk_matrix = (f"{_cur} of {_lym.size} country-instrument pairs have current evidence (0&ndash;5 yrs); "
                 f"{_none} have no completed survey on record.")
    tk_spi = (f"{int((A['spi']['tier']==1).sum())} of {len(A['spi'])} countries reach Strong (SPI &#8805; 75); "
              f"{int((A['spi']['tier']==4).sum())} are Critical (below 30).")

    # Status palette shortcuts (single source of truth: config.CYCLE_STATUS_COLORS)
    # - never reuse TIER_COLORS' hex values here, so a reader can't mistake a
    # status badge for an SPI-tier badge when moving between tabs.
    st_on, st_att, st_off, st_first, st_nev = (CYCLE_STATUS_INK["On Cycle"], CYCLE_STATUS_INK["Attempt to update"],
                                      CYCLE_STATUS_INK["Off Cycle"], CYCLE_STATUS_INK["First Attempt"],
                                      CYCLE_STATUS_INK["Never Conducted"])
    # Colour must encode the VALUE, not just announce the category: a "0 Strong
    # performers" stat should not carry a celebratory green dot.
    strong_dot_color = BRAND["muted"] if n_strong == 0 else TIER_INK[1]
    crit_dot_color   = TIER_INK[4] if n_crit > 0 else BRAND["muted"]
    pct_on   = A["pct_on_track"]
    pct_off  = A["pct_off_cycle"]
    pct_crit = A["pct_gap_critical"]
    n_pipe   = A["n_pipeline"]
    n_curr   = A["n_current_cycle"]
    n_gap_cr = A["n_gap_critical"]

    # ── Executive KPI data for JS injection ───────────────────────────────────
    import json as _json
    exec_kpis_json        = _json.dumps(A["exec_kpis"], ensure_ascii=False)
    timeline_by_type_json = _json.dumps(A["timeline_by_type"], ensure_ascii=False)
    spi_scores_json = _json.dumps(
        {row["country"]: round(float(row["spi"]), 1) for _, row in A["spi"].iterrows()},
        ensure_ascii=False
    )
    import pandas as _pd
    spi_table_json = _json.dumps([
        {"country": str(r["country"]),
         "iso3":  str(r["iso3"]) if _pd.notna(r["iso3"]) else "",
         "spi":   round(float(r["spi"]),  1),
         "tier":  int(r["tier"]),
         "tier_label": str(r["tier_label"]),
         "d_coverage":  round(float(r["d_coverage"]),  1),
         "d_recency":   round(float(r["d_recency"]),   1),
         "d_regularity": round(float(r["d_regularity"]), 1) if _pd.notna(r["d_regularity"]) else None,
         "last_year": int(r["last_year"]) if _pd.notna(r["last_year"]) else None,
         "gap_years": int(r["gap_years"]) if _pd.notna(r["gap_years"]) else None,
         "n_done":    int(r["n_done"]),
         "types_done":int(r["types_done"])}
        for _, r in A["spi"].iterrows()
    ], ensure_ascii=False)
    # ── STEPS / GYTS / GATS profile data ──────────────────────────────────────
    steps_profile = A.get("steps_profile", {})
    gyts_profile  = A.get("gyts_profile", {})
    gats_profile  = A.get("gats_profile", {})
    steps_profile_json = _json.dumps(steps_profile, ensure_ascii=False) if steps_profile else "null"
    gyts_profile_json  = _json.dumps(gyts_profile,  ensure_ascii=False) if gyts_profile  else "null"
    gats_profile_json  = _json.dumps(gats_profile,  ensure_ascii=False) if gats_profile  else "null"

    # Build country profile dropdown options across all three survey types
    # (default: Ethiopia, else first) and a per-country map of which survey
    # types have data, so the Survey dropdown can populate itself in JS.
    _steps_countries_set = set(steps_profile.get("countries", []))
    _gyts_countries_set  = set(gyts_profile.get("countries", []))
    _gats_countries_set  = set(gats_profile.get("countries", []))
    _prof_countries = sorted(_steps_countries_set | _gyts_countries_set | _gats_countries_set)
    _prof_default   = "Ethiopia" if "Ethiopia" in _prof_countries else (_prof_countries[0] if _prof_countries else "")
    _prof_options   = "\n".join(
        f'<option value="{c}"{"  selected" if c == _prof_default else ""}>{c}</option>'
        for c in _prof_countries
    )
    _prof_n = len(_prof_countries)
    _country_surveys_map = {
        c: [s for s, cs in (("STEPS", _steps_countries_set), ("GYTS", _gyts_countries_set), ("GATS", _gats_countries_set)) if c in cs]
        for c in _prof_countries
    }
    country_surveys_json = _json.dumps(_country_surveys_map, ensure_ascii=False)

    exec_global    = A["exec_kpis"]["global"]
    exec_steps     = A["exec_kpis"]["STEPS"]
    js_with_data   = (JS
                      .replace("__EXEC_DATA_PLACEHOLDER__",     exec_kpis_json)
                      .replace("__TIMELINE_DATA_PLACEHOLDER__",  timeline_by_type_json)
                      .replace("__SPI_SCORES_PLACEHOLDER__",    spi_scores_json)
                      .replace("__STEPS_PROFILE_PLACEHOLDER__", steps_profile_json)
                      .replace("__GYTS_PROFILE_PLACEHOLDER__",  gyts_profile_json)
                      .replace("__GATS_PROFILE_PLACEHOLDER__",  gats_profile_json)
                      .replace("__COUNTRY_SURVEYS_PLACEHOLDER__", country_surveys_json)
                      .replace("__STATUS_LABELS_PLACEHOLDER__", _json.dumps(CYCLE_STATUS_LABELS))
                      .replace("__STATUS_COLORS_PLACEHOLDER__", _json.dumps(CYCLE_STATUS_COLORS))
                      .replace("__PALETTE_PLACEHOLDER__", palette_js())
                      .replace("__PLOTLY_THEME_PLACEHOLDER__", json.dumps(PLOTLY_THEME))
                      .replace("__SPI_TABLE_PLACEHOLDER__", spi_table_json)
                      .replace("__REPORT_DATE_PLACEHOLDER__", _json.dumps(REPORT_DATE)))

    # Build favicon link and logo img tags (empty string if asset not found)
    fav_link = f'<link rel="icon" type="image/png" href="data:image/png;base64,{FAV_LOGO_B64}"/>' if FAV_LOGO_B64 else ""
    who_logo_tag = (f'<a href="https://www.afro.who.int/" target="_blank" rel="noopener" title="WHO African Region">'
                    f'<img src="data:image/png;base64,{WHO_LOGO_B64}" {_wh_attr(_LOGOS_DIR / 'who_logo.png', 40)} class="nav-logo" alt="WHO Logo" style="height:40px;display:block;"/></a>') if WHO_LOGO_B64 else ""
    dpc_logo_tag = (f'<a href="https://dataportal.afro.who.int/" target="_blank" rel="noopener" title="DPC Data Portal">'
                    f'<img src="data:image/png;base64,{DPC_LOGO_B64}" {_wh_attr(_LOGOS_DIR / 'dpc_logo.png', 34)} class="nav-logo" alt="DPC Data Portal" style="height:34px;display:block;"/></a>') if DPC_LOGO_B64 else ""
    # Footer logo variants (slightly larger, also clickable)
    who_footer_tag = (f'<a href="https://www.afro.who.int/" target="_blank" rel="noopener" title="WHO African Region">'
                      f'<img src="data:image/png;base64,{WHO_LOGO_B64}" {_wh_attr(_LOGOS_DIR / 'who_logo.png', 44)} alt="WHO" style="height:44px;display:inline-block;vertical-align:middle;filter:brightness(0) invert(1);opacity:.85;transition:opacity var(--dur-ui) var(--ease-out);" class="footer-logo"/></a>') if WHO_LOGO_B64 else ""
    dpc_footer_tag = (f'<a href="https://dataportal.afro.who.int/" target="_blank" rel="noopener" title="DPC Data Portal">'
                      f'<img src="data:image/png;base64,{DPC_LOGO_B64}" {_wh_attr(_LOGOS_DIR / 'dpc_logo.png', 38)} alt="DPC" style="height:38px;display:inline-block;vertical-align:middle;filter:brightness(0) invert(1);opacity:.85;transition:opacity var(--dur-ui) var(--ease-out);" class="footer-logo"/></a>') if DPC_LOGO_B64 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"/>
<meta name="theme-color" content="#00285a"/>
<meta name="color-scheme" content="light"/>
<title>NCD Population-based Surveillance Intelligence Platform - WHO AFRO</title>
{fav_link}
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<link rel="preconnect" href="https://cdn.plot.ly" crossorigin/>
<link rel="preconnect" href="https://unpkg.com" crossorigin/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400..800&family=Source+Sans+3:ital,wght@0,400..800;1,400..600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400..600&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://unpkg.com/@tabler/icons-webfont@3.46.0/dist/tabler-icons.min.css"/>
<style>{country_map_css()}{palette_css()}{CSS}</style>
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<div id="reading-progress"></div>

<nav class="topnav" aria-label="Site header">
  <div class="topnav-inner">
    <div class="nav-logos">
      {who_logo_tag}
      <div class="nav-divider"></div>
      {dpc_logo_tag}
    </div>
  </div>
</nav>

<div class="hero">
  <div class="hero-grid">
    <div class="hero-copy">
      <h1>NCD Population&#8209;based Surveillance Intelligence Platform</h1>
      <p class="hero-sub">A strategic intelligence platform synthesizing <strong>five core NCD population-based surveillance systems</strong> across 47 WHO AFRO Member States + Zanzibar</p>
      <div class="hero-facts">
        <div class="hero-fact"><b>{n_ent}</b><span>Countries &amp;<br>territories</span></div>
        <div class="hero-fact"><b>{n_instr}</b><span>Survey<br>instruments</span></div>
        <div class="hero-fact is-current" title="Countries with at least one completed survey since {CURRENT_CYCLE_START}"><b>{n_curr}</b><span>Countries active<br>this cycle</span></div>
      </div>
    </div>
    <div class="hero-visual">
      <div class="tm-wrap">
        {hero_map}
        {hero_spi_card}
      </div>
      {hero_legend}
      <p class="tm-disclaimer">{WHO_MAP_DISCLAIMER}</p>
    </div>
  </div>
</div>

<div class="tab-nav">
  <div class="tab-nav-inner" role="tablist" aria-label="Dashboard sections">
    <button class="tab-btn" id="tabbtn-tab-exec" data-tab="tab-exec" role="tab" aria-selected="true" aria-controls="tab-exec" tabindex="0">Executive Overview</button>
    <button class="tab-btn" id="tabbtn-tab-perf" data-tab="tab-perf" role="tab" aria-selected="false" aria-controls="tab-perf" tabindex="-1">Surveillance Performance</button>
    <button class="tab-btn" id="tabbtn-tab-cycle" data-tab="tab-cycle" role="tab" aria-selected="false" aria-controls="tab-cycle" tabindex="-1">Cycle &amp; Gap</button>
    <button class="tab-btn" id="tabbtn-tab-profile" data-tab="tab-profile" role="tab" aria-selected="false" aria-controls="tab-profile" tabindex="-1">Country Profile</button>
    <button class="tab-btn" id="tabbtn-tab-priority" data-tab="tab-priority" role="tab" aria-selected="false" aria-controls="tab-priority" tabindex="-1">Strategic Priority</button>
    <button class="tab-btn" id="tabbtn-tab-methods" data-tab="tab-methods" role="tab" aria-selected="false" aria-controls="tab-methods" tabindex="-1">Methods</button>
  </div>
</div>

<main id="main-content" class="container">

  <!-- ═══════════════════ TAB 1: EXECUTIVE OVERVIEW ═══════════════════ -->
  <div id="tab-exec" class="tab-pane active" role="tabpanel" aria-labelledby="tabbtn-tab-exec" tabindex="0">
    <div class="section">

      <!-- Section header -->
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">1</span>
          <h2 class="section-title">Executive Overview</h2>
        </div>
        <p class="section-subtitle">Country-level surveillance status - unit of analysis: unique WHO AFRO countries and territories (N&nbsp;=&nbsp;48)</p>
      </div>

      <!-- ① SURVEY INSTRUMENT STATUS - Static, shown first, not affected by filter -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            {ch_survey_cmp}
            <div class="chart-note">
              <p class="chart-takeaway">{tk_status}</p>
              <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this chart</summary>
              <div class="chart-commentary">
              Status distribution across all five NCD surveillance instruments (N&#160;=&#160;48 countries per instrument). Each bar shows how countries distribute across five mutually exclusive states: <strong style="color:{st_on};">On Cycle</strong> (completed &#8804;&#160;5 yr), <strong style="color:{st_att};">Attempt to update</strong> (prior evidence + active new round), <strong style="color:{st_off};">Off Cycle</strong> (prior evidence but surveillance idle), <strong style="color:{st_first};">First Attempt</strong> (no prior evidence, first-ever round in progress), and <strong style="color:{st_nev};">Never Conducted</strong> (no completed survey and nothing in progress). This panel is static and reflects system-wide status across all survey types.
            </div>
              </details>
            </div>
          </div>
        </div>
      </div>

      <!-- Filter bar - STEPS default, no "All Survey Types" option -->
      <div class="filter-bar">
        <label class="filter-label" for="exec-survey-filter"><i class="ti ti-filter" aria-hidden="true"></i>&nbsp; View by Survey</label>
        <select id="exec-survey-filter" class="filter-select" style="min-width:240px;">
          <option value="STEPS" selected>STEPS - NCD Risk Factor Surveillance</option>
          <option value="GYTS">GYTS - Global Youth Tobacco Survey</option>
          <option value="GSHS">GSHS - School-based Student Health Survey</option>
          <option value="GATS">GATS - Global Adult Tobacco Survey</option>
          <option value="GSHPP">GSHPP - School Health Policies &amp; Practices</option>
        </select>
        <button id="exec-filter-reset" class="filter-reset" style="padding:7px 14px;">
          <i class="ti ti-arrow-back-up" aria-hidden="true"></i>&nbsp; Reset to STEPS
        </button>
        <span id="exec-survey-badge" style="font-size:var(--fs-xs);font-weight:600;color:var(--primary);margin-left:6px;padding:5px 12px;background:#eef4ff;border-radius:9999px;border:1px solid #c8d8f8;">
          STEPS - NCD Risk Factor Surveillance
        </span>
      </div>

      <!-- Analytical note -->
      <div class="chart-note">
        <p class="chart-takeaway">Every count is a unique country (N&nbsp;=&nbsp;48), with exactly one status per instrument.</p>
        <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About these figures</summary>
        <div style="background:var(--tint);border:1px solid var(--rule);border-radius:10px;padding:11px 16px;font-size:var(--fs-sm);color:var(--text);margin-bottom:var(--gap-block);display:flex;align-items:flex-start;gap:10px;">
        <i class="ti ti-info-circle" aria-hidden="true" style="margin-top:2px;color:var(--brand);"></i>
        <span>
          <strong>Unit of analysis:</strong> All counts represent <strong>unique countries/territories</strong> (N&nbsp;=&nbsp;48). Categories are mutually exclusive per country per survey type.
          &nbsp;<strong style="color:{st_on};">&#9632; On Cycle</strong>: completed &#8804;&nbsp;5 yr - current, usable evidence &nbsp;|&nbsp;
          <strong style="color:{st_att};">&#9632; Attempt to update</strong>: prior completed data + new round actively in progress &nbsp;|&nbsp;
          <strong style="color:{st_off};">&#9632; Off Cycle</strong>: has prior evidence but surveillance is currently idle &nbsp;|&nbsp;
          <strong style="color:{st_first};">&#9632; First Attempt</strong>: no prior evidence, but a first-ever round is actively in progress &nbsp;|&nbsp;
          <strong style="color:{st_nev};">&#9632; Never Conducted</strong>: no completed survey and nothing currently in progress
        </span>
      </div>
        </details>
      </div>

      <!-- ② FIVE DYNAMIC KPI SIGNAL CARDS -->
      <div class="signal-grid" style="grid-template-columns:repeat(5,1fr);">

        <div class="signal-card reveal" style="color:{st_on};">
          <div style="font-size:var(--fs-xs);font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{st_on};margin-bottom:4px;">
            <i class="ti ti-circle-check" aria-hidden="true"></i>&nbsp; On Cycle
          </div>
          <div class="signal-val" id="exec-n-oncycle" data-count="{exec_steps['n_on_cycle']}">{exec_steps['n_on_cycle']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-oncycle-sub">{exec_steps['n_on_cycle']} of {n_ent} countries</div>
          <div id="exec-n-oncycle-def" style="font-size:var(--fs-xs);color:var(--muted);margin-top:5px;line-height:1.4;">
            Completed &#8804;&nbsp;5 years ago - current, usable evidence
          </div>
        </div>

        <div class="signal-card reveal" style="color:{st_att};">
          <div style="font-size:var(--fs-xs);font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{st_att};margin-bottom:4px;">
            <i class="ti ti-refresh" aria-hidden="true"></i>&nbsp; Attempt to update
          </div>
          <div class="signal-val" id="exec-n-implement" data-count="{exec_steps['n_attempt_to_update']}">{exec_steps['n_attempt_to_update']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-implement-sub">{exec_steps['n_attempt_to_update']} of {n_ent} countries</div>
          <div id="exec-n-implement-def" style="font-size:var(--fs-xs);color:var(--muted);margin-top:5px;line-height:1.4;">
            Prior evidence exists - actively updating with new survey
          </div>
        </div>

        <div class="signal-card reveal" style="color:{st_off};">
          <div style="font-size:var(--fs-xs);font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{st_off};margin-bottom:4px;">
            <i class="ti ti-player-pause" aria-hidden="true"></i>&nbsp; Off Cycle
          </div>
          <div class="signal-val" id="exec-n-offcycle" data-count="{exec_steps['n_off_cycle']}">{exec_steps['n_off_cycle']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-offcycle-sub">{exec_steps['n_off_cycle']} of {n_ent} countries</div>
          <div id="exec-n-offcycle-def" style="font-size:var(--fs-xs);color:var(--muted);margin-top:5px;line-height:1.4;">
            Has prior evidence but surveillance is idle - off-cycle
          </div>
        </div>

        <div class="signal-card reveal" style="color:{st_first};">
          <div style="font-size:var(--fs-xs);font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{st_first};margin-bottom:4px;">
            <i class="ti ti-flag" aria-hidden="true"></i>&nbsp; First Attempt
          </div>
          <div class="signal-val" id="exec-n-firstattempt" data-count="{exec_steps['n_first_attempt']}">{exec_steps['n_first_attempt']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-firstattempt-sub">{exec_steps['n_first_attempt']} of {n_ent} countries</div>
          <div id="exec-n-firstattempt-def" style="font-size:var(--fs-xs);color:var(--muted);margin-top:5px;line-height:1.4;">
            No prior evidence, but a first-ever survey is in progress now
          </div>
        </div>

        <div class="signal-card reveal" style="color:{st_nev};">
          <div style="font-size:var(--fs-xs);font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{st_nev};margin-bottom:4px;">
            <i class="ti ti-ban" aria-hidden="true"></i>&nbsp; Never Conducted
          </div>
          <div class="signal-val" id="exec-n-never" data-count="{exec_steps['n_never']}">{exec_steps['n_never']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-never-sub">{exec_steps['n_never']} of {n_ent} countries</div>
          <div id="exec-n-never-def" style="font-size:var(--fs-xs);color:var(--muted);margin-top:5px;line-height:1.4;">
            Never completed nor attempted - no policy-usable evidence exists
          </div>
        </div>

      </div>

      <!-- ③ SURVEILLANCE STATUS DISTRIBUTION - Dynamic donut -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            <h3 style="font-size:var(--fs-base);font-weight:700;color:{C['primary']};margin:0 0 4px;">Selected Instrument vs. System-Wide Status Mix</h3>
            <div id="exec-donut-chart" style="min-height:220px;"></div>
            <div class="chart-note">
              <p class="chart-takeaway">Top bar: the selected instrument. Bottom bar: all five instruments combined.</p>
              <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this chart</summary>
              <div class="chart-commentary">
              Compares the status mix of the currently selected instrument against the all-instruments system-wide mix (bottom bar) - use it to see whether the selected instrument is ahead of or behind the region's overall surveillance posture. Switch the survey filter above to compare a different instrument.
            </div>
              </details>
            </div>
          </div>
        </div>
      </div>

      <!-- ④ YEARS SINCE MOST RECENT SURVEY - Dynamic gap chart -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            <div id="exec-gap-chart" style="min-height:500px;"></div>
            <div class="chart-note">
              <p class="chart-takeaway">The longer the bar, the longer that country has gone without a completed survey.</p>
              <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this chart</summary>
              <div class="chart-commentary">
              <strong>Years since last completed survey</strong> for the selected instrument, by country, sorted from most recent (left) to longest gap (right). The Y-axis reflects time relative to 2026 - countries with identical gaps align at the same height. Color coding: <span style="color:var(--rec-0-ink);font-weight:700;">&#9632; On Cycle</span> (0&ndash;5 yrs), <span style="color:var(--rec-1-ink);font-weight:700;">&#9632; Off Cycle</span> (6&ndash;12 yrs), <span style="color:var(--rec-2-ink);font-weight:700;">&#9632; Critical</span> (&gt;12 yrs). Dashed horizontal lines mark the 5- and 12-year thresholds. Countries with no completed survey for the selected instrument are excluded.
            </div>
              </details>
            </div>
          </div>
        </div>
      </div>


    </div>
  </div>

  <!-- TAB 2: SURVEILLANCE PERFORMANCE -->
  <div id="tab-perf" class="tab-pane" role="tabpanel" aria-labelledby="tabbtn-tab-perf" tabindex="0">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">2</span>
          <h2 class="section-title">Surveillance Performance</h2>
        </div>
        <p class="section-subtitle">Surveillance Performance Index (SPI) - composite score across Breadth, Currency &amp; Regularity - all {n_ent} countries ranked</p>
      </div>

      <!-- Regional SPI + Tier overview -->
      <div class="stat-highlight-row reveal">
        <div class="stat-highlight-item" style="text-align:center;padding:0 24px 0 0;">
          <div class="stat-hl-val" style="color:{spi_tier_ink};">{fmt_spi(reg_spi)}<span style="font-size:1rem;font-weight:600;opacity:.6;">/100</span></div>
          <div class="stat-hl-lbl" title="Simple unweighted mean across all {n_ent} entities - not weighted by population. Zanzibar and mainland Tanzania are counted as two separate entities sharing one ISO3 code.">Regional SPI Average&nbsp;<i class="ti ti-info-circle" aria-hidden="true" style="font-size:var(--fs-xs);opacity:.6;"></i></div>
        </div>
        <div class="stat-highlight-item" style="text-align:center;padding:0 24px;">
          <div class="stat-hl-val" style="color:var(--muted);">{A['median_spi']}</div>
          <div class="stat-hl-lbl" title="Simple unweighted median across all {n_ent} entities - not weighted by population.">Median SPI&nbsp;<i class="ti ti-info-circle" aria-hidden="true" style="font-size:var(--fs-xs);opacity:.6;"></i></div>
        </div>
        <div class="stat-tiers" style="flex:1;display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end;">
          <div class="tier-card" style="border-top-color:var(--tier-1);min-width:110px;">
            <div class="tier-card-val" style="color:var(--tier-1-ink);">{int((spi['tier']==1).sum())}</div>
            <div class="tier-card-lbl">Strong</div>
            <div class="tier-card-sub">SPI &#8805; 75</div>
          </div>
          <div class="tier-card" style="border-top-color:var(--tier-2);min-width:110px;">
            <div class="tier-card-val" style="color:var(--tier-2-ink);">{int((spi['tier']==2).sum())}</div>
            <div class="tier-card-lbl">Advancing</div>
            <div class="tier-card-sub">SPI 50&#8211;74</div>
          </div>
          <div class="tier-card" style="border-top-color:var(--tier-3);min-width:110px;">
            <div class="tier-card-val" style="color:var(--tier-3-ink);">{int((spi['tier']==3).sum())}</div>
            <div class="tier-card-lbl">Developing</div>
            <div class="tier-card-sub">SPI 30&#8211;49</div>
          </div>
          <div class="tier-card" style="border-top-color:var(--tier-4);min-width:110px;">
            <div class="tier-card-val" style="color:var(--tier-4-ink);">{n_crit}</div>
            <div class="tier-card-lbl">Critical</div>
            <div class="tier-card-sub">SPI &lt; 30</div>
          </div>
        </div>
      </div>

      {insight_box(f"<strong>Regional SPI: {reg_spi}/100</strong> - Median: {A['median_spi']} &nbsp;·&nbsp; <strong>{n_strong}</strong> countries achieve Strong status (SPI ≥ 75), while <strong>{n_crit}</strong> remain Critical (SPI < 30). The SPI is a composite of three equally-weighted dimensions: <strong>Breadth</strong> (how many of 5 instruments used), <strong>Currency</strong> (recency of evidence), and <strong>Regularity</strong> (cycle adherence). Scroll down to explore dimension-level breakdowns.", "info")}

      <!-- SPI bar chart -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            <div class="chart-wide">{ch_spi_bar}</div>
            <div class="chart-note">
              <p class="chart-takeaway">{tk_spi}</p>
              <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this chart</summary>
              <div class="chart-commentary">Full country ranking by SPI score (0–100). Dashed threshold lines mark the four performance tiers. Countries in the Critical tier show compound weaknesses across all three SPI dimensions - they lack breadth of instruments, currency of evidence, and cycle regularity simultaneously.</div>
              </details>
            </div>
          </div>
        </div>
      </div>

      <!-- Divider -->
      <div class="section-divider-label">Country Scorecard</div>

      <!-- Filter + Scorecard table -->
      <div class="filter-bar">
        <label class="filter-label" for="sc-search"><i class="ti ti-search" aria-hidden="true"></i></label>
        <input id="sc-search" class="filter-input" type="search" name="sc-search" autocomplete="off" spellcheck="false" aria-label="Search country" placeholder="Search country&#8230;"/>
        <label class="filter-label" for="sc-tier">Tier</label>
        <select id="sc-tier" class="filter-select">
          <option value="">All Tiers</option>
          <option value="1">Strong (&#8805;75)</option>
          <option value="2">Advancing (50&#8211;74)</option>
          <option value="3">Developing (30&#8211;49)</option>
          <option value="4">Critical (&lt;30)</option>
        </select>
        <label class="filter-label" for="sc-gap">Gap</label>
        <select id="sc-gap" class="filter-select">
          <option value="">All Gaps</option>
          <option value="&#8804;5 years">&#8804;5 years</option>
          <option value="6&#8211;10 years">6&#8211;10 years</option>
          <option value=">10 years">&gt;10 years</option>
          <option value="No data">No data</option>
        </select>
        <label class="filter-label" for="sc-cycle">Cycle</label>
        <select id="sc-cycle" class="filter-select">
          <option value="">All</option>
          <option value="1">Active this cycle</option>
          <option value="0">No recent activity</option>
        </select>
        <label class="filter-label" for="sc-reg">Regularity</label>
        <select id="sc-reg" class="filter-select">
          <option value="">All</option>
          <option value="High">High (&#8804;6 yr avg)</option>
          <option value="Moderate">Moderate (7&#8211;9 yr avg)</option>
          <option value="Low">Low (&gt;9 yr avg)</option>
          <option value="Not">Not renewable yet</option>
        </select>
        <label class="filter-label" for="sc-top">Show</label>
        <select id="sc-top" class="filter-select">
          <option value="0">All countries</option>
          <option value="10">Top 10</option>
          <option value="20">Top 20</option>
          <option value="30">Top 30</option>
        </select>
        <button id="sc-reset" class="filter-reset"><i class="ti ti-arrow-back-up" aria-hidden="true"></i> Reset</button>
        <span id="sc-count" class="filter-count" aria-live="polite"></span>
      </div>

      <div class="chart-card reveal" style="margin-bottom:var(--gap-block);">
        <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
          <button id="btn-export-spi" style="font-family:var(--font);font-size:var(--fs-xs);font-weight:700;padding:7px 16px;border-radius:10px;border:none;background:#003d82;color:#fff;cursor:pointer;display:inline-flex;align-items:center;gap:6px;"><i class="ti ti-file-type-csv" aria-hidden="true"></i>&nbsp;Export CSV</button>
        </div>
        {scorecard_table(spi)}
      </div>

    </div>
  </div>

  <!-- TAB 3: CYCLE & GAP -->
  <div id="tab-cycle" class="tab-pane" role="tabpanel" aria-labelledby="tabbtn-tab-cycle" tabindex="0">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">3</span>
          <h2 class="section-title">5-Year Cycle &amp; Gap Analysis</h2>
        </div>
        <p class="section-subtitle">Operational accountability - current cycle {CURRENT_CYCLE_START}&ndash;{CURRENT_YEAR} &middot; WHO-recommended 5-year surveillance frequency</p>
      </div>

      <!-- Historical Activity Timeline (dynamic, filterable) -->
      <div class="section-divider-label">Historical Activity Timeline - By Survey Instrument</div>
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;flex-wrap:wrap;">
        <label for="cycle-timeline-filter" style="font-size:var(--fs-sm);font-weight:700;color:var(--muted);letter-spacing:.5px;text-transform:uppercase;">Survey instrument:</label>
        <select id="cycle-timeline-filter" style="font-family:var(--font);font-size:var(--fs-base);font-weight:600;border:1px solid var(--border);border-radius:10px;padding:7px 14px;background:#fff;color:var(--text);cursor:pointer;transition:border-color var(--dur-ui) var(--ease-out);" onchange="updateTimeline(this.value)">
          <option value="STEPS" selected>STEPS - NCD Risk Factor Survey</option>
          <option value="GYTS">GYTS - Global Youth Tobacco Survey</option>
          <option value="GSHS">GSHS - Global School Health Survey</option>
          <option value="GATS">GATS - Global Adult Tobacco Survey</option>
          <option value="GSHPP">GSHPP - School Health Policies &amp; Practices</option>
        </select>
        <button onclick="(function(){{var f=document.getElementById('cycle-timeline-filter');f.value='STEPS';updateTimeline('STEPS');}})();" style="font-family:var(--font);font-size:var(--fs-xs);font-weight:600;border:1px solid var(--border);border-radius:10px;padding:7px 14px;background:#f4f7fb;color:var(--muted);cursor:pointer;transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);" onmouseover="this.style.background='#e2e8f0'" onmouseout="this.style.background='#f4f7fb'"><i class="ti ti-arrow-back-up" aria-hidden="true" style="margin-right:5px;"></i>Reset</button>
      </div>
      <div class="chart-card reveal" style="margin-bottom:24px;">
        <div id="cycle-timeline-chart" style="width:100%;min-height:400px;"></div>
        <div class="chart-note">
          <p class="chart-takeaway">Blue bars fall in the current 2021&ndash;2026 cycle; grey-blue bars are earlier rounds.</p>
          <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this chart</summary>
          <div class="chart-commentary">Annual count of countries completing the selected survey instrument, from {A['year_min']} to {CURRENT_YEAR}. Blue bars = current 5-year cycle ({CURRENT_CYCLE_START}&ndash;{CURRENT_YEAR}). Grey-blue bars = prior survey rounds. The blue-shaded zone highlights the current cycle period. Use the filter above to switch between the five WHO NCD surveillance instruments.</div>
          </details>
        </div>
      </div>

      <!-- Instrument completion overview (current cycle) -->
      <div class="section-divider-label">Instrument Activity Cards - Current Cycle {CURRENT_CYCLE_START}&ndash;{CURRENT_YEAR}</div>
      {instrument_cards(A)}

      <!-- Recency matrix -->
      <div class="section-divider-label" style="margin-top:var(--gap-section);">Surveillance Recency Matrix - Country &times; Instrument</div>
      <div class="chart-card reveal">
        <div class="chart-wide">{ch_heatmap}</div>
        <div class="chart-note">
          <p class="chart-takeaway">{tk_matrix}</p>
          <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this chart</summary>
          <div class="chart-commentary"><strong>Surveillance Recency Matrix:</strong> Each cell = year of the most recent <em>completed</em> survey for a given country &times; instrument pair. <span style="display:inline-block;background:var(--rec-none);border-radius:6px;padding:1px 8px;font-size:var(--fs-xs);font-weight:600;color:var(--dark);">Grey</span> = no completed survey on record (never conducted). Blue = current evidence (2021&ndash;2026). Sand = evidence ageing (6&ndash;12 yrs). Red = critically outdated (&gt;12 yrs). Countries sorted top-to-bottom by SPI rank. Grey cells indicate instrument-specific evidence gaps requiring targeted reinvestment.</div>
          </details>
        </div>
      </div>

    </div>
  </div>

  <!-- TAB 4: COUNTRY PROFILE -->
  <div id="tab-profile" class="tab-pane" role="tabpanel" aria-labelledby="tabbtn-tab-profile" tabindex="0">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">4</span>
          <h2 class="section-title">Country Profile</h2>
        </div>
        <p class="section-subtitle">
          Tabs 1&ndash;3 answered whether countries are surveying on schedule. This tab shows what their most recent survey actually found:
          in-depth NCD risk factor data by domain, sex &amp; survey round.
          {_prof_n} countries with STEPS, GYTS and/or GATS indicator data available.
          <span title="GSHS and GSHPP are tracked for surveillance status/cycle (Tabs 1-3, 5) but their indicator-level results are not yet pipelined into this profile view">GSHS and GSHPP results are not yet available at indicator level here</span>
        </p>
        <div class="chart-note">
          <p class="chart-takeaway">STEPS values come from the validated WHO database; GYTS and GATS values are auto-extracted and not yet verified.</p>
          <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this data</summary>
          <div style="background:var(--tint);border:1px solid var(--rule);border-radius:10px;padding:var(--sp-3) var(--sp-4);font-size:var(--fs-sm);color:var(--text);margin-top:var(--sp-4);display:flex;align-items:flex-start;gap:9px;">
          <i class="ti ti-shield" aria-hidden="true" style="margin-top:2px;color:#003d82;"></i>
          <span><strong>Data provenance:</strong> STEPS indicator values are sourced from the WHO validated STEPS database. GYTS and GATS indicator values are extracted programmatically from published country fact-sheet PDFs (gtssacademy.org) via automated table parsing and have not been independently re-verified against the source documents - treat individual GYTS/GATS figures as indicative pending manual spot-check, and note the provenance badge shown on each country's profile below.</span>
        </div>
          </details>
        </div>
      </div>

      {'<div class="profile-no-data" style="padding:40px;text-align:center;color:var(--muted);"><i class="ti ti-database" aria-hidden="true" style="font-size:36px;opacity:.3;margin-bottom:12px;display:block;"></i><p>No indicator data found. Ensure STEP.db and the GYTS/GATS profile JSON files are present in the data/ folder and run the pipeline.</p></div>' if not _prof_countries else ""}

      <div class="filter-bar" style="{'display:none;' if not _prof_countries else ''}">
        <label class="filter-label" for="profile-country-select"><i class="ti ti-map-pin" aria-hidden="true"></i>&nbsp; Country</label>
        <select id="profile-country-select" class="filter-select" style="min-width:270px;">
          {_prof_options}
        </select>
        <label class="filter-label" for="profile-survey-select" style="margin-left:6px;">Survey</label>
        <select id="profile-survey-select" class="filter-select" style="min-width:240px;">
        </select>
        <button id="btn-export-profile" style="font-family:var(--font);font-size:var(--fs-xs);font-weight:700;padding:7px 16px;border-radius:10px;border:none;background:#003d82;color:#fff;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin-left:auto;"><i class="ti ti-file-type-csv" aria-hidden="true"></i>&nbsp;Export CSV</button>
      </div>

      <div id="country-profile-content">
        <div class="profile-no-data">
          <i class="ti ti-pointer" aria-hidden="true" style="font-size:36px;opacity:.25;"></i>
          <p style="font-size:var(--fs-base);font-weight:600;color:var(--text);">Click the <strong>Country Profile</strong> tab to load the selected country</p>
          <p style="font-size:var(--fs-sm);">Select a country from the filter above to explore its full STEPS indicator profile.</p>
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 5: STRATEGIC PRIORITY -->
  <div id="tab-priority" class="tab-pane" role="tabpanel" aria-labelledby="tabbtn-tab-priority" tabindex="0">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">5</span>
          <h2 class="section-title">Strategic Prioritisation</h2>
        </div>
        <p class="section-subtitle">Decision matrix per survey instrument - identify countries requiring immediate support, reactivation, or sustained monitoring</p>
      </div>

      <!-- Survey instrument filter pills -->
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:24px;padding:16px 20px;background:var(--tint);border-radius:16px;border:1px solid var(--rule);box-shadow:0 2px 10px rgba(0,20,80,.06);">
        <span style="font-size:var(--fs-xs);font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.9px;margin-right:4px;white-space:nowrap;"><i class="ti ti-adjustments-horizontal" aria-hidden="true"></i>&nbsp; Survey instrument:</span>
        <button class="prio-pill" data-survey="STEPS"  data-color="#003d82" style="font-family:var(--font);font-size:var(--fs-sm);font-weight:700;padding:8px 20px;border-radius:9999px;border:2px solid #003d82;background:#003d82;color:#fff;cursor:pointer;transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);box-shadow:0 4px 12px rgba(0,61,130,.3);">STEPS</button>
        <button class="prio-pill" data-survey="GYTS"   data-color="#003d82" style="font-family:var(--font);font-size:var(--fs-sm);font-weight:700;padding:8px 20px;border-radius:9999px;border:1px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);">GYTS</button>
        <button class="prio-pill" data-survey="GSHS"   data-color="#003d82" style="font-family:var(--font);font-size:var(--fs-sm);font-weight:700;padding:8px 20px;border-radius:9999px;border:1px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);">GSHS</button>
        <button class="prio-pill" data-survey="GATS"   data-color="#003d82" style="font-family:var(--font);font-size:var(--fs-sm);font-weight:700;padding:8px 20px;border-radius:9999px;border:1px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);">GATS</button>
        <button class="prio-pill" data-survey="GSHPP"  data-color="#003d82" style="font-family:var(--font);font-size:var(--fs-sm);font-weight:700;padding:8px 20px;border-radius:9999px;border:1px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:background-color var(--dur-ui) var(--ease-out),color var(--dur-ui) var(--ease-out),border-color var(--dur-ui) var(--ease-out),transform var(--dur-press) var(--ease-out);">GSHPP</button>
        <input id="pr-search" type="search" name="pr-search" autocomplete="off" spellcheck="false" placeholder="Search country&hellip;" class="filter-input" style="margin-left:auto;width:190px;" aria-label="Search countries across the Strategic Priority tables"/>
        <span id="pr-count" class="filter-count" style="margin-left:0;" aria-live="polite"></span>
      </div>

      <!-- Quadrant scatter chart -->
      <div class="chart-card reveal" style="margin-bottom:24px;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:14px;">
          <div>
            <h3 style="font-size:var(--fs-base);font-weight:700;color:{C['primary']};margin:0 0 4px;"><i class="ti ti-target" aria-hidden="true"></i>&nbsp; Strategic Quadrant Analysis</h3>
            <p style="font-size:var(--fs-xs);color:var(--muted);margin:0;line-height:1.5;">Country position: <strong>survey gap</strong> (x) vs <strong>overall SPI</strong> (y). Drag sliders to redefine quadrant boundaries.</p>
          </div>
          <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:var(--fs-xs);font-weight:600;align-items:center;">
            <span><span style="color:var(--tier-4-ink);font-size:var(--fs-base);">&#9632;</span> URGENT</span>
            <span><span style="color:var(--tier-3-ink);font-size:var(--fs-base);">&#9632;</span> REINVEST</span>
            <span><span style="color:var(--tier-2-ink);font-size:var(--fs-base);">&#9632;</span> DEVELOP</span>
            <span><span style="color:var(--tier-1-ink);font-size:var(--fs-base);">&#9632;</span> SUSTAIN</span>
          </div>
        </div>
        <!-- Movable threshold sliders -->
        <div class="prio-sliders" style="display:flex;gap:32px;flex-wrap:wrap;align-items:center;padding:12px 16px;background:var(--tint);border-radius:10px;margin-bottom:14px;border:1px solid var(--rule);">
          <div style="display:flex;align-items:center;gap:10px;">
            <i class="ti ti-arrows-horizontal" aria-hidden="true" style="color:var(--dark);font-size:var(--fs-base);"></i>
            <span style="font-size:var(--fs-xs);font-weight:700;color:{C['primary']};white-space:nowrap;">Gap threshold:</span>
            <input type="range" id="prio-gap-cut" min="1" max="35" value="5" aria-label="Gap threshold in years"
              style="width:130px;accent-color:#003d82;cursor:pointer;"/>
            <span style="font-size:var(--fs-base);font-weight:800;color:#003d82;min-width:38px;"><span id="prio-gap-val">5</span>&nbsp;yrs</span>
          </div>
          <div class="slider-sep" style="width:1px;height:28px;background:var(--rule);"></div>
          <div style="display:flex;align-items:center;gap:10px;">
            <i class="ti ti-arrows-vertical" aria-hidden="true" style="color:var(--dark);font-size:var(--fs-base);"></i>
            <span style="font-size:var(--fs-xs);font-weight:700;color:{C['primary']};white-space:nowrap;">SPI threshold:</span>
            <input type="range" id="prio-spi-cut" min="5" max="95" value="50" aria-label="SPI threshold in points"
              style="width:130px;accent-color:#003d82;cursor:pointer;"/>
            <span style="font-size:var(--fs-base);font-weight:800;color:#003d82;min-width:38px;"><span id="prio-spi-val">50</span>&nbsp;pts</span>
          </div>
          <span class="slider-hint" style="font-size:var(--fs-xs);color:var(--muted);font-style:italic;margin-left:auto;"><i class="ti ti-hand-click" aria-hidden="true"></i>&nbsp; Sliders update the chart in real time</span>
        </div>
        <div class="chart-wide"><div id="prio-scatter-chart" style="height:490px;width:100%;"></div></div>
        <div class="chart-note">
          <p class="chart-takeaway">Quadrants rank the need for surveillance re-engagement, not disease burden.</p>
          <details class="chart-about"><summary><i class="ti ti-chevron-right" aria-hidden="true"></i>About this chart</summary>
          <div style="font-size:var(--fs-xs);color:var(--muted);margin-top:10px;line-height:1.6;padding:8px 12px;background:var(--tint);border:1px solid var(--rule);border-radius:6px;">
          <i class="ti ti-info-circle" aria-hidden="true" style="color:var(--brand);"></i>&nbsp;
          Quadrant position reflects <strong>surveillance gap and SPI only</strong> - a tool for prioritizing surveillance re-engagement, consistent with this platform's scope (surveillance instruments and the prevalence indicators they produce, not disease burden). The dot color/shape (survey status for the instrument selected below) can disagree with the quadrant a country falls into, since SPI is computed across all five instruments while the gap axis is instrument-specific.
        </div>
          </details>
        </div>
      </div>

      <!-- Per-instrument operational detail -->
      <div class="section-divider-label">Country-Level Operational Detail</div>
      {survey_sections}

    </div>
  </div>

  <!-- TAB 6: METHODS -->
  <div id="tab-methods" class="tab-pane" role="tabpanel" aria-labelledby="tabbtn-tab-methods" tabindex="0">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">6</span>
          <h2 class="section-title">Methodology &amp; Definitions</h2>
        </div>
        <p class="section-subtitle">Analytical framework, key definitions, and data model underpinning this platform</p>
      </div>

      <div class="methods-grid" style="grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px;">

        <!-- Data Source -->
        <div class="method-card reveal" style="border-top:4px solid #003d82;">
          <h3 style="color:#003d82;"><i class="ti ti-world" aria-hidden="true"></i>&nbsp; Data Source</h3>
          <ul>
            <li><strong>Source:</strong> WHO Noncommunicable Diseases Country Tracking (surveillance status &amp; cycle metadata); STEPS indicator values from the WHO validated STEPS database; GYTS/GATS indicator values extracted from published country fact sheets on <a href="https://gtssacademy.org/" target="_blank" rel="noopener">gtssacademy.org</a></li>
            <li><strong>Coverage:</strong> {n_ent} entities (47 WHO AFRO Member States + Zanzibar)</li>
            <li><strong>Instruments:</strong> 5 NCD population-based surveillance systems</li>
            <li><strong>Period:</strong> {A['year_min']}&ndash;{CURRENT_YEAR} &nbsp;&middot;&nbsp; {A['n_records']} survey records</li>
            <li><strong>Compiled:</strong> {REPORT_DATE}</li>
          </ul>
        </div>

        <!-- SPI -->
        <div class="method-card reveal" style="border-top:4px solid var(--brand);">
          <h3 style="color:var(--brand);"><i class="ti ti-gauge" aria-hidden="true"></i>&nbsp; Surveillance Performance Index (SPI)</h3>
          <p style="font-size:var(--fs-sm);color:var(--muted);margin-bottom:12px;line-height:1.8;">
            The SPI is a composite score from <strong>0 to 100</strong> that summarises how well a country&rsquo;s NCD surveillance system is performing across three equally weighted dimensions. It is designed for <strong>relative ranking and trend monitoring</strong> across WHO AFRO Member States.
          </p>
          <ul>
            <li style="margin-bottom:8px;"><strong style="color:#003d82;">Breadth:</strong> Has the country ever completed each of the five NCD surveillance instruments? A country that has used more instruments scores higher on this dimension, reflecting the <em>institutional range</em> of its surveillance system.</li>
            <li style="margin-bottom:8px;"><strong style="color:#003d82;">Currency:</strong> How recent is the available evidence? Older surveys contribute progressively less, with evidence value halving every 5 years - the WHO-recommended survey cycle, so a survey exactly at the cycle boundary carries half credit. This dimension rewards countries that keep their data fresh and penalises those whose most recent survey is distant in time.</li>
            <li><strong style="color:#003d82;">Regularity:</strong> Does the country survey on schedule? Countries that complete each instrument close to the WHO-recommended five-year cycle score well. This dimension is only applicable when a country has conducted a given instrument at least twice, as a single round is not enough to assess cycling behaviour.</li>
          </ul>
          <p style="font-size:var(--fs-xs);color:var(--muted);margin-top:12px;margin-bottom:12px;line-height:1.75;font-style:italic;">
            The three dimensions are equally weighted and combined into a single score. Countries that have never conducted any survey score zero. Countries with broad, current, and regular surveillance score toward 100.
          </p>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <span class="tier-badge t1" style="padding:3px 10px;">Strong &#8805;75</span>
            <span class="tier-badge t2" style="padding:3px 10px;">Advancing 50&ndash;74</span>
            <span class="tier-badge t3" style="padding:3px 10px;">Developing 30&ndash;49</span>
            <span class="tier-badge t4" style="padding:3px 10px;">Critical &lt;30</span>
          </div>
        </div>

        <!-- Surveillance Status -->
        <div class="method-card reveal" style="border-top:4px solid var(--brand);">
          <h3 style="color:var(--brand);"><i class="ti ti-satellite" aria-hidden="true"></i>&nbsp; Surveillance Status Categories</h3>
          <p style="font-size:var(--fs-sm);color:var(--muted);margin-bottom:10px;line-height:1.7;">
            Each country is assigned exactly <strong>one status per survey instrument</strong>. Categories are mutually exclusive and exhaustive; all 48 entities are covered. This is the single vocabulary used throughout the platform - Executive Overview, Strategic Priority tables, and here.
          </p>
          <ul>
            <li><strong style="color:{st_on};">On Cycle:</strong> Completed within the last 5 years. Evidence is current and policy-usable.</li>
            <li><strong style="color:{st_att};">Attempt to update:</strong> Prior completed evidence exists and a new survey round is actively in progress.</li>
            <li><strong style="color:{st_off};">Off Cycle:</strong> Has completed before but no current survey process is active. Surveillance is idle and evidence is ageing.</li>
            <li><strong style="color:{st_first};">First Attempt:</strong> No completed survey on record, but a first-ever round is actively in progress. Kept distinct from Never Conducted so active first-time engagement is not scored the same as no engagement at all.</li>
            <li><strong style="color:{st_nev};">Never Conducted:</strong> No completed survey and nothing currently in progress - the region's most severe evidence gap.</li>
          </ul>
        </div>

        <!-- Instruments -->
        <div class="method-card reveal" style="border-top:4px solid var(--brand);">
          <h3 style="color:var(--brand);"><i class="ti ti-flask" aria-hidden="true"></i>&nbsp; The 5 Population-Based Surveillance Instruments</h3>
          <ul>
            <li><strong style="color:#003d82;">STEPS:</strong> WHO STEPwise Approach to NCD Risk Factor Surveillance, adults 18-69, NCD risk factors (flagship instrument)</li>
            <li><strong style="color:var(--brand);">GYTS:</strong> Global Youth Tobacco Survey, students 13-15, youth tobacco use</li>
            <li><strong style="color:var(--brand);">GSHS:</strong> Global School-based Student Health Survey, students 13-17, youth health behaviours</li>
            <li><strong style="color:var(--brand);">GATS:</strong> Global Adult Tobacco Survey, adults 15 years and older, adult tobacco and cessation</li>
            <li><strong style="color:var(--brand);">GSHPP:</strong> Global School Health Policies and Practices, school level, health policy environment</li>
          </ul>
          <p style="font-size:var(--fs-xs);color:var(--muted);margin-top:10px;line-height:1.6;">All instruments operate on a WHO-recommended 5-year renewal cycle. Countries are expected to complete a new round within each 5-year window to maintain current population-based surveillance intelligence.</p>
        </div>

        <!-- Limitations -->
        <div class="method-card reveal" style="border-top:4px solid var(--brand);">
          <h3 style="color:var(--brand);"><i class="ti ti-alert-triangle" aria-hidden="true"></i>&nbsp; Analytical Notes &amp; Limitations</h3>
          <ul>
            <li><strong>Unit of analysis:</strong> Country/territory (N=48). Sub-national units are not tracked.</li>
            <li><strong>Data currency:</strong> Status reflects the most recent available WHO tracking data. In-progress surveys may have completed since last extraction.</li>
            <li><strong>Regularity dimension:</strong> Requires &#8805;&nbsp;2 completed rounds per instrument. Countries with a single completion score zero on Regularity by methodology, not by performance failure - this still enters the SPI average at full weight.</li>
            <li><strong>Gap calculation:</strong> Computed relative to {CURRENT_YEAR}. Countries with only &ldquo;Not Usable&rdquo; records are treated as having no completed survey.</li>
            <li><strong>SPI interpretation:</strong> The index is a point estimate designed for relative ranking and trend monitoring, not for absolute quality assessment of individual surveys, and carries no confidence interval.</li>
            <li><strong>Regional averages:</strong> Regional SPI mean/median are unweighted by population. Zanzibar and mainland Tanzania are tracked as two separate entities sharing one ISO3 code.</li>
            <li><strong>School-based instruments:</strong> GYTS and GSHS sample <em>school-attending</em> students only; out-of-school youth - often at higher risk - are not represented in these instruments' results.</li>
            <li><strong>Response rates:</strong> Not consistently available in the source data for every survey round; where absent, no response-rate quality signal is shown rather than assuming full compliance.</li>
            <li><strong>Scope, by design:</strong> This platform tracks surveillance <em>instruments</em> - whether a survey happened, how current it is, and the prevalence indicators it produced. It does not model disease, mortality, or burden (e.g. GBD/DALYs); that is a distinct data domain outside this platform's remit. A high SPI reflects a well-run surveillance system, not low NCD risk in that country, and a low SPI reflects a surveillance gap, not necessarily high NCD risk.</li>
            <li><strong>Strategic Priority quadrant:</strong> Ranks countries by surveillance gap and SPI only, consistent with the platform's scope above - it is a surveillance re-engagement tool, not a health-burden prioritization tool, and should not be read as one.</li>
          </ul>
        </div>

        <!-- WHO Global Monitoring Framework -->
        <div class="method-card reveal" style="border-top:4px solid var(--brand);">
          <h3 style="color:var(--brand);"><i class="ti ti-link" aria-hidden="true"></i>&nbsp; Link to WHO Global Monitoring Framework &amp; SDG 3.4</h3>
          <p style="font-size:var(--fs-sm);color:var(--muted);line-height:1.7;">
            These five instruments are the primary country-level data sources feeding the WHO Global Monitoring Framework on NCDs and SDG target 3.4 (reduce premature NCD mortality by one third by 2030). STEPS and GATS underpin indicators on tobacco use, blood pressure, glucose and obesity (SDG 3.a.1, 3.4.1 risk-factor inputs); GYTS and GSHS track youth risk-factor uptake; GSHPP tracks the school policy environment enabling prevention. Surveillance breadth, currency and regularity - as measured by the SPI - are therefore a proxy for a country's capacity to report against these global commitments, not for its NCD burden itself.
          </p>
        </div>


      </div>

    </div>
  </div>

</main><!-- /container -->

<footer class="footer">
  <div class="footer-inner">
    <div style="display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
      {who_footer_tag}
      <div style="width:1px;height:40px;background:rgba(255,255,255,.18);"></div>
      {dpc_footer_tag}
      <div style="width:1px;height:40px;background:rgba(255,255,255,.18);"></div>
      <div>
        <div style="font-size:var(--fs-sm);font-weight:600;color:rgba(255,255,255,.9);line-height:1.6;">
          &copy; {CURRENT_YEAR} WHO African Region &ndash; Health Promotion / Disease Prevention and Control (DPC) Cluster
        </div>
      </div>
    </div>
  </div>
</footer>

<button id="back-to-top" aria-label="Back to top"><i class="ti ti-arrow-up" aria-hidden="true"></i></button>
<script>{js_with_data}</script>
</body>
</html>"""
