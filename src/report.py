"""
NCD Surveillance Intelligence Platform - WHO African Region
Report builder: CSS, JavaScript, HTML assembly
"""
import base64
import json
import pandas as pd
from pathlib import Path
from src.config import (C, FONT, TIER_COLORS, TIER_LABELS, SURVEY_META,
                        CURRENT_YEAR, CYCLE_YEARS, CURRENT_CYCLE_START,
                        REPORT_DATE, ASSETS_DIR)
from src.charts import (fig_tier_donut, fig_spi_bar, fig_spi_choropleth,
                        fig_spi_components, fig_current_cycle,
                        fig_last_year_heatmap, fig_priority_scatter,
                        fig_timeline, fig_gap_bar, fig_survey_type_comparison)

# ── Embed assets as base64 ─────────────────────────────────────────────────────
def _b64(path: Path) -> str:
    """Return base64-encoded PNG as data URI string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""

_LOGOS_DIR = ASSETS_DIR / "logos"
_MAPS_DIR  = ASSETS_DIR / "maps"

WHO_LOGO_B64 = _b64(_LOGOS_DIR / "who_logo.png")
DPC_LOGO_B64 = _b64(_LOGOS_DIR / "dpc_logo.png")
FAV_LOGO_B64 = _b64(_LOGOS_DIR / "favicon.png")

# Load all country maps: {ISO3: base64_string}
COUNTRY_MAPS: dict = {}
if _MAPS_DIR.exists():
    for mp in sorted(_MAPS_DIR.glob("*.png")):
        COUNTRY_MAPS[mp.stem] = _b64(mp)

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --primary:#003d82;--secondary:#006eb6;--accent:#4a90e2;
  --success:#00a651;--warning:#f7941d;--danger:#c0392b;
  --light:#f4f7fb;--white:#fff;--dark:#0d1f4e;
  --text:#1e2a4a;--muted:#6b7280;--border:#e2e8f0;
  --font:'Poppins',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --shadow-sm:0 2px 8px rgba(0,20,80,.06);
  --shadow-md:0 6px 20px rgba(0,20,80,.10);
  --shadow-lg:0 14px 36px rgba(0,20,80,.15);
  --radius:14px;
}
html{scroll-behavior:smooth}
body{font-family:var(--font);background:#f0f4fa;color:var(--text);line-height:1.65;font-size:14px;overflow-x:hidden}
@keyframes fadeScale{from{opacity:0;transform:scale(.96) translateY(12px)}to{opacity:1;transform:scale(1) translateY(0)}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-16px)}}
@keyframes shimmer{0%{background-position:-600px 0}100%{background-position:600px 0}}
@keyframes slideDown{from{opacity:0;transform:translateY(-16px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
/* ── Reading progress ── */
#reading-progress{position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,#00a651,#4a90e2,#56d0ff);width:0%;z-index:9999;transition:width .1s linear}
/* ── Back to top ── */
#back-to-top{position:fixed;bottom:32px;right:32px;width:46px;height:46px;background:var(--primary);color:#fff;border:none;border-radius:50%;font-size:17px;cursor:pointer;display:none;align-items:center;justify-content:center;box-shadow:var(--shadow-lg);transition:all .25s;z-index:999}
#back-to-top:hover{background:var(--accent);transform:translateY(-5px) scale(1.08)}
/* ── Top nav ── */
.topnav{position:sticky;top:0;z-index:1000;background:linear-gradient(135deg,#000d28 0%,#001a4a 40%,#003270 70%,#004d99 100%);box-shadow:0 4px 28px rgba(0,10,50,.6);height:70px;animation:slideDown .5s ease;border-bottom:1px solid rgba(255,255,255,.1)}
.topnav::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#003d82,#4a90e2,#56d0ff,#00a651,#56d0ff,#4a90e2,#003d82);background-size:400% auto;animation:shimmer 10s linear infinite}
.topnav-inner{max-width:1400px;margin:0 auto;padding:0 32px;height:100%;display:flex;align-items:center;justify-content:space-between;gap:20px}
.nav-logos{display:flex;align-items:center;gap:18px;flex-shrink:0}
.nav-logos img{height:40px;object-fit:contain;filter:brightness(1.05)}
.nav-divider{width:1px;height:34px;background:rgba(255,255,255,.18)}
.nav-brand-text{display:flex;flex-direction:column;justify-content:center}
.nav-brand-title{color:#fff;font-weight:800;font-size:14px;letter-spacing:-.015em;line-height:1.2}
.nav-brand-sub{color:rgba(255,255,255,.5);font-size:10.5px;font-weight:500;letter-spacing:.4px;margin-top:2px}
.nav-right{display:flex;align-items:center;gap:14px;flex-shrink:0}
.nav-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);border-radius:20px;padding:5px 13px;font-size:11px;font-weight:600;color:rgba(255,255,255,.75);white-space:nowrap;transition:background .2s}
.nav-badge:hover{background:rgba(255,255,255,.14)}
.nav-badge i{font-size:10px;color:rgba(255,255,255,.55)}
.nav-date{color:rgba(255,255,255,.6);font-size:11px;background:rgba(255,255,255,.09);padding:6px 14px;border-radius:20px;border:1px solid rgba(255,255,255,.15);white-space:nowrap;flex-shrink:0;display:flex;align-items:center;gap:6px}
/* ── Hero ── */
@keyframes badgeIn{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:translateX(0)}}
.hero{background:#fff;padding:0;position:relative;overflow:hidden;border-bottom:1px solid var(--border)}
/* Subtle dot-grid on the left panel */
.hero::after{content:'';position:absolute;top:0;left:0;width:60%;bottom:0;background-image:radial-gradient(rgba(74,144,226,.07) 1px,transparent 1px);background-size:26px 26px;pointer-events:none;z-index:0}
.hero-inner{display:flex;align-items:stretch;min-height:290px}
.hero-left{flex:1;padding:56px 60px 52px;display:flex;flex-direction:column;justify-content:center;position:relative;z-index:1}
.hero-right{width:370px;flex-shrink:0;background:linear-gradient(155deg,#000a1e 0%,#001540 30%,#002f70 65%,#0050a0 100%);display:flex;align-items:center;justify-content:center;padding:36px 30px;position:relative;overflow:hidden;clip-path:polygon(7% 0,100% 0,100% 100%,0% 100%)}
/* Dot-grid texture on right panel */
.hero-right::before{content:'';position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.055) 1px,transparent 1px);background-size:20px 20px;z-index:1;pointer-events:none}
.hero-right-orb{position:absolute;border-radius:50%;pointer-events:none}
.hero-right-orb-1{width:340px;height:340px;top:-90px;right:-90px;background:radial-gradient(circle,rgba(86,208,255,.2) 0%,transparent 65%);animation:float 9s ease-in-out infinite}
.hero-right-orb-2{width:220px;height:220px;bottom:-60px;left:-40px;background:radial-gradient(circle,rgba(0,166,81,.14) 0%,transparent 65%);animation:float 12s ease-in-out infinite reverse}
.hero-right-orb-3{width:130px;height:130px;top:40%;left:38%;background:radial-gradient(circle,rgba(74,144,226,.15) 0%,transparent 70%);animation:float 7s ease-in-out 2s infinite}
.hero-stats{display:flex;flex-direction:column;gap:12px;position:relative;z-index:2;width:100%}
/* Each badge staggered entrance */
.hero-stat-badge{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);border-radius:14px;padding:0;overflow:hidden;transition:background .25s,transform .25s,box-shadow .25s;cursor:default;animation:badgeIn .55s ease both}
.hero-stat-badge:nth-child(1){animation-delay:.15s;border-top:3px solid #4a90e2}
.hero-stat-badge:nth-child(2){animation-delay:.28s;border-top:3px solid #00a651}
.hero-stat-badge:nth-child(3){animation-delay:.41s}
.hero-stat-badge:hover{background:rgba(255,255,255,.12);transform:translateX(5px);box-shadow:0 4px 20px rgba(0,0,0,.25)}
.hero-stat-inner{padding:14px 18px}
.hero-stat-val{font-size:2.15rem;font-weight:900;color:#fff;line-height:1;letter-spacing:-.04em;display:flex;align-items:baseline;gap:4px}
.hero-stat-val sup{font-size:.85rem;font-weight:700;opacity:.6;margin-left:1px}
.hero-stat-lbl{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.8px;color:rgba(255,255,255,.42);margin-top:6px}
/* SPI progress bar */
.hero-spi-bar{height:3px;background:rgba(255,255,255,.12);margin:10px 18px 0;border-radius:2px;overflow:hidden}
.hero-spi-fill{height:100%;border-radius:2px;transition:width 1.2s cubic-bezier(.4,0,.2,1)}
/* Hero left */
.hero-eyebrow{font-size:10px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--accent);margin-bottom:20px;display:inline-flex;align-items:center;gap:10px;background:rgba(74,144,226,.08);border:1px solid rgba(74,144,226,.2);padding:5px 13px 5px 10px;border-radius:20px;align-self:flex-start}
.hero-eyebrow::before{content:'';display:inline-block;width:6px;height:6px;background:var(--accent);border-radius:50%;flex-shrink:0;animation:pulse 2.5s ease-in-out infinite}
.hero h1{font-size:3.5rem;font-weight:900;line-height:1.04;letter-spacing:-.055em;color:var(--dark);margin-bottom:14px;animation:fadeScale .8s ease forwards}
.grad{background:linear-gradient(90deg,#0065b3 0%,#4a90e2 50%,#56d0ff 100%);-webkit-background-clip:text;background-clip:text;color:transparent;background-size:200% auto;animation:shimmer 6s linear infinite}
.hero-sub{font-size:15px;color:#4a5568;max-width:620px;line-height:1.85;animation:fadeScale 1s ease .1s both;font-weight:400;margin-bottom:20px}
.hero-sub strong{color:var(--dark);font-weight:700}
/* Quick-stat pills below subtitle */
.hero-quick-stats{display:flex;flex-wrap:wrap;gap:8px;animation:fadeScale .9s ease .25s both}
.hero-qs{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;color:var(--muted);background:#f4f7fb;border:1px solid var(--border);border-radius:20px;padding:4px 12px;white-space:nowrap}
.hero-qs i{font-size:9px}
/* ── Reveal animation (hidden only when JS adds .will-animate) ── */
.reveal{transition:opacity .65s ease,transform .65s ease}
.reveal.will-animate{opacity:0;transform:translateY(28px)}
.reveal.visible{opacity:1;transform:translateY(0)}
/* ── Container ── */
.container{max-width:1400px;margin:0 auto;padding:0 28px;position:relative}
/* ── Wide-screen centering (>1400px): all frame elements stay centered ── */
@media(min-width:1500px){
  .topnav-inner,.tab-nav-inner,.footer-inner{max-width:1480px}
  .container{max-width:1480px}
  .hero-inner{max-width:1480px;margin:0 auto}
  .hero-left{padding-left:clamp(40px,4vw,80px)}
  .hero h1{font-size:clamp(3rem,3.8vw,4.4rem)}
  .nav-brand-title{font-size:clamp(12px,1vw,15px)}
}
@media(min-width:1800px){
  .topnav-inner,.tab-nav-inner,.footer-inner{max-width:1600px}
  .container{max-width:1600px}
  .hero-inner{max-width:1600px}
}
body{background:#f0f4fa}
/* ── Layout ── */
.row{display:flex;flex-wrap:wrap;gap:20px;margin-bottom:20px}
.col-12{flex:0 0 100%}.col-8{flex:0 0 calc(66.666% - 10px)}.col-7{flex:0 0 calc(58.333% - 9px)}.col-6{flex:0 0 calc(50% - 10px)}.col-5{flex:0 0 calc(41.666% - 11px)}.col-4{flex:0 0 calc(33.333% - 14px)}.col-3{flex:0 0 calc(25% - 15px)}
/* ── Section ── */
.section{padding:40px 0 24px}
.section-header{margin-bottom:28px}
.section-header-inner{display:inline-flex;align-items:center;gap:10px;margin-bottom:5px}
.section-num{background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;border-radius:8px;padding:3px 10px;font-size:11px;font-weight:700}
.section-title{font-size:1.55rem;font-weight:800;color:var(--dark);letter-spacing:-.025em;border-bottom:3px solid var(--accent);padding-bottom:3px;display:inline}
.section-subtitle{color:var(--muted);font-size:13px;margin-top:5px}
hr.section-divider{border:none;border-top:1px solid var(--border);margin:32px 0}
/* ── Cards ── */
.chart-card{background:#fff;border-radius:var(--radius);padding:22px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);height:100%;transition:transform .3s,box-shadow .3s,border-color .3s;position:relative;overflow:hidden}
.chart-card::before{content:'';position:absolute;inset:0;border-radius:var(--radius);opacity:0;background:linear-gradient(135deg,rgba(74,144,226,.05),rgba(0,166,81,.05));transition:opacity .3s;pointer-events:none}
.chart-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);border-color:rgba(74,144,226,.3)}
.chart-card:hover::before{opacity:1}
.chart-commentary{margin-top:12px;padding:12px 16px;background:linear-gradient(135deg,#f7fbff,#eef4ff);border-radius:10px;font-size:12.5px;color:var(--text);line-height:1.8;border-left:4px solid var(--accent)}
/* ── Insight boxes ── */
.insight-box{display:flex;align-items:flex-start;gap:12px;padding:14px 18px;border-radius:10px;margin-bottom:12px;font-size:13px;line-height:1.75;transition:transform .2s}
.insight-box:hover{transform:translateX(4px)}
.insight-icon{font-size:16px;flex-shrink:0;margin-top:2px}
/* ── KPI cards ── */
.kpi-row{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:28px}
.kpi-card{flex:1;min-width:145px;background:#fff;border-radius:var(--radius);padding:20px 18px 17px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);transition:transform .28s,box-shadow .28s;position:relative;overflow:hidden}
.kpi-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:currentColor;opacity:.3}
.kpi-card:hover{transform:translateY(-5px);box-shadow:var(--shadow-md)}
.kpi-icon{font-size:22px;margin-bottom:9px}
.kpi-value{font-size:2rem;font-weight:800;line-height:1;margin-bottom:5px;letter-spacing:-.03em}
.kpi-label{font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.9px;color:var(--muted)}
.kpi-delta{font-size:11px;margin-top:6px;font-weight:600;display:flex;align-items:center;gap:4px}
/* ── Instrument cards ── */
.instrument-grid{display:flex;flex-wrap:wrap;gap:18px;margin-bottom:24px}
.instrument-card{flex:1;min-width:200px;background:#fff;border-radius:var(--radius);padding:20px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);transition:transform .28s,box-shadow .28s}
.instrument-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-md)}
.inst-type{font-size:22px;font-weight:900;letter-spacing:-.02em;margin-bottom:4px}
.inst-full{font-size:11.5px;color:var(--muted);line-height:1.5;margin-bottom:10px;min-height:34px}
.inst-meta{display:flex;flex-direction:column;gap:3px;margin-bottom:12px}
.inst-meta span{font-size:11px;color:var(--muted);display:flex;align-items:center;gap:5px}
.inst-stats{display:flex;gap:14px;margin-bottom:12px}
.inst-stat{display:flex;flex-direction:column;align-items:center}
.stat-val{font-size:1.4rem;font-weight:800;line-height:1;color:var(--dark)}
.stat-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted)}
.inst-bar-wrap{height:6px;background:#f0f0f0;border-radius:3px;overflow:hidden;margin-bottom:5px}
.inst-bar{height:6px;border-radius:3px}
.inst-pct{font-size:11.5px;font-weight:700}
/* ── Recommendations ── */
.rec-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px;margin-top:8px}
.rec-card{background:#fff;border-radius:var(--radius);padding:22px 24px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);display:flex;gap:18px;align-items:flex-start;transition:transform .28s,box-shadow .28s}
.rec-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-md)}
.rec-num{width:34px;height:34px;background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:800;flex-shrink:0}
.rec-content h4{font-size:13.5px;font-weight:700;color:var(--dark);margin-bottom:7px}
.rec-content p{font-size:12.5px;color:var(--muted);line-height:1.75}
/* ── Methods ── */
.methods-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.method-card{background:#fff;border-radius:var(--radius);padding:22px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border)}
.method-card h4{font-size:13.5px;font-weight:700;color:var(--dark);margin-bottom:12px;display:flex;align-items:center;gap:8px}
.method-card ul{list-style:none;padding:0}
.method-card li{font-size:12.5px;color:var(--muted);padding:4px 0;border-bottom:1px solid #f5f5f5;line-height:1.65}
.method-card li:last-child{border-bottom:none}
.method-card li code{background:#f0f4ff;padding:1px 6px;border-radius:4px;font-family:monospace;font-size:11px;color:var(--primary)}
/* ── Footer ── */
.footer{background:linear-gradient(135deg,#000d28,#001a4a);color:rgba(255,255,255,.7);padding:0;margin-top:40px}
.footer-inner{max-width:1400px;margin:0 auto;padding:28px 32px;display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
.footer-badge{display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:20px;padding:3px 11px;font-size:11px;margin:2px;color:rgba(255,255,255,.8)}
/* ══ TABS ════════════════════════════════════════════════════════════════════ */
.tab-nav{background:linear-gradient(to bottom,#ffffff 0%,#f5f8ff 100%);border-bottom:2px solid var(--border);position:sticky;top:70px;z-index:990;box-shadow:0 4px 18px rgba(0,20,80,.09);overflow-x:auto}
.tab-nav-inner{max-width:1400px;margin:0 auto;padding:0 16px;display:flex;gap:0}
.tab-btn{background:none;border:none;padding:13px 22px;font-family:var(--font);font-size:12.5px;font-weight:600;color:var(--muted);cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;gap:8px;letter-spacing:-.01em;position:relative;transition:color .22s,background .22s;border-radius:0}
.tab-btn::before{content:'';position:absolute;bottom:6px;top:6px;left:8px;right:8px;border-radius:8px;background:linear-gradient(135deg,rgba(0,61,130,.08),rgba(74,144,226,.06));opacity:0;transition:opacity .25s}
.tab-btn::after{content:'';position:absolute;bottom:-2px;left:18px;right:18px;height:3px;background:linear-gradient(90deg,var(--primary),var(--accent));border-radius:3px 3px 0 0;opacity:0;transition:opacity .25s,left .25s,right .25s}
.tab-btn:hover{color:var(--primary)}
.tab-btn:hover::before{opacity:.6}
.tab-btn:hover::after{opacity:.3}
.tab-btn.active{color:var(--primary);font-weight:800}
.tab-btn.active::before{opacity:1}
.tab-btn.active::after{opacity:1;left:8px;right:8px}
.tab-btn i{font-size:12px;opacity:.65;transition:opacity .2s,color .2s}
.tab-btn.active i{opacity:1;color:var(--accent)}
.tab-btn:hover i{opacity:.9}
.tab-pane{display:none}
.tab-pane.active{display:block}
/* ══ FILTER BAR ═════════════════════════════════════════════════════════════ */
.filter-bar{background:#fff;border:1.5px solid var(--border);border-radius:var(--radius);padding:14px 20px;margin-bottom:22px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;box-shadow:var(--shadow-sm)}
.filter-label{font-size:10.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;white-space:nowrap}
.filter-select{border:1.5px solid var(--border);border-radius:8px;padding:7px 12px;font-family:var(--font);font-size:12px;color:var(--text);background:#fafbff;cursor:pointer;outline:none;transition:border-color .2s,box-shadow .2s}
.filter-select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(74,144,226,.12)}
.filter-input{border:1.5px solid var(--border);border-radius:8px;padding:7px 13px;font-family:var(--font);font-size:12px;color:var(--text);background:#fafbff;outline:none;width:175px;transition:border-color .2s,box-shadow .2s}
.filter-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(74,144,226,.12)}
.filter-reset{background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;border:none;border-radius:8px;padding:8px 16px;font-family:var(--font);font-size:12px;font-weight:600;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:6px}
.filter-reset:hover{box-shadow:0 4px 14px rgba(74,144,226,.4);transform:translateY(-1px)}
.filter-count{font-size:11px;color:var(--muted);margin-left:auto;font-style:italic;white-space:nowrap}
/* ══ TABLES ═════════════════════════════════════════════════════════════════ */
.prio-table{width:100%;border-collapse:collapse;font-size:12.5px}
.prio-table th{background:linear-gradient(135deg,var(--primary),#005fa3);color:#fff;padding:10px 13px;text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;font-weight:700;position:sticky;top:0;z-index:1}
.prio-table td{padding:9px 13px;border-bottom:1px solid var(--border)}
.prio-table tbody tr{transition:background .15s}
.prio-table tbody tr:hover td{background:#f0f6ff}
.rank-cell{font-weight:700;color:var(--muted);font-size:12px;text-align:center}
.num-cell{text-align:center;font-variant-numeric:tabular-nums}
/* Country map thumbnail */
.country-map{width:40px;height:28px;object-fit:contain;opacity:.85;border-radius:3px;background:#f5f8ff;padding:2px;border:1px solid #e8eef8;vertical-align:middle;margin-right:8px;transition:opacity .2s}
.country-map:hover{opacity:1}
/* ══ EXECUTIVE SIGNALS ══════════════════════════════════════════════════════ */
.signal-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-bottom:28px}
.signal-card{background:#fff;border-radius:var(--radius);padding:24px 22px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);position:relative;overflow:hidden;transition:transform .3s,box-shadow .3s}
.signal-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:currentColor;opacity:.5;border-radius:var(--radius) var(--radius) 0 0}
.signal-card::after{content:'';position:absolute;bottom:-30px;right:-20px;width:100px;height:100px;border-radius:50%;background:currentColor;opacity:.04}
.signal-card:hover{transform:translateY(-5px);box-shadow:var(--shadow-md)}
.signal-val{font-size:2.8rem;font-weight:900;line-height:1;letter-spacing:-.05em}
.signal-lbl{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-top:8px}
.signal-sub{font-size:11.5px;color:var(--muted);margin-top:5px;line-height:1.55}
/* ══ EXECUTIVE MESSAGE ══════════════════════════════════════════════════════ */
.exec-message{background:linear-gradient(135deg,#000d28 0%,#001a4a 50%,#003270 100%);color:#fff;border-radius:var(--radius);padding:30px 34px;margin-bottom:28px;position:relative;overflow:hidden;box-shadow:0 8px 32px rgba(0,10,50,.3)}
.exec-message::before{content:'';position:absolute;top:-60px;right:-60px;width:200px;height:200px;border-radius:50%;background:radial-gradient(circle,rgba(74,144,226,.15),transparent);pointer-events:none}
.exec-message h3{font-size:1.1rem;font-weight:800;margin-bottom:12px;color:#56d0ff;letter-spacing:-.01em;display:flex;align-items:center;gap:10px}
.exec-message p{font-size:13.5px;line-height:1.9;opacity:.9;max-width:900px}
.exec-message strong{color:#fff}
/* ══ TIER BADGE ═════════════════════════════════════════════════════════════ */
.tier-badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:10.5px;font-weight:700;color:#fff;vertical-align:middle}
.schema-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px;margin-bottom:24px}
.schema-card{background:#fff;border-radius:12px;border:1.5px solid var(--border);overflow:hidden;box-shadow:0 4px 12px rgba(0,20,80,.06)}
.schema-card-head{padding:11px 16px;font-weight:700;font-size:12.5px;color:#fff;display:flex;align-items:center;gap:8px}
.schema-card table{width:100%;border-collapse:collapse;font-size:12px}
.schema-card table tr{border-bottom:1px solid var(--border)}
.schema-card table td{padding:7px 14px;color:var(--muted)}
.schema-card table td:first-child{color:var(--text);font-weight:500;font-family:monospace;font-size:11.5px}
@media(max-width:920px){.col-6,.col-4,.col-3,.col-8,.col-7,.col-5{flex:0 0 100%}.hero h1{font-size:2.2rem}.hero-right{display:none}.hero-left{padding:36px 28px 32px}}
@media(max-width:1100px){.signal-grid[style*="repeat(5"]{grid-template-columns:repeat(3,1fr)!important}}
@media(max-width:700px){.signal-grid[style*="repeat(5"]{grid-template-columns:repeat(2,1fr)!important}}
/* ══ TIER SUMMARY CARDS ══════════════════════════════════════════════════ */
.tier-row{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:24px;}
.tier-card{flex:1;min-width:130px;background:#fff;border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);border-top-width:4px;transition:transform .28s,box-shadow .28s;}
.tier-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-md);}
.tier-card-val{font-size:2.2rem;font-weight:900;line-height:1;letter-spacing:-.04em;}
.tier-card-lbl{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-top:6px;}
.tier-card-sub{font-size:11px;color:var(--muted);margin-top:3px;}
/* ══ STAT HIGHLIGHT ROW ══════════════════════════════════════════════════ */
.stat-highlight-row{display:flex;flex-wrap:wrap;gap:14px;background:#fff;border-radius:var(--radius);padding:20px 24px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);margin-bottom:22px;align-items:center;}
.stat-highlight-item{display:flex;flex-direction:column;align-items:center;padding:0 16px;border-right:1px solid var(--border);last-child:border-right:none;}
.stat-highlight-item:last-child{border-right:none;}
.stat-hl-val{font-size:2rem;font-weight:900;letter-spacing:-.04em;line-height:1;}
.stat-hl-lbl{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin-top:5px;}
/* ══ SECTION DIVIDER LABEL ═══════════════════════════════════════════════ */
.section-divider-label{display:flex;align-items:center;gap:12px;margin:28px 0 18px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);}
.section-divider-label::before,.section-divider-label::after{content:'';flex:1;height:1px;background:var(--border);}
/* ══ COUNTRY PROFILE TAB ═════════════════════════════════════════════════ */
.profile-header-card{background:linear-gradient(135deg,#f4f7fc 0%,#eef2f8 100%);border:1.5px solid var(--border);border-radius:var(--radius);padding:24px 28px;box-shadow:var(--shadow-sm);position:relative;overflow:hidden;}
.profile-header-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--primary),var(--accent),#56d0ff);border-radius:var(--radius) var(--radius) 0 0;}
.profile-iso-badge{display:inline-flex;align-items:center;justify-content:center;width:60px;height:44px;background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;border-radius:10px;font-size:11px;font-weight:800;letter-spacing:.5px;flex-shrink:0;box-shadow:0 4px 12px rgba(0,61,130,.25);}
.profile-kpi-row{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:22px;}
.profile-kpi-card{flex:1;min-width:150px;background:#fff;border-radius:var(--radius);padding:18px 16px 14px;box-shadow:var(--shadow-sm);border:1.5px solid var(--border);position:relative;overflow:hidden;transition:transform .28s,box-shadow .28s;}
.profile-kpi-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-md);}
.profile-kpi-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:currentColor;opacity:.25;}
.profile-kpi-icon{font-size:20px;margin-bottom:8px;}
.profile-kpi-value{font-size:1.9rem;font-weight:900;line-height:1;letter-spacing:-.03em;margin-bottom:4px;}
.profile-kpi-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.9px;color:var(--muted);}
.profile-kpi-trend{font-size:12px;margin-top:6px;font-weight:700;}
.profile-kpi-sex{display:flex;gap:6px;margin-top:8px;}
.profile-kpi-sex span{font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:8px;}
.profile-section-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px;margin-bottom:24px;}
.profile-section-card{background:#fff;border-radius:var(--radius);box-shadow:var(--shadow-sm);border:1.5px solid var(--border);overflow:hidden;transition:transform .28s,box-shadow .28s;}
.profile-section-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);}
.profile-section-head{padding:10px 15px;display:flex;align-items:center;gap:8px;}
.profile-section-head span.sec-title{font-size:12px;font-weight:700;color:#fff;flex:1;}
.profile-section-head span.sec-step{font-size:9.5px;color:rgba(255,255,255,.65);font-style:italic;}
.profile-ind-table{width:100%;border-collapse:collapse;font-size:11px;}
.profile-ind-table th{padding:6px 8px;font-size:9px;text-transform:uppercase;letter-spacing:.5px;font-weight:700;background:#f7f9ff;border-bottom:1px solid var(--border);white-space:nowrap;}
.profile-ind-table td{padding:6px 8px;border-bottom:1px solid #f3f5fb;vertical-align:middle;line-height:1.45;}
.profile-ind-table tbody tr:last-child td{border-bottom:none;}
.profile-ind-table tbody tr:hover td{background:#f0f5ff;}
.profile-no-data{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:64px 20px;color:var(--muted);text-align:center;gap:16px;}
.profile-no-data i{font-size:40px;opacity:.28;}
.profile-survey-pill{display:inline-flex;align-items:center;gap:5px;background:rgba(0,61,130,.08);border:1px solid rgba(0,61,130,.18);border-radius:20px;padding:3px 11px;font-size:10.5px;font-weight:600;color:var(--primary);}
.profile-cmp-badge{display:inline-block;font-size:10px;font-weight:700;padding:1px 6px;border-radius:6px;vertical-align:middle;}
"""

# ── JavaScript ─────────────────────────────────────────────────────────────────
JS = """
(function(){
  const bar=document.getElementById('reading-progress');
  const btn=document.getElementById('back-to-top');
  if(bar&&btn){
    window.addEventListener('scroll',()=>{
      const p=window.scrollY/(document.documentElement.scrollHeight-window.innerHeight)*100;
      bar.style.width=p+'%';
      btn.style.display=window.scrollY>300?'flex':'none';
    },{passive:true});
    btn.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
  }
  // Mark reveal elements for animation only when JS is running
  document.querySelectorAll('.reveal').forEach(el=>el.classList.add('will-animate'));
  const ro=new IntersectionObserver((es)=>{
    es.forEach((e,i)=>{if(e.isIntersecting){setTimeout(()=>e.target.classList.add('visible'),i*55);ro.unobserve(e.target);}});
  },{threshold:0.04});
  document.querySelectorAll('.reveal').forEach(el=>ro.observe(el));
  function animCount(el,target,dur){
    const isF=target%1!==0,t0=performance.now();
    const step=now=>{const p=Math.min((now-t0)/dur,1),e2=1-Math.pow(1-p,3),v=target*e2;
      el.textContent=isF?v.toFixed(1):Math.round(v).toLocaleString();
      if(p<1)requestAnimationFrame(step);else el.textContent=isF?target.toFixed(1):target.toLocaleString();
    };requestAnimationFrame(step);
  }
  const ko=new IntersectionObserver((es)=>{
    es.forEach(e=>{if(e.isIntersecting&&!e.target.dataset.counted){
      e.target.dataset.counted='1';
      e.target.querySelectorAll('[data-count]').forEach(el=>animCount(el,parseFloat(el.dataset.count),1400));
    }});
  },{threshold:0.15});
  document.querySelectorAll('.signal-grid,.kpi-row').forEach(el=>ko.observe(el));
  const bo=new IntersectionObserver((es)=>{
    es.forEach(e=>{if(e.isIntersecting){
      e.target.querySelectorAll('.inst-bar').forEach(b=>{
        const w=b.style.width;b.style.width='0';
        setTimeout(()=>{b.style.transition='width 1.1s cubic-bezier(0.22,1,0.36,1)';b.style.width=w;},80);
      });bo.unobserve(e.target);
    }});
  },{threshold:0.2});
  document.querySelectorAll('.instrument-card').forEach(c=>bo.observe(c));

  function activateTab(id){
    document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    const pane=document.getElementById(id);
    const btn=document.querySelector('.tab-btn[data-tab="'+id+'"]');
    if(pane)pane.classList.add('active');
    if(btn)btn.classList.add('active');
    window.scrollTo({top:62,behavior:'smooth'});
    if(pane){
      pane.querySelectorAll('.reveal:not(.visible)').forEach((el,i)=>{el.classList.add('will-animate');setTimeout(()=>el.classList.add('visible'),i*45);});
      pane.querySelectorAll('.signal-grid,.kpi-row').forEach(el=>{
        if(!el.dataset.counted){el.dataset.counted='1';el.querySelectorAll('[data-count]').forEach(e=>animCount(e,parseFloat(e.dataset.count),1400));}
      });
      window.dispatchEvent(new Event('resize'));
      setTimeout(function(){
        window.dispatchEvent(new Event('resize'));
        if(typeof Plotly==='undefined')return;
        pane.querySelectorAll('.plotly-graph-div').forEach(function(el){
          try{Plotly.relayout(el,{autosize:true});}catch(e){}
        });
      },250);
    }
  }
  document.querySelectorAll('.tab-btn').forEach(btn=>btn.addEventListener('click',()=>activateTab(btn.dataset.tab)));
  const firstTab=document.querySelector('.tab-btn');if(firstTab)activateTab(firstTab.dataset.tab);

  function applyFilters(tableId,searchId,tierSelId,gapSelId,cycleSelId,regSelId,topSelId,countId){
    const tbl=document.getElementById(tableId);if(!tbl)return;
    const search=((document.getElementById(searchId)||{}).value||'').toLowerCase();
    const tier=((document.getElementById(tierSelId)||{}).value||'');
    const gap=((document.getElementById(gapSelId)||{}).value||'');
    const cycle=((document.getElementById(cycleSelId)||{}).value||'');
    const reg=((document.getElementById(regSelId)||{}).value||'').toLowerCase();
    const top=parseInt(((document.getElementById(topSelId)||{}).value||'0'))||0;
    let vis=0;
    const rows=tbl.querySelectorAll('tbody tr');
    rows.forEach(tr=>{
      let show=true;
      if(search&&!(tr.dataset.country||'').includes(search))show=false;
      if(tier&&(tr.dataset.tier||'')!==tier)show=false;
      if(gap&&(tr.dataset.gap||'')!==gap)show=false;
      if(cycle&&(tr.dataset.cycle||'')!==cycle)show=false;
      if(reg&&!(tr.dataset.reg||'').toLowerCase().includes(reg))show=false;
      tr.style.display=show?'':'none';
      if(show)vis++;
    });
    if(top>0){let n=0;rows.forEach(tr=>{if(tr.style.display!=='none'){n++;if(n>top)tr.style.display='none';}});vis=Math.min(vis,top);}
    const cnt=document.getElementById(countId);
    if(cnt)cnt.textContent='Showing '+vis+' of '+rows.length+' countries';
  }
  function bindFilters(tId,sId,trId,gId,cId,rgId,topId,rId,cntId){
    [sId,trId,gId,cId,rgId,topId].forEach(id=>{
      const el=document.getElementById(id);
      if(el){el.addEventListener('input',()=>applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId));
              el.addEventListener('change',()=>applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId));}
    });
    const rb=document.getElementById(rId);
    if(rb)rb.addEventListener('click',()=>{
      [sId,trId,gId,cId,rgId,topId].forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});
      applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId);
    });
    applyFilters(tId,sId,trId,gId,cId,rgId,topId,cntId);
  }
  bindFilters('scorecard-table','sc-search','sc-tier','sc-gap','sc-cycle','sc-reg','sc-top','sc-reset','sc-count');
  bindFilters('prio-table-el','pr-search','pr-tier','pr-gap','pr-cycle','','pr-top','pr-reset','pr-count');

  // ── Executive Overview dynamic filter ────────────────────────────────────
  const EXEC_DATA = __EXEC_DATA_PLACEHOLDER__;

  // ── Cycle & Gap - Historical Activity Timeline ────────────────────────────
  const TIMELINE_DATA = __TIMELINE_DATA_PLACEHOLDER__;

  // ── Strategic Priority - overall SPI scores per country ──────────────────
  const SPI_SCORES = __SPI_SCORES_PLACEHOLDER__;

  const _FONT = "Poppins,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";
  const _STATUS_LABELS = ['On Cycle','Attempt to update','Off Cycle','Never Conducted'];
  const _STATUS_CLR = {
    'On Cycle':          '#00a651',
    'Attempt to update': '#4a90e2',
    'Off Cycle':         '#f7941d',
    'Never Conducted':   '#909090'
  };

  function updateExecDonut(d) {
    var divId='exec-donut-chart';
    var el=document.getElementById(divId);
    if(!el||typeof Plotly==='undefined')return;
    var valMap={
      'On Cycle':d.n_on_cycle,'Attempt to update':d.n_attempt_to_update,
      'Off Cycle':d.n_off_cycle,'Never Conducted':d.n_never
    };
    var total=d.n_total;
    var vals=_STATUS_LABELS.map(function(s){return valMap[s];});
    var colors=_STATUS_LABELS.map(function(s){return _STATUS_CLR[s];});
    var customText=_STATUS_LABELS.map(function(s){
      var v=valMap[s],pct=Math.round(v/total*100);
      return '<b>'+v+'</b><br>'+pct+'%';
    });
    Plotly.react(divId,[{
      type:'pie',labels:_STATUS_LABELS,values:vals,
      text:customText,textinfo:'text',textposition:'outside',
      textfont:{family:_FONT,size:12,color:'#333e5c'},
      marker:{colors:colors,line:{color:'#ffffff',width:3}},
      hole:0.65,sort:false,pull:[0.05,0,0,0],automargin:true,
      hovertemplate:'<b>%{label}</b><br>Countries: <b>%{value}</b> of '+total+'<br>%{percent}<extra></extra>',
    }],{
      paper_bgcolor:'#ffffff',plot_bgcolor:'#ffffff',
      font:{family:_FONT,size:12,color:'#333e5c'},
      height:420,margin:{l:60,r:60,t:64,b:40},
      showlegend:true,
      legend:{orientation:'h',y:-0.08,x:0.5,xanchor:'center',font:{size:12,family:_FONT},itemsizing:'constant'},
      title:{text:'<b>Surveillance Status Distribution</b>',font:{size:14,color:'#14265c',family:_FONT},x:0,xanchor:'left',pad:{l:4,t:4}},
      annotations:[{
        text:'<b>'+total+'</b><br><span style="font-size:11px">countries</span>',
        x:0.5,y:0.5,xref:'paper',yref:'paper',
        showarrow:false,font:{size:20,color:'#14265c',family:_FONT},align:'center',
      }],
    },{responsive:true,displayModeBar:false});
  }

  function updateGapChart(surveyKey) {
    var divId='exec-gap-chart';
    var el=document.getElementById(divId);
    if(!el||typeof Plotly==='undefined')return;
    var d=EXEC_DATA[surveyKey];
    if(!d||!d.countries_gap)return;
    var withData=d.countries_gap.filter(function(c){return c.gap!==null;});
    withData.sort(function(a,b){return a.gap-b.gap;});
    var noDataCount=d.countries_gap.length-withData.length;
    var names=withData.map(function(c){return c.country;});
    var gaps=withData.map(function(c){return c.gap;});
    var clrs=gaps.map(function(g){
      if(g>=15)return'#c0392b';
      if(g>=10)return'#f7941d';
      if(g>=5)return'#f1c40f';
      return'#00a651';
    });
    var hov=withData.map(function(c){
      return'<b>'+c.country+'</b><br>Last '+surveyKey+': <b>'+c.last_year+'</b><br>Gap: <b>'+c.gap+' year'+(c.gap===1?'':'s')+'</b>';
    });
    var maxGap=gaps.length>0?Math.max.apply(null,gaps):20;
    var noNote=noDataCount>0?'  <span style="font-size:11px;color:#6b7280">('+noDataCount+' countries with no completed '+surveyKey+' not shown)</span>':'';
    Plotly.react(divId,[{
      type:'bar',x:names,y:gaps,
      marker:{color:clrs,line:{color:'#fff',width:0.8}},
      text:gaps.map(function(g){return g+' yr'+(g===1?'':'s');}),
      textposition:'outside',
      textfont:{size:9,family:_FONT,color:'#6b7280'},
      hovertext:hov,hoverinfo:'text',cliponaxis:false,
    }],{
      paper_bgcolor:'#ffffff',plot_bgcolor:'#ffffff',
      font:{family:_FONT,size:11,color:'#333e5c'},
      height:500,margin:{l:60,r:80,t:64,b:150},
      title:{
        text:'<b>Years Since Most Recent '+surveyKey+' Survey</b>'+noNote,
        font:{size:13,color:'#14265c',family:_FONT},x:0,xanchor:'left',pad:{l:4,t:4}
      },
      xaxis:{tickangle:-50,tickfont:{size:9.5,family:_FONT,color:'#6b7280'},showgrid:false,linecolor:'#e2e8f0',showline:true,automargin:true},
      yaxis:{
        title:{text:'Years since last survey (relative to 2026)',font:{size:11,color:'#6b7280'}},
        range:[0,maxGap+4],dtick:5,gridcolor:'#f0f4fa',linecolor:'#e2e8f0',showline:true,
        tickfont:{size:11,family:_FONT},zeroline:true,zerolinecolor:'#e2e8f0',
      },
      shapes:[
        {type:'line',x0:0,x1:1,y0:5,y1:5,xref:'paper',yref:'y',line:{color:'#c8a600',dash:'dash',width:1.8}},
        {type:'line',x0:0,x1:1,y0:10,y1:10,xref:'paper',yref:'y',line:{color:'#f7941d',dash:'dash',width:1.8}},
        {type:'line',x0:0,x1:1,y0:15,y1:15,xref:'paper',yref:'y',line:{color:'#c0392b',dash:'dash',width:1.8}},
      ],
      annotations:[
        {x:1.01,y:5,xref:'paper',yref:'y',text:'<b>5 yr</b>',showarrow:false,font:{size:10,color:'#c8a600',family:_FONT},xanchor:'left'},
        {x:1.01,y:10,xref:'paper',yref:'y',text:'<b>10 yr</b>',showarrow:false,font:{size:10,color:'#f7941d',family:_FONT},xanchor:'left'},
        {x:1.01,y:15,xref:'paper',yref:'y',text:'<b>15 yr</b>',showarrow:false,font:{size:10,color:'#c0392b',family:_FONT},xanchor:'left'},
      ],
      hoverlabel:{bgcolor:'#14265c',font_size:12,font_family:_FONT,font_color:'white'},
    },{responsive:true,displayModeBar:false});
  }

  function updateTimeline(surveyKey) {
    var divId='cycle-timeline-chart';
    var el=document.getElementById(divId);
    if(!el||typeof Plotly==='undefined')return;
    var rows=TIMELINE_DATA[surveyKey]||[];
    if(rows.length===0){Plotly.purge(divId);return;}
    var years=rows.map(function(r){return r.year;});
    var counts=rows.map(function(r){return r.n;});
    var maxN=Math.max.apply(null,counts);
    // Color bars by period: grey for pre-2000, blue for 2000-2020, green for current cycle
    var barColors=years.map(function(y){
      if(y>=2021)return'#00a651';
      if(y>=2000)return'#4a90e2';
      return'#adb5bd';
    });
    var meta=EXEC_DATA[surveyKey]||{};
    var fullName=meta.full_name||surveyKey;
    var textLabels=counts.map(function(n){return n>0?String(n):'';});
    try{
      Plotly.react(divId,[{
        type:'bar',x:years,y:counts,
        marker:{color:barColors,line:{color:'#fff',width:1}},
        text:textLabels,
        textposition:'outside',
        textfont:{size:10,family:_FONT,color:'#333e5c'},
        cliponaxis:false,
        hovertemplate:'<b>Year %{x}</b><br>Countries completed '+surveyKey+': <b>%{y}</b><extra></extra>',
      }],{
        paper_bgcolor:'#ffffff',plot_bgcolor:'#f8faff',
        font:{family:_FONT,size:12,color:'#333e5c'},
        height:400,margin:{l:60,r:30,t:70,b:60},
        title:{
          text:'<b>Historical Activity \u2014 '+surveyKey+'</b>&nbsp;&nbsp;<span style="font-size:12px;color:#6b7280;font-weight:400">'+fullName+'</span><br><span style="font-size:10px;color:#6b7280;font-weight:400">Number of countries completing the survey each year</span>',
          font:{size:14,color:'#14265c',family:_FONT},x:0,xanchor:'left',pad:{l:4,t:4}
        },
        xaxis:{
          title:{text:'Survey Year',font:{size:11,color:'#6b7280'}},
          dtick:2,tickfont:{size:10,family:_FONT},
          showgrid:false,linecolor:'#e2e8f0',showline:true,
        },
        yaxis:{
          title:{text:'Number of Countries',font:{size:11,color:'#6b7280'}},
          range:[0,maxN+4],dtick:2,
          gridcolor:'#eef2f7',linecolor:'#e2e8f0',showline:true,
          tickfont:{size:11,family:_FONT},zeroline:true,zerolinecolor:'#e2e8f0',
        },
        shapes:[
          {type:'rect',xref:'x',yref:'paper',x0:2020.5,x1:2026.5,y0:0,y1:1,
           fillcolor:'rgba(0,166,81,0.07)',line:{width:0}},
          {type:'line',xref:'x',yref:'paper',x0:2020.5,x1:2020.5,y0:0,y1:1,
           line:{color:'#00a651',dash:'dot',width:1.5}},
        ],
        annotations:[
          {x:2021,y:1.04,xref:'x',yref:'paper',text:'<b>Current 5-yr cycle</b>',
           showarrow:false,font:{size:10,color:'#00a651',family:_FONT},xanchor:'left'},
        ],
        hoverlabel:{bgcolor:'#14265c',font_size:12,font_family:_FONT,font_color:'white'},
      },{responsive:true,displayModeBar:false});
    }catch(e){console.warn('Timeline render error:',e);}
  }

  function filterSurveyDetail(code) {
    document.querySelectorAll('.survey-detail-section').forEach(function(el){
      el.style.display = el.dataset.survey === code ? '' : 'none';
    });
    // update active state on filter pills
    document.querySelectorAll('.survey-pill').forEach(function(btn){
      var active = btn.dataset.survey === code;
      btn.style.background    = active ? btn.dataset.color : '#f4f7fb';
      btn.style.color         = active ? '#ffffff' : 'var(--muted)';
      btn.style.borderColor   = active ? btn.dataset.color : 'var(--border)';
    });
  }

  var _prioCurSurvey = 'STEPS';

  function filterPriority(surveyKey) {
    _prioCurSurvey = surveyKey;
    var d = EXEC_DATA[surveyKey];
    if(!d) return;
    var n = d.n_total;
    // Read movable threshold values
    var gapEl=document.getElementById('prio-gap-cut');
    var spiEl=document.getElementById('prio-spi-cut');
    var gapCut=gapEl?Math.max(1,parseInt(gapEl.value)||5):5;
    var spiCut=spiEl?Math.max(1,Math.min(99,parseInt(spiEl.value)||50)):50;
    var gv=document.getElementById('prio-gap-val'); if(gv)gv.textContent=gapCut;
    var sv=document.getElementById('prio-spi-val'); if(sv)sv.textContent=spiCut;
    // Pill active states
    document.querySelectorAll('.prio-pill').forEach(function(btn){
      var active=btn.dataset.survey===surveyKey;
      btn.style.background  =active?btn.dataset.color:'#f4f7fb';
      btn.style.color       =active?'#ffffff':'var(--muted)';
      btn.style.borderColor =active?btn.dataset.color:'var(--border)';
      btn.style.boxShadow   =active?'0 4px 12px rgba(0,0,0,.2)':'none';
    });
    // Survey detail sections
    document.querySelectorAll('.survey-detail-section').forEach(function(sec){
      sec.style.display=sec.dataset.survey===surveyKey?'':'none';
    });
    // Scatter chart
    var divId='prio-scatter-chart';
    var chartEl=document.getElementById(divId);
    if(!chartEl||typeof Plotly==='undefined') return;
    var cgap=d.countries_gap||[];
    var MAXGAP=40;
    var statusCfg={
      'On Cycle':          {color:'#00a651',fill:'rgba(0,166,81,.85)',  symbol:'circle',      sz:15,lw:1.5},
      'Attempt to update': {color:'#4a90e2',fill:'rgba(74,144,226,.85)',symbol:'triangle-up', sz:14,lw:1.5},
      'Off Cycle':         {color:'#f7941d',fill:'rgba(247,148,29,.85)',symbol:'square',       sz:13,lw:1.5},
      'Never Conducted':   {color:'#c0392b',fill:'rgba(0,0,0,0)',       symbol:'circle-open',  sz:12,lw:2}
    };
    var traceData={};
    Object.keys(statusCfg).forEach(function(s){traceData[s]={x:[],y:[],text:[]};});
    cgap.forEach(function(c){
      var st=c.status||'Never Conducted';
      var xVal=(c.gap!==null&&c.gap!==undefined)?c.gap:MAXGAP-2;
      var yVal=SPI_SCORES[c.country]!==undefined?SPI_SCORES[c.country]:0;
      if(traceData[st]){traceData[st].x.push(xVal);traceData[st].y.push(yVal);traceData[st].text.push(c.country);}
    });
    var traces=Object.keys(statusCfg).map(function(st){
      var cfg=statusCfg[st];
      var td=traceData[st];
      return{
        x:td.x,y:td.y,text:td.text,
        type:'scatter',mode:'markers+text',
        textposition:'top center',
        textfont:{size:8.5,family:_FONT,color:'#3a3a5c'},
        name:st,
        marker:{
          color:cfg.fill, size:cfg.sz, opacity:0.92, symbol:cfg.symbol,
          line:{color:cfg.color,width:cfg.lw}
        },
        hovertemplate:'<b>%{text}</b><br>'+surveyKey+' gap: <b>%{x} yrs</b><br>Overall SPI: <b>%{y:.1f}</b><extra><b style="color:'+cfg.color+'">'+st+'</b></extra>'
      };
    });
    var hL=gapCut/2, mR=gapCut+(MAXGAP-gapCut)/2;
    var mBot=spiCut/2, mTop=spiCut+(100-spiCut)/2;
    var shapes=[
      // Quadrant fills
      {type:'rect',x0:gapCut,x1:MAXGAP,y0:0,    y1:spiCut,xref:'x',yref:'y',fillcolor:'rgba(192,57,43,.10)',line:{width:0}},
      {type:'rect',x0:gapCut,x1:MAXGAP,y0:spiCut,y1:100,  xref:'x',yref:'y',fillcolor:'rgba(247,148,29,.10)',line:{width:0}},
      {type:'rect',x0:-2,    x1:gapCut,y0:spiCut,y1:100,  xref:'x',yref:'y',fillcolor:'rgba(0,166,81,.10)',  line:{width:0}},
      {type:'rect',x0:-2,    x1:gapCut,y0:0,    y1:spiCut,xref:'x',yref:'y',fillcolor:'rgba(74,144,226,.10)',line:{width:0}},
      // Threshold lines - dotted navy
      {type:'line',x0:gapCut,x1:gapCut,y0:-6,y1:106,xref:'x',yref:'y',line:{color:'#14265c',width:2,dash:'dot'}},
      {type:'line',x0:-2,x1:MAXGAP,y0:spiCut,y1:spiCut,xref:'x',yref:'y',line:{color:'#14265c',width:2,dash:'dot'}}
    ];
    var annotations=[
      // Large watermark labels
      {x:mR,   y:mBot, text:'URGENT',   showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(192,57,43,.18)',family:_FONT}},
      {x:mR,   y:mTop, text:'REINVEST', showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(247,148,29,.18)',family:_FONT}},
      {x:hL,   y:mTop, text:'SUSTAIN',  showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(0,166,81,.18)',  family:_FONT}},
      {x:hL,   y:mBot, text:'DEVELOP',  showarrow:false,xref:'x',yref:'y',font:{size:28,color:'rgba(74,144,226,.18)',family:_FONT}},
      // Threshold value labels on lines
      {x:gapCut, y:104, text:'\u25bc Gap\u2009=\u2009'+gapCut+' yr', showarrow:false,
       xref:'x',yref:'y',xanchor:'center',font:{size:10,color:'#14265c',family:_FONT},
       bgcolor:'rgba(255,255,255,.9)',borderpad:3,bordercolor:'#c8d2e8',borderwidth:1},
      {x:MAXGAP-0.5,y:spiCut,text:'\u25c4 SPI\u2009=\u2009'+spiCut,showarrow:false,
       xref:'x',yref:'y',xanchor:'right',yanchor:'bottom',font:{size:10,color:'#14265c',family:_FONT},
       bgcolor:'rgba(255,255,255,.9)',borderpad:3,bordercolor:'#c8d2e8',borderwidth:1},
      // Never-conducted note
      {x:MAXGAP-2,y:-5,xref:'x',yref:'y',text:'\u25cb\u2009=\u2009Never conducted (plotted at far right)',
       showarrow:false,font:{size:9,color:'#aaa',family:_FONT}}
    ];
    var layout={
      xaxis:{
        title:{text:'Years Since Last '+surveyKey+' Survey',font:{size:12,family:_FONT,color:'#333e5c'}},
        range:[-2,MAXGAP+1],showgrid:true,gridcolor:'#edf0f8',gridwidth:1,
        zeroline:false,showline:true,linecolor:'#d8def0',linewidth:1,
        tickfont:{size:11,family:_FONT,color:'#555e7c'},
        dtick:5
      },
      yaxis:{
        title:{text:'Overall SPI Score (0\u2013100)',font:{size:12,family:_FONT,color:'#333e5c'}},
        range:[-8,108],showgrid:true,gridcolor:'#edf0f8',gridwidth:1,
        zeroline:false,showline:true,linecolor:'#d8def0',linewidth:1,
        tickfont:{size:11,family:_FONT,color:'#555e7c'},
        dtick:25
      },
      shapes:shapes, annotations:annotations,
      legend:{
        orientation:'h',y:-0.18,x:0.5,xanchor:'center',
        font:{size:11,family:_FONT,color:'#333e5c'},
        bgcolor:'rgba(248,250,255,.97)',bordercolor:'#d8def0',borderwidth:1,
        itemsizing:'constant'
      },
      margin:{l:65,r:22,t:16,b:100},
      paper_bgcolor:'#f4f7fc',
      plot_bgcolor:'#ffffff',
      font:{family:_FONT,size:11,color:'#333e5c'},
      hoverlabel:{bgcolor:'#14265c',font_size:12,font_family:_FONT,font_color:'#fff',bordercolor:'transparent',namelength:-1}
    };
    try{Plotly.react(divId,traces,layout,{responsive:true,displayModeBar:false});}
    catch(e){console.warn('Prio scatter error:',e);}
  }

  function updateExecKPIs(surveyKey) {
    var d=EXEC_DATA[surveyKey];
    if(!d)return;
    var n=d.n_total;
    var updates=[
      ['exec-n-oncycle',  d.n_on_cycle,          d.n_on_cycle+' of '+n+' countries',          'Completed \u2264\u20095 years ago \u2014 current, usable evidence'],
      ['exec-n-implement',d.n_attempt_to_update, d.n_attempt_to_update+' of '+n+' countries', 'Prior evidence exists \u2014 actively updating with new survey'],
      ['exec-n-offcycle', d.n_off_cycle,         d.n_off_cycle+' of '+n+' countries',         'Has prior evidence but surveillance is idle \u2014 off-cycle'],
      ['exec-n-never',    d.n_never,             d.n_never+' of '+n+' countries',             'Never completed \u2014 no policy-usable evidence exists'],
    ];
    updates.forEach(function(u){
      var id=u[0],val=u[1],sub=u[2],def=u[3];
      var elV=document.getElementById(id);if(elV)elV.textContent=val;
      var elS=document.getElementById(id+'-sub');if(elS)elS.textContent=sub;
      var elD=document.getElementById(id+'-def');if(elD)elD.textContent=def;
    });
    var brief=document.getElementById('exec-briefing-text');
    if(brief)brief.innerHTML=d.briefing;
    var badge=document.getElementById('exec-survey-badge');
    if(badge)badge.textContent=surveyKey+' \u2014 '+d.full_name;
    setTimeout(function(){updateExecDonut(d);},50);
    setTimeout(function(){updateGapChart(surveyKey);},60);
  }

  var execFilter=document.getElementById('exec-survey-filter');
  if(execFilter){
    execFilter.addEventListener('change',function(){updateExecKPIs(execFilter.value||'STEPS');});
  }
  var execReset=document.getElementById('exec-filter-reset');
  if(execReset){
    execReset.addEventListener('click',function(){
      if(execFilter)execFilter.value='STEPS';
      updateExecKPIs('STEPS');
    });
  }
  window.addEventListener('load',function(){
    updateExecKPIs('STEPS');
    filterSurveyDetail('STEPS');
    window.dispatchEvent(new Event('resize'));
    setTimeout(function(){
      window.dispatchEvent(new Event('resize'));
      if(typeof Plotly==='undefined')return;
      document.querySelectorAll('.tab-pane.active .plotly-graph-div').forEach(function(el){
        try{Plotly.relayout(el,{autosize:true});}catch(e){}
      });
    },300);
  });
  document.querySelectorAll('.tab-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      if(btn.dataset.tab==='tab-exec'){
        setTimeout(function(){
          var filt=document.getElementById('exec-survey-filter');
          updateExecKPIs((filt&&filt.value)?filt.value:'STEPS');
        },80);
      }
      if(btn.dataset.tab==='tab-cycle'){
        setTimeout(function(){
          var filt=document.getElementById('cycle-timeline-filter');
          updateTimeline((filt&&filt.value)?filt.value:'STEPS');
        },80);
      }
      if(btn.dataset.tab==='tab-priority'){
        setTimeout(function(){filterPriority(_prioCurSurvey);},80);
      }
      if(btn.dataset.tab==='tab-profile'){
        setTimeout(function(){
          var s=document.getElementById('profile-country-select');
          if(s&&s.value) renderCountryProfile(s.value);
        },80);
      }
    });
  });
  // ── Strategic Priority: pill & slider event listeners ─────────────────────
  document.querySelectorAll('.prio-pill').forEach(function(btn){
    btn.addEventListener('click',function(){filterPriority(btn.dataset.survey);});
  });
  ['prio-gap-cut','prio-spi-cut'].forEach(function(id){
    var el=document.getElementById(id);
    if(el) el.addEventListener('input',function(){filterPriority(_prioCurSurvey);});
  });

  // ════════════════════════════════════════════════════════════════════════════
  // COUNTRY PROFILE TAB
  // ════════════════════════════════════════════════════════════════════════════
  var STEPS_PROFILE_DATA = __STEPS_PROFILE_PLACEHOLDER__;
  var _profileCurrent = '';

  var _SECTION_ORDER = ['S1_TOB','S1_ALC','S1_DIT','S1_PAC','S2_BPR','S2_ANT','S3_GLU','S3_CHO','S_RISK'];
  var _RADAR_CFG = [
    {code:'tobacco_current_smoke_pct',     label:'Tobacco'},
    {code:'alcohol_current_drinker_pct',   label:'Alcohol'},
    {code:'diet_less5_servings_pct',       label:'Diet'},
    {code:'pa_low_activity_pct',           label:'Inactivity'},
    {code:'bp_raised_140_pct',             label:'Hypertension'},
    {code:'bmi_obese_pct',                 label:'Obesity'},
    {code:'glucose_raised_7_pct',          label:'Diabetes'},
    {code:'cholesterol_raised_5_pct',      label:'Cholesterol'},
    {code:'risk_3plus_pct',                label:'Multi-Risk'},
  ];
  var _KPI_CFG = [
    {code:'tobacco_current_smoke_pct',  icon:'fa-smoking',            label:'Tobacco Use',          col:'#c0392b'},
    {code:'alcohol_binge_pct',          icon:'fa-wine-glass-alt',     label:'Heavy/Binge Drinking',  col:'#8e44ad'},
    {code:'bp_raised_140_pct',          icon:'fa-heartbeat',          label:'Raised Blood Pressure', col:'#e74c3c'},
    {code:'bmi_obese_pct',              icon:'fa-weight',             label:'Obesity (BMI\u226530)', col:'#e67e22'},
    {code:'glucose_raised_7_pct',       icon:'fa-tint',               label:'Raised Glucose',        col:'#d35400'},
    {code:'risk_3plus_pct',             icon:'fa-exclamation-circle', label:'3+ Risk Factors',       col:'#2c3e50'},
  ];
  var _TIER_CLR = {1:'#00a651',2:'#4a90e2',3:'#f7941d',4:'#c0392b'};

  function _trendArrow(cur, prev, hib) {
    if(cur===null||cur===undefined||prev===null||prev===undefined) return '';
    var diff=cur-prev, abs=Math.abs(diff);
    if(abs<0.5) return '<span style="color:#6b7280;font-size:12px;">\u2248</span>';
    var up=diff>0;
    var good= hib===null||hib===undefined ? null : (hib?up:!up);
    var clr= good===null?'#6b7280':(good?'#00a651':'#c0392b');
    return '<span style="color:'+clr+';font-weight:700;">'+(up?'\u2191':'\u2193')+' '+abs.toFixed(1)+'</span>';
  }


  function renderCountryProfile(country) {
    if(!STEPS_PROFILE_DATA||!STEPS_PROFILE_DATA.profiles){
      document.getElementById('country-profile-content').innerHTML=
        '<div class="profile-no-data"><i class="fas fa-database"></i><p>No STEPS indicator data available.</p></div>';
      return;
    }
    _profileCurrent=country;
    var p=STEPS_PROFILE_DATA.profiles[country];
    if(!p||!p.surveys||p.surveys.length===0){
      document.getElementById('country-profile-content').innerHTML=
        '<div class="profile-no-data"><i class="fas fa-info-circle"></i><p>No STEPS data available for <strong>'+country+'</strong>.</p></div>';
      return;
    }
    var ind=STEPS_PROFILE_DATA.indicators||{};
    var sec=STEPS_PROFILE_DATA.sections||{};
    var reg=STEPS_PROFILE_DATA.regional||{};
    var surveys=p.surveys;
    var latYr=surveys[surveys.length-1].year;
    var latData=p.data[String(latYr)]||{};
    var hasMulti=surveys.length>=2;
    var prevYr=hasMulti?surveys[surveys.length-2].year:null;
    var prevData=prevYr?(p.data[String(prevYr)]||{}):{};
    var tc=_TIER_CLR[p.tier]||'#4a90e2';
    var latS=surveys[surveys.length-1];
    var yrsStr=surveys.map(function(s){return s.year;}).join(' \u00b7 ');
    var nStr=latS.n?latS.n.toLocaleString():'N/A';

    // ── Header ─────────────────────────────────────────────────────────────
    var hdr='<div class="profile-header-card reveal">';
    hdr+='<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:18px;">';
    hdr+='<div style="display:flex;align-items:center;gap:18px;">';
    hdr+='<div class="profile-iso-badge">'+(p.iso3||'???')+'</div>';
    hdr+='<div>';
    hdr+='<div style="font-size:22px;font-weight:900;color:var(--dark);letter-spacing:-.025em;">'+country+'</div>';
    hdr+='<div style="font-size:12px;color:var(--muted);margin-top:5px;display:flex;flex-wrap:wrap;gap:10px;">';
    hdr+='<span class="profile-survey-pill"><i class="fas fa-flask"></i>&nbsp;STEPS surveys: <strong>'+yrsStr+'</strong></span>';
    if(latS.rr) hdr+='<span class="profile-survey-pill"><i class="fas fa-percentage"></i>&nbsp;Response rate: '+latS.rr+'%</span>';
    hdr+='</div></div></div>';
    hdr+='<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">';
    if(p.spi!==null&&p.spi!==undefined){
      hdr+='<div style="text-align:center;padding:12px 20px;background:linear-gradient(135deg,'+tc+'18,'+tc+'0a);border:2px solid '+tc+';border-radius:12px;min-width:90px;">';
      hdr+='<div style="font-size:1.75rem;font-weight:900;color:'+tc+';line-height:1;">'+p.spi.toFixed(1)+'</div>';
      hdr+='<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:'+tc+';margin-top:3px;">SPI Score</div>';
      hdr+='<div style="font-size:10.5px;color:'+tc+';font-weight:600;margin-top:2px;">'+( p.tier_label||'')+'</div></div>';
    }
    if(hasMulti){
      hdr+='<div style="padding:10px 18px;background:#e6f5ec;border:1.5px solid #9dd4b0;border-radius:10px;text-align:center;">';
      hdr+='<div style="font-size:1.5rem;font-weight:900;color:#00a651;">'+surveys.length+'</div>';
      hdr+='<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#00a651;">STEPS Rounds</div>';
      hdr+='<div style="font-size:9.5px;color:#00a651;margin-top:1px;">Trend available</div></div>';
    }
    hdr+='</div></div></div>';

    // ── KPI Cards ──────────────────────────────────────────────────────────
    var kpi='<div class="profile-kpi-row">';
    _KPI_CFG.forEach(function(k){
      var d=latData[k.code]||{};
      var pd=prevData[k.code]||{};
      var ki=ind[k.code]||{};
      var v=d.b!==undefined?d.b:null;
      var pv=pd.b!==undefined?pd.b:null;
      var unit=ki.unit||'%';
      var valStr=v!==null?v.toFixed(1)+unit:'N/A';
      var arrow=_trendArrow(v,pv,ki.hib);
      var mV=d.m!==undefined?d.m:null, fV=d.f!==undefined?d.f:null;
      var loStr=(d.lo!==null&&d.lo!==undefined&&d.hi!==null&&d.hi!==undefined)?
        ' title="95% CI: '+d.lo.toFixed(1)+'\u2013'+d.hi.toFixed(1)+unit+'"':'';
      kpi+='<div class="profile-kpi-card" style="color:'+k.col+';">';
      kpi+='<div class="profile-kpi-icon"><i class="fas '+k.icon+'" style="color:'+k.col+';"></i></div>';
      kpi+='<div class="profile-kpi-value" style="color:'+k.col+';"'+loStr+'>'+valStr+'</div>';
      kpi+='<div class="profile-kpi-label">'+k.label+'</div>';
      if(arrow){kpi+='<div class="profile-kpi-trend">'+arrow+'<span style="font-size:10px;color:var(--muted);font-weight:400;"> vs '+prevYr+'</span></div>';}
      if(mV!==null||fV!==null){
        kpi+='<div class="profile-kpi-sex">';
        if(mV!==null) kpi+='<span style="background:#e8f0fb;color:#2980b9;">M: '+mV.toFixed(1)+'</span>';
        if(fV!==null) kpi+='<span style="background:#fce8e6;color:#c0392b;">F: '+fV.toFixed(1)+'</span>';
        kpi+='</div>';
      }
      kpi+='</div>';
    });
    kpi+='</div>';

    // ── Store state for re-render on toggle ────────────────────────────────
    _profileState = {
      latData: latData, prevData: prevData, latYr: latYr, prevYr: prevYr,
      ind: ind, sec: sec, reg: reg, hasMulti: hasMulti, tier: p.tier,
      country: country
    };
    // ── Section divider label ──────────────────────────────────────────────
    var sdiv='<div class="section-divider-label" style="margin:28px 0 18px;">Detailed Indicator Dashboard \u2014 All STEPS Sections</div>';
    sdiv+='<div id="profile-section-detail-grid"></div>';

    document.getElementById('country-profile-content').innerHTML=
      hdr+kpi+sdiv;

    _renderSectionDetail();

    // ── Render Plotly charts ────────────────────────────────────────────────
    setTimeout(function(){
      document.querySelectorAll('#country-profile-content .reveal').forEach(function(el){
        el.classList.add('visible');
      });
      window.dispatchEvent(new Event('resize'));
    },80);
  }

  // ── Section state ───────────────────────────────────────────────────────────
  var _profileState = {};

  function _renderSectionDetail() {
    var el = document.getElementById('profile-section-detail-grid');
    if(!el) return;
    var s   = _profileState;
    var latData  = s.latData  || {};
    var prevData = s.prevData || {};
    var latYr    = s.latYr;
    var prevYr   = s.prevYr;
    var ind      = s.ind  || {};
    var sec      = s.sec  || {};
    var reg      = s.reg  || {};

    var grid = '<div class="profile-section-grid">';
    _SECTION_ORDER.forEach(function(sc){
      var sv = sec[sc]; if(!sv) return;
      var secInds = Object.entries(ind).filter(function(e){return e[1].sec===sc;});

      grid += '<div class="profile-section-card">';
      grid += '<div class="profile-section-head" style="background:'+sv.color+';">';
      grid += '<i class="fas '+sv.icon+'" style="color:rgba(255,255,255,.9);font-size:13px;"></i>';
      grid += '<span class="sec-title">'+sv.name+'</span>';
      grid += '<span class="sec-step">'+sv.step+'</span>';
      grid += '</div>';

      grid += '<div style="overflow-x:auto;">';
      grid += '<table class="profile-ind-table">';
      grid += '<thead><tr>';
      grid += '<th style="text-align:left;min-width:140px;">Indicator</th>';
      grid += '<th style="text-align:center;">Both</th>';
      grid += '<th style="text-align:center;color:#2980b9;">Male</th>';
      grid += '<th style="text-align:center;color:#c0392b;">Female</th>';
      grid += '<th style="text-align:center;">Trend</th>';
      grid += '</tr></thead><tbody>';

      secInds.forEach(function(entry, idx){
        var code = entry[0], i2 = entry[1];
        var d  = latData[code]  || {};
        var pd = prevData[code] || {};
        var bV  = d.b  !== undefined ? d.b  : null;
        var mV  = d.m  !== undefined ? d.m  : null;
        var fV  = d.f  !== undefined ? d.f  : null;
        var pbV = pd.b !== undefined ? pd.b : null;
        var unit = i2.unit || '%';
        var hib  = i2.hib;
        var bg   = idx % 2 === 0 ? '#fff' : '#f9fafb';
        var lbl  = i2.label.length > 58 ? i2.label.substring(0, 57) + '\u2026' : i2.label;
        var ciAttr = (d.lo !== null && d.lo !== undefined && d.hi !== null && d.hi !== undefined)
          ? ' title="95% CI: ' + d.lo.toFixed(1) + '\u2013' + d.hi.toFixed(1) + unit + '"' : '';

        var bStr = bV !== null
          ? '<strong' + ciAttr + '>' + bV.toFixed(1) + '</strong>'
            + '<span style="font-size:9px;color:var(--muted);">' + unit + '</span>'
          : '<span style="color:#ccc;">\u2014</span>';
        var mStr = mV !== null ? mV.toFixed(1)  : '<span style="color:#ccc;">\u2014</span>';
        var fStr = fV !== null ? fV.toFixed(1)  : '<span style="color:#ccc;">\u2014</span>';
        var tArr = _trendArrow(bV, pbV, hib);

        grid += '<tr style="background:' + bg + ';">';
        grid += '<td style="color:var(--text);word-break:break-word;font-size:11px;">' + lbl + '</td>';
        grid += '<td style="text-align:center;">' + bStr + '</td>';
        grid += '<td style="text-align:center;color:#2980b9;">' + mStr + '</td>';
        grid += '<td style="text-align:center;color:#c0392b;">' + fStr + '</td>';
        grid += '<td style="text-align:center;">' + (tArr || '<span style="color:#ccc;">\u2014</span>') + '</td>';
        grid += '</tr>';
      });
      grid += '</tbody></table></div></div>';
    });
    grid += '</div>';
    el.innerHTML = grid;
  }

  // ── Compare: Regional Benchmark ─────────────────────────────────────────────
  function _renderProfileCompare(latData,country,reg,ind,sec){
    var divId='profile-compare-chart';
    if(!document.getElementById(divId)||typeof Plotly==='undefined') return;
    var _SEC_CLR={'S1_TOB':'#c0392b','S1_ALC':'#8e44ad','S1_DIT':'#27ae60','S1_PAC':'#2980b9',
                  'S2_BPR':'#e74c3c','S2_ANT':'#e67e22','S3_GLU':'#d35400','S3_CHO':'#16a085','S_RISK':'#2c3e50'};
    var names=[],cVals=[],rVals=[],clrs=[];
    _RADAR_CFG.forEach(function(r){
      var i2=ind[r.code]; if(!i2) return;
      var d=latData[r.code]||{}, rv=reg[r.code]||{};
      var cv=d.b!==null&&d.b!==undefined?d.b:null;
      var rvB=rv.b!==null&&rv.b!==undefined?rv.b:null;
      if(cv===null&&rvB===null) return;
      names.push(r.label);
      cVals.push(cv); rVals.push(rvB);
      clrs.push(_SEC_CLR[i2.sec]||'#6b7280');
    });
    if(!names.length) return;
    try{Plotly.react(divId,[
      {type:'bar',orientation:'h',x:rVals,y:names,name:'AFRO Avg',
       marker:{color:'rgba(173,181,189,.5)',line:{color:'#adb5bd',width:1}},
       hovertemplate:'AFRO Avg: <b>%{x:.1f}%</b><extra></extra>'},
      {type:'bar',orientation:'h',x:cVals,y:names,name:country,
       marker:{color:clrs,opacity:.88,line:{color:'rgba(0,0,0,.08)',width:1}},
       hovertemplate:country+': <b>%{x:.1f}%</b><extra></extra>'},
    ],{
      barmode:'overlay',
      xaxis:{title:{text:'Prevalence (%)',font:{size:11,color:'#6b7280'}},tickfont:{size:10,family:_FONT},showgrid:true,gridcolor:'#f0f4fa',zeroline:false},
      yaxis:{tickfont:{size:11,family:_FONT,color:'#333e5c'},automargin:true},
      showlegend:true,
      legend:{orientation:'h',y:-0.16,x:0.5,xanchor:'center',font:{size:11,family:_FONT}},
      margin:{l:10,r:22,t:8,b:60},height:360,
      paper_bgcolor:'#fff',plot_bgcolor:'#fff',
      font:{family:_FONT,size:11},
      hoverlabel:{bgcolor:'#14265c',font_size:12,font_family:_FONT,font_color:'#fff'},
    },{responsive:true,displayModeBar:false});}catch(e){console.warn('Compare error',e);}
  }

  // ── Trend: Key Indicators Over Time ────────────────────────────────────────
  function _renderProfileTrend(profile,ind){
    var divId='profile-trend-chart';
    if(!document.getElementById(divId)||typeof Plotly==='undefined') return;
    var surveys=profile.surveys;
    var years=surveys.map(function(s){return s.year;});
    var _TREND_CFG=[
      {code:'tobacco_current_smoke_pct',  label:'Tobacco Use',       clr:'#c0392b'},
      {code:'bp_raised_140_pct',          label:'Raised BP',         clr:'#e74c3c'},
      {code:'bmi_obese_pct',              label:'Obesity',           clr:'#e67e22'},
      {code:'glucose_raised_7_pct',       label:'Raised Glucose',    clr:'#d35400'},
      {code:'risk_3plus_pct',             label:'3+ Risk Factors',   clr:'#2c3e50'},
      {code:'pa_low_activity_pct',        label:'Low Physical Act.', clr:'#2980b9'},
      {code:'alcohol_current_drinker_pct',label:'Alcohol Use',       clr:'#8e44ad'},
    ];
    var traces=[];
    _TREND_CFG.forEach(function(t){
      var vals=years.map(function(yr){
        var yd=profile.data[String(yr)]||{};
        var d=yd[t.code]; return d&&d.b!==null&&d.b!==undefined?d.b:null;
      });
      if(vals.every(function(v){return v===null;})) return;
      var lo=years.map(function(yr){var yd=profile.data[String(yr)]||{};var d=yd[t.code];return d&&d.lo!==null&&d.lo!==undefined?d.lo:null;});
      var hi=years.map(function(yr){var yd=profile.data[String(yr)]||{};var d=yd[t.code];return d&&d.hi!==null&&d.hi!==undefined?d.hi:null;});
      // CI ribbon
      var xCI=years.concat(years.slice().reverse());
      var yCI=hi.concat(lo.slice().reverse());
      if(xCI.length>0&&yCI.some(function(v){return v!==null;})){
        traces.push({type:'scatter',mode:'none',x:xCI,y:yCI,fill:'toself',
          fillcolor:t.clr.replace('#','rgba(').replace(/([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i,
            function(m,r,g,b){return parseInt(r,16)+','+parseInt(g,16)+','+parseInt(b,16)+',0.12)';}),
          line:{width:0},showlegend:false,hoverinfo:'skip'});
      }
      traces.push({type:'scatter',mode:'lines+markers',x:years,y:vals,name:t.label,
        line:{color:t.clr,width:2.5},
        marker:{color:t.clr,size:9,line:{color:'#fff',width:2}},
        connectgaps:false,
        hovertemplate:'<b>'+t.label+'</b><br>Year: <b>%{x}</b><br>Value: <b>%{y:.1f}%</b><extra></extra>'});
    });
    if(!traces.length){document.getElementById(divId).innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);">No trend data available</div>';return;}
    try{Plotly.react(divId,traces,{
      xaxis:{title:{text:'Survey Year',font:{size:11,color:'#6b7280'}},tickmode:'array',tickvals:years,
        tickfont:{size:11,family:_FONT},showgrid:true,gridcolor:'#f0f4fa',zeroline:false},
      yaxis:{title:{text:'Prevalence (%)',font:{size:11,color:'#6b7280'}},tickfont:{size:11,family:_FONT},
        showgrid:true,gridcolor:'#f0f4fa',zeroline:false},
      showlegend:true,
      legend:{orientation:'h',y:-0.22,x:0.5,xanchor:'center',font:{size:11,family:_FONT},itemsizing:'constant'},
      margin:{l:60,r:20,t:16,b:100},
      paper_bgcolor:'#fff',plot_bgcolor:'#fff',
      font:{family:_FONT,size:11},
      hoverlabel:{bgcolor:'#14265c',font_size:12,font_family:_FONT,font_color:'#fff'},
    },{responsive:true,displayModeBar:false});}catch(e){console.warn('Trend error',e);}
  }

  // ── Sex Disaggregation ──────────────────────────────────────────────────────
  function _renderProfileSexChart(latData,country,ind,reg){
    var divId='profile-sex-chart';
    if(!document.getElementById(divId)||typeof Plotly==='undefined') return;
    var names=[],mV=[],fV=[],bV=[];
    _RADAR_CFG.forEach(function(r){
      var d=latData[r.code]||{};
      names.push(r.label);
      mV.push(d.m!==null&&d.m!==undefined?d.m:null);
      fV.push(d.f!==null&&d.f!==undefined?d.f:null);
      bV.push(d.b!==null&&d.b!==undefined?d.b:null);
    });
    try{Plotly.react(divId,[
      {type:'bar',orientation:'h',x:mV,y:names,name:'Males',
       marker:{color:'rgba(41,128,185,.82)',line:{color:'#2980b9',width:1}},
       hovertemplate:'Males: <b>%{x:.1f}%</b><extra></extra>'},
      {type:'bar',orientation:'h',x:fV,y:names,name:'Females',
       marker:{color:'rgba(192,57,43,.82)',line:{color:'#c0392b',width:1}},
       hovertemplate:'Females: <b>%{x:.1f}%</b><extra></extra>'},
      {type:'scatter',mode:'markers',x:bV,y:names,name:'Both Sexes',
       marker:{color:'#14265c',symbol:'diamond',size:10,line:{color:'#fff',width:2}},
       hovertemplate:'Both Sexes: <b>%{x:.1f}%</b><extra></extra>'},
    ],{
      barmode:'group',
      xaxis:{title:{text:'Prevalence (%)',font:{size:11,color:'#6b7280'}},tickfont:{size:10,family:_FONT},showgrid:true,gridcolor:'#f0f4fa',zeroline:false},
      yaxis:{tickfont:{size:11,family:_FONT,color:'#333e5c'},automargin:true},
      showlegend:true,
      legend:{orientation:'h',y:-0.16,x:0.5,xanchor:'center',font:{size:11,family:_FONT}},
      margin:{l:10,r:22,t:8,b:60},height:380,
      paper_bgcolor:'#fff',plot_bgcolor:'#fff',
      font:{family:_FONT,size:11},
      hoverlabel:{bgcolor:'#14265c',font_size:12,font_family:_FONT,font_color:'#fff'},
    },{responsive:true,displayModeBar:false});}catch(e){console.warn('Sex chart error',e);}
  }

  // ── Profile tab: event listeners ────────────────────────────────────────────
  var _profSel=document.getElementById('profile-country-select');
  if(_profSel){
    _profSel.addEventListener('change',function(){renderCountryProfile(this.value);});
  }

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
})();
"""

# ── Font Awesome icon map ──────────────────────────────────────────────────────
_FA = {
    "globe":    "fa-globe-africa",   "clipboard": "fa-clipboard-list",
    "check":    "fa-check-circle",   "sync":      "fa-sync-alt",
    "times":    "fa-times-circle",   "flask":     "fa-flask",
    "calendar": "fa-calendar-alt",   "trophy":    "fa-trophy",
    "chart":    "fa-chart-bar",      "map":       "fa-map-marker-alt",
    "star":     "fa-star",           "gauge":     "fa-tachometer-alt",
    "users":    "fa-users",          "exclaim":   "fa-exclamation-triangle",
}


def kpi_card(fa_key, value, label, delta=None, color=None, bg=None):
    color = color or C["primary"]
    bg    = bg    or "#f0f6ff"
    fa    = _FA.get(fa_key, "fa-circle")
    try:
        num = float(str(value).replace(",", "").replace("%", ""))
        val_html = (f'<div class="kpi-value" style="color:{color};" '
                    f'data-count="{num}">{value}</div>')
    except ValueError:
        val_html = f'<div class="kpi-value" style="color:{color};">{value}</div>'
    delta_html = ""
    if delta:
        delta_html = (f'<div class="kpi-delta" style="color:{color};">'
                      f'<i class="fas fa-arrow-up" style="font-size:9px;"></i> {delta}</div>')
    return f"""
<div class="kpi-card reveal" style="color:{color};background:{bg};">
  <div class="kpi-icon"><i class="fas {fa}" style="color:{color};"></i></div>
  {val_html}
  <div class="kpi-label">{label}</div>
  {delta_html}
</div>"""


def section_header(anchor, num, title, subtitle=""):
    sub = f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""
    return f"""
<div class="section-header" id="{anchor}">
  <div class="section-header-inner">
    <span class="section-num">{num}</span>
    <h2 class="section-title">{title}</h2>
  </div>
  {sub}
</div>"""


def insight_box(text, kind="info"):
    fa_map  = {"info":"fa-info-circle","warning":"fa-exclamation-triangle",
               "success":"fa-check-circle","critical":"fa-exclamation-circle"}
    colors  = {
        "info":     ("#003d82","#eef4ff","#c5d9f5"),
        "warning":  ("#7a4500","#fff8e1","#ffe082"),
        "success":  ("#165c35","#e8f5ee","#9dd4b0"),
        "critical": ("#7f1d1d","#fff0f0","#fca5a5"),
    }
    fg, bg, border = colors.get(kind, colors["info"])
    fa = fa_map.get(kind, "fa-info-circle")
    return f"""
<div class="insight-box reveal" style="background:{bg};border-left:5px solid {border};color:{fg};">
  <span class="insight-icon"><i class="fas {fa}"></i></span>
  <span>{text}</span>
</div>"""


def chart_card(chart_html, commentary="", span=12):
    comm = f'<div class="chart-commentary">{commentary}</div>' if commentary else ""
    return f"""
<div class="col-{span}">
  <div class="chart-card reveal">
    {chart_html}
    {comm}
  </div>
</div>"""


def instrument_cards(A):
    st_sum = A["survey_type_summary"].set_index("survey_type")
    cards = ""
    for code, meta in SURVEY_META.items():
        if code not in st_sum.index:
            continue
        row = st_sum.loc[code]
        pct = row["pct_done"]
        bc  = C["success"] if pct >= 70 else C["warning"] if pct >= 40 else C["danger"]
        cards += f"""
<div class="instrument-card reveal" style="border-top:4px solid {meta['color']};">
  <div class="inst-type" style="color:{meta['color']};">{code}</div>
  <div class="inst-full">{meta['full']}</div>
  <div class="inst-meta">
    <span><i class="fas fa-users" style="font-size:10px;margin-right:4px;"></i>{meta['target']}</span>
    <span><i class="fas fa-tag" style="font-size:10px;margin-right:4px;"></i>{meta['domain']}</span>
  </div>
  <div class="inst-stats">
    <div class="inst-stat"><span class="stat-val">{int(row['total'])}</span><span class="stat-lbl">Surveys</span></div>
    <div class="inst-stat"><span class="stat-val">{int(row['done'])}</span><span class="stat-lbl">Completed</span></div>
    <div class="inst-stat"><span class="stat-val">{int(row['countries'])}</span><span class="stat-lbl">Countries</span></div>
  </div>
  <div class="inst-bar-wrap">
    <div class="inst-bar" style="width:{pct}%;background:{bc};"></div>
  </div>
  <span class="inst-pct" style="color:{bc};">{pct}% completion rate</span>
</div>"""
    return f'<div class="instrument-grid">{cards}</div>'


def scorecard_table(spi):
    rows = ""
    for i, (_, r) in enumerate(spi.iterrows(), 1):
        tc  = TIER_COLORS[r["tier"]]
        gap_s  = f"{int(r['gap_years'])} yrs" if pd.notna(r["gap_years"]) and r["gap_years"] else "-"
        last_s = str(int(r["last_year"])) if pd.notna(r["last_year"]) and r["last_year"] else "-"
        cycle_val = 1 if r["recent_done"] > 0 else 0
        cycle_s = (f"{int(r['recent_done'])} done" if r["recent_done"] > 0
                   else (f"{int(r['recent_inprog'])} in prog." if r["recent_inprog"] > 0 else "-"))
        bw = int(r["spi"])
        map_img = (f'<img class="country-map" src="data:image/png;base64,{COUNTRY_MAPS[r["iso3"]]}" '
                   f'alt="{r["iso3"]}"/>'
                   if r["iso3"] in COUNTRY_MAPS else "")
        reg_s  = (f"{r['d_regularity']:.1f}" if r["n_renewable"] > 0
                  else '<span style="color:#aaa;font-style:italic;font-size:10px;" title="No instrument has been conducted twice yet">n/a</span>')
        avg_iv = (f"~{r['avg_cycle_interval']:.0f} yr" if r["avg_cycle_interval"] else "-")
        rows += f"""
<tr data-country="{r['country'].lower()}" data-tier="{r['tier']}" data-gap="{r['gap_cat']}" data-cycle="{cycle_val}" data-reg="{r['reg_cat']}">
  <td class="rank-cell" style="padding:8px 10px;">{i}</td>
  <td style="padding:8px 10px;">
    <div style="display:flex;align-items:center;">{map_img}<strong>{r['country']}</strong></div>
  </td>
  <td style="padding:8px 10px;">
    <div style="display:flex;align-items:center;gap:7px;">
      <div style="background:{tc};height:5px;border-radius:3px;width:{bw}px;max-width:80px;flex-shrink:0;"></div>
      <strong style="color:{tc}">{r['spi']:.1f}</strong>
      <span style="background:{tc};color:#fff;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:700">{r['tier_label']}</span>
    </div>
  </td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{r['d_coverage']:.0f}%</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{r['d_recency']:.0f}%</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{reg_s}</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;font-size:10.5px;color:var(--muted);">{avg_iv}</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{last_s}</td>
  <td class="num-cell" style="padding:8px 10px;text-align:center;">{gap_s}</td>
</tr>"""
    return f"""
<div style="overflow-x:auto;">
<table id="scorecard-table" style="width:100%;border-collapse:collapse;font-size:12.5px;">
<thead><tr style="background:{C['primary']};color:#fff;">
  <th style="padding:9px 10px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;">#</th>
  <th style="padding:9px 10px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;">Country</th>
  <th style="padding:9px 10px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;">SPI / Tier</th>
  <th style="padding:9px 10px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.5px;" title="Breadth Score - count of instrument types completed ≥1 time / 5">BS</th>
  <th style="padding:9px 10px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.5px;" title="Currency Score - mean exp decay μ=ln2/7 over all 5 instruments">CS</th>
  <th style="padding:9px 10px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.5px;" title="Coverage-Adjusted Regularity - ARI × (assessable / 5); n/a if no instrument has ≥2 rounds">CA-ARI</th>
  <th style="padding:9px 10px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.5px;" title="Average years between consecutive survey rounds">Avg Interval</th>
  <th style="padding:9px 10px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.5px;">Last Survey</th>
  <th style="padding:9px 10px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.5px;">Gap</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>"""


def priority_table(spi):
    rows = ""
    for i, (_, r) in enumerate(spi.iterrows(), 1):
        tc  = TIER_COLORS[r["tier"]]
        gap_s  = f"{int(r['gap_years'])} yrs" if pd.notna(r["gap_years"]) and r["gap_years"] else "No data"
        last_s = str(int(r["last_year"])) if pd.notna(r["last_year"]) and r["last_year"] else "Never"
        cycle_val = 1 if r["recent_done"] > 0 else 0
        if r["recent_done"] > 0:
            act_s = "Active ✓"; act_c = C["success"]
        elif r["recent_inprog"] > 0:
            act_s = "In Pipeline"; act_c = C["warning"]
        else:
            act_s = "Inactive"; act_c = C["danger"]
        gap_c = C["danger"] if r["gap_years"] and r["gap_years"] > 10 else (
                C["warning"] if r["gap_years"] and r["gap_years"] > 5 else C["success"])
        map_img = (f'<img class="country-map" src="data:image/png;base64,{COUNTRY_MAPS[r["iso3"]]}" '
                   f'alt="{r["iso3"]}"/>'
                   if r["iso3"] in COUNTRY_MAPS else "")
        rows += f"""
<tr data-country="{r['country'].lower()}" data-tier="{r['tier']}" data-gap="{r['gap_cat']}" data-cycle="{cycle_val}">
  <td style="padding:8px 12px;">{i}</td>
  <td style="padding:8px 12px;">
    <div style="display:flex;align-items:center;">{map_img}<strong>{r['country']}</strong></div>
  </td>
  <td style="padding:8px 12px;"><strong style="color:{tc}">{r['spi']:.1f}</strong></td>
  <td style="padding:8px 12px;"><span style="background:{tc};color:#fff;padding:2px 9px;border-radius:10px;font-size:10.5px;font-weight:700">{r['tier_label']}</span></td>
  <td style="padding:8px 12px;">{r['d_coverage']:.0f}%</td>
  <td style="padding:8px 12px;">{r['d_recency']:.0f}%</td>
  <td style="padding:8px 12px;">{last_s}</td>
  <td style="padding:8px 12px;color:{gap_c};font-weight:600">{gap_s}</td>
  <td style="padding:8px 12px;"><span style="color:{act_c};font-weight:600">{act_s}</span></td>
</tr>"""
    return f"""
<div style="overflow-x:auto;max-height:560px;overflow-y:auto;">
<table id="prio-table-el" class="prio-table">
<thead><tr>
  <th style="padding:9px 12px;">#</th>
  <th style="padding:9px 12px;">Country</th>
  <th style="padding:9px 12px;">SPI</th>
  <th style="padding:9px 12px;">Tier</th>
  <th style="padding:9px 12px;">Coverage</th>
  <th style="padding:9px 12px;">Recency</th>
  <th style="padding:9px 12px;">Last Survey</th>
  <th style="padding:9px 12px;">Gap</th>
  <th style="padding:9px 12px;">Cycle Status</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>"""


def schema_cards():
    tables = [
        ("#003d82", "fa-globe",          "dim_country",
         [("country_id","PK · INTEGER"),("country_name","TEXT UNIQUE"),
          ("iso3","TEXT"),("is_zanzibar","INTEGER"),("sub_region","TEXT")]),
        ("#8e44ad", "fa-flask",          "dim_survey_type",
         [("survey_type_id","PK · INTEGER"),("survey_code","TEXT UNIQUE"),
          ("survey_full_name","TEXT"),("target_population","TEXT"),
          ("domain","TEXT"),("cycle_years","INTEGER DEFAULT 5")]),
        ("#27ae60", "fa-check-circle",   "dim_status",
         [("status_id","PK · INTEGER"),("status_code","TEXT UNIQUE"),
          ("is_completed","INTEGER"),("completion_weight","REAL")]),
        ("#e67e22", "fa-calendar-alt",   "dim_year",
         [("year_id","PK = year value"),("year","INTEGER UNIQUE"),
          ("decade","TEXT"),("five_yr_period","TEXT"),("cycle_label","TEXT")]),
        ("#c0392b", "fa-table",          "fact_surveys",
         [("survey_id","PK · INTEGER"),("country_id","FK → dim_country"),
          ("survey_type_id","FK → dim_survey_type"),("year_id","FK → dim_year"),
          ("status_id","FK → dim_status"),("survey_year","INTEGER")]),
        ("#718096", "fa-layer-group",    "dim_indicator (future)",
         [("indicator_id","PK · INTEGER"),("indicator_code","TEXT UNIQUE"),
          ("indicator_name","TEXT"),("survey_type_id","FK → dim_survey_type"),
          ("unit","TEXT"),("direction","TEXT")]),
        ("#718096", "fa-chart-line",     "fact_indicators (future)",
         [("fact_id","PK · INTEGER"),("country_id","FK → dim_country"),
          ("indicator_id","FK → dim_indicator"),("year_id","FK → dim_year"),
          ("value","REAL"),("ci_lower / ci_upper","REAL")]),
    ]
    html = '<div class="schema-grid">'
    for color, icon, name, cols in tables:
        trows = "".join(f"<tr><td>{c}</td><td>{t}</td></tr>" for c, t in cols)
        html += f"""
<div class="schema-card">
  <div class="schema-card-head" style="background:{color};">
    <i class="fas {icon}"></i> {name}
  </div>
  <table>{trows}</table>
</div>"""
    html += "</div>"
    return html


def gap_priority_table(A):
    spi  = A["spi"].copy()
    crit = spi[spi["tier"] == 4].sort_values("gap_years", ascending=False, na_position="last").head(15)
    if len(crit) == 0:
        return "<p style='color:var(--muted);font-size:13px;'>No Critical-tier countries identified.</p>"
    rows = ""
    for _, r in crit.iterrows():
        gap_s  = f"{int(r['gap_years'])} yrs" if pd.notna(r["gap_years"]) and r["gap_years"] else "No data"
        last_s = str(int(r["last_year"])) if pd.notna(r["last_year"]) and r["last_year"] else "Never"
        cycle_s = (f"{int(r['recent_done'])} completed" if r["recent_done"] > 0
                   else (f"{int(r['recent_inprog'])} in progress" if r["recent_inprog"] > 0
                         else "No current activity"))
        rows += f"""
<tr>
  <td style="padding:8px 12px;"><strong>{r['country']}</strong></td>
  <td style="padding:8px 12px;font-weight:700;color:{C['danger']}">{r['spi']:.1f}</td>
  <td style="padding:8px 12px;">{r['d_coverage']:.0f}%</td>
  <td style="padding:8px 12px;">{r['d_recency']:.0f}%</td>
  <td style="padding:8px 12px;color:{C['danger']}">{last_s}</td>
  <td style="padding:8px 12px;color:{C['danger']}">{gap_s}</td>
  <td style="padding:8px 12px;">{cycle_s}</td>
</tr>"""
    return f"""
<div style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-size:12.5px;">
<thead><tr style="background:{C['danger']};color:#fff;">
  <th style="padding:9px 12px;text-align:left;">Country</th>
  <th style="padding:9px 12px;text-align:left;">SPI</th>
  <th style="padding:9px 12px;text-align:left;">Coverage</th>
  <th style="padding:9px 12px;text-align:left;">Recency</th>
  <th style="padding:9px 12px;text-align:left;">Last Survey</th>
  <th style="padding:9px 12px;text-align:left;">Gap</th>
  <th style="padding:9px 12px;text-align:left;">Cycle Status</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>"""


def per_survey_sections(A):
    """Generate per-instrument section cards for the Survey Analysis tab."""
    kpis = A["exec_kpis"]
    cm   = A["cycle_matrix"]

    STATUS_COLORS = {
        "Current":     "#00a651",
        "In Pipeline": "#f7941d",
        "Overdue":     "#4a90e2",
        "Critical":    "#c0392b",
        "Never":       "#adb5bd",
    }

    html = ""
    for code, meta in SURVEY_META.items():
        if code not in kpis:
            continue
        k   = kpis[code]
        sub = cm[cm["survey_type"] == code].sort_values("order").reset_index(drop=True)

        rows_html = ""
        for i, (_, row) in enumerate(sub.iterrows(), 1):
            sc     = STATUS_COLORS.get(row["cycle_status"], "#adb5bd")
            last_s = str(int(row["last_year"])) if pd.notna(row["last_year"]) and row["last_year"] else "Never"
            gap_s  = f"{int(row['gap'])} yrs"   if pd.notna(row["gap"]) and row["gap"] else "-"
            bg     = "#fafbff" if i % 2 == 0 else "#ffffff"
            rows_html += f"""<tr style="background:{bg};">
  <td style="padding:6px 12px;font-size:12px;">{row['country']}</td>
  <td style="padding:6px 12px;text-align:center;">
    <span style="background:{sc};color:#fff;padding:2px 8px;border-radius:10px;font-size:10.5px;font-weight:700;">{row['cycle_status']}</span>
  </td>
  <td style="padding:6px 12px;text-align:center;font-size:12px;">{last_s}</td>
  <td style="padding:6px 12px;text-align:center;font-size:12px;">{gap_s}</td>
</tr>"""

        html += f"""
<div class="chart-card reveal survey-detail-section" data-survey="{code}" style="border-top:4px solid {meta['color']};margin-bottom:20px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
    <div>
      <h3 style="font-size:15px;font-weight:700;color:{meta['color']};margin:0 0 2px;">{code}</h3>
      <div style="font-size:11.5px;color:var(--muted);">{meta['full']} &mdash; {meta['target']}</div>
    </div>
    <div style="display:flex;gap:7px;flex-wrap:wrap;">
      <span style="background:#e6f5ec;color:#00a651;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;">{k['n_on_cycle']} On Cycle</span>
      <span style="background:#fff4e5;color:#f7941d;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;">{k['n_attempt_to_update']} Updating</span>
      <span style="background:#e8f0fb;color:#4a90e2;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;">{k['n_off_cycle']} Off Cycle</span>
      <span style="background:#fce8e6;color:#c0392b;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;">{k['n_never']} Never</span>
    </div>
  </div>
  <p style="font-size:12px;color:var(--muted);margin-bottom:12px;line-height:1.7;">{k['briefing']}</p>
  <div style="overflow-x:auto;max-height:420px;overflow-y:auto;">
  <table style="width:100%;border-collapse:collapse;">
  <thead><tr style="background:{meta['color']};color:#fff;position:sticky;top:0;z-index:1;">
    <th style="padding:7px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.4px;">Country</th>
    <th style="padding:7px 12px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.4px;">Status</th>
    <th style="padding:7px 12px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.4px;">Last Survey</th>
    <th style="padding:7px 12px;text-align:center;font-size:11px;text-transform:uppercase;letter-spacing:.4px;">Gap</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
  </table>
  </div>
</div>"""

    return html


def build_html(A: dict) -> str:
    # All figures use include_plotlyjs=False - Plotly CDN is loaded once in <head>
    def R(fig):
        return fig.to_html(full_html=False,
                           include_plotlyjs=False,
                           config={"displayModeBar": True, "responsive": True,
                                   "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                                   "displaylogo": False})

    ch_tier        = R(fig_tier_donut(A))
    ch_spi_bar     = R(fig_spi_bar(A))
    ch_spi_map     = R(fig_spi_choropleth(A))
    ch_components  = R(fig_spi_components(A))
    ch_curr        = R(fig_current_cycle(A))
    ch_heatmap     = R(fig_last_year_heatmap(A))
    ch_prio        = R(fig_priority_scatter(A))
    ch_timeline    = R(fig_timeline(A))
    ch_gap         = R(fig_gap_bar(A))
    ch_survey_cmp  = R(fig_survey_type_comparison(A))
    survey_sections = per_survey_sections(A)

    spi      = A["spi"]
    top5     = spi.head(5)["country"].tolist()
    n_crit   = A["n_critical"]
    n_strong = A["n_strong"]
    reg_spi  = A["regional_spi"]
    n_ent    = A["n_entities"]
    spi_tier_color = ("#00a651" if reg_spi >= 75 else
                      "#4a90e2" if reg_spi >= 50 else
                      "#f7941d" if reg_spi >= 25 else "#c0392b")
    pct_on   = A["pct_on_track"]
    pct_off  = A["pct_off_cycle"]
    pct_crit = A["pct_gap_critical"]
    n_pipe   = A["n_pipeline"]
    n_curr   = A["n_current_cycle"]
    n_gap_cr = A["n_gap_critical"]

    # ── Executive KPI data for JS injection ───────────────────────────────────
    import json as _json
    exec_kpis_json        = _json.dumps(A["exec_kpis"], ensure_ascii=False)
    timeline_by_type_json = _json.dumps(A["timeline_by_type"], ensure_ascii=False)
    spi_scores_json = _json.dumps(
        {row["country"]: round(float(row["spi"]), 1) for _, row in A["spi"].iterrows()},
        ensure_ascii=False
    )
    import pandas as _pd
    spi_table_json = _json.dumps([
        {"country": str(r["country"]),
         "iso3":  str(r["iso3"]) if _pd.notna(r["iso3"]) else "",
         "spi":   round(float(r["spi"]),  1),
         "tier":  int(r["tier"]),
         "tier_label": str(r["tier_label"]),
         "d_coverage":  round(float(r["d_coverage"]),  1),
         "d_recency":   round(float(r["d_recency"]),   1),
         "d_regularity": round(float(r["d_regularity"]), 1) if _pd.notna(r["d_regularity"]) else None,
         "last_year": int(r["last_year"]) if _pd.notna(r["last_year"]) else None,
         "gap_years": int(r["gap_years"]) if _pd.notna(r["gap_years"]) else None,
         "n_done":    int(r["n_done"]),
         "types_done":int(r["types_done"])}
        for _, r in A["spi"].iterrows()
    ], ensure_ascii=False)
    # ── STEPS profile data ────────────────────────────────────────────────────
    steps_profile = A.get("steps_profile", {})
    steps_profile_json = _json.dumps(steps_profile, ensure_ascii=False) if steps_profile else "null"

    # Build country profile dropdown options (default: Ethiopia, else first)
    _prof_countries = steps_profile.get("countries", [])
    _prof_default   = "Ethiopia" if "Ethiopia" in _prof_countries else (_prof_countries[0] if _prof_countries else "")
    _prof_options   = "\n".join(
        f'<option value="{c}"{"  selected" if c == _prof_default else ""}>{c}</option>'
        for c in _prof_countries
    )
    _prof_n = len(_prof_countries)

    exec_global    = A["exec_kpis"]["global"]
    exec_steps     = A["exec_kpis"]["STEPS"]
    js_with_data   = (JS
                      .replace("__EXEC_DATA_PLACEHOLDER__",     exec_kpis_json)
                      .replace("__TIMELINE_DATA_PLACEHOLDER__",  timeline_by_type_json)
                      .replace("__SPI_SCORES_PLACEHOLDER__",    spi_scores_json)
                      .replace("__STEPS_PROFILE_PLACEHOLDER__", steps_profile_json)
                      .replace("__SPI_TABLE_PLACEHOLDER__", spi_table_json))

    # Build favicon link and logo img tags (empty string if asset not found)
    fav_link = f'<link rel="icon" type="image/png" href="data:image/png;base64,{FAV_LOGO_B64}"/>' if FAV_LOGO_B64 else ""
    who_logo_tag = (f'<a href="https://www.afro.who.int/" target="_blank" rel="noopener" title="WHO African Region">'
                    f'<img src="data:image/png;base64,{WHO_LOGO_B64}" alt="WHO Logo" style="height:40px;display:block;"/></a>') if WHO_LOGO_B64 else ""
    dpc_logo_tag = (f'<a href="https://dataportal.afro.who.int/" target="_blank" rel="noopener" title="DPC Data Portal">'
                    f'<img src="data:image/png;base64,{DPC_LOGO_B64}" alt="DPC Data Portal" style="height:34px;display:block;"/></a>') if DPC_LOGO_B64 else ""
    # Footer logo variants (slightly larger, also clickable)
    who_footer_tag = (f'<a href="https://www.afro.who.int/" target="_blank" rel="noopener" title="WHO African Region">'
                      f'<img src="data:image/png;base64,{WHO_LOGO_B64}" alt="WHO" style="height:44px;display:inline-block;vertical-align:middle;filter:brightness(0) invert(1);opacity:.85;transition:opacity .2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=.85"/></a>') if WHO_LOGO_B64 else ""
    dpc_footer_tag = (f'<a href="https://dataportal.afro.who.int/" target="_blank" rel="noopener" title="DPC Data Portal">'
                      f'<img src="data:image/png;base64,{DPC_LOGO_B64}" alt="DPC" style="height:38px;display:inline-block;vertical-align:middle;filter:brightness(0) invert(1);opacity:.85;transition:opacity .2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=.85"/></a>') if DPC_LOGO_B64 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>NCD Population-based Surveillance Intelligence Platform - WHO AFRO</title>
{fav_link}
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
<style>{CSS}</style>
</head>
<body>
<div id="reading-progress"></div>

<nav class="topnav">
  <div class="topnav-inner">
    <div class="nav-logos">
      {who_logo_tag}
      <div class="nav-divider"></div>
      {dpc_logo_tag}
      <div class="nav-divider"></div>
      <div class="nav-brand-text">
        <div class="nav-brand-title">NCD Population-based Surveillance Intelligence Platform</div>
        <div class="nav-brand-sub">WHO African Region &middot; DPC &middot; {CURRENT_YEAR}</div>
      </div>
    </div>
  </div>
</nav>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-left">
      <h1>NCD Population-based<br>Surveillance <span class="grad">Intelligence</span> Platform</h1>
      <p class="hero-sub">A strategic intelligence platform synthesizing <strong>five core NCD population-based surveillance systems</strong> across 47 WHO AFRO Member States + Zanzibar</p>
      <div class="hero-quick-stats">
        <span class="hero-qs"><i class="fas fa-circle" style="color:#00a651"></i> {n_strong} Strong performers</span>
        <span class="hero-qs"><i class="fas fa-circle" style="color:#c0392b"></i> {n_crit} Critical</span>
        <span class="hero-qs"><i class="fas fa-sync-alt" style="color:#4a90e2"></i> {n_curr} surveys this cycle</span>
      </div>
    </div>
    <div class="hero-right">
      <div class="hero-right-orb hero-right-orb-1"></div>
      <div class="hero-right-orb hero-right-orb-2"></div>
      <div class="hero-right-orb hero-right-orb-3"></div>
      <div class="hero-stats">
        <div class="hero-stat-badge">
          <div class="hero-stat-inner">
            <div class="hero-stat-val">{n_ent}</div>
            <div class="hero-stat-lbl">Countries &amp; Territories</div>
          </div>
        </div>
        <div class="hero-stat-badge">
          <div class="hero-stat-inner">
            <div class="hero-stat-val">5</div>
            <div class="hero-stat-lbl">Survey Instruments</div>
          </div>
        </div>
        <div class="hero-stat-badge" style="border-top:3px solid {spi_tier_color}">
          <div class="hero-stat-inner">
            <div class="hero-stat-val">{reg_spi:.0f}<sup>/100</sup></div>
            <div class="hero-stat-lbl">Regional SPI Score</div>
          </div>
          <div class="hero-spi-bar"><div class="hero-spi-fill" style="width:{reg_spi:.0f}%;background:{spi_tier_color}"></div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="tab-nav">
  <div class="tab-nav-inner">
    <button class="tab-btn" data-tab="tab-exec"><i class="fas fa-tachometer-alt"></i> Executive Overview</button>
    <button class="tab-btn" data-tab="tab-perf"><i class="fas fa-medal"></i> Surveillance Performance</button>
    <button class="tab-btn" data-tab="tab-cycle"><i class="fas fa-sync-alt"></i> Cycle &amp; Gap</button>
    <button class="tab-btn" data-tab="tab-profile"><i class="fas fa-user-md"></i> Country Profile</button>
    <button class="tab-btn" data-tab="tab-priority"><i class="fas fa-crosshairs"></i> Strategic Priority</button>
    <button class="tab-btn" data-tab="tab-methods"><i class="fas fa-book"></i> Methods</button>
  </div>
</div>

<div class="container">

  <!-- ═══════════════════ TAB 1: EXECUTIVE OVERVIEW ═══════════════════ -->
  <div id="tab-exec" class="tab-pane active">
    <div class="section">

      <!-- Section header -->
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">1</span>
          <h2 class="section-title">Executive Overview</h2>
        </div>
        <p class="section-subtitle">Country-level surveillance status &mdash; unit of analysis: unique WHO AFRO countries and territories (N&nbsp;=&nbsp;48)</p>
      </div>

      <!-- ① SURVEY INSTRUMENT STATUS - Static, shown first, not affected by filter -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            {ch_survey_cmp}
            <div class="chart-commentary">
              Status distribution across all five NCD surveillance instruments (N&#160;=&#160;48 countries per instrument). Each bar shows how countries distribute across four mutually exclusive states: <strong style="color:#00a651;">On Cycle</strong> (completed &#8804;&#160;5 yr), <strong style="color:#f7941d;">Attempt to Update</strong> (prior evidence + active new round), <strong style="color:#4a90e2;">Off Cycle</strong> (prior evidence but surveillance idle), and <strong style="color:#adb5bd;">Never Conducted</strong> (no completed survey on record). This panel is static and reflects system-wide status across all survey types.
            </div>
          </div>
        </div>
      </div>

      <!-- Filter bar - STEPS default, no "All Survey Types" option -->
      <div class="filter-bar">
        <span class="filter-label"><i class="fas fa-filter"></i>&nbsp; View by Survey</span>
        <select id="exec-survey-filter" class="filter-select" style="min-width:240px;">
          <option value="STEPS" selected>STEPS &mdash; NCD Risk Factor Surveillance</option>
          <option value="GYTS">GYTS &mdash; Global Youth Tobacco Survey</option>
          <option value="GSHS">GSHS &mdash; School-based Student Health Survey</option>
          <option value="GATS">GATS &mdash; Global Adult Tobacco Survey</option>
          <option value="GSHPP">GSHPP &mdash; School Health Policies &amp; Practices</option>
        </select>
        <button id="exec-filter-reset" class="filter-reset" style="padding:7px 14px;">
          <i class="fas fa-undo"></i>&nbsp; Reset to STEPS
        </button>
        <span id="exec-survey-badge" style="font-size:11.5px;font-weight:600;color:var(--primary);margin-left:6px;padding:5px 12px;background:#eef4ff;border-radius:20px;border:1px solid #c8d8f8;">
          STEPS &mdash; NCD Risk Factor Surveillance
        </span>
      </div>

      <!-- Analytical note -->
      <div style="background:#fffbeb;border:1px solid #fde68a;border-left:4px solid #f59e0b;border-radius:10px;padding:11px 16px;font-size:12px;color:#78350f;margin-bottom:20px;display:flex;align-items:flex-start;gap:10px;">
        <i class="fas fa-info-circle" style="margin-top:2px;color:#f59e0b;"></i>
        <span>
          <strong>Unit of analysis:</strong> All counts represent <strong>unique countries/territories</strong> (N&nbsp;=&nbsp;48). Categories are mutually exclusive per country per survey type.
          &nbsp;<strong style="color:#00a651;">&#9632; On Cycle</strong>: completed &#8804;&nbsp;5 yr &mdash; current, usable evidence &nbsp;|&nbsp;
          <strong style="color:#4a90e2;">&#9632; Attempt to update</strong>: prior completed data + new round actively in progress (never-conducted excluded) &nbsp;|&nbsp;
          <strong style="color:#f7941d;">&#9632; Off Cycle</strong>: has prior evidence but surveillance is currently idle &nbsp;|&nbsp;
          <strong style="color:#909090;">&#9632; Never Conducted</strong>: no completed survey ever &mdash; includes countries currently in a first-time attempt
        </span>
      </div>

      <!-- ② FOUR DYNAMIC KPI SIGNAL CARDS -->
      <div class="signal-grid" style="grid-template-columns:repeat(4,1fr);">

        <div class="signal-card reveal" style="color:#00a651;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#00a651;margin-bottom:4px;">
            <i class="fas fa-check-circle"></i>&nbsp; On Cycle
          </div>
          <div class="signal-val" id="exec-n-oncycle">{exec_steps['n_on_cycle']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-oncycle-sub">{exec_steps['n_on_cycle']} of {n_ent} countries</div>
          <div id="exec-n-oncycle-def" style="font-size:10px;color:#6b7280;margin-top:5px;line-height:1.4;">
            Completed &#8804;&nbsp;5 years ago &mdash; current, usable evidence
          </div>
        </div>

        <div class="signal-card reveal" style="color:#4a90e2;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#4a90e2;margin-bottom:4px;">
            <i class="fas fa-sync-alt"></i>&nbsp; Attempt to Update
          </div>
          <div class="signal-val" id="exec-n-implement">{exec_steps['n_attempt_to_update']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-implement-sub">{exec_steps['n_attempt_to_update']} of {n_ent} countries</div>
          <div id="exec-n-implement-def" style="font-size:10px;color:#6b7280;margin-top:5px;line-height:1.4;">
            Prior evidence exists &mdash; actively updating with new survey
          </div>
        </div>

        <div class="signal-card reveal" style="color:#f7941d;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#f7941d;margin-bottom:4px;">
            <i class="fas fa-pause-circle"></i>&nbsp; Off Cycle
          </div>
          <div class="signal-val" id="exec-n-offcycle">{exec_steps['n_off_cycle']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-offcycle-sub">{exec_steps['n_off_cycle']} of {n_ent} countries</div>
          <div id="exec-n-offcycle-def" style="font-size:10px;color:#6b7280;margin-top:5px;line-height:1.4;">
            Has prior evidence but surveillance is idle &mdash; off-cycle
          </div>
        </div>

        <div class="signal-card reveal" style="color:#909090;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#909090;margin-bottom:4px;">
            <i class="fas fa-ban"></i>&nbsp; Never Conducted
          </div>
          <div class="signal-val" id="exec-n-never">{exec_steps['n_never']}</div>
          <div class="signal-lbl">Countries</div>
          <div class="signal-sub" id="exec-n-never-sub">{exec_steps['n_never']} of {n_ent} countries</div>
          <div id="exec-n-never-def" style="font-size:10px;color:#6b7280;margin-top:5px;line-height:1.4;">
            Never completed &mdash; no policy-usable evidence exists
          </div>
        </div>

      </div>

      <!-- ③ SURVEILLANCE STATUS DISTRIBUTION - Dynamic donut -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            <div id="exec-donut-chart" style="min-height:420px;"></div>
            <div class="chart-commentary">
              Distribution of 48 countries by surveillance status for the selected survey instrument. Each slice shows the count and percentage for that status category. Categories are mutually exclusive and exhaustive &mdash; every country falls into exactly one group. Switch the survey filter above to compare status profiles across instruments.
            </div>
          </div>
        </div>
      </div>

      <!-- ④ YEARS SINCE MOST RECENT SURVEY - Dynamic gap chart -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            <div id="exec-gap-chart" style="min-height:500px;"></div>
            <div class="chart-commentary">
              <strong>Years since last completed survey</strong> for the selected instrument, by country, sorted from most recent (left) to longest gap (right). The Y-axis reflects time relative to 2026 &mdash; countries with identical gaps align at the same height. Color coding: <span style="color:#00a651;font-weight:700;">&#9632; On Cycle</span> (0&ndash;4 yrs), <span style="color:#c8a600;font-weight:700;">&#9632; Approaching</span> (5&ndash;9 yrs), <span style="color:#f7941d;font-weight:700;">&#9632; Off Cycle</span> (10&ndash;14 yrs), <span style="color:#c0392b;font-weight:700;">&#9632; Critical</span> (15+ yrs). Dashed horizontal lines mark the 5, 10, and 15-year thresholds. Countries with no completed survey for the selected instrument are excluded.
            </div>
          </div>
        </div>
      </div>

      <!-- Executive briefing (dynamic narrative) -->
      <div class="exec-message reveal">
        <h3><i class="fas fa-satellite-dish"></i>&nbsp; Regional Surveillance Intelligence Briefing</h3>
        <p id="exec-briefing-text">{exec_steps['briefing']}</p>
      </div>

    </div>
  </div>

  <!-- TAB 2: SURVEILLANCE PERFORMANCE -->
  <div id="tab-perf" class="tab-pane">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">2</span>
          <h2 class="section-title">Surveillance Performance</h2>
        </div>
        <p class="section-subtitle">Surveillance Performance Index (SPI) &mdash; composite score across Coverage, Recency &amp; Regularity &mdash; all {n_ent} countries ranked</p>
      </div>

      <!-- Regional SPI + Tier overview -->
      <div class="stat-highlight-row reveal">
        <div class="stat-highlight-item" style="text-align:center;padding:0 24px 0 0;">
          <div class="stat-hl-val" style="color:{spi_tier_color};">{reg_spi}<span style="font-size:1rem;font-weight:600;opacity:.6;">/100</span></div>
          <div class="stat-hl-lbl">Regional SPI Average</div>
        </div>
        <div class="stat-highlight-item" style="text-align:center;padding:0 24px;">
          <div class="stat-hl-val" style="color:var(--muted);">{A['median_spi']}</div>
          <div class="stat-hl-lbl">Median SPI</div>
        </div>
        <div style="flex:1;display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end;">
          <div class="tier-card" style="border-top-color:#00a651;min-width:110px;">
            <div class="tier-card-val" style="color:#00a651;">{int((spi['tier']==1).sum())}</div>
            <div class="tier-card-lbl">Strong</div>
            <div class="tier-card-sub">SPI &#8805; 75</div>
          </div>
          <div class="tier-card" style="border-top-color:#4a90e2;min-width:110px;">
            <div class="tier-card-val" style="color:#4a90e2;">{int((spi['tier']==2).sum())}</div>
            <div class="tier-card-lbl">Advancing</div>
            <div class="tier-card-sub">SPI 50&#8211;74</div>
          </div>
          <div class="tier-card" style="border-top-color:#f7941d;min-width:110px;">
            <div class="tier-card-val" style="color:#f7941d;">{int((spi['tier']==3).sum())}</div>
            <div class="tier-card-lbl">Developing</div>
            <div class="tier-card-sub">SPI 30&#8211;49</div>
          </div>
          <div class="tier-card" style="border-top-color:#c0392b;min-width:110px;">
            <div class="tier-card-val" style="color:#c0392b;">{n_crit}</div>
            <div class="tier-card-lbl">Critical</div>
            <div class="tier-card-sub">SPI &lt; 30</div>
          </div>
        </div>
      </div>

      {insight_box(f"<strong>Regional SPI: {reg_spi}/100</strong> - Median: {A['median_spi']} &nbsp;·&nbsp; <strong>{n_strong}</strong> countries achieve Strong status (SPI ≥ 75), while <strong>{n_crit}</strong> remain Critical (SPI < 30). The SPI is a composite of three equally-weighted dimensions: <strong>Coverage</strong> (how many of 5 instruments used), <strong>Recency</strong> (currency of evidence), and <strong>Regularity</strong> (cycle adherence). Scroll down to explore dimension-level breakdowns.", "info")}

      <!-- SPI bar chart -->
      <div class="row">
        <div class="col-12">
          <div class="chart-card reveal">
            {ch_spi_bar}
            <div class="chart-commentary">Full country ranking by SPI score (0–100). Dashed threshold lines mark the four performance tiers. Countries in the Critical tier show compound weaknesses across all three SPI dimensions - they lack breadth of instruments, currency of evidence, and cycle regularity simultaneously.</div>
          </div>
        </div>
      </div>

      <!-- Divider -->
      <div class="section-divider-label">Country Scorecard</div>

      <!-- Filter + Scorecard table -->
      <div class="filter-bar">
        <span class="filter-label"><i class="fas fa-search"></i></span>
        <input id="sc-search" class="filter-input" type="text" placeholder="Search country&#8230;"/>
        <span class="filter-label">Tier</span>
        <select id="sc-tier" class="filter-select">
          <option value="">All Tiers</option>
          <option value="1">Strong (&#8805;75)</option>
          <option value="2">Advancing (50&#8211;74)</option>
          <option value="3">Developing (30&#8211;49)</option>
          <option value="4">Critical (&lt;30)</option>
        </select>
        <span class="filter-label">Gap</span>
        <select id="sc-gap" class="filter-select">
          <option value="">All Gaps</option>
          <option value="&#8804;5 years">&#8804;5 years</option>
          <option value="6&#8211;10 years">6&#8211;10 years</option>
          <option value=">10 years">&gt;10 years</option>
          <option value="No data">No data</option>
        </select>
        <span class="filter-label">Cycle</span>
        <select id="sc-cycle" class="filter-select">
          <option value="">All</option>
          <option value="1">Active this cycle</option>
          <option value="0">No recent activity</option>
        </select>
        <span class="filter-label">Regularity</span>
        <select id="sc-reg" class="filter-select">
          <option value="">All</option>
          <option value="High">High (&#8804;6 yr avg)</option>
          <option value="Moderate">Moderate (7&#8211;9 yr avg)</option>
          <option value="Low">Low (&gt;9 yr avg)</option>
          <option value="Not">Not renewable yet</option>
        </select>
        <span class="filter-label">Show</span>
        <select id="sc-top" class="filter-select">
          <option value="0">All countries</option>
          <option value="10">Top 10</option>
          <option value="20">Top 20</option>
          <option value="30">Top 30</option>
        </select>
        <button id="sc-reset" class="filter-reset"><i class="fas fa-undo"></i> Reset</button>
        <span id="sc-count" class="filter-count"></span>
      </div>

      <div class="chart-card reveal" style="margin-bottom:20px;">
        <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
          <button id="btn-export-spi" style="font-family:var(--font);font-size:11px;font-weight:700;padding:7px 16px;border-radius:8px;border:none;background:#003d82;color:#fff;cursor:pointer;display:inline-flex;align-items:center;gap:6px;"><i class="fas fa-file-excel"></i>&nbsp;Export Excel</button>
        </div>
        {scorecard_table(spi)}
      </div>

    </div>
  </div>

  <!-- TAB 3: CYCLE & GAP -->
  <div id="tab-cycle" class="tab-pane">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">3</span>
          <h2 class="section-title">5-Year Cycle &amp; Gap Analysis</h2>
        </div>
        <p class="section-subtitle">Operational accountability &mdash; current cycle {CURRENT_CYCLE_START}&ndash;{CURRENT_YEAR} &middot; WHO-recommended 5-year surveillance frequency</p>
      </div>

      <!-- Historical Activity Timeline (dynamic, filterable) -->
      <div class="section-divider-label">Historical Activity Timeline - By Survey Instrument</div>
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;flex-wrap:wrap;">
        <label style="font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.5px;text-transform:uppercase;">Survey instrument:</label>
        <select id="cycle-timeline-filter" style="font-family:var(--font);font-size:13px;font-weight:600;border:1.5px solid var(--border);border-radius:8px;padding:7px 14px;background:#fff;color:var(--text);cursor:pointer;transition:border-color .2s;" onchange="updateTimeline(this.value)">
          <option value="STEPS" selected>STEPS - NCD Risk Factor Survey</option>
          <option value="GYTS">GYTS - Global Youth Tobacco Survey</option>
          <option value="GSHS">GSHS - Global School Health Survey</option>
          <option value="GATS">GATS - Global Adult Tobacco Survey</option>
          <option value="GSHPP">GSHPP - School Health Policies &amp; Practices</option>
        </select>
        <button onclick="(function(){{var f=document.getElementById('cycle-timeline-filter');f.value='STEPS';updateTimeline('STEPS');}})();" style="font-family:var(--font);font-size:11px;font-weight:600;border:1.5px solid var(--border);border-radius:8px;padding:7px 14px;background:#f4f7fb;color:var(--muted);cursor:pointer;transition:all .2s;" onmouseover="this.style.background='#e2e8f0'" onmouseout="this.style.background='#f4f7fb'"><i class="fas fa-undo" style="margin-right:5px;"></i>Reset</button>
      </div>
      <div class="chart-card reveal" style="margin-bottom:24px;">
        <div id="cycle-timeline-chart" style="width:100%;min-height:400px;"></div>
        <div class="chart-commentary">Annual count of countries completing the selected survey instrument, from {A['year_min']} to {CURRENT_YEAR}. Green bars = current 5-year cycle ({CURRENT_CYCLE_START}&ndash;{CURRENT_YEAR}). Blue bars = prior survey rounds. The green-shaded zone highlights the current cycle period. Use the filter above to switch between the five WHO NCD surveillance instruments.</div>
      </div>

      <!-- Instrument completion overview (current cycle) -->
      <div class="section-divider-label">Instrument Activity Cards &mdash; Current Cycle {CURRENT_CYCLE_START}&ndash;{CURRENT_YEAR}</div>
      {instrument_cards(A)}

      <!-- Recency matrix -->
      <div class="section-divider-label" style="margin-top:28px;">Surveillance Recency Matrix &mdash; Country &times; Instrument</div>
      <div class="chart-card reveal">
        {ch_heatmap}
        <div class="chart-commentary"><strong>Surveillance Recency Matrix:</strong> Each cell = year of the most recent <em>completed</em> survey for a given country &times; instrument pair. <span style="display:inline-block;background:#dde4ee;border-radius:4px;padding:1px 8px;font-size:11px;font-weight:600;color:#555;">Grey</span> = no completed survey on record (never conducted). Deep green = current evidence (2021&ndash;2026). Yellow/orange = evidence ageing. Red = critically outdated. Countries sorted top-to-bottom by SPI rank. Grey cells indicate instrument-specific evidence gaps requiring targeted reinvestment.</div>
      </div>

    </div>
  </div>

  <!-- TAB 4: COUNTRY PROFILE -->
  <div id="tab-profile" class="tab-pane">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">4</span>
          <h2 class="section-title">Country Profile</h2>
        </div>
        <p class="section-subtitle">
          In-depth NCD risk factor profile &mdash; STEPS indicator data by domain, sex &amp; survey round &mdash;
          {_prof_n} countries with STEPS data available
        </p>
      </div>

      {'<div class="profile-no-data" style="padding:40px;text-align:center;color:var(--muted);"><i class="fas fa-database" style="font-size:32px;opacity:.3;margin-bottom:12px;display:block;"></i><p>No STEPS indicator data found. Ensure STEP.db is present in the data/ folder and run the pipeline.</p></div>' if not _prof_countries else ""}

      <div class="filter-bar" style="{'display:none;' if not _prof_countries else ''}">
        <span class="filter-label"><i class="fas fa-map-marker-alt"></i>&nbsp; Country</span>
        <select id="profile-country-select" class="filter-select" style="min-width:270px;">
          {_prof_options}
        </select>
        <span class="filter-label" style="margin-left:6px;">Survey</span>
        <select id="profile-survey-select" class="filter-select" style="min-width:200px;" disabled>
          <option value="STEPS" selected>STEPS &mdash; NCD Risk Factor Surveillance</option>
        </select>
        <span style="font-size:11px;color:var(--muted);font-style:italic;margin-left:4px;display:flex;align-items:center;gap:5px;">
          <i class="fas fa-lock" style="font-size:10px;"></i>Additional survey types coming soon
        </span>
        <button id="btn-export-profile" style="font-family:var(--font);font-size:11px;font-weight:700;padding:7px 16px;border-radius:8px;border:none;background:#003d82;color:#fff;cursor:pointer;display:inline-flex;align-items:center;gap:6px;" style="margin-left:auto;"><i class="fas fa-file-excel"></i>&nbsp;Export Excel</button>
      </div>

      <div id="country-profile-content">
        <div class="profile-no-data">
          <i class="fas fa-mouse-pointer" style="font-size:36px;opacity:.25;"></i>
          <p style="font-size:14px;font-weight:600;color:var(--text);">Click the <strong>Country Profile</strong> tab to load the selected country</p>
          <p style="font-size:12px;">Select a country from the filter above to explore its full STEPS indicator profile.</p>
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 5: STRATEGIC PRIORITY -->
  <div id="tab-priority" class="tab-pane">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">5</span>
          <h2 class="section-title">Strategic Prioritisation</h2>
        </div>
        <p class="section-subtitle">Decision matrix per survey instrument &mdash; identify countries requiring immediate support, reactivation, or sustained monitoring</p>
      </div>

      <!-- Survey instrument filter pills -->
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:24px;padding:16px 20px;background:linear-gradient(135deg,#f0f4fc,#e8eef8);border-radius:14px;border:1px solid #d8def0;box-shadow:0 2px 10px rgba(0,20,80,.06);">
        <span style="font-size:10.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.9px;margin-right:4px;white-space:nowrap;"><i class="fas fa-sliders-h"></i>&nbsp; Survey instrument:</span>
        <button class="prio-pill" data-survey="STEPS"  data-color="#003d82" style="font-family:var(--font);font-size:12px;font-weight:700;padding:8px 20px;border-radius:22px;border:2px solid #003d82;background:#003d82;color:#fff;cursor:pointer;transition:all .25s;box-shadow:0 4px 12px rgba(0,61,130,.3);">STEPS</button>
        <button class="prio-pill" data-survey="GYTS"   data-color="#c0392b" style="font-family:var(--font);font-size:12px;font-weight:700;padding:8px 20px;border-radius:22px;border:2px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:all .25s;">GYTS</button>
        <button class="prio-pill" data-survey="GSHS"   data-color="#f7941d" style="font-family:var(--font);font-size:12px;font-weight:700;padding:8px 20px;border-radius:22px;border:2px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:all .25s;">GSHS</button>
        <button class="prio-pill" data-survey="GATS"   data-color="#8e44ad" style="font-family:var(--font);font-size:12px;font-weight:700;padding:8px 20px;border-radius:22px;border:2px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:all .25s;">GATS</button>
        <button class="prio-pill" data-survey="GSHPP"  data-color="#00a651" style="font-family:var(--font);font-size:12px;font-weight:700;padding:8px 20px;border-radius:22px;border:2px solid var(--border);background:#f4f7fb;color:var(--muted);cursor:pointer;transition:all .25s;">GSHPP</button>
        <span style="margin-left:auto;font-size:11px;color:var(--muted);font-style:italic;"><i class="fas fa-info-circle"></i>&nbsp; All elements refresh on survey change</span>
      </div>

      <!-- Quadrant scatter chart -->
      <div class="chart-card reveal" style="margin-bottom:24px;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:14px;">
          <div>
            <h3 style="font-size:14px;font-weight:700;color:{C['primary']};margin:0 0 4px;"><i class="fas fa-crosshairs"></i>&nbsp; Strategic Quadrant Analysis</h3>
            <p style="font-size:11.5px;color:var(--muted);margin:0;line-height:1.5;">Country position: <strong>survey gap</strong> (x) vs <strong>overall SPI</strong> (y). Drag sliders to redefine quadrant boundaries.</p>
          </div>
          <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:11px;font-weight:600;align-items:center;">
            <span><span style="color:#c0392b;font-size:14px;">&#9632;</span> URGENT</span>
            <span><span style="color:#f7941d;font-size:14px;">&#9632;</span> REINVEST</span>
            <span><span style="color:#4a90e2;font-size:14px;">&#9632;</span> DEVELOP</span>
            <span><span style="color:#00a651;font-size:14px;">&#9632;</span> SUSTAIN</span>
          </div>
        </div>
        <!-- Movable threshold sliders -->
        <div style="display:flex;gap:32px;flex-wrap:wrap;align-items:center;padding:12px 16px;background:#f0f4fc;border-radius:10px;margin-bottom:14px;border:1px solid #d8def0;">
          <div style="display:flex;align-items:center;gap:10px;">
            <i class="fas fa-arrows-alt-h" style="color:#14265c;font-size:13px;"></i>
            <span style="font-size:11px;font-weight:700;color:{C['primary']};white-space:nowrap;">Gap threshold:</span>
            <input type="range" id="prio-gap-cut" min="1" max="35" value="5"
              style="width:130px;accent-color:#003d82;cursor:pointer;"/>
            <span style="font-size:13px;font-weight:800;color:#003d82;min-width:38px;"><span id="prio-gap-val">5</span>&nbsp;yrs</span>
          </div>
          <div style="width:1px;height:28px;background:#d0d8ee;"></div>
          <div style="display:flex;align-items:center;gap:10px;">
            <i class="fas fa-arrows-alt-v" style="color:#14265c;font-size:13px;"></i>
            <span style="font-size:11px;font-weight:700;color:{C['primary']};white-space:nowrap;">SPI threshold:</span>
            <input type="range" id="prio-spi-cut" min="5" max="95" value="50"
              style="width:130px;accent-color:#003d82;cursor:pointer;"/>
            <span style="font-size:13px;font-weight:800;color:#003d82;min-width:38px;"><span id="prio-spi-val">50</span>&nbsp;pts</span>
          </div>
          <span style="font-size:10.5px;color:var(--muted);font-style:italic;margin-left:auto;"><i class="fas fa-hand-pointer"></i>&nbsp; Sliders update the chart in real time</span>
        </div>
        <div id="prio-scatter-chart" style="height:490px;width:100%;"></div>
      </div>

      <!-- Per-instrument operational detail -->
      <div class="section-divider-label">Country-Level Operational Detail</div>
      {survey_sections}

    </div>
  </div>

  <!-- TAB 6: METHODS -->
  <div id="tab-methods" class="tab-pane">
    <div class="section">
      <div class="section-header">
        <div class="section-header-inner">
          <span class="section-num">6</span>
          <h2 class="section-title">Methodology &amp; Definitions</h2>
        </div>
        <p class="section-subtitle">Analytical framework, key definitions, and data model underpinning this platform</p>
      </div>

      <div class="methods-grid" style="grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px;">

        <!-- Data Source -->
        <div class="method-card reveal" style="border-top:4px solid #003d82;">
          <h4 style="color:#003d82;"><i class="fas fa-globe-africa"></i>&nbsp; Data Source</h4>
          <ul>
            <li><strong>Source:</strong> WHO Noncommunicable Diseases Country Tracking</li>
            <li><strong>Coverage:</strong> {n_ent} entities (47 WHO AFRO Member States + Zanzibar)</li>
            <li><strong>Instruments:</strong> 5 NCD population-based surveillance systems</li>
            <li><strong>Period:</strong> {A['year_min']}&ndash;{CURRENT_YEAR} &nbsp;&middot;&nbsp; {A['n_records']} survey records</li>

          </ul>
        </div>

        <!-- SPI -->
        <div class="method-card reveal" style="border-top:4px solid #0070c0;">
          <h4 style="color:#0070c0;"><i class="fas fa-tachometer-alt"></i>&nbsp; Surveillance Performance Index (SPI)</h4>
          <p style="font-size:12px;color:var(--muted);margin-bottom:12px;line-height:1.8;">
            The SPI is a composite score from <strong>0 to 100</strong> that summarises how well a country&rsquo;s NCD surveillance system is performing across three equally weighted dimensions. It is designed for <strong>relative ranking and trend monitoring</strong> across WHO AFRO Member States.
          </p>
          <ul>
            <li style="margin-bottom:8px;"><strong style="color:#003d82;">Breadth:</strong> Has the country ever completed each of the five NCD surveillance instruments? A country that has used more instruments scores higher on this dimension, reflecting the <em>institutional range</em> of its surveillance system.</li>
            <li style="margin-bottom:8px;"><strong style="color:#003d82;">Currency:</strong> How recent is the available evidence? Older surveys contribute progressively less, with evidence value halving roughly every seven years. This dimension rewards countries that keep their data fresh and penalises those whose most recent survey is distant in time.</li>
            <li><strong style="color:#003d82;">Regularity:</strong> Does the country survey on schedule? Countries that complete each instrument close to the WHO-recommended five-year cycle score well. This dimension is only applicable when a country has conducted a given instrument at least twice, as a single round is not enough to assess cycling behaviour.</li>
          </ul>
          <p style="font-size:11.5px;color:var(--muted);margin-top:12px;margin-bottom:12px;line-height:1.75;font-style:italic;">
            The three dimensions are equally weighted and combined into a single score. Countries that have never conducted any survey score zero. Countries with broad, current, and regular surveillance score toward 100.
          </p>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <span style="background:#00a651;color:#fff;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">Strong &#8805;75</span>
            <span style="background:#4a90e2;color:#fff;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">Advancing 50&ndash;74</span>
            <span style="background:#f7941d;color:#fff;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">Developing 30&ndash;49</span>
            <span style="background:#c0392b;color:#fff;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">Critical &lt;30</span>
          </div>
        </div>

        <!-- Surveillance Status -->
        <div class="method-card reveal" style="border-top:4px solid #00a651;">
          <h4 style="color:#00a651;"><i class="fas fa-satellite-dish"></i>&nbsp; Surveillance Status Categories</h4>
          <p style="font-size:12px;color:var(--muted);margin-bottom:10px;line-height:1.7;">
            Each country is assigned exactly <strong>one status per survey instrument</strong>. Categories are mutually exclusive and exhaustive; all 48 entities are covered.
          </p>
          <ul>
            <li><strong style="color:#00a651;">On Cycle:</strong> Completed within the last 5 years. Evidence is current and policy-usable.</li>
            <li><strong style="color:#4a90e2;">Attempt to Update:</strong> Prior completed evidence exists and a new survey round is actively in progress. Countries with no prior completion are excluded even if attempting a first round.</li>
            <li><strong style="color:#f7941d;">Off Cycle:</strong> Has completed before but no current survey process is active. Surveillance is idle and evidence is ageing.</li>
            <li><strong style="color:#909090;">Never Conducted:</strong> No completed survey on record. Countries in a first-time attempt remain here until completion is confirmed.</li>
          </ul>
        </div>

        <!-- Instruments -->
        <div class="method-card reveal" style="border-top:4px solid #8e44ad;">
          <h4 style="color:#8e44ad;"><i class="fas fa-flask"></i>&nbsp; The 5 Population-Based Surveillance Instruments</h4>
          <ul>
            <li><strong style="color:#003d82;">STEPS:</strong> WHO STEPwise Approach to NCD Risk Factor Surveillance, adults 18-69, NCD risk factors (flagship instrument)</li>
            <li><strong style="color:#c0392b;">GYTS:</strong> Global Youth Tobacco Survey, students 13-15, youth tobacco use</li>
            <li><strong style="color:#f7941d;">GSHS:</strong> Global School-based Student Health Survey, students 13-17, youth health behaviours</li>
            <li><strong style="color:#8e44ad;">GATS:</strong> Global Adult Tobacco Survey, adults 15 years and older, adult tobacco and cessation</li>
            <li><strong style="color:#00a651;">GSHPP:</strong> Global School Health Policies and Practices, school level, health policy environment</li>
          </ul>
          <p style="font-size:11px;color:var(--muted);margin-top:10px;line-height:1.6;">All instruments operate on a WHO-recommended 5-year renewal cycle. Countries are expected to complete a new round within each 5-year window to maintain current population-based surveillance intelligence.</p>
        </div>

        <!-- Limitations -->
        <div class="method-card reveal" style="border-top:4px solid #e67e22;">
          <h4 style="color:#e67e22;"><i class="fas fa-exclamation-triangle"></i>&nbsp; Analytical Notes &amp; Limitations</h4>
          <ul>
            <li><strong>Unit of analysis:</strong> Country/territory (N=48). Sub-national units are not tracked.</li>
            <li><strong>Data currency:</strong> Status reflects the most recent available WHO tracking data. In-progress surveys may have completed since last extraction.</li>
            <li><strong>Regularity dimension:</strong> Requires &#8805;&nbsp;2 completed rounds per instrument. Countries with a single completion score zero on Regularity by methodology, not by performance failure.</li>
            <li><strong>Gap calculation:</strong> Computed relative to {CURRENT_YEAR}. Countries with only &ldquo;Not Usable&rdquo; records are treated as having no completed survey.</li>
            <li><strong>SPI interpretation:</strong> The index is designed for relative ranking and trend monitoring, not for absolute quality assessment of individual surveys.</li>
          </ul>
        </div>


      </div>

    </div>
  </div>

</div><!-- /container -->

<footer class="footer">
  <div class="footer-inner">
    <div style="display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
      {who_footer_tag}
      <div style="width:1px;height:40px;background:rgba(255,255,255,.18);"></div>
      {dpc_footer_tag}
      <div style="width:1px;height:40px;background:rgba(255,255,255,.18);"></div>
      <div>
        <div style="font-size:12px;font-weight:600;color:rgba(255,255,255,.9);line-height:1.6;">
          &copy; {CURRENT_YEAR} WHO African Region &ndash; Health Promotion / Disease Prevention and Control (DPC) Cluster
        </div>
      </div>
    </div>
  </div>
</footer>

<button id="back-to-top" aria-label="Back to top"><i class="fas fa-arrow-up"></i></button>
<script>{js_with_data}</script>
</body>
</html>"""
