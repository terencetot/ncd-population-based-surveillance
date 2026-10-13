"""
NCD Surveillance Intelligence Platform - WHO African Region
Configuration: constants, palette, survey metadata
"""
from pathlib import Path
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR     = Path(__file__).parent.parent
DATA_DIR     = ROOT_DIR / "data"
ASSETS_DIR   = ROOT_DIR / "assets"
OUTPUT_DIR   = ROOT_DIR / "output"

EXCEL_PATH    = DATA_DIR  / "NCD_Surveillance_Survey_AFRO_dataset.xlsx"
STEPS_DB_PATH = DATA_DIR  / "STEP.db"
GYTS_JSON_PATH = DATA_DIR / "gyts_country_profile.json"
GATS_JSON_PATH = DATA_DIR / "gats_country_profile.json"
DB_PATH       = OUTPUT_DIR / "ncd_surveillance.db"
OUTPUT_PATH   = OUTPUT_DIR / "NCD_AFRO_Dashboard.html"

REPORT_DATE  = datetime.now().strftime("%d %B %Y")

# ── Surveillance cycle ─────────────────────────────────────────────────────────
CURRENT_YEAR        = 2026
CYCLE_YEARS         = 5
CURRENT_CYCLE_START = CURRENT_YEAR - CYCLE_YEARS    # 2021
PREV_CYCLE_START    = CURRENT_CYCLE_START - CYCLE_YEARS  # 2016

# ── SPI weights (3 dimensions - must sum to 1.0) ──────────────────────────────
# B Coverage    (33.333%) : breadth across 5 instrument types
# R Recency     (33.333%) : step function on gap since last completed survey
# D Regularity  (33.334%) : average renewal cycle interval vs 5-yr standard
SPI_W = {"coverage": 1/3, "recency": 1/3, "regularity": 1/3}

# ══ COLOUR SYSTEM ═════════════════════════════════════════════════════════════
# One system, one rule: colour encodes EVIDENCE QUALITY and nothing else.
#   blue        current / strong evidence   (the WHO anchor carries "good")
#   sand        ageing evidence
#   amber, red  concern, critical
#   grey        absence of evidence
#   texture     a survey round is in progress (hatch = updating, dots = first ever)
# Everything non-semantic (instruments, indicator domains, chrome) is WHO navy,
# so hue is never spent on decoration and never means two things.
#
# Built for colour-vision deficiency: every status/tier pair is separated on
# the two axes that survive protan-, deutan- and tritanopia (lightness and
# blue<->yellow), verified with Machado-2009 simulation: min OKLab dE >= 9.4
# between statuses under protan/deutan (6.8 under tritan, where First Attempt
# also carries its dot pattern) and >= 19 between tiers. The two
# in-progress statuses also carry a fill pattern, so greyscale print stays
# unambiguous. Each colour has a FILL (marks, bars, swatches) and an INK
# (text on white, >= 4.5:1). Text on a fill uses *_ON.
#
# report.py emits all of this as CSS custom properties and a JS object, so
# server-rendered HTML, Plotly figures and client-side charts share one source.

BRAND = {
    "navy":     "#003d82",   # WHO AFRO navy - actions, headings, non-semantic marks
    "who_blue": "#009ade",   # WHO blue (Pantone 2925) - accent hairlines, focus
    "ink":      "#0d1f4e",   # darkest text / text on light fills
    "text":     "#1e2a4a", "muted": "#5b6577",
    "border":   "#e4e7ef", "canvas": "#f6f7fb", "surface": "#ffffff",
    "tint":     "#eef3fa",   # navy-tinted panel background
    "rule":     "#c9d3e3",   # neutral chart rules / gridlines
}

# Evidence primitives (shared by status, tier and recency)
_BLUE, _BLUE_LT, _SAND, _AMBER, _RED, _SLATE, _GREY = (
    "#1f5fa8", "#86b6e0", "#d8b863", "#e0932e", "#c4432b", "#636f84", "#d3d8e0")

# ── Performance tiers (ordinal ramp: blue -> amber -> red) ────────────────────
TIER_LABELS = {1: "Strong", 2: "Advancing", 3: "Developing", 4: "Critical"}
TIER_COLORS = {1: _BLUE, 2: _BLUE_LT, 3: _AMBER, 4: _RED}
TIER_INK    = {1: "#1f5fa8", 2: "#2f6ba8", 3: "#8a5a00", 4: "#b13a24"}
TIER_ON     = {1: "#ffffff", 2: BRAND["ink"], 3: BRAND["ink"], 4: "#ffffff"}
TIER_CUTS   = (75, 50, 30)   # must match analytics.py tier assignment

def tier_of(spi: float) -> int:
    return 1 if spi >= TIER_CUTS[0] else 2 if spi >= TIER_CUTS[1] else 3 if spi >= TIER_CUTS[2] else 4

# ── Surveillance cycle status (single source of truth, used everywhere: KPI
#    cards, bars, scatter, per-instrument tables, briefings). Named distinctly
#    from STATUS_COLORS below (raw ETL record status: Completed/In Progress/
#    Not Usable) - different concept, would otherwise collide on import. ──────
CYCLE_STATUS_LABELS = ["On Cycle", "Attempt to update", "Off Cycle", "First Attempt", "Never Conducted"]
CYCLE_STATUS_COLORS = {                       # FILL
    "On Cycle":          _BLUE,     # current, usable evidence (= Strong)
    "Attempt to update": "#7fb2e5", # prior evidence + new round in progress (hatched)
    "Off Cycle":         _SAND,     # evidence exists but ageing, nothing active
    "First Attempt":     _SLATE,    # no evidence yet, first-ever round in progress (dotted)
    "Never Conducted":   _GREY,     # no evidence (never red: red is the Critical tier)
}
CYCLE_STATUS_INK = {
    "On Cycle": "#1f5fa8", "Attempt to update": "#2a6aa6", "Off Cycle": "#7a5c0e",
    "First Attempt": "#4f5a6e", "Never Conducted": "#5b6475",
}
CYCLE_STATUS_ON = {
    "On Cycle": "#ffffff", "Attempt to update": BRAND["ink"], "Off Cycle": BRAND["ink"],
    "First Attempt": "#ffffff", "Never Conducted": BRAND["ink"],
}
# Plotly marker.pattern shapes - the non-colour cue for "in progress"
CYCLE_STATUS_PATTERN = {"Attempt to update": "/", "First Attempt": "."}
CYCLE_STATUS_PATTERN_FG = {"Attempt to update": "#1f5fa8", "First Attempt": "#ffffff"}

# ── Recency (years since last completed survey) ───────────────────────────────
# One step function, used by the recency matrix, the gap bars and every
# threshold line. <=5 yr IS the On Cycle definition, so it wears On Cycle blue.
RECENCY_NONE  = _GREY
# Three bands, named in the platform's own vocabulary:
#   0-5 yr  On Cycle (the status definition)   6-12 yr  Off Cycle   >12 yr  Critical
# "No record" (never conducted) is NOT critical: it is the grey of absence.
RECENCY_STEPS = [   # (max gap inclusive, fill, ink, label)
    (5,    _BLUE,  "#1f5fa8", "On Cycle (0-5 yr)"),
    (12,   _SAND,  "#7a5c0e", "Off Cycle (6-12 yr)"),
    (999,  _RED,   "#b13a24", "Critical (>12 yr)"),
]
RECENCY_THRESHOLDS = (5, 12)   # band edges drawn as reference lines

def recency_color(gap, ink: bool = False) -> str:
    if gap is None or gap != gap:   # None or NaN
        return "#5b6475" if ink else RECENCY_NONE
    for hi, fill, ink_c, _ in RECENCY_STEPS:
        if gap <= hi:
            return ink_c if ink else fill
    return RECENCY_STEPS[-1][2 if ink else 1]

# ── UI colour palette (legacy keys kept; semantic keys now point at the system)
C = {
    "primary":   BRAND["navy"], "secondary": "#006eb6",
    "accent":    BRAND["who_blue"], "success": TIER_INK[1],
    "warning":   TIER_INK[3],   "danger":    TIER_INK[4],
    "light":     "#f9fbff",     "white":     "#ffffff",
    "dark":      BRAND["ink"],  "text":      BRAND["text"],
    "muted":     BRAND["muted"], "border":   BRAND["border"],
}

# ── Design-system scale tokens (fonts / radii / motion) - Phase 4 ────────────
FS = {  # font-size scale: micro/body/lead/h3/h2/display
    "micro": "11px", "body": "12px", "lead": "14px",
    "h3": "16px", "h2": "22px", "display": "34px",
}
RADIUS = {"sm": "6px", "md": "10px", "lg": "16px"}
DUR = {"micro": "120ms", "block": "240ms"}
EASE = "cubic-bezier(.4,0,.2,1)"

FONT = "'Source Sans 3', 'Segoe UI', system-ui, -apple-system, sans-serif"

# ── Status mapping ─────────────────────────────────────────────────────────────
STATUS_MAP = {
    "Completed (At least data analysis completed)": "Completed",
    "In progress": "In Progress",
    "Data not usable": "Not Usable",
}
STATUS_COLORS = {   # raw record status, mapped onto the evidence system
    "Completed":  BRAND["navy"],
    "In Progress":CYCLE_STATUS_COLORS["Attempt to update"],
    "Not Usable": CYCLE_STATUS_COLORS["Never Conducted"],
}

# ── Survey instrument metadata ─────────────────────────────────────────────────
SURVEY_META = {
    "STEPS":  {"full": "STEPwise Approach to NCD Risk Factor Surveillance",
               "target": "Adults 18–69",  "domain": "NCD risk factors",   "color": BRAND["navy"]},
    "GYTS":   {"full": "Global Youth Tobacco Survey",
               "target": "School-attending students 13–15", "domain": "Youth tobacco",     "color": BRAND["navy"]},
    "GSHS":   {"full": "Global School-based Student Health Survey",
               "target": "School-attending students 13–17", "domain": "Youth health",      "color": BRAND["navy"]},
    "GATS":   {"full": "Global Adult Tobacco Survey",
               "target": "Adults 15+",    "domain": "Adult tobacco",      "color": BRAND["navy"]},
    "GSHPP":  {"full": "Global School Health Policies and Practices",
               "target": "School level",  "domain": "School health policy","color": BRAND["navy"]},
}

# ── ISO codes ──────────────────────────────────────────────────────────────────
ISO_CODES = {
    "Algeria":"DZA","Angola":"AGO","Benin":"BEN","Botswana":"BWA","Burkina Faso":"BFA",
    "Burundi":"BDI","Cabo Verde":"CPV","Cameroon":"CMR","Central African Republic":"CAF",
    "Chad":"TCD","Comoros":"COM","Congo":"COG","Cote d'Ivoire":"CIV","Côte d'Ivoire":"CIV",
    "Democratic Republic of the Congo":"COD","Equatorial Guinea":"GNQ","Eritrea":"ERI",
    "Eswatini":"SWZ","Ethiopia":"ETH","Gabon":"GAB","Gambia":"GMB","Ghana":"GHA",
    "Guinea":"GIN","Guinea-Bissau":"GNB","Kenya":"KEN","Lesotho":"LSO","Liberia":"LBR",
    "Madagascar":"MDG","Malawi":"MWI","Mali":"MLI","Mauritania":"MRT","Mauritius":"MUS",
    "Mozambique":"MOZ","Namibia":"NAM","Niger":"NER","Nigeria":"NGA","Rwanda":"RWA",
    "Sao Tome and Principe":"STP","Senegal":"SEN","Seychelles":"SYC","Sierra Leone":"SLE",
    "South Africa":"ZAF","South Sudan":"SSD","Togo":"TGO","Uganda":"UGA",
    "United Republic of Tanzania":"TZA","Zambia":"ZMB","Zanzibar":"TZA","Zimbabwe":"ZWE",
}
