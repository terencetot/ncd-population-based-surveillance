"""
NCD Surveillance Intelligence Platform - WHO African Region
Chart factory: all Plotly figure generators
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from src.config import (C, FONT, TIER_COLORS, TIER_LABELS, SURVEY_META,
                        CURRENT_YEAR, CYCLE_YEARS, CURRENT_CYCLE_START,
                        PREV_CYCLE_START, STATUS_COLORS)


def _layout(fig, title="", height=420):
    fig.update_layout(
        title=dict(text=title, font=dict(family=FONT, size=14, color=C["dark"]),
                   x=0, xanchor="left", pad=dict(l=2, t=4)),
        paper_bgcolor=C["white"], plot_bgcolor=C["white"],
        font=dict(family=FONT, size=12, color=C["text"]),
        autosize=True, height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(bgcolor="rgba(255,255,255,0.92)", bordercolor=C["border"],
                    borderwidth=1, font=dict(size=11)),
        hoverlabel=dict(bgcolor=C["dark"], font_size=12,
                        font_family=FONT, font_color="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor=C["border"], tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#f0f0f0", linecolor=C["border"], tickfont=dict(size=11))
    return fig


def _html(fig, first=False):
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if first else False,
        config={"displayModeBar":True,"responsive":True,
                "modeBarButtonsToRemove":["lasso2d","select2d"],
                "displaylogo":False},
    )


def fig_status_donut(A):
    sd = A["status_dist"]
    colors = [STATUS_COLORS.get(s, C["muted"]) for s in sd["status"]]
    fig = go.Figure(go.Pie(
        labels=sd["status"], values=sd["count"], marker_colors=colors,
        hole=0.62, textinfo="label+percent",
        textfont=dict(size=12, family=FONT),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        pull=[0.04 if s == "Not Usable" else 0 for s in sd["status"]],
    ))
    fig.add_annotation(
        text=f"<b>{A['n_completed']}</b><br><span style='font-size:11px'>Completed</span>",
        x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(size=16, color=C["dark"], family=FONT), align="center",
    )
    _layout(fig, "Survey Implementation Status", 360)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.08))
    return fig


def fig_spi_bar(A):
    spi = A["spi"].sort_values("spi", ascending=True)
    colors = [TIER_COLORS[t] for t in spi["tier"]]
    fig = go.Figure(go.Bar(
        y=spi["country"], x=spi["spi"],
        orientation="h", marker_color=colors,
        text=[f"{v:.0f}" for v in spi["spi"]], textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "SPI: %{x:.1f}/100<br>"
            "<extra></extra>"
        ),
    ))
    # Tier reference lines
    for thresh, label, col in [(28,"Developing",C["warning"]),(45,"Advancing",C["accent"]),(65,"Strong",C["success"])]:
        fig.add_vline(x=thresh, line_dash="dot", line_color=col, line_width=1.5,
                      annotation_text=label, annotation_position="top right",
                      annotation_font_size=10)
    _layout(fig, "Surveillance Performance Index (SPI) - All Countries", 900)
    fig.update_layout(
        xaxis=dict(title="SPI Score (0–100)", range=[0, 110]),
        yaxis=dict(title="", tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=50, b=10),
    )
    return fig


def fig_spi_choropleth(A):
    spi = A["spi"].copy()
    iso_agg = spi.groupby("iso3").agg(
        spi=("spi","mean"), country=("country","first"), tier=("tier","min")
    ).reset_index()
    fig = go.Figure(go.Choropleth(
        locations=iso_agg["iso3"], z=iso_agg["spi"], text=iso_agg["country"],
        colorscale=[[0,"#fde8e8"],[0.28,"#c0392b"],[0.45,"#f7941d"],
                    [0.65,"#4a90e2"],[1.0,"#00a651"]],
        zmin=0, zmax=100,
        marker_line_color=C["white"], marker_line_width=0.6,
        colorbar=dict(
            title=dict(text="SPI Score", font=dict(size=12)),
            thickness=14, len=0.55, x=0.93,
            tickvals=[0,30,50,75,100],
            ticktext=["0","Critical","Developing","Advancing","Strong"],
            tickfont=dict(size=10),
        ),
        hovertemplate="<b>%{text}</b><br>SPI: %{z:.1f}/100<extra></extra>",
    ))
    fig.update_geos(
        scope="africa", showframe=False,
        showcoastlines=True, coastlinecolor=C["border"],
        showland=True, landcolor="#f8f9fa",
        showocean=True, oceancolor="#e8f4f8",
        projection_type="natural earth", bgcolor=C["white"],
    )
    _layout(fig, "Surveillance Performance Index - Geographic Distribution", 520)
    fig.update_layout(geo=dict(bgcolor=C["white"]), margin=dict(l=0,r=0,t=50,b=0))
    return fig


def fig_tier_donut(A):
    spi = A["spi"]
    tier_counts = spi.groupby(["tier","tier_label"]).size().reset_index(name="n")
    tier_counts = tier_counts.sort_values("tier")
    colors = [TIER_COLORS[t] for t in tier_counts["tier"]]
    total = len(spi)
    fig = go.Figure(go.Pie(
        labels=tier_counts["tier_label"], values=tier_counts["n"],
        marker_colors=colors, hole=0.60,
        textinfo="label+value",
        textfont=dict(size=12, family=FONT),
        hovertemplate="<b>%{label}</b><br>Countries: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:11px'>Countries</span>",
        x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(size=16, color=C["dark"], family=FONT), align="center",
    )
    _layout(fig, "Performance Tier Distribution", 360)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.08))
    return fig


def fig_spi_components(A):
    spi = A["spi"].copy().sort_values("spi", ascending=True)
    fig = go.Figure()
    dims = [
        ("d_coverage",   "BS - Breadth Score",                   "#4a90e2"),
        ("d_recency",    "CS - Currency Score",                   "#f7941d"),
        ("d_regularity", "CA-ARI - Coverage-Adjusted Regularity", "#8e44ad"),
    ]
    for col, name, color in dims:
        fig.add_trace(go.Bar(
            y=spi["country"], x=spi[col],
            name=name, orientation="h",
            marker_color=color,
            hovertemplate=f"<b>%{{y}}</b><br>{name.split('-')[0].strip()}: %{{x:.1f}}<extra></extra>",
        ))
    _layout(fig, "SPI Dimension Breakdown - BS · CS · CA-ARI (All Countries)", 1000)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Weighted score contribution (0–100)", range=[0, 100]),
        yaxis=dict(tickfont=dict(size=10)),
        legend=dict(orientation="h", y=1.02, x=0, xanchor="left", font=dict(size=11)),
        margin=dict(l=10, r=30, t=60, b=10),
    )
    return fig


def fig_current_cycle(A):
    spi = A["spi"].copy()
    # Include only countries with any current-cycle activity
    active = spi[(spi["recent_done"] > 0) | (spi["recent_inprog"] > 0)].sort_values(
        ["recent_done","recent_inprog"], ascending=[True,True]
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=active["country"], x=active["recent_done"],
        name="Completed", orientation="h", marker_color=C["success"],
        hovertemplate="<b>%{y}</b><br>Completed in 2021–2026: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=active["country"], x=active["recent_inprog"],
        name="In Progress", orientation="h", marker_color=C["warning"],
        hovertemplate="<b>%{y}</b><br>In Progress 2021–2026: %{x}<extra></extra>",
    ))
    _layout(fig, f"Current 5-Year Cycle Activity ({CURRENT_CYCLE_START}–{CURRENT_YEAR})", 580)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Number of Surveys", dtick=1),
        yaxis=dict(title="", tickfont=dict(size=10)),
        legend=dict(orientation="h", y=-0.12),
        margin=dict(l=10, r=20, t=50, b=10),
    )
    return fig


def fig_last_year_heatmap(A):
    """
    Surveillance Recency Matrix - Country × Instrument.
    Colour = gap in years since last completed survey (green=recent, red=old, grey=never).
    Cell text = last completed year. Countries sorted by SPI rank (best at top).
    """
    lym    = A["last_year_matrix"].copy()
    spi_df = A["spi"]

    # Sort rows by SPI (best at top)
    spi_order = (spi_df.set_index("country")["spi"]
                 .reindex(lym.index, fill_value=0)
                 .sort_values(ascending=False).index)
    lym = lym.loc[spi_order]

    instruments = lym.columns.tolist()
    countries   = lym.index.tolist()

    # ── z = gap years; sentinel = -1 for no data ──────────────────────────────
    SENTINEL = -1
    Z_MAX    = 28        # cap: anything older than 28 yrs maps to darkest red

    z_arr, text_arr, hover_arr = [], [], []
    for c in countries:
        zrow, trow, hrow = [], [], []
        for st in instruments:
            yr = lym.loc[c, st]
            if pd.isna(yr):
                zrow.append(SENTINEL)
                trow.append("-")
                hrow.append(f"<b>{c}</b><br><b>{st}</b><br><i>No completed survey on record</i>")
            else:
                yr_int = int(yr)
                gap    = CURRENT_YEAR - yr_int
                z_val  = min(gap, Z_MAX)
                zrow.append(z_val)
                trow.append(str(yr_int))
                tag = ("✓ On Cycle" if gap <= 5
                       else f"⚠ {gap} yr gap" if gap <= 10
                       else f"⛔ {gap} yr gap")
                hrow.append(
                    f"<b>{c}</b><br><b>{st}</b>"
                    f"<br>Last completed: <b>{yr_int}</b>"
                    f"<br>Gap: <b>{gap} years</b>"
                    f"<br>{tag}"
                )
        z_arr.append(zrow)
        text_arr.append(trow)
        hover_arr.append(hrow)

    # ── Beautiful colorscale (gap 0=green → 28=dark red; sentinel=soft grey) ─
    # Plotly normalises [zmin, zmax] → [0, 1]
    # SENTINEL=-1, Z_MAX=28  →  range=29
    R = Z_MAX - SENTINEL          # = 29
    def _n(v): return (v - SENTINEL) / R   # normalize to [0,1]

    colorscale = [
        [_n(SENTINEL),       "#dde4ee"],   # no data: soft blue-grey
        [_n(SENTINEL)+0.025, "#dde4ee"],   # keep grey for sentinel zone
        [_n(0),              "#00693e"],   # gap 0: deep emerald - perfectly current
        [_n(3),              "#00a651"],   # gap 3: WHO green
        [_n(5),              "#52c41a"],   # gap 5: bright lime - on-cycle boundary
        [_n(8),              "#fadb14"],   # gap 8: yellow - approaching overdue
        [_n(12),             "#fa8c16"],   # gap 12: orange - clearly overdue
        [_n(18),             "#cf1322"],   # gap 18: deep red - critical
        [_n(Z_MAX),          "#5c0011"],   # gap 28+: dark wine - very critical
    ]

    n_rows = len(countries)
    height = max(580, n_rows * 20 + 180)

    fig = go.Figure(go.Heatmap(
        z=z_arr, x=instruments, y=countries,
        text=text_arr,
        texttemplate="%{text}",
        textfont=dict(size=10, family=FONT, color="white"),
        customdata=hover_arr,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=colorscale,
        zmin=SENTINEL, zmax=Z_MAX,
        showscale=True,
        colorbar=dict(
            title=dict(text="Gap (years)", font=dict(size=11, family=FONT), side="right"),
            thickness=16, len=0.55, x=1.01,
            tickvals=[0, 5, 10, 15, 20, Z_MAX],
            ticktext=["0 - Current", "5", "10", "15", "20", "28+"],
            tickfont=dict(size=10, family=FONT),
            outlinewidth=0,
            bgcolor="rgba(255,255,255,0)",
        ),
        xgap=5, ygap=4,
    ))

    fig.update_layout(
        title=dict(
            text="<b>Surveillance Recency Matrix</b> &nbsp;·&nbsp; Last Completed Survey Year",
            font=dict(family=FONT, size=14, color=C["dark"]),
            x=0, xanchor="left", pad=dict(l=4, t=6),
        ),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8faff",
        font=dict(family=FONT, size=12),
        autosize=True, height=height,
        margin=dict(l=10, r=100, t=80, b=50),
        xaxis=dict(
            side="top",
            tickangle=0,
            tickfont=dict(size=13, color=C["dark"], family=FONT),
            showgrid=False,
            linecolor=C["border"],
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=10, family=FONT),
            showgrid=False,
            linecolor=C["border"],
            title="",
        ),
        hoverlabel=dict(bgcolor=C["dark"], font_size=12,
                        font_family=FONT, font_color="white"),
    )

    # ── Bottom caption strip (legend) ─────────────────────────────────────────
    leg_items = [
        ("#dde4ee", "#555",  "No record"),
        ("#00693e", "white", "On Cycle (0–5 yr)"),
        ("#fa8c16", "white", "Off Cycle (6–12 yr)"),
        ("#cf1322", "white", "Critical (>12 yr)"),
    ]
    annotations = []
    n = len(leg_items)
    for i, (bg, fg, lbl) in enumerate(leg_items):
        annotations.append(dict(
            x=i / (n - 1), y=-0.06, xref="paper", yref="paper",
            text=(f"<span style='background:{bg};color:{fg};padding:3px 10px;"
                  f"border-radius:5px;font-size:10.5px;font-weight:600;"
                  f"border:1px solid rgba(0,0,0,.1)'>&nbsp;{lbl}&nbsp;</span>"),
            showarrow=False, xanchor="center",
        ))
    fig.update_layout(annotations=annotations)
    return fig


def fig_priority_scatter(A):
    spi = A["spi"].copy()
    spi["gap_plot"] = spi["gap_years"].fillna(float(CURRENT_YEAR - A["year_min"]))

    # Fixed thresholds matching the quadrant summary cards
    GAP_THRESH = 10   # years
    SPI_THRESH = 50   # score

    x_max = float(spi["gap_plot"].max()) + 3

    # Shade quadrant backgrounds before adding data traces
    fig = go.Figure()

    # Background rectangles per quadrant (added as shapes)
    quadrant_fills = [
        # (x0, x1, y0, y1, fillcolor, name)
        (0,          GAP_THRESH, SPI_THRESH, 105, "rgba(0,166,81,0.07)"),    # SUSTAIN
        (GAP_THRESH, x_max,      SPI_THRESH, 105, "rgba(247,148,29,0.07)"),  # REINVEST
        (0,          GAP_THRESH, 0,          SPI_THRESH, "rgba(74,144,226,0.07)"),  # DEVELOP
        (GAP_THRESH, x_max,      0,          SPI_THRESH, "rgba(192,57,43,0.08)"),   # URGENT
    ]

    for tier in [4, 3, 2, 1]:
        sub = spi[spi["tier"] == tier]
        if len(sub) == 0:
            continue

        # Use lists (not numpy arrays) for customdata to avoid serialisation issues
        cd = [[int(row["n_done"]), str(row["tier_label"]),
               int(row["gap_plot"]) if not pd.isna(row["gap_years"]) else "N/A"]
              for _, row in sub.iterrows()]

        fig.add_trace(go.Scatter(
            x=sub["gap_plot"].tolist(),
            y=sub["spi"].tolist(),
            mode="markers",
            name=TIER_LABELS[tier],
            marker=dict(
                size=[max(14, min(38, int(n) * 4)) for n in sub["n_done"]],
                color=TIER_COLORS[tier],
                line=dict(width=1.5, color="white"),
                opacity=0.85,
            ),
            text=sub["country"].tolist(),
            customdata=cd,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "SPI: <b>%{y:.1f}</b>/100 &nbsp; Tier: %{customdata[1]}<br>"
                "Gap since last survey: %{customdata[2]} yrs<br>"
                "Surveys completed: %{customdata[0]}<br>"
                "<extra></extra>"
            ),
        ))

    # Divider lines at fixed thresholds
    fig.add_vline(x=GAP_THRESH, line_dash="dash", line_color="#888", line_width=1.5)
    fig.add_hline(y=SPI_THRESH, line_dash="dash", line_color="#888", line_width=1.5)

    # Quadrant background shading
    fig.update_layout(shapes=[
        dict(type="rect", xref="x", yref="y",
             x0=0,          x1=GAP_THRESH, y0=SPI_THRESH, y1=105,
             fillcolor="rgba(0,166,81,0.06)",  line_width=0),
        dict(type="rect", xref="x", yref="y",
             x0=GAP_THRESH, x1=x_max,      y0=SPI_THRESH, y1=105,
             fillcolor="rgba(247,148,29,0.07)", line_width=0),
        dict(type="rect", xref="x", yref="y",
             x0=0,          x1=GAP_THRESH, y0=0,          y1=SPI_THRESH,
             fillcolor="rgba(74,144,226,0.06)", line_width=0),
        dict(type="rect", xref="x", yref="y",
             x0=GAP_THRESH, x1=x_max,      y0=0,          y1=SPI_THRESH,
             fillcolor="rgba(192,57,43,0.07)",  line_width=0),
    ])

    # Quadrant labels (placed at data coords for stability)
    labels = [
        (GAP_THRESH / 2,       92, "SUSTAIN",  C["success"]),
        (GAP_THRESH + (x_max - GAP_THRESH) / 2, 92, "REINVEST", C["warning"]),
        (GAP_THRESH / 2,        8, "DEVELOP",  C["accent"]),
        (GAP_THRESH + (x_max - GAP_THRESH) / 2,  8, "URGENT",   C["danger"]),
    ]
    for lx, ly, lbl, lc in labels:
        fig.add_annotation(
            x=lx, y=ly, xref="x", yref="y",
            text=f"<b>{lbl}</b>", showarrow=False,
            font=dict(size=13, color=lc, family=FONT),
            bgcolor="rgba(255,255,255,0.8)", borderpad=5,
            bordercolor=lc, borderwidth=1,
        )

    _layout(fig, "Strategic Quadrant - SPI Score vs Surveillance Gap (bubble size = surveys completed)", 700)
    fig.update_layout(
        xaxis=dict(title="Years Since Last Completed Survey",
                   range=[-0.5, x_max], zeroline=False),
        yaxis=dict(title="Surveillance Performance Index (SPI)",
                   range=[-2, 108], zeroline=False),
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
        margin=dict(l=10, r=20, t=50, b=60),
    )
    return fig


def fig_survey_type_comparison(A):
    """Stacked horizontal bar: status distribution across all 5 survey instruments."""
    kpis = A["exec_kpis"]
    survey_types = [st for st in SURVEY_META.keys() if st in kpis]

    statuses = [
        ("n_on_cycle",           "On Cycle",           "#00a651"),
        ("n_attempt_to_update",  "Attempt to Update",  "#4a90e2"),
        ("n_off_cycle",          "Off Cycle",          "#f7941d"),
        ("n_never",              "Never Conducted",    "#adb5bd"),
    ]

    fig = go.Figure()
    for key, label, color in statuses:
        values = [kpis[st][key] for st in survey_types]
        fig.add_trace(go.Bar(
            name=label,
            y=survey_types,
            x=values,
            orientation="h",
            marker_color=color,
            text=[str(v) if v > 0 else "" for v in values],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=11, color="white", family=FONT),
            hovertemplate=f"<b>%{{y}}</b> - {label}: <b>%{{x}}</b> countries<extra></extra>",
        ))

    _layout(fig, "Survey Instrument Status - All 5 Types (N = 48 countries per instrument)", 320)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Number of Countries", range=[0, 52]),
        yaxis=dict(tickfont=dict(size=12)),
        legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center", font=dict(size=11)),
        margin=dict(l=10, r=30, t=50, b=80),
    )
    return fig


def fig_timeline(A):
    tl  = A["timeline"]
    cum = A["cumulative"]
    order = ["Completed", "In Progress", "Not Usable"]
    fig = go.Figure()
    for status in order:
        sub = tl[tl["status"] == status].sort_values("survey_year")
        fig.add_trace(go.Bar(
            x=sub["survey_year"], y=sub["count"], name=status,
            marker_color=STATUS_COLORS[status],
            hovertemplate=f"<b>{status}</b><br>Year: %{{x}}<br>Surveys: %{{y}}<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=cum["survey_year"], y=cum["cumulative"],
        name="Cumulative (Completed)", mode="lines+markers", yaxis="y2",
        line=dict(color=C["primary"], width=2.5, dash="dot"),
        marker=dict(size=5, color=C["primary"]),
        hovertemplate="<b>Cumulative completed</b><br>Year: %{x}<br>Total: %{y}<extra></extra>",
    ))
    _layout(fig, f"Annual Survey Activity ({A['year_min']}–{CURRENT_YEAR})", 520)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Survey Year", dtick=2),
        yaxis=dict(title="Surveys per Year"),
        yaxis2=dict(
            title=dict(text="Cumulative Completed", font=dict(color=C["primary"])),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color=C["primary"], size=11),
        ),
        legend=dict(orientation="h", y=-0.18),
        margin=dict(l=10, r=80, t=50, b=60),   # right margin for y2 axis labels
    )
    # Shade current cycle (no inline annotation - add separately for clean placement)
    fig.add_vrect(x0=CURRENT_CYCLE_START - 0.5, x1=CURRENT_YEAR + 0.5,
                  fillcolor="rgba(0,166,81,0.07)", line_width=0)
    fig.add_annotation(
        x=CURRENT_CYCLE_START, y=1.0, xref="x", yref="paper",
        text="Current cycle", showarrow=False,
        font=dict(size=10, color=C["success"], family=FONT),
        xanchor="left", yanchor="bottom",
    )
    return fig


def fig_gap_bar(A):
    spi = A["spi"].copy()
    spi["gap_plot"] = spi["gap_years"].fillna(CURRENT_YEAR - A["year_min"])
    spi_sorted = spi.sort_values("gap_plot", ascending=True)
    colors = [
        C["danger"]  if g >= 15 else
        C["warning"] if g >= 10 else
        "#f1c40f"    if g >= 5  else
        C["success"]
        for g in spi_sorted["gap_plot"]
    ]
    fig = go.Figure(go.Bar(
        y=spi_sorted["country"], x=spi_sorted["gap_plot"],
        orientation="h", marker_color=colors,
        text=[f"{int(g)} yrs" for g in spi_sorted["gap_plot"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Gap: %{x} years since last survey<extra></extra>",
    ))
    for thresh, col, lbl in [(5,"#f1c40f","5yr"),(10,C["warning"],"10yr"),(15,C["danger"],"15yr")]:
        fig.add_vline(x=thresh, line_dash="dot", line_color=col, line_width=1.5,
                      annotation_text=lbl, annotation_position="top right",
                      annotation_font_size=10)
    _layout(fig, "Years Since Most Recent Survey (Surveillance Gap)", 900)
    fig.update_layout(
        xaxis=dict(title="Years (relative to 2026)"),
        margin=dict(l=10, r=70, t=50, b=10),
    )
    return fig
