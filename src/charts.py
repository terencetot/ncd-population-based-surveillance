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
                        PREV_CYCLE_START, STATUS_COLORS, CYCLE_STATUS_COLORS,
                        CYCLE_STATUS_ON, CYCLE_STATUS_PATTERN, CYCLE_STATUS_PATTERN_FG,
                        BRAND, TIER_INK, RECENCY_STEPS, RECENCY_NONE, recency_color)


def _layout(fig, title="", height=420):
    fig.update_layout(
        title=dict(text=title, font=dict(family=FONT, size=14, color=C["dark"]),
                   x=0, xanchor="left", pad=dict(l=2, t=4)),
        paper_bgcolor=C["white"], plot_bgcolor=C["white"],
        font=dict(family=FONT, size=13, color=C["text"]),
        autosize=True, height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(bgcolor="rgba(255,255,255,0.92)", bordercolor=C["border"],
                    borderwidth=1, font=dict(size=12)),
        hoverlabel=dict(bgcolor=C["dark"], font_size=13,
                        font_family=FONT, font_color="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor=C["border"], tickfont=dict(size=12))
    fig.update_yaxes(gridcolor=BRAND["border"], linecolor=C["border"], tickfont=dict(size=12))
    return fig


def _html(fig, first=False):
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if first else False,
        config={"displayModeBar":True,"responsive":True,
                "modeBarButtonsToRemove":["lasso2d","select2d"],
                "displaylogo":False},
    )


def fig_spi_bar(A):
    spi = A["spi"].sort_values("spi", ascending=True)
    colors = [TIER_COLORS[t] for t in spi["tier"]]
    fig = go.Figure(go.Bar(
        y=spi["country"], x=spi["spi"],
        orientation="h", marker_color=colors,
        text=[f"{v:.1f}" for v in spi["spi"]], textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "SPI: %{x:.1f}/100<br>"
            "<extra></extra>"
        ),
    ))
    # Tier reference lines (must match analytics.py tier cutoffs: spi>=75/50/30)
    for thresh, label, col in [(30,"Developing",TIER_INK[3]),(50,"Advancing",TIER_INK[2]),(75,"Strong",TIER_INK[1])]:
        fig.add_vline(x=thresh, line_dash="dot", line_color=col, line_width=1.5,
                      annotation_text=label, annotation_position="top right",
                      annotation_font_size=11)
    # Direct label for the band below the first threshold (identity never colour-only)
    fig.add_annotation(x=0, y=1, xref="x", yref="paper", text="Critical", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=11, color=TIER_INK[4], family=FONT))
    _layout(fig, "Surveillance Performance Index (SPI) - All Countries", max(420, len(spi) * 16 + 140))
    fig.update_layout(
        xaxis=dict(title="SPI Score (0–100)", range=[0, 110]),
        yaxis=dict(title="", tickfont=dict(size=11)),
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
        colorscale=[[0, TIER_COLORS[4]], [0.299, TIER_COLORS[4]], [0.30, TIER_COLORS[3]],
                    [0.499, TIER_COLORS[3]], [0.50, TIER_COLORS[2]], [0.749, TIER_COLORS[2]],
                    [0.75, TIER_COLORS[1]], [1.0, TIER_COLORS[1]]],
        zmin=0, zmax=100,
        marker_line_color=C["white"], marker_line_width=0.6,
        colorbar=dict(
            title=dict(text="SPI Score", font=dict(size=13)),
            thickness=14, len=0.55, x=0.93,
            tickvals=[0,30,50,75,100],
            ticktext=["0","Developing","Advancing","Strong","100"],
            tickfont=dict(size=11),
        ),
        hovertemplate="<b>%{text}</b><br>SPI: %{z:.1f}/100<extra></extra>",
    ))
    fig.update_geos(
        scope="africa", showframe=False,
        showcoastlines=True, coastlinecolor=C["border"],
        showland=True, landcolor=BRAND["canvas"],
        showocean=True, oceancolor=BRAND["surface"],
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
        textfont=dict(size=13, family=FONT),
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
        ("d_coverage",   "BS - Breadth Score",                   BRAND["navy"]),
        ("d_recency",    "CS - Currency Score",                   BRAND["who_blue"]),
        ("d_regularity", "CA-ARI - Coverage-Adjusted Regularity", "#9fc3e6"),
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
        yaxis=dict(tickfont=dict(size=11)),
        legend=dict(orientation="h", y=1.02, x=0, xanchor="left", font=dict(size=12)),
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
        name="Completed", orientation="h", marker_color=BRAND["navy"],
        hovertemplate="<b>%{y}</b><br>Completed in 2021–2026: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=active["country"], x=active["recent_inprog"],
        name="In Progress", orientation="h", marker_color=CYCLE_STATUS_COLORS["Attempt to update"],
        marker_pattern=dict(shape="/", fgcolor=CYCLE_STATUS_PATTERN_FG["Attempt to update"], fgopacity=0.45, size=7, fillmode="overlay"),
        hovertemplate="<b>%{y}</b><br>In Progress 2021–2026: %{x}<extra></extra>",
    ))
    _layout(fig, f"Current 5-Year Cycle Activity ({CURRENT_CYCLE_START}–{CURRENT_YEAR})", 580)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Number of Surveys", dtick=1),
        yaxis=dict(title="", tickfont=dict(size=11)),
        legend=dict(orientation="h", y=-0.12),
        margin=dict(l=10, r=20, t=50, b=10),
    )
    return fig


def fig_last_year_heatmap(A):
    """
    Surveillance Recency Matrix - Country × Instrument.
    Colour = gap in years since last completed survey (config.RECENCY_STEPS; grey=never).
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
                       else f"⚠ {gap} yr gap" if gap <= 12
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

    # ── Recency colorscale (config.RECENCY_STEPS; sentinel = no-evidence grey) ─
    # Plotly normalises [zmin, zmax] → [0, 1]
    # SENTINEL=-1, Z_MAX=28  →  range=29
    R = Z_MAX - SENTINEL          # = 29
    def _n(v): return (v - SENTINEL) / R   # normalize to [0,1]

    # Stepped, not continuous: each cell reads as one recency band, identical
    # to the gap bars and threshold lines (config.RECENCY_STEPS), and stays
    # legible in greyscale print. Integers only, so band edges sit at +0.5.
    colorscale = [[0, RECENCY_NONE], [_n(-0.5), RECENCY_NONE]]
    lo = -0.5
    for hi, fill, _ink, _lbl in RECENCY_STEPS:
        top = min(hi + 0.5, Z_MAX)
        colorscale += [[_n(lo) + 1e-6, fill], [_n(top), fill]]
        lo = top
        if top >= Z_MAX:
            break

    n_rows = len(countries)
    height = max(580, n_rows * 20 + 180)

    fig = go.Figure(go.Heatmap(
        z=z_arr, x=instruments, y=countries,
        text=text_arr,
        texttemplate="%{text}",
        textfont=dict(size=11, family=FONT),   # no colour: Plotly picks dark/light per cell
        customdata=hover_arr,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=colorscale,
        zmin=SENTINEL, zmax=Z_MAX,
        showscale=True,
        colorbar=dict(
            title=dict(text="Gap (years)", font=dict(size=12, family=FONT), side="right"),
            thickness=16, len=0.55, x=1.01,
            tickvals=[0, 5, 10, 15, 20, Z_MAX],
            ticktext=["0 - Current", "5", "10", "15", "20", "28+"],
            tickfont=dict(size=11, family=FONT),
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
        plot_bgcolor=BRAND["surface"],
        font=dict(family=FONT, size=13),
        autosize=True, height=height,
        margin=dict(l=10, r=100, t=80, b=70),
        xaxis=dict(
            side="top",
            tickangle=0,
            tickfont=dict(size=14, color=C["dark"], family=FONT),
            showgrid=False,
            linecolor=C["border"],
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=11, family=FONT),
            showgrid=False,
            linecolor=C["border"],
            title="",
        ),
        hoverlabel=dict(bgcolor=C["dark"], font_size=13,
                        font_family=FONT, font_color="white"),
    )

    # ── Bottom caption strip (legend) ─────────────────────────────────────────
    leg_items = [
        (RECENCY_NONE,             BRAND["ink"], "No record"),
        (recency_color(0),         "#ffffff",    "On Cycle (0–5 yr)"),
        (recency_color(6),         BRAND["ink"], "Off Cycle (6–12 yr)"),
        (recency_color(13),        "#ffffff",    "Critical (>12 yr)"),
    ]
    annotations = []
    n = len(leg_items)
    for i, (bg, fg, lbl) in enumerate(leg_items):
        annotations.append(dict(
            x=i / (n - 1), y=-0.015, xref="paper", yref="paper", yanchor="top",
            text=f"<b>{lbl}</b>", font=dict(size=12, color=fg, family=FONT),
            bgcolor=bg, borderpad=4, bordercolor="rgba(13,31,78,.12)", borderwidth=1,
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
        (0,          GAP_THRESH, SPI_THRESH, 105, "rgba(31,95,168,0.06)"),    # SUSTAIN
        (GAP_THRESH, x_max,      SPI_THRESH, 105, "rgba(224,147,46,0.08)"),  # REINVEST
        (0,          GAP_THRESH, 0,          SPI_THRESH, "rgba(134,182,224,0.10)"),  # DEVELOP
        (GAP_THRESH, x_max,      0,          SPI_THRESH, "rgba(196,67,43,0.07)"),   # URGENT
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
    fig.add_vline(x=GAP_THRESH, line_dash="dash", line_color=BRAND["muted"], line_width=1.5)
    fig.add_hline(y=SPI_THRESH, line_dash="dash", line_color=BRAND["muted"], line_width=1.5)

    # Quadrant background shading
    fig.update_layout(shapes=[
        dict(type="rect", xref="x", yref="y",
             x0=0,          x1=GAP_THRESH, y0=SPI_THRESH, y1=105,
             fillcolor="rgba(31,95,168,0.06)",  line_width=0),
        dict(type="rect", xref="x", yref="y",
             x0=GAP_THRESH, x1=x_max,      y0=SPI_THRESH, y1=105,
             fillcolor="rgba(224,147,46,0.08)", line_width=0),
        dict(type="rect", xref="x", yref="y",
             x0=0,          x1=GAP_THRESH, y0=0,          y1=SPI_THRESH,
             fillcolor="rgba(134,182,224,0.10)", line_width=0),
        dict(type="rect", xref="x", yref="y",
             x0=GAP_THRESH, x1=x_max,      y0=0,          y1=SPI_THRESH,
             fillcolor="rgba(196,67,43,0.07)",  line_width=0),
    ])

    # Quadrant labels (placed at data coords for stability)
    labels = [
        (GAP_THRESH / 2,       92, "SUSTAIN",  TIER_INK[1]),
        (GAP_THRESH + (x_max - GAP_THRESH) / 2, 92, "REINVEST", TIER_INK[3]),
        (GAP_THRESH / 2,        8, "DEVELOP",  TIER_INK[2]),
        (GAP_THRESH + (x_max - GAP_THRESH) / 2,  8, "URGENT",   TIER_INK[4]),
    ]
    for lx, ly, lbl, lc in labels:
        fig.add_annotation(
            x=lx, y=ly, xref="x", yref="y",
            text=f"<b>{lbl}</b>", showarrow=False,
            font=dict(size=14, color=lc, family=FONT),
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
        ("n_on_cycle",           "On Cycle",           CYCLE_STATUS_COLORS["On Cycle"]),
        ("n_attempt_to_update",  "Attempt to Update",  CYCLE_STATUS_COLORS["Attempt to update"]),
        ("n_off_cycle",          "Off Cycle",          CYCLE_STATUS_COLORS["Off Cycle"]),
        ("n_first_attempt",      "First Attempt",      CYCLE_STATUS_COLORS["First Attempt"]),
        ("n_never",              "Never Conducted",    CYCLE_STATUS_COLORS["Never Conducted"]),
    ]

    fig = go.Figure()
    for key, label, color in statuses:
        key_label = {"Attempt to Update": "Attempt to update"}.get(label, label)
        values = [kpis[st][key] for st in survey_types]
        fig.add_trace(go.Bar(
            name=label,
            y=survey_types,
            x=values,
            orientation="h",
            marker=dict(
                color=color, line=dict(color="#ffffff", width=1),
                pattern=(dict(shape=CYCLE_STATUS_PATTERN[key_label], fgcolor=CYCLE_STATUS_PATTERN_FG[key_label],
                              fgopacity=0.3 if CYCLE_STATUS_PATTERN[key_label] == "." else 0.4,
                              size=9 if CYCLE_STATUS_PATTERN[key_label] == "." else 7,
                              solidity=0.15 if CYCLE_STATUS_PATTERN[key_label] == "." else 0.25, fillmode="overlay")
                         if key_label in CYCLE_STATUS_PATTERN else None),
            ),
            text=[str(v) if v > 0 else "" for v in values],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=12, color=CYCLE_STATUS_ON[key_label], family=FONT),
            hovertemplate=f"<b>%{{y}}</b> - {label}: <b>%{{x}}</b> countries<extra></extra>",
        ))

    _layout(fig, "Survey Instrument Status - All 5 Types (N = 48 countries per instrument)", 320)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Number of Countries", range=[0, 52]),
        yaxis=dict(tickfont=dict(size=13)),
        legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center", font=dict(size=12),
                    traceorder="reversed"),
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
                  fillcolor="rgba(31,95,168,0.06)", line_width=0)
    fig.add_annotation(
        x=CURRENT_CYCLE_START, y=1.0, xref="x", yref="paper",
        text="Current cycle", showarrow=False,
        font=dict(size=11, color=TIER_INK[1], family=FONT),
        xanchor="left", yanchor="bottom",
    )
    return fig


def fig_gap_bar(A):
    spi = A["spi"].copy()
    spi["gap_plot"] = spi["gap_years"].fillna(CURRENT_YEAR - A["year_min"])
    spi_sorted = spi.sort_values("gap_plot", ascending=True)
    colors = [recency_color(g) for g in spi_sorted["gap_plot"]]
    fig = go.Figure(go.Bar(
        y=spi_sorted["country"], x=spi_sorted["gap_plot"],
        orientation="h", marker_color=colors,
        text=[f"{int(g)} yrs" for g in spi_sorted["gap_plot"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Gap: %{x} years since last survey<extra></extra>",
    ))
    for thresh, col, lbl in [(5.5,recency_color(6, ink=True),"5yr"),(12.5,recency_color(13, ink=True),"12yr")]:
        fig.add_vline(x=thresh, line_dash="dot", line_color=col, line_width=1.5,
                      annotation_text=lbl, annotation_position="top right",
                      annotation_font_size=11)
    _layout(fig, "Years Since Most Recent Survey (Surveillance Gap)", 900)
    fig.update_layout(
        xaxis=dict(title="Years (relative to 2026)"),
        margin=dict(l=10, r=70, t=50, b=10),
    )
    return fig
