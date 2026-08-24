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

# ── Performance tiers ─────────────────────────────────────────────────────────
# The green→amber→red performance ramp is reserved EXCLUSIVELY for SPI tiers
# and gap severity. Surveillance STATUS (below) deliberately uses a distinct
# palette family so a reader moving between the Performance tab and any
# status view is never shown the same colour meaning two different things.
TIER_LABELS = {1: "Strong", 2: "Advancing", 3: "Developing", 4: "Critical"}
TIER_COLORS = {1: "#00a651", 2: "#4a90e2", 3: "#f7941d", 4: "#c0392b"}

# ── Surveillance cycle status (single source of truth, used everywhere: KPI
#    cards, donut, scatter, per-instrument tables, briefings). Named distinctly
#    from STATUS_COLORS below (raw ETL record status: Completed/In Progress/
#    Not Usable) — different concept, would otherwise collide on import. ──────
CYCLE_STATUS_LABELS = ["On Cycle", "Attempt to update", "Off Cycle", "First Attempt", "Never Conducted"]
CYCLE_STATUS_COLORS = {
    "On Cycle":          "#0d9488",   # teal    - current, usable evidence
    "Attempt to update": "#7c3aed",   # violet  - actively updating
    "Off Cycle":         "#d97706",   # amber   - idle, ageing
    "First Attempt":     "#0891b2",   # cyan    - no prior evidence, but fielding a first-ever round now
    "Never Conducted":   "#64748b",   # slate   - no evidence (never red: red is reserved for URGENT/Critical tier)
}

# ── UI colour palette ─────────────────────────────────────────────────────────
C = {
    "primary":   "#003d82", "secondary": "#006eb6",
    "accent":    "#4a90e2", "success":   "#00a651",
    "warning":   "#f7941d", "danger":    "#c0392b",
    "light":     "#f9fbff", "white":     "#ffffff",
    "dark":      "#14265c", "text":      "#333e5c",
    "muted":     "#6b7280", "border":    "#e2e8f0",
}

# ── Design-system scale tokens (fonts / radii / motion) — Phase 4 ────────────
FS = {  # font-size scale: micro/body/lead/h3/h2/display
    "micro": "11px", "body": "12px", "lead": "14px",
    "h3": "16px", "h2": "22px", "display": "34px",
}
RADIUS = {"sm": "6px", "md": "10px", "lg": "16px"}
DUR = {"micro": "120ms", "block": "240ms"}
EASE = "cubic-bezier(.4,0,.2,1)"

FONT = "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# ── Status mapping ─────────────────────────────────────────────────────────────
STATUS_MAP = {
    "Completed (At least data analysis completed)": "Completed",
    "In progress": "In Progress",
    "Data not usable": "Not Usable",
}
STATUS_COLORS = {
    "Completed":  "#00a651",
    "In Progress":"#f7941d",
    "Not Usable": "#c0392b",
}

# ── Survey instrument metadata ─────────────────────────────────────────────────
SURVEY_META = {
    "STEPS":  {"full": "STEPwise Approach to NCD Risk Factor Surveillance",
               "target": "Adults 18–69",  "domain": "NCD risk factors",   "color": "#003d82"},
    "GYTS":   {"full": "Global Youth Tobacco Survey",
               "target": "School-attending students 13–15", "domain": "Youth tobacco",     "color": "#c0392b"},
    "GSHS":   {"full": "Global School-based Student Health Survey",
               "target": "School-attending students 13–17", "domain": "Youth health",      "color": "#f7941d"},
    "GATS":   {"full": "Global Adult Tobacco Survey",
               "target": "Adults 15+",    "domain": "Adult tobacco",      "color": "#8e44ad"},
    "GSHPP":  {"full": "Global School Health Policies and Practices",
               "target": "School level",  "domain": "School health policy","color": "#00a651"},
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
