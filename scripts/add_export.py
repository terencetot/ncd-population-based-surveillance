"""
Add Excel export.

ROOT CAUSE OF PREVIOUS FAILURES:
  Functions defined inside (function(){...})() are NOT in global scope.
  onclick="exportSPIXLS()" looks for window.exportSPIXLS -> not found -> silent fail.

FIX:
  - Give buttons unique IDs (no onclick attribute)
  - Attach event listeners INSIDE the IIFE (same pattern as all existing UI)
  - Listeners have closure access to IIFE variables (_SPI_TABLE, etc.)

ALSO: zero backslash sequences in injected JS (Python triple-quote rule).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.stdout.reconfigure(encoding='utf-8')

with open(ROOT / 'src/report.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ---------------------------------------------------------------------------
# 1.  Export functions + event listener wiring — injected before IIFE close
# ---------------------------------------------------------------------------
EXPORT_JS = """
  // ── Excel export (XML Spreadsheet 2003) ──────────────────────────────────────
  function _xlEsc(v) {
    return String(v === null || v === undefined ? '' : v)
      .split('&').join('&amp;')
      .split('<').join('&lt;')
      .split('>').join('&gt;');
  }

  function _buildXLS(rows) {
    var Q   = '"';
    var xml = '<?xml version=' +Q+'1.0'+Q+' encoding='+Q+'UTF-8'+Q+'?>'
            + '<Workbook xmlns='+Q+'urn:schemas-microsoft-com:office:spreadsheet'+Q
            + ' xmlns:ss='+Q+'urn:schemas-microsoft-com:office:spreadsheet'+Q+'>'
            + '<Worksheet ss:Name='+Q+'Data'+Q+'><Table>';
    rows.forEach(function(row) {
      xml += '<Row>';
      row.forEach(function(cell) {
        var t = (typeof cell === 'number') ? 'Number' : 'String';
        xml += '<Cell><Data ss:Type='+Q+t+Q+'>'+_xlEsc(cell)+'</Data></Cell>';
      });
      xml += '</Row>';
    });
    return xml + '</Table></Worksheet></Workbook>';
  }

  function _saveXLS(filename, rows) {
    var xml  = _buildXLS(rows);
    var link = document.createElement('a');
    link.style.display = 'none';
    link.setAttribute('download', filename);
    link.setAttribute('href',
      'data:application/vnd.ms-excel;charset=utf-8,' + encodeURIComponent(xml));
    document.body.appendChild(link);
    link.click();
    setTimeout(function() { document.body.removeChild(link); }, 500);
  }

  // ── SPI export ────────────────────────────────────────────────────────────────
  var _SPI_TABLE = __SPI_TABLE_PLACEHOLDER__;

  function _doExportSPI() {
    var rows = [['Rank','Country','ISO3','SPI Score','Tier','Tier Label',
                 'Breadth (%)','Currency (%)','Regularity (%)','Last Survey Year',
                 'Gap (years)','Completed Surveys','Instrument Types Used']];
    (_SPI_TABLE || []).forEach(function(r, i) {
      rows.push([
        i + 1, r.country, r.iso3 || '', r.spi, r.tier, r.tier_label,
        r.d_coverage, r.d_recency,
        (r.d_regularity !== null && r.d_regularity !== undefined) ? r.d_regularity : '',
        (r.last_year    !== null && r.last_year    !== undefined) ? r.last_year    : '',
        (r.gap_years    !== null && r.gap_years    !== undefined) ? r.gap_years    : '',
        r.n_done, r.types_done
      ]);
    });
    _saveXLS('NCD_AFRO_SPI_Rankings.xls', rows);
  }

  // ── Country Profile export ────────────────────────────────────────────────────
  function _doExportProfile() {
    if (!_profileCurrent) {
      alert('Please select a country from the dropdown first.');
      return;
    }
    if (!STEPS_PROFILE_DATA || !STEPS_PROFILE_DATA.profiles) return;
    var p = STEPS_PROFILE_DATA.profiles[_profileCurrent]; if (!p) return;
    var ind = STEPS_PROFILE_DATA.indicators || {};
    var sec = STEPS_PROFILE_DATA.sections   || {};
    var rows = [['Country','ISO3','Survey Year','Section','Indicator Code',
                 'Indicator','Unit','Both Sexes','Males','Females',
                 '95% CI Lower','95% CI Upper']];
    p.surveys.forEach(function(sv) {
      var yrData = p.data[String(sv.year)] || {};
      Object.keys(yrData).sort().forEach(function(code) {
        var vals = yrData[code];
        var i2 = ind[code] || {};
        var sc = sec[i2.sec] || {};
        rows.push([
          _profileCurrent, p.iso3 || '', sv.year,
          sc.name || i2.sec || '', code, i2.label || code, i2.unit || '%',
          (vals.b  !== undefined && vals.b  !== null) ? vals.b  : '',
          (vals.m  !== undefined && vals.m  !== null) ? vals.m  : '',
          (vals.f  !== undefined && vals.f  !== null) ? vals.f  : '',
          (vals.lo !== undefined && vals.lo !== null) ? vals.lo : '',
          (vals.hi !== undefined && vals.hi !== null) ? vals.hi : ''
        ]);
      });
    });
    _saveXLS(_profileCurrent.split(' ').join('_') + '_STEPS.xls', rows);
  }

  // ── Wire buttons via addEventListener (NOT onclick) ───────────────────────────
  (function() {
    var btnSPI  = document.getElementById('btn-export-spi');
    var btnProf = document.getElementById('btn-export-profile');
    if (btnSPI)  btnSPI.addEventListener('click',  _doExportSPI);
    if (btnProf) btnProf.addEventListener('click',  _doExportProfile);
  })();
"""

IIFE_CLOSE = "})();\n\"\"\""
if IIFE_CLOSE not in src:
    print("ERROR: IIFE close not found"); sys.exit(1)
src = src.replace(IIFE_CLOSE, EXPORT_JS + "})();\n\"\"\"", 1)
print("JS injected")

# ---------------------------------------------------------------------------
# 2.  SPI table JSON
# ---------------------------------------------------------------------------
OLD_SPI = (
    '    spi_scores_json       = _json.dumps(\n'
    '        {row["country"]: round(float(row["spi"]), 1) for _, row in A["spi"].iterrows()},\n'
    '        ensure_ascii=False\n'
    '    )'
)
NEW_SPI = (
    '    spi_scores_json = _json.dumps(\n'
    '        {row["country"]: round(float(row["spi"]), 1) for _, row in A["spi"].iterrows()},\n'
    '        ensure_ascii=False\n'
    '    )\n'
    '    import pandas as _pd\n'
    '    spi_table_json = _json.dumps([\n'
    '        {"country": str(r["country"]),\n'
    '         "iso3":  str(r["iso3"]) if _pd.notna(r["iso3"]) else "",\n'
    '         "spi":   round(float(r["spi"]),  1),\n'
    '         "tier":  int(r["tier"]),\n'
    '         "tier_label": str(r["tier_label"]),\n'
    '         "d_coverage":  round(float(r["d_coverage"]),  1),\n'
    '         "d_recency":   round(float(r["d_recency"]),   1),\n'
    '         "d_regularity": round(float(r["d_regularity"]), 1) if _pd.notna(r["d_regularity"]) else None,\n'
    '         "last_year": int(r["last_year"]) if _pd.notna(r["last_year"]) else None,\n'
    '         "gap_years": int(r["gap_years"]) if _pd.notna(r["gap_years"]) else None,\n'
    '         "n_done":    int(r["n_done"]),\n'
    '         "types_done":int(r["types_done"])}\n'
    '        for _, r in A["spi"].iterrows()\n'
    '    ], ensure_ascii=False)'
)
if OLD_SPI not in src:
    print("ERROR: SPI block not found"); sys.exit(1)
src = src.replace(OLD_SPI, NEW_SPI, 1)
print("SPI table JSON added")

# ---------------------------------------------------------------------------
# 3.  Placeholder in replace chain
# ---------------------------------------------------------------------------
OLD_CHAIN = '.replace("__STEPS_PROFILE_PLACEHOLDER__", steps_profile_json))'
NEW_CHAIN = (
    '.replace("__STEPS_PROFILE_PLACEHOLDER__", steps_profile_json)\n'
    '                      .replace("__SPI_TABLE_PLACEHOLDER__", spi_table_json))'
)
if OLD_CHAIN not in src:
    print("ERROR: replace chain not found"); sys.exit(1)
src = src.replace(OLD_CHAIN, NEW_CHAIN, 1)
print("Placeholder added")

# ---------------------------------------------------------------------------
# 4.  HTML buttons — with IDs, NO onclick attribute
# ---------------------------------------------------------------------------
BTN = (
    'style="font-family:var(--font);font-size:11px;font-weight:700;'
    'padding:7px 16px;border-radius:8px;border:none;'
    'background:#003d82;color:#fff;cursor:pointer;'
    'display:inline-flex;align-items:center;gap:6px;"'
)

OLD_SC = (
    '      <div class="chart-card reveal" style="margin-bottom:20px;">\n'
    '        {scorecard_table(spi)}\n'
    '      </div>'
)
NEW_SC = (
    '      <div class="chart-card reveal" style="margin-bottom:20px;">\n'
    '        <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">\n'
    f'          <button id="btn-export-spi" {BTN}>'
    '<i class="fas fa-file-excel"></i>&nbsp;Export Excel</button>\n'
    '        </div>\n'
    '        {scorecard_table(spi)}\n'
    '      </div>'
)
if OLD_SC not in src:
    print("ERROR: scorecard not found"); sys.exit(1)
src = src.replace(OLD_SC, NEW_SC, 1)
print("SPI button added")

OLD_FB = (
    '        <span style="font-size:11px;color:var(--muted);font-style:italic;'
    'margin-left:4px;display:flex;align-items:center;gap:5px;">\n'
    '          <i class="fas fa-lock" style="font-size:10px;"></i>'
    'Additional survey types coming soon\n'
    '        </span>\n'
    '      </div>'
)
NEW_FB = (
    '        <span style="font-size:11px;color:var(--muted);font-style:italic;'
    'margin-left:4px;display:flex;align-items:center;gap:5px;">\n'
    '          <i class="fas fa-lock" style="font-size:10px;"></i>'
    'Additional survey types coming soon\n'
    '        </span>\n'
    f'        <button id="btn-export-profile" {BTN} style="margin-left:auto;">'
    '<i class="fas fa-file-excel"></i>&nbsp;Export Excel</button>\n'
    '      </div>'
)
if OLD_FB not in src:
    print("ERROR: filter bar not found"); sys.exit(1)
src = src.replace(OLD_FB, NEW_FB, 1)
print("Profile button added")

# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------
with open(ROOT / 'src/report.py', 'w', encoding='utf-8') as f:
    f.write(src)
print(f"\nDone — {len(src.splitlines())} lines")
