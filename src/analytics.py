"""
NCD Surveillance Intelligence Platform - WHO African Region
Analytics: SPI computation, cycle matrix, regional KPIs
"""
import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from src.config import (CURRENT_YEAR, CYCLE_YEARS, CURRENT_CYCLE_START,
                        SPI_W, TIER_LABELS, TIER_COLORS, SURVEY_META, ISO_CODES)


def compute_spi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Surveillance Performance Index (SPI) v2 - 3 orthogonal dimensions (0–100).

    BS  Breadth Score  (structural, discrete):
         BS = |{k : instrument k completed ≥1 time}| / K
         Range: {0, 0.2, 0.4, 0.6, 0.8, 1.0}  (K=5)
         Measures permanent institutional capacity - not time-decaying.

    CS  Currency Score  (continuous, single exponential decay):
         c_k = exp(−μ · g_k),  μ = ln(2)/CYCLE_YEARS  (5-yr half-life, matching
              the WHO-recommended cycle: a survey at exactly the "On Cycle" gap
              boundary has decayed to 50% currency value, not ~61% as with the
              previous 7-yr half-life -- the earlier value understated how much
              a survey is due once a country's own status badge calls it Off Cycle)
         c_k = 0 if instrument k was never completed
         CS = mean(c_k) over all 5 instrument types
         Measures recency of the entire surveillance portfolio.

    CA-ARI  Coverage-Adjusted Regularity Index  (structural × regularity):
         d_k = min(1, 5 / avg_interval_k)  for instrument types k with ≥2 rounds
         ARI = mean(d_k) over assessable types only  (0 if none assessable)
         CA-ARI = ARI × (|A| / K)   [penalises partial assessability]
         CA-ARI = 0 when |A|=0 - universal formula, no SPI* split.

    SPI = 100 × (BS + CS + CA-ARI) / 3   [universal, no partial formula]

    Tiers: Strong ≥75 · Advancing 50–74 · Developing 30–49 · Critical <30
    """
    done   = df[df["completed"]]
    inprog = df[df["status"] == "In Progress"]

    MU      = np.log(2) / CYCLE_YEARS  # Currency half-life = the WHO 5-yr cycle,
                                        # so a survey exactly "on cycle" (gap==CYCLE_YEARS)
                                        # scores 50% Currency, not ~61% (was half-life=7,
                                        # inconsistent with the 5-yr "On Cycle" badge used
                                        # throughout the rest of the platform)
    CYCLE   = 5                # Recommended renewal cycle (years)
    K       = len(SURVEY_META) # Number of instrument types (5)
    survey_types = list(SURVEY_META.keys())

    records = []
    for country, grp in df.groupby("country_name"):
        c_done = done[done["country_name"] == country]
        c_inp  = inprog[inprog["country_name"] == country]

        cs_weights   = []   # one per instrument type (0 if never completed)
        ari_scores   = []   # only for instrument types with ≥2 completions
        avg_ivl_list = []   # for avg_cycle_interval metadata
        n_ever_done  = 0    # count of instrument types completed ≥1 time

        for st in survey_types:
            st_done = c_done[c_done["survey_type"] == st]
            yrs     = sorted(st_done["survey_year"].tolist())

            if len(yrs) > 0:
                n_ever_done += 1
                g = int(CURRENT_YEAR - yrs[-1])
                cs_weights.append(float(np.exp(-MU * g)))
                if len(yrs) >= 2:
                    intervals = [yrs[i + 1] - yrs[i] for i in range(len(yrs) - 1)]
                    avg_ivl   = float(np.mean(intervals))
                    avg_ivl_list.append(avg_ivl)
                    ari_scores.append(min(1.0, CYCLE / avg_ivl))
            else:
                cs_weights.append(0.0)

        # ── Three orthogonal dimensions ────────────────────────────────────────
        BS  = n_ever_done / K                              # discrete breadth
        CS  = float(np.mean(cs_weights))                  # continuous currency
        n_renewable    = len(ari_scores)
        ari_assessable = n_renewable > 0
        ARI    = float(np.mean(ari_scores)) if ari_assessable else 0.0
        CA_ARI = ARI * (n_renewable / K)                  # coverage-adjusted
        avg_cycle_interval = round(float(np.mean(avg_ivl_list)), 1) if avg_ivl_list else None

        # ── Universal SPI (no partial formula) ────────────────────────────────
        spi  = 100.0 * (BS + CS + CA_ARI) / 3.0
        tier = 1 if spi >= 75 else 2 if spi >= 50 else 3 if spi >= 30 else 4

        # ── Metadata for filters / display ────────────────────────────────────
        n_done    = int(c_done.shape[0])
        n_inprog  = int(c_inp.shape[0])
        types_ever = n_ever_done

        last_yr_any = c_done["survey_year"].max() if n_done > 0 else np.nan
        gap = int(CURRENT_YEAR - last_yr_any) if pd.notna(last_yr_any) else None

        recent_done   = int(c_done[c_done["survey_year"] >= CURRENT_CYCLE_START].shape[0])
        recent_inprog = int(c_inp[c_inp["survey_year"]   >= CURRENT_CYCLE_START].shape[0])

        if gap is None:
            gap_cat = "No data"
        elif gap <= 5:
            gap_cat = "≤5 years"
        elif gap <= 10:
            gap_cat = "6–10 years"
        else:
            gap_cat = ">10 years"

        if not ari_assessable:
            reg_cat = "Not yet assessable"
        elif CA_ARI >= 0.8 / K * n_renewable:
            reg_cat = "High (≤6 yr avg)"
        elif CA_ARI >= 0.55 / K * n_renewable:
            reg_cat = "Moderate (7–9 yr avg)"
        else:
            reg_cat = "Low (>9 yr avg)"

        records.append({
            "country":            country,
            "iso3":               grp["iso3"].iloc[0],
            "total":              len(grp),
            "n_done":             n_done,
            "n_inprog":           n_inprog,
            "types_done":         int(types_ever),
            "last_year":          int(last_yr_any) if pd.notna(last_yr_any) else None,
            "gap_years":          gap,
            "gap_cat":            gap_cat,
            "recent_done":        recent_done,
            "recent_inprog":      recent_inprog,
            "n_renewable":        n_renewable,
            "avg_cycle_interval": avg_cycle_interval,
            "reg_cat":            reg_cat,
            "d_coverage":         round(BS  * 100, 1),   # BS  → breadth
            "d_recency":          round(CS  * 100, 1),   # CS  → currency
            "d_regularity":       round(CA_ARI * 100, 1),   # 0.0 when not yet assessable — still enters the SPI average at full weight, see report.py display
            "ari_assessable":     ari_assessable,
            "spi":                round(spi, 1),
            "tier":               tier,
            "tier_label":         TIER_LABELS[tier],
        })

    return pd.DataFrame(records).sort_values("spi", ascending=False).reset_index(drop=True)


def compute_cycle_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each (country, survey_type): classify cycle status based on
    recency of last completed survey relative to 5-year cycle expectation.

    Status values:
      Current    - last completed within 5 years (2021–2026)
      Overdue    - last completed 6–10 years ago
      Critical   - last completed > 10 years ago
      In Pipeline- no completed, but in-progress survey >= 2021
      Never      - no completed survey and no active pipeline
    """
    done   = df[df["completed"]]
    inprog = df[df["status"] == "In Progress"]

    countries    = sorted(df["country_name"].unique())
    survey_types = list(SURVEY_META.keys())

    rows = []
    for c in countries:
        for st in survey_types:
            sub_done  = done[(done["country_name"] == c) & (done["survey_type"] == st)]
            sub_all   = df[(df["country_name"] == c) & (df["survey_type"] == st)]
            sub_inp   = inprog[(inprog["country_name"] == c) & (inprog["survey_type"] == st) &
                               (inprog["survey_year"] >= CURRENT_CYCLE_START)]

            if len(sub_done) > 0:
                last_yr = sub_done["survey_year"].max()
                gap     = CURRENT_YEAR - last_yr
                if gap <= CYCLE_YEARS:
                    status_c = "Current"
                    order    = 1
                elif gap <= CYCLE_YEARS * 2:
                    status_c = "Overdue"
                    order    = 2
                else:
                    status_c = "Critical"
                    order    = 3
            elif len(sub_inp) > 0:
                last_yr  = sub_inp["survey_year"].max()
                gap      = CURRENT_YEAR - last_yr
                status_c = "In Pipeline"
                order    = 4
            else:
                last_yr  = None
                gap      = None
                status_c = "Never" if len(sub_all) == 0 else "Never"
                order    = 5

            rows.append({
                "country":     c,
                "survey_type": st,
                "last_year":   last_yr,
                "gap":         gap,
                "cycle_status": status_c,
                "order":       order,
                "n_surveys":   len(sub_all),
            })

    return pd.DataFrame(rows)


def compute_exec_kpis(df: pd.DataFrame) -> dict:
    """
    Compute country-level executive KPIs for each survey type AND globally.
    Categories are strictly mutually exclusive per country (per survey type).

    Status priority (in order):
      1. On Cycle         - has completed AND gap <= 5 years (current, usable evidence)
      2. Attempt to update- has completed AND gap > 5 AND has in-progress in current cycle
                           (prior evidence exists; updating it)
      3. Off Cycle        - has completed AND gap > 5 AND no active in-progress survey
                           (surveillance idle - data ageing)
      4. First Attempt    - never completed AND has in-progress in current cycle
                           (no prior evidence yet, but actively fielding a first round -
                           distinct from true non-engagement per epidemiological review:
                           collapsing this into "Never Conducted" made an active first
                           national survey score identically to a country that has never
                           engaged with the instrument at all)
      5. Never Conducted  - never completed AND no active in-progress survey
                           (no evidence, no current activity)
    """
    import logging
    done   = df[df["completed"]]
    inprog = df[df["status"] == "In Progress"]

    countries     = sorted(df["country_name"].unique())
    survey_types  = list(SURVEY_META.keys())
    N             = len(countries)

    result = {}

    # ── Per-survey-type KPIs ──────────────────────────────────────────────────
    for st in survey_types:
        counts = {"On Cycle": 0, "Attempt to update": 0, "Off Cycle": 0,
                  "First Attempt": 0, "Never Conducted": 0}
        country_statuses = {}

        for c in countries:
            completed_rows = done[(done["country_name"] == c) & (done["survey_type"] == st)]
            inprog_current = inprog[(inprog["country_name"] == c) &
                                    (inprog["survey_type"] == st) &
                                    (inprog["survey_year"] >= CURRENT_CYCLE_START)]

            has_completed      = len(completed_rows) > 0
            has_inprog_current = len(inprog_current) > 0

            if not has_completed:
                if has_inprog_current:
                    # No prior evidence, but actively fielding a first round now
                    counts["First Attempt"] += 1
                    country_statuses[c] = "First Attempt"
                else:
                    counts["Never Conducted"] += 1
                    country_statuses[c] = "Never Conducted"
            else:
                last_yr = int(completed_rows["survey_year"].max())
                gap     = CURRENT_YEAR - last_yr
                if gap <= 5:
                    counts["On Cycle"] += 1
                    country_statuses[c] = "On Cycle"
                elif has_inprog_current:
                    # Has prior evidence; currently updating with a new in-progress survey
                    counts["Attempt to update"] += 1
                    country_statuses[c] = "Attempt to update"
                else:
                    # Has prior evidence but surveillance is idle
                    counts["Off Cycle"] += 1
                    country_statuses[c] = "Off Cycle"

        meta   = SURVEY_META[st]
        n_on   = counts["On Cycle"]
        n_att  = counts["Attempt to update"]
        n_off  = counts["Off Cycle"]
        n_first= counts["First Attempt"]
        n_nev  = counts["Never Conducted"]

        briefing = (
            f"For the <strong>{st}</strong> survey ({meta['full']}, targeting {meta['target']}), "
            f"<strong>{n_on} of {N} countries</strong> ({round(n_on/N*100)}%) have completed "
            f"a {st} survey within the recommended 5-year cycle ({CURRENT_CYCLE_START}&#8211;{CURRENT_YEAR}). "
            f"<strong>{n_att}</strong> {'country' if n_att == 1 else 'countries'} "
            f"{'has' if n_att == 1 else 'have'} prior {st} evidence and {'is' if n_att == 1 else 'are'} currently "
            f"conducting a new round to update {'its' if n_att == 1 else 'their'} surveillance baseline. "
            f"<strong>{n_off}</strong> {'country' if n_off == 1 else 'countries'} "
            f"{'has' if n_off == 1 else 'have'} conducted {st} before but {'is' if n_off == 1 else 'are'} "
            f"not currently active \u2014 {'its' if n_off == 1 else 'their'} surveillance data is off-cycle and ageing. "
            f"<strong>{n_first}</strong> {'country has' if n_first == 1 else 'countries have'} "
            f"no prior {st} evidence but {'is' if n_first == 1 else 'are'} actively fielding a first-ever round right now. "
            f"<strong>{n_nev}</strong> {'country' if n_nev == 1 else 'countries'} "
            f"{'has' if n_nev == 1 else 'have'} <em>never completed nor attempted</em> a {st} survey \u2014 "
            f"no {st}-generated evidence exists and none is currently in progress."
        )

        # ── Per-country gap data for the dynamic gap chart ──────────────────
        cgap = []
        for c in countries:
            cr = done[(done["country_name"] == c) & (done["survey_type"] == st)]
            if len(cr) > 0:
                ly = int(cr["survey_year"].max())
                cgap.append({"country": c, "last_year": ly, "gap": CURRENT_YEAR - ly,
                             "status": country_statuses.get(c, "Never Conducted")})
            else:
                cgap.append({"country": c, "last_year": None, "gap": None,
                             "status": country_statuses.get(c, "Never Conducted")})
        cgap.sort(key=lambda x: (x["gap"] is None, x["gap"] or 999))

        result[st] = {
            "n_total":            N,
            "n_on_cycle":         n_on,
            "n_attempt_to_update": n_att,
            "n_off_cycle":        n_off,
            "n_first_attempt":    n_first,
            "n_never":            n_nev,
            "briefing":           briefing,
            "full_name":          meta["full"],
            "target":             meta["target"],
            "domain":             meta["domain"],
            "color":              meta["color"],
            "countries_gap":      cgap,
        }

    # ── Global KPIs (across all survey types combined) ────────────────────────
    g_counts = {"On Cycle": 0, "Attempt to update": 0, "Off Cycle": 0,
                "First Attempt": 0, "Never Conducted": 0}

    for c in countries:
        completed_rows = done[done["country_name"] == c]
        inprog_current = inprog[(inprog["country_name"] == c) &
                                 (inprog["survey_year"] >= CURRENT_CYCLE_START)]

        has_completed      = len(completed_rows) > 0
        has_inprog_current = len(inprog_current) > 0

        if not has_completed:
            if has_inprog_current:
                g_counts["First Attempt"] += 1
            else:
                g_counts["Never Conducted"] += 1
        else:
            last_yr = int(completed_rows["survey_year"].max())
            gap     = CURRENT_YEAR - last_yr
            if gap <= 5:
                g_counts["On Cycle"] += 1
            elif has_inprog_current:
                g_counts["Attempt to update"] += 1
            else:
                g_counts["Off Cycle"] += 1

    gn_on    = g_counts["On Cycle"]
    gn_att   = g_counts["Attempt to update"]
    gn_off   = g_counts["Off Cycle"]
    gn_first = g_counts["First Attempt"]
    gn_nev   = g_counts["Never Conducted"]

    global_briefing = (
        f"Across the five NCD population-based surveillance instruments, "
        f"<strong>{gn_on} of {N} countries</strong> ({round(gn_on/N*100)}%) have completed "
        f"at least one survey of any type within the last 5 years, generating current surveillance intelligence. "
        f"<strong>{gn_att}</strong> additional {'country' if gn_att == 1 else 'countries'} "
        f"{'has' if gn_att == 1 else 'have'} prior evidence and {'is' if gn_att == 1 else 'are'} actively "
        f"conducting a new survey round in the current cycle ({CURRENT_CYCLE_START}&#8211;{CURRENT_YEAR}). "
        f"<strong>{gn_off}</strong> countries have prior survey evidence but are not currently active \u2014 "
        f"their surveillance systems are off-cycle and require re-engagement. "
        f"<strong>{gn_first}</strong> {'country has' if gn_first == 1 else 'countries have'} no completed survey of any type "
        f"but {'is' if gn_first == 1 else 'are'} actively fielding a first-ever round right now. "
        f"<strong>{gn_nev}</strong> countries have <em>never completed nor attempted</em> any of the five NCD survey instruments \u2014 "
        f"representing the region\u2019s most severe evidence deficits for NCD policy and programming."
    )

    result["global"] = {
        "n_total":            N,
        "n_on_cycle":         gn_on,
        "n_attempt_to_update": gn_att,
        "n_off_cycle":        gn_off,
        "n_first_attempt":    gn_first,
        "n_never":            gn_nev,
        "briefing":           global_briefing,
        "full_name":          "All Survey Types \u2014 System-wide view",
        "target":             "All 48 WHO AFRO entities",
        "domain":             "NCD surveillance system",
        "color":              "#003d82",
    }

    # ── Validation ────────────────────────────────────────────────────────────
    for key, d in result.items():
        total_check = (d["n_on_cycle"] + d["n_attempt_to_update"] +
                       d["n_off_cycle"] + d["n_first_attempt"] + d["n_never"])
        if total_check != d["n_total"]:
            logging.warning(f"KPI totals mismatch for {key}: {total_check} != {d['n_total']}")
        assert total_check == d["n_total"], \
            f"KPI totals mismatch for {key}: {total_check} != {d['n_total']}"

    return result


def build_steps_profile_data(ncd_db_path: Path, spi_df: pd.DataFrame) -> dict:
    """
    Load STEPS indicator data from ncd_surveillance.db (populated by etl_steps_indicators)
    and build the per-country profile data structure for the Country Profile tab.

    Returns a dict with keys:
      countries   : sorted list of country names that have STEPS data
      sections    : {section_code: {id, name, step, color, icon}}
      indicators  : {indicator_code: {label, unit, sec (section_code), hib}}
      regional    : {indicator_code: {b, m, f, n}} - AFRO averages from latest survey/country
      profiles    : {country_name: {iso3, spi, tier, tier_label, surveys, data}}
        data      : {survey_year_str: {indicator_code: {b, lo, hi, m, f}}}
    """
    conn = sqlite3.connect(ncd_db_path)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    if "steps_measurement" not in tables:
        conn.close()
        return {}
    n_meas = conn.execute("SELECT COUNT(*) FROM steps_measurement").fetchone()[0]
    if n_meas == 0:
        conn.close()
        return {}

    # ── Load all measurements in one query ────────────────────────────────────
    df_m = pd.read_sql_query("""
        SELECT
            c.country_name, c.iso3, c.is_zanzibar,
            ss.survey_year, ss.sample_size, ss.response_rate, ss.source_country,
            si.indicator_code, si.section_id, si.label_en, si.unit_sym,
            si.higher_is_better,
            m.sex, m.value, m.ci_lower, m.ci_upper
        FROM steps_measurement m
        JOIN steps_survey ss ON ss.steps_survey_id = m.steps_survey_id
        JOIN dim_country  c  ON c.country_id        = ss.country_id
        JOIN steps_indicator si ON si.indicator_id  = m.indicator_id
        WHERE m.value IS NOT NULL
        ORDER BY c.country_name, ss.survey_year, si.section_id, si.indicator_code, m.sex
    """, conn)

    sec_df  = pd.read_sql_query("SELECT * FROM steps_section",  conn)
    ind_df  = pd.read_sql_query("SELECT * FROM steps_indicator", conn)
    conn.close()

    if df_m.empty:
        return {}

    # ── Section metadata ──────────────────────────────────────────────────────
    _SEC_META = {
        "S1_TOB": {"color": "#c0392b", "icon": "fa-smoking"},
        "S1_ALC": {"color": "#8e44ad", "icon": "fa-wine-glass-alt"},
        "S1_DIT": {"color": "#27ae60", "icon": "fa-apple-alt"},
        "S1_PAC": {"color": "#2980b9", "icon": "fa-running"},
        "S1_SAL": {"color": "#1a7fc1", "icon": "fa-utensils"},
        "S2_BPR": {"color": "#e74c3c", "icon": "fa-heartbeat"},
        "S2_ANT": {"color": "#e67e22", "icon": "fa-weight"},
        "S3_GLU": {"color": "#d35400", "icon": "fa-tint"},
        "S3_CHO": {"color": "#16a085", "icon": "fa-vial"},
        "S_RISK": {"color": "#2c3e50", "icon": "fa-exclamation-triangle"},
    }
    sid_to_code = {}
    sections: dict = {}
    for _, row in sec_df.iterrows():
        code = row["section_code"]
        sid  = int(row["section_id"])
        sid_to_code[sid] = code
        m = _SEC_META.get(code, {"color": "#6b7280", "icon": "fa-circle"})
        sections[code] = {
            "id":    sid,
            "name":  row["section_name"],
            "step":  row["who_step"],
            "color": m["color"],
            "icon":  m["icon"],
        }

    # ── Indicator metadata ────────────────────────────────────────────────────
    indicators: dict = {}
    for _, row in ind_df.iterrows():
        raw_hib = row["higher_is_better"]
        hib = None if pd.isna(raw_hib) else bool(int(raw_hib))
        indicators[row["indicator_code"]] = {
            "label": row["label_en"],
            "unit":  row["unit_sym"] or "%",
            "sec":   sid_to_code.get(int(row["section_id"]), ""),
            "hib":   hib,
        }

    # ── SPI lookup by ISO3 ────────────────────────────────────────────────────
    spi_by_iso3: dict = {}
    if spi_df is not None and len(spi_df) > 0:
        for _, row in spi_df.iterrows():
            if row["iso3"]:
                spi_by_iso3[str(row["iso3"])] = {
                    "spi":        float(row["spi"]),
                    "tier":       int(row["tier"]),
                    "tier_label": str(row["tier_label"]),
                }

    # ── Build per-country profiles ────────────────────────────────────────────
    profiles: dict = {}
    countries_list: list = []

    for (cname, iso3, is_zan), cgrp in df_m.groupby(
        ["country_name", "iso3", "is_zanzibar"], sort=False
    ):
        spi_info = spi_by_iso3.get(str(iso3) if iso3 else "", {})

        # surveys list (sorted by year)
        surveys = []
        for yr, yg in cgrp.groupby("survey_year"):
            row0 = yg.iloc[0]
            n  = row0["sample_size"]
            rr = row0["response_rate"]
            surveys.append({
                "year": int(yr),
                "n":    int(n)  if pd.notna(n)  else None,
                "rr":   round(float(rr), 1) if pd.notna(rr) else None,
            })
        surveys.sort(key=lambda x: x["year"])

        # data: {year_str: {indicator_code: {b, lo, hi, m, f}}}
        data: dict = {}
        for yr, yg in cgrp.groupby("survey_year"):
            yd: dict = {}
            for ind_code, ig in yg.groupby("indicator_code"):
                ind_vals: dict = {}
                for _, r in ig.iterrows():
                    sk = {"both_sexes": "b", "males": "m", "females": "f"}.get(r["sex"], "b")
                    v  = round(float(r["value"]),    2) if pd.notna(r["value"])    else None
                    lo = round(float(r["ci_lower"]), 2) if pd.notna(r["ci_lower"]) else None
                    hi = round(float(r["ci_upper"]), 2) if pd.notna(r["ci_upper"]) else None
                    if sk == "b":
                        ind_vals["b"]  = v
                        ind_vals["lo"] = lo
                        ind_vals["hi"] = hi
                    else:
                        ind_vals[sk] = v
                if ind_vals:
                    yd[str(ind_code)] = ind_vals
            data[str(int(yr))] = yd

        profiles[cname] = {
            "iso3":       iso3,
            "spi":        spi_info.get("spi"),
            "tier":       spi_info.get("tier"),
            "tier_label": spi_info.get("tier_label"),
            "surveys":    surveys,
            "data":       data,
        }
        countries_list.append(cname)

    countries_list = sorted(countries_list)

    # ── Regional averages (latest survey per country, mean across region) ─────
    regional: dict = {}
    for ind_code in indicators:
        bv, mv, fv = [], [], []
        for cname, p in profiles.items():
            if not p["surveys"]:
                continue
            latest_yr = str(p["surveys"][-1]["year"])
            d = p["data"].get(latest_yr, {}).get(ind_code, {})
            if d.get("b") is not None:
                bv.append(d["b"])
            if d.get("m") is not None:
                mv.append(d["m"])
            if d.get("f") is not None:
                fv.append(d["f"])
        regional[ind_code] = {
            "b":          round(sum(bv) / len(bv), 1) if bv else None,
            "m":          round(sum(mv) / len(mv), 1) if mv else None,
            "f":          round(sum(fv) / len(fv), 1) if fv else None,
            "n_countries": len(bv),
        }

    return {
        "countries":  countries_list,
        "sections":   sections,
        "indicators": indicators,
        "regional":   regional,
        "profiles":   profiles,
    }


_GTSS_SEC_META = {
    "GYTS": {
        "SMOKED":    {"name": "Smoked Tobacco",              "color": "#c0392b", "icon": "fa-smoking"},
        "SMOKELESS": {"name": "Smokeless Tobacco",            "color": "#e67e22", "icon": "fa-ban"},
        "ANY":       {"name": "Any Tobacco Use",              "color": "#8e44ad", "icon": "fa-lungs"},
        "SUSCEPT":   {"name": "Susceptibility",               "color": "#2c3e50", "icon": "fa-exclamation-triangle"},
        "ECIG":      {"name": "Electronic Cigarettes",        "color": "#16a085", "icon": "fa-bolt"},
        "CESSATION": {"name": "Cessation",                    "color": "#2980b9", "icon": "fa-briefcase-medical"},
        "SHS":       {"name": "Secondhand Smoke",             "color": "#d35400", "icon": "fa-wind"},
        "ACCESS":    {"name": "Access & Availability",        "color": "#27ae60", "icon": "fa-store"},
        "ADVERT":    {"name": "Tobacco Advertising",          "color": "#7f8c8d", "icon": "fa-bullhorn"},
        "KNOW":      {"name": "Knowledge & Attitudes",        "color": "#34495e", "icon": "fa-brain"},
    },
    "GATS": {
        "USE":       {"name": "Tobacco & E-Cigarette Use",    "color": "#8e44ad", "icon": "fa-smoking"},
        "SMOKING":   {"name": "Tobacco Smoking",               "color": "#c0392b", "icon": "fa-fire"},
        "SMOKELESS": {"name": "Smokeless Tobacco Use",         "color": "#e67e22", "icon": "fa-ban"},
        "HEATED":    {"name": "Heated Tobacco Products",       "color": "#d35400", "icon": "fa-temperature-high"},
        "ECIG":      {"name": "Electronic Cigarettes",         "color": "#16a085", "icon": "fa-bolt"},
        "CESSATION": {"name": "Cessation",                     "color": "#2980b9", "icon": "fa-briefcase-medical"},
        "SHS":       {"name": "Secondhand Smoke",              "color": "#7f8c8d", "icon": "fa-wind"},
        "MEDIA":     {"name": "Media & Warning Labels",        "color": "#2c3e50", "icon": "fa-bullhorn"},
        "KNOW":      {"name": "Knowledge & Attitudes",         "color": "#34495e", "icon": "fa-brain"},
    },
}


def build_gtss_profile_data(json_path: Path, survey_code: str, spi_df: pd.DataFrame) -> dict:
    """
    Load a GYTS/GATS country-profile JSON (built by
    scripts/build_gtss_profiles.py from fact-sheet PDFs) and shape it into
    the same {countries, sections, indicators, regional, profiles} structure
    build_steps_profile_data() produces, so the Country Profile tab can
    render any of the three survey types through one code path.

    Each country in the source JSON has exactly one survey round (the latest
    fact sheet year available), so `profiles[c]["surveys"]` is a single-item
    list and `data` has a single year key.
    """
    if not json_path.exists():
        return {}
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    if not raw:
        return {}

    sec_meta = _GTSS_SEC_META.get(survey_code, {})
    spi_by_iso3: dict = {}
    if spi_df is not None and len(spi_df) > 0:
        for _, row in spi_df.iterrows():
            if row["iso3"]:
                spi_by_iso3[str(row["iso3"])] = {
                    "spi":        float(row["spi"]),
                    "tier":       int(row["tier"]),
                    "tier_label": str(row["tier_label"]),
                }

    sections:   dict = {}
    indicators: dict = {}
    profiles:   dict = {}
    sums: dict = {}  # code -> {"b": [...], "m": [...], "f": [...]}

    for country, entry in raw.items():
        iso3 = ISO_CODES.get(country)
        spi_info = spi_by_iso3.get(iso3 or "", {})
        year = int(entry["year"])
        yd = {}
        for code, ind in entry["indicators"].items():
            sc = ind["sec"]
            if sc not in sections:
                meta = sec_meta.get(sc, {"name": ind.get("sec_name", sc), "color": "#6b7280", "icon": "fa-circle"})
                sections[sc] = {"id": len(sections) + 1, "name": meta["name"], "step": survey_code,
                                 "color": meta["color"], "icon": meta["icon"]}
            if code not in indicators:
                indicators[code] = {"label": ind["label"], "unit": "%", "sec": sc, "hib": None}
            yd[code] = {"b": ind["b"], "lo": None, "hi": None, "m": ind["m"], "f": ind["f"],
                        "conf": ind.get("score")}
            bucket = sums.setdefault(code, {"b": [], "m": [], "f": []})
            if ind["b"] is not None:
                bucket["b"].append(ind["b"])
            if ind["m"] is not None:
                bucket["m"].append(ind["m"])
            if ind["f"] is not None:
                bucket["f"].append(ind["f"])

        profiles[country] = {
            "iso3":       iso3,
            "spi":        spi_info.get("spi"),
            "tier":       spi_info.get("tier"),
            "tier_label": spi_info.get("tier_label"),
            "surveys":    [{"year": year, "n": None, "rr": None}],
            "data":       {str(year): yd},
            "source_file": entry.get("source_file"),
        }

    regional = {}
    for code, bucket in sums.items():
        regional[code] = {
            "b": round(sum(bucket["b"]) / len(bucket["b"]), 1) if bucket["b"] else None,
            "m": round(sum(bucket["m"]) / len(bucket["m"]), 1) if bucket["m"] else None,
            "f": round(sum(bucket["f"]) / len(bucket["f"]), 1) if bucket["f"] else None,
            "n_countries": len(bucket["b"]),
        }

    return {
        "countries":  sorted(profiles.keys()),
        "sections":   sections,
        "indicators": indicators,
        "regional":   regional,
        "profiles":   profiles,
    }


def build_analytics(df: pd.DataFrame) -> dict:
    A = {}

    completed = df[df["completed"]]
    inprog    = df[df["status"] == "In Progress"]

    # ── Basic counts ──────────────────────────────────────────────────────────
    A["n_entities"]    = df["country_name"].nunique()
    A["n_records"]     = len(df)
    A["n_completed"]   = int(df["completed"].sum())
    A["n_inprog"]      = int((df["status"] == "In Progress").sum())
    A["n_unusable"]    = int((df["status"] == "Not Usable").sum())
    A["completion_pct"]= round(A["n_completed"] / A["n_records"] * 100, 1)
    A["year_min"]      = int(df["survey_year"].min())
    A["year_max"]      = int(df["survey_year"].max())

    # ── SPI ───────────────────────────────────────────────────────────────────
    spi = compute_spi(df)
    A["spi"] = spi
    A["regional_spi"]  = round(spi["spi"].mean(), 1)
    A["median_spi"]    = round(spi["spi"].median(), 1)
    A["tier_counts"]   = spi["tier_label"].value_counts().to_dict()
    A["n_strong"]      = int((spi["tier"] == 1).sum())
    A["n_critical"]    = int((spi["tier"] == 4).sum())

    # ── Strategic KPIs (for Executive tab) ───────────────────────────────────
    # On track: gap ≤ 5 years (R=1.0)
    A["n_on_track"]    = int((spi["gap_years"].fillna(999) <= 5).sum())
    # Off-cycle: gap 6–10 years
    A["n_off_cycle"]   = int(((spi["gap_years"].fillna(999) > 5) &
                               (spi["gap_years"].fillna(999) <= 10)).sum())
    # Critical gap: >10 years or never
    A["n_gap_critical"]= int((spi["gap_years"].fillna(999) > 10).sum())
    # Active this cycle (completed or in-progress in 2021+)
    A["n_current_cycle"] = int((spi["recent_done"] > 0).sum())
    A["n_pipeline"]      = int(((spi["recent_done"] == 0) & (spi["recent_inprog"] > 0)).sum())
    # Pct calculations
    n = A["n_entities"]
    A["pct_on_track"]     = round(A["n_on_track"]    / n * 100)
    A["pct_off_cycle"]    = round(A["n_off_cycle"]   / n * 100)
    A["pct_gap_critical"] = round(A["n_gap_critical"]/ n * 100)

    # ── Cycle matrix ──────────────────────────────────────────────────────────
    A["cycle_matrix"] = compute_cycle_matrix(df)

    # ── Current cycle (2021–2026) ─────────────────────────────────────────────
    curr = df[df["survey_year"] >= CURRENT_CYCLE_START]
    A["current_cycle_df"]    = curr
    A["current_cycle_done"]  = int(curr["completed"].sum())
    A["current_cycle_inprog"]= int((curr["status"] == "In Progress").sum())

    # ── Survey type summary ───────────────────────────────────────────────────
    st = df.groupby("survey_type").agg(
        total    =("status","count"),
        done     =("completed","sum"),
        countries=("country_name","nunique"),
        yr_min   =("survey_year","min"),
        yr_max   =("survey_year","max"),
    ).reset_index()
    st["pct_done"] = (st["done"] / st["total"] * 100).round(1)
    A["survey_type_summary"] = st.sort_values("total", ascending=False)

    # ── Timeline ──────────────────────────────────────────────────────────────
    A["timeline"] = df.groupby(["survey_year","status"]).size().reset_index(name="count")
    A["cumulative"] = (
        completed.groupby("survey_year").size().sort_index()
        .cumsum().reset_index(name="cumulative")
    )

    # ── Per-survey-type timeline: distinct countries per year (completed) ────
    tbt = {}
    for st_name in SURVEY_META.keys():
        st_comp = completed[completed["survey_type"] == st_name]
        yearly = (
            st_comp.groupby("survey_year")["country_name"]
            .nunique()
            .reset_index(name="n_countries")
            .sort_values("survey_year")
        )
        tbt[st_name] = [
            {"year": int(r["survey_year"]), "n": int(r["n_countries"])}
            for _, r in yearly.iterrows()
        ]
    A["timeline_by_type"] = tbt

    # ── Last-year heatmap matrix (country × instrument) ───────────────────────
    # Each cell = year of most recent *completed* survey (NaN = never completed)
    last_yr_pivot = (
        completed
        .groupby(["country_name", "survey_type"])["survey_year"]
        .max()
        .unstack(fill_value=np.nan)
    )
    # Ensure all 5 instrument types appear as columns
    for st_name in list(SURVEY_META.keys()):
        if st_name not in last_yr_pivot.columns:
            last_yr_pivot[st_name] = np.nan
    last_yr_pivot = last_yr_pivot[list(SURVEY_META.keys())]
    # Reindex to include ALL countries in dataset, even those with no completed surveys
    all_countries = sorted(df["country_name"].unique())
    A["last_year_matrix"] = last_yr_pivot.reindex(all_countries)

    # ── Executive KPIs (mutually exclusive country-level status) ─────────────
    A["exec_kpis"] = compute_exec_kpis(df)

    return A
