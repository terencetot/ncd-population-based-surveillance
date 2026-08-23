#!/usr/bin/env python3
"""
Merge freshly-fetched GATS/GYTS fact sheet years (gtss_api_results.json) into
data/NCD_Surveillance_Survey_AFRO_dataset.xlsx (sheet Survey_Data).

Only ADDS rows for (country, survey_type, year) combinations that are not
already present. Never modifies or removes existing rows.
"""
import json
from datetime import date

import pandas as pd

XLSX = "NCD_Surveillance_Survey_AFRO_dataset.xlsx"
TODAY = "2026-08-23"
STATUS = "Completed (At least data analysis completed)"

df = pd.read_excel(XLSX, sheet_name="Survey_Data")

existing = set(
    zip(df["country_normalized"], df["survey_type"], df["survey_year"].astype(int))
)

data = json.load(open("gtss_api_results.json", encoding="utf-8"))
results = data["results"]

# Dedup API results themselves (comparison factsheets can repeat a (country,type,year))
seen = set()
new_rows = []
for r in results:
    key = (r["who_country"], r["survey_type"], int(r["year"]))
    if key in seen:
        continue
    seen.add(key)
    if key in existing:
        continue
    new_rows.append({
        "country_normalized": r["who_country"],
        "region": "AFRO",
        "survey_type": r["survey_type"],
        "survey_year": int(r["year"]),
        "NCD Surveillance status": STATUS,
        "last_update": TODAY,
    })

print(f"New rows to add: {len(new_rows)}")
for r in new_rows:
    print(" ", r["country_normalized"], r["survey_type"], r["survey_year"])

if new_rows:
    new_df = pd.DataFrame(new_rows)
    out = pd.concat([df, new_df], ignore_index=True)
    out = out.sort_values(["country_normalized", "survey_type", "survey_year"]).reset_index(drop=True)
    with pd.ExcelWriter(XLSX, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="Survey_Data", index=False)
    print(f"\nWrote {len(out)} total rows ({len(new_rows)} new) to {XLSX}")
else:
    print("\nNothing new to add - dataset already up to date.")
