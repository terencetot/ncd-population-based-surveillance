#!/usr/bin/env python3
"""
Build data/gyts_country_profile.json and data/gats_country_profile.json from
the downloaded GATS/GYTS fact sheet PDFs, using gtss_extract.py (layout-based
table extraction) + gtss_indicators.py (canonical-label fuzzy matching).

For each country, only the LATEST available fact-sheet year per survey type
is parsed (matches what the recency tables already show as "Last Survey").
Comparison fact sheets (covering two years in one PDF, e.g. "2016 & 2024")
are skipped in favour of the single-year fact sheet for the latest year when
both exist, since the single-year one is the clean template.

Quality gate: a country is only included if enough canonical indicators were
matched (GYTS >= 12, GATS >= 10 of the ~35-41/33 candidates) — fewer than
that means the fact sheet uses an older/incompatible template and the
extraction is not trustworthy enough to publish.
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from gtss_extract import extract_sex_disaggregated
from gtss_indicators import GYTS_INDICATORS, GATS_INDICATORS, best_match

FACTSHEET_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "GTSS_AFRO_Factsheets")
RESULTS_JSON = os.path.join(os.path.dirname(__file__), "gtss_api_results_20260823.json")
QUALITY_GATE = {"GYTS": 12, "GATS": 10}
SEX_KEYS = {"GYTS": ("OVERALL", "BOYS", "GIRLS"), "GATS": ("OVERALL", "MEN", "WOMEN")}
CANON = {"GYTS": GYTS_INDICATORS, "GATS": GATS_INDICATORS}


def pick_latest_files(results):
    """{(country, survey_type): (year, file_path)} - prefers a single-year
    file over a multi-year comparison PDF for the same latest year."""
    by_country_type = defaultdict(list)
    for r in results:
        by_country_type[(r["who_country"], r["survey_type"])].append(r)

    picked = {}
    for key, rows in by_country_type.items():
        latest_year = max(r["year"] for r in rows)
        candidates = [r for r in rows if r["year"] == latest_year]
        # prefer a file whose OTHER recorded years (if any) don't include an
        # earlier year too (i.e. not a "2016 & 2024"-style comparison sheet)
        single = [r for r in candidates if "year_label_raw" not in r or "&" not in r.get("year_label_raw", "")]
        chosen = single[0] if single else candidates[0]
        picked[key] = (latest_year, chosen["file"])
    return picked


def main():
    with open(RESULTS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    picked = pick_latest_files(data["results"])

    profiles = {"GYTS": {}, "GATS": {}}
    report_lines = []

    for (country, survey_type), (year, rel_path) in sorted(picked.items()):
        pdf_path = os.path.join(FACTSHEET_DIR, rel_path)
        if not os.path.exists(pdf_path):
            report_lines.append(f"MISSING FILE  {survey_type:5s} {country:35s} {rel_path}")
            continue
        ok, mk, fk = SEX_KEYS[survey_type]
        try:
            raw = extract_sex_disaggregated(pdf_path, overall_key=ok, m_key=mk, f_key=fk)
        except Exception as exc:
            report_lines.append(f"EXTRACT ERROR {survey_type:5s} {country:35s} {exc}")
            continue

        matched = {}
        for frag_label, vals in raw.items():
            m = best_match(frag_label, CANON[survey_type])
            if not m:
                continue
            code, canon_label, sec_code, sec_name, score = m
            if code in matched:
                continue  # keep first (best positional) match if duplicate
            if vals["b"] is not None and not (0 <= vals["b"] <= 100):
                continue  # sanity bound
            matched[code] = {
                "label": canon_label, "sec": sec_code, "sec_name": sec_name,
                "b": vals["b"], "m": vals["m"], "f": vals["f"],
            }

        gate = QUALITY_GATE[survey_type]
        status = "OK" if len(matched) >= gate else "SKIP (below quality gate)"
        report_lines.append(f"{status:26s} {survey_type:5s} {country:35s} year={year} matched={len(matched)}/{len(raw)} raw rows")

        if len(matched) >= gate:
            profiles[survey_type][country] = {"year": year, "source_file": rel_path, "indicators": matched}

    for survey_type in ("GYTS", "GATS"):
        out_path = os.path.join(os.path.dirname(__file__), "..", "data", f"{survey_type.lower()}_country_profile.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(profiles[survey_type], f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(profiles[survey_type])} {survey_type} country profiles -> {out_path}")

    print("\n--- Extraction report ---")
    for line in report_lines:
        print(line)


if __name__ == "__main__":
    main()
