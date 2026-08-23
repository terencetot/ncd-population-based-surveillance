# GTSS fact sheets — GATS & GYTS, WHO African Region

## What this does

Two scripts, run in order from the `data/` folder:

1. **`fetch_gtss_api.py`** — calls gtssacademy.org's own JSON API
   (`GET /api/survey-sites/?country=<name>`) for each of the 47 AFRO Member
   States, collects every GATS/GYTS fact-sheet PDF listed for the country's
   **National** survey site, downloads them into
   `data/GTSS_AFRO_Factsheets/{GATS,GYTS}/<Country>/`, and writes
   `gtss_api_results.json` (one entry per country/survey/year/URL).
   Resumable — an already-downloaded PDF is skipped.

2. **`merge_gtss.py`** — reads `gtss_api_results.json`, compares it against
   `data/NCD_Surveillance_Survey_AFRO_dataset.xlsx` (`Survey_Data` sheet),
   and appends a row for every (country, survey_type, year) combination that
   isn't already recorded. It never touches or removes existing rows.

## Why not scrape the HTML page

The first attempt did drive a headless browser (Playwright) over each
country page and read `<a href>` links — see the git history for
`download_gtss_afro.py` (removed 2026-08-23). It silently failed: the
fact-sheet "View" buttons on gtssacademy.org are `<button>` elements wired to
a JS modal, not `<a href="...pdf">` links, so the DOM scrape only ever
picked up two unrelated footer PDFs (privacy policy, glossary) and treated
every other country as a duplicate of those. The page actually gets its data
from `GET /api/survey-sites/?country=<name>`, which returns clean JSON with
the fact-sheet URL and survey year directly — no browser needed, no PDF
parsing needed to know the year.

## Run (from `data/`)

```bash
cd data
python ../scripts/fetch_gtss_api.py
python ../scripts/merge_gtss.py
cd ..
python scripts/build_gtss_profiles.py   # extract indicator-level data -> data/gyts_country_profile.json, data/gats_country_profile.json
python main.py        # rebuild output/ncd_surveillance.db + NCD_AFRO_Dashboard.html
```

`fetch_gtss_api.py` takes well under a minute (47 API calls + ~100 PDF
downloads). `merge_gtss.py` prints exactly which (country, survey, year)
rows it's about to add before writing the workbook — read that list before
re-running `main.py`.

## Indicator-level Country Profile (gtss_extract.py / gtss_indicators.py / build_gtss_profiles.py)

The Country Profile tab shows a full indicator breakdown (prevalence by
sex, grouped by section) for STEPS, and — as of 2026-08-23 — for GYTS and
GATS too, sourced directly from the downloaded fact-sheet PDFs rather than
a separate pre-built database:

- **`gtss_extract.py`** — generic layout-based table extractor for the
  GATS/GYTS fact-sheet template. Pulls words with position + font size from
  page 2's stat table, drops the small superscript footnote digits, splits
  the page into its two visual columns, and reconstructs each indicator's
  (possibly line-wrapped) label plus its Overall/Boys/Girls (GYTS) or
  Overall/Men/Women (GATS) values. Indicator blocks are separated primarily
  by text case (a label starts a new sentence with a capital letter;
  wrapped continuation fragments consistently start lowercase) rather than
  a fixed pixel gap — an absolute-gap threshold tuned on one country's PDF
  was found to silently over-merge distinct one-line indicators in
  another's.
- **`gtss_indicators.py`** — canonical GYTS (41 indicators) and GATS (33
  indicators) label vocabularies, built from a fully clean extraction
  (Ghana 2017 GYTS, Ethiopia 2024 GATS). Raw extracted fragments — which
  can carry layout noise, e.g. an adjacent section title bleeding into the
  same line cluster — are matched to the closest canonical label by
  word-set (Jaccard) similarity rather than trusted verbatim.
- **`build_gtss_profiles.py`** — runs the extractor over the LATEST
  fact-sheet year per country per survey type (matching what the recency
  tables already show as "Last Survey"), matches labels to the canonical
  vocabulary, and applies a **quality gate**: a country is only published
  if enough canonical indicators were matched (GYTS ≥ 12, GATS ≥ 10). Older
  fact sheets (pre-~2013, roughly) use a different, non-extractable
  template and are correctly skipped rather than silently mismatched —
  check the script's printed report for the per-country match count and
  skip reason.

Re-run all three whenever new fact sheets are downloaded. `build_gtss_profiles.py`
overwrites `data/gyts_country_profile.json` and `data/gats_country_profile.json`
in full each time (not additive) — it recomputes from the current PDF set.

## Notes

- **South Sudan** has no GTSS data published on the site.
- **Angola**'s only listed site (Huambo) has a raw dataset file but no
  fact-sheet PDF for its one GYTS round — nothing to fetch there, not a bug.
- **Sub-national sites** (e.g. Nigeria's Lagos/Kano/Abuja, Tanzania's
  Arusha/Dar es Salaam) are intentionally excluded — the project's dataset
  tracks national-level survey editions only.
- **Country-name spelling matters for dedup.** `merge_gtss.py` compares
  strings exactly; `Côte d'Ivoire` (with the accented ô) is the spelling
  already used throughout the dataset. If you edit the country list in
  `fetch_gtss_api.py`, keep that spelling or the dedup check will silently
  treat an existing row as new.
- **Comparison fact sheets** (e.g. a single PDF titled "2016 & 2024" or
  "2013 & 2023") are parsed into all years they mention; `merge_gtss.py`'s
  own dedup then drops whichever of those years was already on file.
