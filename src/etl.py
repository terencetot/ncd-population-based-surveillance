"""
NCD Surveillance Intelligence Platform — WHO African Region
ETL Pipeline: Excel → SQLite star schema
"""
import sqlite3
import pandas as pd
from pathlib import Path
from src.config import (EXCEL_PATH, DB_PATH, OUTPUT_DIR, STATUS_MAP, STATUS_COLORS,
                        SURVEY_META, ISO_CODES, CURRENT_YEAR, CYCLE_YEARS,
                        CURRENT_CYCLE_START, PREV_CYCLE_START)

# Ensure output directory exists when module is loaded
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
