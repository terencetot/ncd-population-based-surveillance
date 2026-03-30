#!/usr/bin/env python3
"""
NCD Surveillance Intelligence Platform — WHO African Region
Main entry point: runs ETL pipeline -> analytics -> HTML report generation

Usage:
    py main.py
    python main.py

Output:
    output/ncd_surveillance.db     SQLite star-schema database
    output/NCD_AFRO_Dashboard.html Standalone HTML intelligence platform
"""
import sys
import io

# UTF-8 stdout for Windows compatibility
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from src.config import EXCEL_PATH, DB_PATH, OUTPUT_PATH, REPORT_DATE
from src.etl import etl_pipeline, load_flat
from src.analytics import build_analytics
from src.report import build_html


def main():
    print("=" * 62)
    print("  NCD Surveillance Intelligence Platform — WHO AFRO")
    print("  Build Pipeline")
    print("=" * 62)

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1. ETL
    print(f"\n[1/4] ETL: Extract -> Transform -> Load ...")
    etl_pipeline(EXCEL_PATH, DB_PATH)
    print("      OK: Star schema populated")

    # 2. Analytics
    print(f"\n[2/4] Analytics: Loading from SQLite ...")
    df = load_flat(DB_PATH)
    print(f"      OK: {len(df)} records loaded from fact_surveys")

    print(f"\n[3/4] Analytics: Computing SPI, cycle metrics, KPIs ...")
    A = build_analytics(df)
    reg_spi = A["regional_spi"]
    n_strong = A["n_strong"]
    n_crit = A["n_critical"]
    print(f"      OK: Regional SPI = {reg_spi}/100  |  Strong: {n_strong}  |  Critical: {n_crit}")

    # 3. Build HTML
    print(f"\n[4/4] Rendering charts & assembling HTML report ...")
    html = build_html(A)
    print("      OK: All charts rendered")

    # 4. Write output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = OUTPUT_PATH.stat().st_size // 1024
    print(f"\n      OK: {size_kb} KB written -> {OUTPUT_PATH.name}")

    print("\n" + "=" * 62)
    print(f"  DONE. Open output/{OUTPUT_PATH.name} in your browser.")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
