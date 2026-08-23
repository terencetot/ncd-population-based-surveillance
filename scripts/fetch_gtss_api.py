#!/usr/bin/env python3
"""
Fetch GATS/GYTS fact sheet metadata + PDFs for the 47 WHO AFRO countries via
the gtssacademy.org JSON API (much more reliable than DOM scraping — the
country page's "Surveys & Data" table is populated from this same endpoint).

Endpoint: GET https://www.gtssacademy.org/api/survey-sites/?country=<label>
Returns a list of "survey sites" for that country (national + any
sub-national sites). Each site has documents.gats.factsheets and
documents.gyts.factsheets, each entry: {id, surveysite, year, survey, url}.

Only NATIONAL-level sites are kept (the project's dataset tracks national
survey editions, not sub-national ones like Lagos/Kano/Arusha).

Output:
    gtss_api_results.json   raw harvest, one entry per (country, survey, year)
    GTSS_AFRO_Factsheets/GATS/<Country>/*.pdf
    GTSS_AFRO_Factsheets/GYTS/<Country>/*.pdf
"""
import json
import os
import re
import time
from urllib.parse import unquote

import requests

BASE = "https://www.gtssacademy.org"
OUTDIR = "GTSS_AFRO_Factsheets"
HEADERS = {"User-Agent": "Mozilla/5.0 (WHO AFRO NCD surveillance - fact sheet archive)"}

AFRO_COUNTRIES = [
    ("Algeria", "Algeria"), ("Angola", "Angola"), ("Benin", "Benin"),
    ("Botswana", "Botswana"), ("Burkina Faso", "Burkina Faso"), ("Burundi", "Burundi"),
    ("Cabo Verde", "Cape Verde"), ("Cameroon", "Cameroon"),
    ("Central African Republic", "Central African Republic"), ("Chad", "Chad"),
    ("Comoros", "Comoros"), ("Congo", "Congo"),
    ("Cote d'Ivoire", "Côte d'Ivoire"),
    ("Democratic Republic of the Congo", "Congo, The Democratic Republic of the"),
    ("Equatorial Guinea", "Equatorial Guinea"), ("Eritrea", "Eritrea"),
    ("Eswatini", "Swaziland"), ("Ethiopia", "Ethiopia"), ("Gabon", "Gabon"),
    ("Gambia", "Gambia"), ("Ghana", "Ghana"), ("Guinea", "Guinea"),
    ("Guinea-Bissau", "Guinea-Bissau"), ("Kenya", "Kenya"), ("Lesotho", "Lesotho"),
    ("Liberia", "Liberia"), ("Madagascar", "Madagascar"), ("Malawi", "Malawi"),
    ("Mali", "Mali"), ("Mauritania", "Mauritania"), ("Mauritius", "Mauritius"),
    ("Mozambique", "Mozambique"), ("Namibia", "Namibia"), ("Niger", "Niger"),
    ("Nigeria", "Nigeria"), ("Rwanda", "Rwanda"),
    ("Sao Tome and Principe", "Sao Tome and Principe"), ("Senegal", "Senegal"),
    ("Seychelles", "Seychelles"), ("Sierra Leone", "Sierra Leone"),
    ("South Africa", "South Africa"), ("South Sudan", None), ("Togo", "Togo"),
    ("Uganda", "Uganda"),
    ("United Republic of Tanzania", "Tanzania, United Republic of"),
    ("Zambia", "Zambia"), ("Zimbabwe", "Zimbabwe"),
]


def safe_name(name: str) -> str:
    name = unquote(name)
    name = re.sub(r"[\\/:*?\"<>|]+", "-", name)
    return re.sub(r"\s+", " ", name).strip()[:150]


def download(session, url, dest_path):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 5_000:
        return "skipped (already downloaded)"
    r = session.get(url, timeout=120, stream=True)
    r.raise_for_status()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as fh:
        for chunk in r.iter_content(65_536):
            fh.write(chunk)
    return f"{os.path.getsize(dest_path) // 1024} KB"


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    results = []   # one row per (who_country, survey_type, year, url, file)
    missing = []

    for who_name, site_label in AFRO_COUNTRIES:
        if site_label is None:
            print(f"--  {who_name}: not published on gtssacademy.org")
            missing.append({"country": who_name, "reason": "not listed on the site"})
            continue

        try:
            r = session.get(f"{BASE}/api/survey-sites/", params={"country": site_label}, timeout=30)
            r.raise_for_status()
            sites = r.json()
        except Exception as exc:
            print(f"!!  {who_name}: API error {exc}")
            missing.append({"country": who_name, "reason": f"API error: {exc}"})
            continue

        national_sites = [s for s in sites if "national" in (s.get("surveysite") or "").lower()]
        if not national_sites and sites:
            national_sites = sites[:1]   # fallback: single-site countries with no "National" label

        found_any = False
        for site in national_sites:
            docs = site.get("documents", {})
            for survey_key, survey_code in (("gats", "GATS"), ("gyts", "GYTS")):
                for fs in docs.get(survey_key, {}).get("factsheets", []):
                    year_raw = fs.get("year")
                    url = fs.get("url")
                    if not year_raw or not url:
                        continue
                    years = [int(y) for y in re.findall(r"\d{4}", str(year_raw))]
                    if not years:
                        continue
                    found_any = True
                    filename = safe_name(os.path.basename(url.split("?")[0]))
                    dest = os.path.join(OUTDIR, survey_code, safe_name(who_name), filename)
                    try:
                        status = download(session, url, dest)
                    except Exception as exc:
                        status = f"FAILED: {exc}"
                    print(f"[{survey_code}] {who_name} {year_raw}: {filename} -> {status}")
                    for year in years:
                        results.append({
                            "who_country": who_name,
                            "site_label": site_label,
                            "surveysite": site.get("surveysite"),
                            "survey_type": survey_code,
                            "year": year,
                            "year_label_raw": str(year_raw),
                            "url": url,
                            "file": os.path.relpath(dest, OUTDIR),
                            "download_status": status,
                        })
        if not found_any:
            print(f"--  {who_name}: no GATS/GYTS factsheets found")
            missing.append({"country": who_name, "reason": "no factsheets in API response"})

        time.sleep(0.4)

    with open("gtss_api_results.json", "w", encoding="utf-8") as f:
        json.dump({"results": results, "missing": missing}, f, indent=2, ensure_ascii=False)

    n_gats = sum(1 for r in results if r["survey_type"] == "GATS")
    n_gyts = sum(1 for r in results if r["survey_type"] == "GYTS")
    print(f"\nDone. {len(results)} factsheets ({n_gats} GATS, {n_gyts} GYTS). {len(missing)} countries with nothing found.")


if __name__ == "__main__":
    main()
