"""
NCD Surveillance Intelligence Platform — WHO African Region
ETL Pipeline: Excel → SQLite star schema
"""
import sqlite3
import pandas as pd
from pathlib import Path
from src.config import (EXCEL_PATH, DB_PATH, OUTPUT_DIR, STATUS_MAP, STATUS_COLORS,
                        SURVEY_META, ISO_CODES, CURRENT_YEAR, CYCLE_YEARS,
                        CURRENT_CYCLE_START, PREV_CYCLE_START, STEPS_DB_PATH)

# Ensure output directory exists when module is loaded
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STEPS_DDL = """
-- ── STEPS Sections ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS steps_section (
    section_id   INTEGER PRIMARY KEY,
    section_code TEXT NOT NULL UNIQUE,
    who_step     TEXT,
    section_name TEXT NOT NULL
);

-- ── STEPS Indicators ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS steps_indicator (
    indicator_id    INTEGER PRIMARY KEY,
    indicator_code  TEXT NOT NULL UNIQUE,
    section_id      INTEGER REFERENCES steps_section(section_id),
    label_en        TEXT NOT NULL,
    unit_sym        TEXT DEFAULT '%',
    higher_is_better INTEGER
);

-- ── STEPS Survey metadata ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS steps_survey (
    steps_survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id      INTEGER REFERENCES dim_country(country_id),
    survey_year     INTEGER NOT NULL,
    sample_size     INTEGER,
    response_rate   REAL,
    source_country  TEXT,
    UNIQUE(country_id, survey_year)
);

-- ── STEPS Measurements ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS steps_measurement (
    meas_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    steps_survey_id INTEGER REFERENCES steps_survey(steps_survey_id),
    indicator_id    INTEGER REFERENCES steps_indicator(indicator_id),
    sex             TEXT NOT NULL DEFAULT 'both_sexes',
    value           REAL,
    ci_lower        REAL,
    ci_upper        REAL
);
"""

DDL = """
-- ── Dimension: Countries ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_country (
    country_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    country_name TEXT    NOT NULL UNIQUE,
    iso3         TEXT,
    is_zanzibar  INTEGER DEFAULT 0,
    sub_region   TEXT    DEFAULT 'AFRO'
);

-- ── Dimension: Survey Types ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_survey_type (
    survey_type_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_code       TEXT NOT NULL UNIQUE,
    survey_full_name  TEXT,
    target_population TEXT,
    domain            TEXT,
    cycle_years       INTEGER DEFAULT 5
);

-- ── Dimension: Status ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_status (
    status_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    status_code       TEXT    NOT NULL UNIQUE,
    status_label      TEXT,
    is_completed      INTEGER DEFAULT 0,
    completion_weight REAL    DEFAULT 0.0
);

-- ── Dimension: Year ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_year (
    year_id          INTEGER PRIMARY KEY,
    year             INTEGER NOT NULL UNIQUE,
    decade           TEXT,
    five_yr_period   TEXT,
    cycle_label      TEXT
);

-- ── Fact: Surveys ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_surveys (
    survey_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id     INTEGER NOT NULL REFERENCES dim_country(country_id),
    survey_type_id INTEGER NOT NULL REFERENCES dim_survey_type(survey_type_id),
    year_id        INTEGER NOT NULL REFERENCES dim_year(year_id),
    status_id      INTEGER NOT NULL REFERENCES dim_status(status_id),
    survey_year    INTEGER NOT NULL,
    UNIQUE (country_id, survey_type_id, survey_year)
);

-- ── Extensibility: Indicator dimension (future) ──────────────────────────────
CREATE TABLE IF NOT EXISTS dim_indicator (
    indicator_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_code TEXT NOT NULL UNIQUE,
    indicator_name TEXT,
    survey_type_id INTEGER REFERENCES dim_survey_type(survey_type_id),
    unit           TEXT,
    direction      TEXT DEFAULT 'lower_better'
);

-- ── Extensibility: Indicator facts (future) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_indicators (
    fact_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id   INTEGER REFERENCES dim_country(country_id),
    indicator_id INTEGER REFERENCES dim_indicator(indicator_id),
    year_id      INTEGER REFERENCES dim_year(year_id),
    value        REAL,
    ci_lower     REAL,
    ci_upper     REAL,
    sex          TEXT DEFAULT 'Both'
);
"""


def _cycle_label(yr):
    if yr >= CURRENT_CYCLE_START:
        return f"{CURRENT_CYCLE_START}–{CURRENT_YEAR}"
    elif yr >= PREV_CYCLE_START:
        return f"{PREV_CYCLE_START}–{CURRENT_CYCLE_START - 1}"
    elif yr >= 2011:
        return "2011–2015"
    elif yr >= 2006:
        return "2006–2010"
    elif yr >= 2001:
        return "2001–2005"
    else:
        return "≤2000"


def etl_pipeline(excel_path: Path, db_path: Path) -> None:
    """Extract → Transform → Load into SQLite star schema."""

    # ── 1. Extract ────────────────────────────────────────────────────────────
    df = pd.read_excel(excel_path, sheet_name="Survey_Data", engine="openpyxl")

    # ── 2. Transform ──────────────────────────────────────────────────────────
    df = df.rename(columns={"NCD Surveillance status": "raw_status"})
    df["status_code"] = df["raw_status"].map(STATUS_MAP).fillna("Unknown")
    df["iso3"]        = df["country_normalized"].map(ISO_CODES)
    df["is_zanzibar"] = (df["country_normalized"] == "Zanzibar").astype(int)
    df["decade"]      = (df["survey_year"] // 10 * 10).astype(str) + "s"
    df["five_yr"]     = ((df["survey_year"] - 1999) // 5 * 5 + 1999).astype(int)
    df["five_yr_lbl"] = df["survey_year"].apply(
        lambda y: f"{(y//5)*5}–{(y//5)*5+4}")
    df["cycle_label"] = df["survey_year"].apply(_cycle_label)

    # ── 3. Load ───────────────────────────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(DDL)

    # Clear fact table before reload; replace dim_country to pick up ISO3 changes
    conn.execute("DELETE FROM fact_surveys;")
    conn.execute("DELETE FROM dim_country;")

    # dim_country
    for _, row in df[["country_normalized", "iso3", "is_zanzibar"]].drop_duplicates().iterrows():
        conn.execute(
            "INSERT INTO dim_country (country_name, iso3, is_zanzibar) VALUES (?,?,?)",
            (row["country_normalized"], row["iso3"], int(row["is_zanzibar"]))
        )

    # dim_survey_type
    for code, meta in SURVEY_META.items():
        conn.execute("""
            INSERT OR IGNORE INTO dim_survey_type
              (survey_code, survey_full_name, target_population, domain, cycle_years)
            VALUES (?,?,?,?,?)""",
            (code, meta["full"], meta["target"], meta["domain"], 5)
        )

    # dim_status
    status_defs = [
        ("Completed",   "Completed",    1, 1.0),
        ("In Progress", "In Progress",  0, 0.0),
        ("Not Usable",  "Not Usable",   0, 0.0),
        ("Unknown",     "Unknown",      0, 0.0),
    ]
    for sc, sl, ic, cw in status_defs:
        conn.execute(
            "INSERT OR IGNORE INTO dim_status (status_code,status_label,is_completed,completion_weight) VALUES (?,?,?,?)",
            (sc, sl, ic, cw)
        )

    # dim_year
    for yr in sorted(df["survey_year"].unique()):
        yr = int(yr)
        conn.execute("""
            INSERT OR IGNORE INTO dim_year (year_id, year, decade, five_yr_period, cycle_label)
            VALUES (?,?,?,?,?)""",
            (yr, yr,
             str(yr // 10 * 10) + "s",
             f"{(yr//5)*5}–{(yr//5)*5+4}",
             _cycle_label(yr))
        )

    # fact_surveys
    cid_map  = {r[0]: r[1] for r in conn.execute("SELECT country_name, country_id FROM dim_country")}
    stid_map = {r[0]: r[1] for r in conn.execute("SELECT survey_code, survey_type_id FROM dim_survey_type")}
    sid_map  = {r[0]: r[1] for r in conn.execute("SELECT status_code, status_id FROM dim_status")}

    rows = []
    for _, r in df.iterrows():
        cid  = cid_map.get(r["country_normalized"])
        stid = stid_map.get(r["survey_type"])
        yid  = int(r["survey_year"])
        sid  = sid_map.get(r["status_code"])
        if cid and stid and yid and sid:
            rows.append((cid, stid, yid, sid, yid))

    conn.executemany(
        "INSERT OR IGNORE INTO fact_surveys (country_id,survey_type_id,year_id,status_id,survey_year) VALUES (?,?,?,?,?)",
        rows
    )
    conn.commit()
    conn.close()


def etl_steps_indicators(steps_db_path: Path, ncd_db_path: Path) -> int:
    """
    Merge STEPS indicator data from STEP.db into ncd_surveillance.db.
    Links countries via ISO3 code; handles Zanzibar as a separate entity.
    Returns the number of measurements loaded.
    """
    if not steps_db_path.exists():
        print(f"      WARNING: {steps_db_path.name} not found — skipping STEPS ETL")
        return 0

    src = sqlite3.connect(steps_db_path)
    ncd = sqlite3.connect(ncd_db_path)
    ncd.execute("PRAGMA journal_mode=WAL;")

    # ── Create STEPS tables ────────────────────────────────────────────────────
    ncd.executescript(STEPS_DDL)

    # ── Clear and reload ───────────────────────────────────────────────────────
    for t in ("steps_measurement", "steps_survey", "steps_indicator", "steps_section"):
        ncd.execute(f"DELETE FROM {t}")

    # ── Sections ──────────────────────────────────────────────────────────────
    sec_rows = src.execute(
        "SELECT section_id, section_code, who_step, section_name_en FROM dim_section"
    ).fetchall()
    ncd.executemany(
        "INSERT OR IGNORE INTO steps_section (section_id,section_code,who_step,section_name) VALUES (?,?,?,?)",
        sec_rows
    )

    # ── Unit symbol lookup (unit_id → display symbol) ─────────────────────────
    unit_sym = {r[0]: r[3] for r in src.execute("SELECT * FROM dim_unit").fetchall()}

    # ── Indicators ────────────────────────────────────────────────────────────
    ind_rows = src.execute(
        "SELECT indicator_id, indicator_code, section_id, label_en, unit_id, higher_is_better FROM dim_indicator"
    ).fetchall()
    ind_rows_mapped = [
        (r[0], r[1], r[2], r[3], unit_sym.get(r[4], "%"), r[5])
        for r in ind_rows
    ]
    ncd.executemany(
        "INSERT OR IGNORE INTO steps_indicator "
        "(indicator_id,indicator_code,section_id,label_en,unit_sym,higher_is_better) VALUES (?,?,?,?,?,?)",
        ind_rows_mapped
    )

    # ── ISO3 → country_id mapping (prefer non-Zanzibar for shared TZA) ────────
    iso3_to_cid: dict = {}
    zanzibar_cid: int | None = None
    for r in ncd.execute(
        "SELECT iso3, country_id, is_zanzibar FROM dim_country ORDER BY is_zanzibar ASC"
    ):
        iso3, cid, is_zan = r
        if iso3 and iso3 not in iso3_to_cid:
            iso3_to_cid[iso3] = cid
        if is_zan:
            zanzibar_cid = cid

    # ── STEPS surveys ─────────────────────────────────────────────────────────
    surveys = src.execute("""
        SELECT s.survey_id, c.iso3, s.survey_year,
               s.sample_size_total, s.response_rate_pct, c.country_name
        FROM fact_survey s
        JOIN dim_country c ON c.country_id = s.country_id
    """).fetchall()

    survey_id_map: dict = {}
    for step_sid, iso3, yr, n_sz, rr, src_name in surveys:
        if src_name and "Zanzibar" in src_name and zanzibar_cid:
            cid = zanzibar_cid
        else:
            cid = iso3_to_cid.get(iso3 or "")
        if not cid:
            continue
        ncd.execute(
            "INSERT OR IGNORE INTO steps_survey "
            "(country_id,survey_year,sample_size,response_rate,source_country) VALUES (?,?,?,?,?)",
            (cid, int(yr), int(n_sz) if n_sz else None,
             round(float(rr), 2) if rr else None, src_name)
        )
        row = ncd.execute(
            "SELECT steps_survey_id FROM steps_survey WHERE country_id=? AND survey_year=?",
            (cid, int(yr))
        ).fetchone()
        if row:
            survey_id_map[step_sid] = row[0]

    # ── Sex code lookup ───────────────────────────────────────────────────────
    sex_code_map = {r[0]: r[1] for r in src.execute("SELECT sex_id, sex_code FROM dim_sex")}

    # ── Measurements ─────────────────────────────────────────────────────────
    meas = src.execute("""
        SELECT survey_id, indicator_id, sex_id, value_numeric, ci_lower, ci_upper
        FROM fact_measurement
        WHERE is_suppressed = 0 AND value_numeric IS NOT NULL
    """).fetchall()

    meas_rows = []
    for step_sid, ind_id, sex_id, val, lo, hi in meas:
        ncd_sid = survey_id_map.get(step_sid)
        if not ncd_sid:
            continue
        sex = sex_code_map.get(sex_id, "both_sexes")
        meas_rows.append((ncd_sid, ind_id, sex,
                          round(float(val), 4),
                          round(float(lo), 4) if lo is not None else None,
                          round(float(hi), 4) if hi is not None else None))

    ncd.executemany(
        "INSERT INTO steps_measurement "
        "(steps_survey_id,indicator_id,sex,value,ci_lower,ci_upper) VALUES (?,?,?,?,?,?)",
        meas_rows
    )
    ncd.commit()
    src.close()
    ncd.close()
    return len(meas_rows)


def load_flat(db_path: Path) -> pd.DataFrame:
    """Return denormalised fact table for downstream analytics."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT
            c.country_name,
            c.iso3,
            c.is_zanzibar,
            s.survey_code    AS survey_type,
            f.survey_year,
            st.status_code   AS status,
            st.is_completed  AS completed,
            dy.decade,
            dy.cycle_label,
            dy.five_yr_period
        FROM fact_surveys      f
        JOIN dim_country       c  ON c.country_id     = f.country_id
        JOIN dim_survey_type   s  ON s.survey_type_id = f.survey_type_id
        JOIN dim_year          dy ON dy.year_id        = f.year_id
        JOIN dim_status        st ON st.status_id      = f.status_id
        ORDER BY c.country_name, f.survey_year
    """, conn)
    conn.close()
    df["completed"] = df["completed"].astype(bool)
    return df
