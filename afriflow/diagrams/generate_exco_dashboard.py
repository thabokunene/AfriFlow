# diagrams/generate_exco_dashboard.py

"""
AfriFlow ExCo Strategic Intelligence Dashboard

We generate a high fidelity mockup of the Group
Executive Committee dashboard that Suri Sobrun
(Head of CIB Data and Analytics) would use to
present cross-domain revenue intelligence to the
Group ExCo.

This is not an RM operational screen. This is the
strategic command view that answers the questions
ExCo asks every quarter:

  "Where is the revenue?"
  "Where are we losing to competitors?"
  "Where is the risk concentrating?"
  "What is the MTN partnership actually delivering?"
  "Which corridors are undermonetised?"

Usage:
    python diagrams/generate_exco_dashboard.py

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.patches import Circle
from matplotlib.patches import FancyArrowPatch
import numpy as np
import os


# -------------------------------------------------------
# Colour palette: Executive dark dashboard
# -------------------------------------------------------
C = {
    "bg": "#0A1220",
    "card_bg": "#111D2E",
    "card_border": "#1E3048",
    "card_header": "#152238",
    "text_primary": "#E8EDF2",
    "text_secondary": "#7D8FA0",
    "text_muted": "#4A5A6A",
    "accent_blue": "#1976D2",
    "accent_green": "#43A047",
    "accent_red": "#E53935",
    "accent_amber": "#FB8C00",
    "accent_purple": "#8E24AA",
    "accent_teal": "#00897B",
    "accent_cyan": "#00ACC1",
    "accent_gold": "#FFB300",
    "cib": "#1565C0",
    "forex": "#0D47A1",
    "insurance": "#2E7D32",
    "cell": "#F9A825",
    "pbb": "#C62828",
    "topbar_bg": "#0D1824",
    "divider": "#1E3048",
    "progress_bg": "#152238",
    "chart_grid": "#152238",
    "positive": "#43A047",
    "negative": "#E53935",
    "neutral": "#7D8FA0",
    "sb_blue": "#003DA5",
    "heatmap_low": "#1B3A26",
    "heatmap_med": "#4A6A2F",
    "heatmap_high": "#8BC34A",
    "heatmap_critical": "#FF6F00",
    "map_land": "#152238",
    "map_border": "#1E3048",
    "map_active": "#1976D2",
    "corridor_line": "#1976D240",
    "white": "#FFFFFF",
}


def draw_box(
    ax, x, y, w, h, facecolor,
    text_lines=None, text_color="#FFFFFF",
    fontsize=7, bold_first=False,
    corner_radius=0.06, alpha=1.0,
    border_color=None, border_width=0.5,
    zorder=2, text_ha="center",
    shadow=False, linestyle="-",
):
    """Draw a rounded rectangle."""

    if shadow:
        s = FancyBboxPatch(
            (x + 0.03, y - 0.03), w, h,
            boxstyle=f"round,pad=0.02,rounding_size={corner_radius}",
            facecolor="#00000025",
            edgecolor="none",
            zorder=zorder - 1,
        )
        ax.add_patch(s)

    edge = border_color if border_color else facecolor
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={corner_radius}",
        facecolor=facecolor,
        edgecolor=edge,
        linewidth=border_width,
        linestyle=linestyle,
        alpha=alpha,
        zorder=zorder,
    )
    ax.add_patch(box)

    if text_lines is None:
        return

    if isinstance(text_lines, str):
        text_lines = [text_lines]

    n = len(text_lines)
    spacing = min(0.22, (h * 0.85) / max(n, 1))
    start_y = y + h / 2 + (n - 1) * spacing / 2

    for i, line in enumerate(text_lines):
        weight = "bold" if (i == 0 and bold_first) else "normal"
        fs = fontsize + 0.5 if (i == 0 and bold_first) else fontsize
        tx = x + w / 2 if text_ha == "center" else x + 0.1

        ax.text(
            tx, start_y - i * spacing,
            line,
            ha=text_ha, va="center",
            fontsize=fs, fontweight=weight,
            color=text_color,
            zorder=zorder + 1,
            fontfamily="sans-serif",
        )


def draw_sparkline(ax, x, y, w, h, data, color, fill=True):
    """Draw a small sparkline chart."""

    n = len(data)
    xs = np.linspace(x, x + w, n)
    d_min = min(data)
    d_max = max(data)
    d_range = d_max - d_min if d_max != d_min else 1
    ys = [y + (d - d_min) / d_range * h for d in data]

    ax.plot(xs, ys, color=color, linewidth=1.0, zorder=5, solid_capstyle="round")

    if fill:
        fill_xs = list(xs) + [xs[-1], xs[0]]
        fill_ys = list(ys) + [y, y]
        ax.fill(fill_xs, fill_ys, color=color, alpha=0.08, zorder=4)

    ax.plot(xs[-1], ys[-1], "o", color=color, markersize=2.5, zorder=6)


def draw_progress_bar(ax, x, y, w, h, pct, color, bg=None):
    """Draw a horizontal progress bar."""

    bg_c = bg if bg else C["progress_bg"]
    draw_box(ax, x, y, w, h, bg_c, corner_radius=0.02)
    fill_w = w * min(pct / 100, 1.0)
    if fill_w > 0.03:
        draw_box(ax, x, y, fill_w, h, color, corner_radius=0.02)


def draw_donut(ax, cx, cy, r_outer, r_inner, segments, start_angle=90):
    """Draw a donut chart."""

    total = sum(s[1] for s in segments)
    current_angle = start_angle

    for label, value, color in segments:
        angle = (value / total) * 360 if total > 0 else 0
        wedge = mpatches.Wedge(
            (cx, cy), r_outer,
            current_angle, current_angle + angle,
            facecolor=color,
            edgecolor=C["card_bg"],
            linewidth=1.0,
            zorder=4,
        )
        ax.add_patch(wedge)
        current_angle += angle

    # Inner circle (creates donut hole)
    inner = Circle(
        (cx, cy), r_inner,
        facecolor=C["card_bg"],
        edgecolor="none",
        zorder=5,
    )
    ax.add_patch(inner)


def draw_heatmap_cell(ax, x, y, w, h, value, max_val, label=None, val_label=None):
    """Draw a single heatmap cell."""

    intensity = min(value / max_val, 1.0) if max_val > 0 else 0

    if intensity > 0.75:
        color = C["heatmap_critical"]
    elif intensity > 0.5:
        color = C["heatmap_high"]
    elif intensity > 0.25:
        color = C["heatmap_med"]
    elif intensity > 0:
        color = C["heatmap_low"]
    else:
        color = C["progress_bg"]

    draw_box(
        ax, x, y, w, h,
        color,
        corner_radius=0.03,
        border_color=C["card_bg"],
        border_width=0.5,
    )

    if val_label:
        ax.text(
            x + w / 2, y + h / 2,
            val_label,
            ha="center", va="center",
            fontsize=5, fontweight="bold",
            color="#FFFFFF" if intensity > 0.3 else C["text_muted"],
            zorder=5,
        )


def generate_exco_dashboard():
    """Generate the ExCo strategic dashboard."""

    fig, ax = plt.subplots(1, 1, figsize=(36, 22))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 36)
    ax.set_ylim(0, 22)
    ax.set_aspect("equal")
    ax.axis("off")

    # ===================================================
    # TOP BAR
    # ===================================================

    draw_box(
        ax, 0, 21.0, 36, 1.0,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    ax.text(
        0.5, 21.5,
        "AfriFlow",
        ha="left", va="center",
        fontsize=14, fontweight="bold",
        color=C["accent_blue"],
        zorder=3,
    )

    ax.text(
        2.8, 21.5,
        "Group Executive Intelligence",
        ha="left", va="center",
        fontsize=8,
        color=C["text_secondary"],
        zorder=3,
    )

    # Period selector
    periods = ["7D", "30D", "90D", "YTD", "12M"]
    for pi, period in enumerate(periods):
        px = 20.0 + pi * 1.0
        active = period == "90D"

        draw_box(
            ax, px, 21.25,
            0.8, 0.35,
            C["accent_blue"] if active else C["card_bg"],
            text_lines=[period],
            text_color="#FFFFFF" if active else C["text_muted"],
            fontsize=5.5,
            corner_radius=0.04,
            border_color=C["accent_blue"] if active else C["card_border"],
            border_width=0.5,
        )

    # Last updated
    ax.text(
        28.0, 21.5,
        "Last updated: 14 Jun 2025 09:14 UTC",
        ha="left", va="center",
        fontsize=5,
        color=C["text_muted"],
        zorder=3,
    )

    # Data freshness indicators
    domains_fresh = [
        ("CIB", True), ("FX", True), ("INS", True),
        ("CELL", True), ("PBB", True),
    ]

    for di, (dname, fresh) in enumerate(domains_fresh):
        dx = 33.0 + di * 0.6
        dc = C["positive"] if fresh else C["negative"]

        circle = Circle(
            (dx, 21.5), 0.08,
            facecolor=dc,
            edgecolor="none",
            zorder=4,
        )
        ax.add_patch(circle)

        ax.text(
            dx, 21.25,
            dname,
            ha="center", va="center",
            fontsize=3.5,
            color=C["text_muted"],
            zorder=3,
        )

    # ===================================================
    # ROW 1: HEADLINE METRICS (6 cards)
    # ===================================================

    row1_y = 19.5
    metric_w = 5.5
    metric_h = 1.3
    metric_gap = 0.2
    metrics_start_x = 0.3

    headlines = [
        {
            "label": "TOTAL GROUP REVENUE",
            "value": "R18.4B",
            "sub": "Across 2,847 integrated clients",
            "trend": "+14%", "trend_dir": "up",
            "spark": [14.2, 14.8, 15.1, 15.9, 16.3, 16.8, 17.5, 18.4],
            "color": C["accent_blue"],
        },
        {
            "label": "CROSS-SELL REVENUE",
            "value": "R2.1B",
            "sub": "Revenue from AfriFlow signals",
            "trend": "+340%", "trend_dir": "up",
            "spark": [0.1, 0.2, 0.4, 0.6, 0.9, 1.2, 1.6, 2.1],
            "color": C["accent_green"],
        },
        {
            "label": "COMPETITIVE LEAKAGE",
            "value": "R4.7B",
            "sub": "Identified across Top 500 clients",
            "trend": "-8%", "trend_dir": "down",
            "spark": [5.8, 5.6, 5.4, 5.3, 5.1, 5.0, 4.8, 4.7],
            "color": C["accent_red"],
        },
        {
            "label": "ACTIVE SIGNALS",
            "value": "1,247",
            "sub": "Across 12 signal types",
            "trend": "+89", "trend_dir": "up",
            "spark": [420, 510, 620, 780, 890, 980, 1100, 1247],
            "color": C["accent_amber"],
        },
        {
            "label": "ENTITY COVERAGE",
            "value": "87%",
            "sub": "Top 500 clients across 3+ domains",
            "trend": "+12%", "trend_dir": "up",
            "spark": [52, 58, 63, 68, 72, 78, 83, 87],
            "color": C["accent_teal"],
        },
        {
            "label": "SHADOW OPPORTUNITY",
            "value": "R890M",
            "sub": "From data gap analysis",
            "trend": "NEW", "trend_dir": "up",
            "spark": None,
            "color": C["accent_purple"],
        },
    ]

    for mi, m in enumerate(headlines):
        mx = metrics_start_x + mi * (metric_w + metric_gap)

        draw_box(
            ax, mx, row1_y,
            metric_w, metric_h,
            C["card_bg"],
            corner_radius=0.06,
            border_color=C["card_border"],
            border_width=0.5,
            shadow=True,
        )

        # Label
        ax.text(
            mx + 0.15, row1_y + metric_h - 0.2,
            m["label"],
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_secondary"],
            zorder=3,
        )

        # Value
        ax.text(
            mx + 0.15, row1_y + metric_h - 0.55,
            m["value"],
            ha="left", va="center",
            fontsize=11, fontweight="bold",
            color=m["color"],
            zorder=3,
        )

        # Sublabel
        ax.text(
            mx + 0.15, row1_y + metric_h - 0.85,
            m["sub"],
            ha="left", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

        # Trend
        tc = C["positive"] if m["trend_dir"] == "up" else C["negative"]
        if m["label"] == "COMPETITIVE LEAKAGE":
            tc = C["positive"]  # Leakage going down is good

        ax.text(
            mx + metric_w - 0.15, row1_y + metric_h - 0.55,
            m["trend"],
            ha="right", va="center",
            fontsize=6, fontweight="bold",
            color=tc,
            zorder=3,
        )

        # Sparkline
        if m["spark"]:
            draw_sparkline(
                ax, mx + 0.1, row1_y + 0.05,
                metric_w - 0.2, metric_h * 0.2,
                m["spark"], m["color"],
            )

    # ===================================================
    # ROW 2: Three main panels
    # ===================================================

    row2_top = 19.1
    panel_gap = 0.25

    # Panel widths
    p1_w = 11.5
    p2_w = 13.0
    p3_w = 10.5

    p1_x = 0.3
    p2_x = p1_x + p1_w + panel_gap
    p3_x = p2_x + p2_w + panel_gap

    panel_h = 8.5

    # ===================================================
    # PANEL 1: Revenue by Domain (donut + breakdown)
    # ===================================================

    draw_box(
        ax, p1_x, row2_top - panel_h,
        p1_w, panel_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    draw_box(
        ax, p1_x, row2_top - 0.5,
        p1_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        p1_x + 0.15, row2_top - 0.25,
        "GROUP REVENUE BY DOMAIN",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    ax.text(
        p1_x + p1_w - 0.15, row2_top - 0.25,
        "Annual | R18.4B",
        ha="right", va="center",
        fontsize=5.5,
        color=C["accent_blue"],
        zorder=3,
    )

    # Donut chart
    donut_cx = p1_x + 3.0
    donut_cy = row2_top - 3.5

    segments = [
        ("CIB", 52, C["cib"]),
        ("Forex", 23, C["forex"]),
        ("Insurance", 12, C["insurance"]),
        ("Cell/MoMo", 8, C["cell"]),
        ("PBB", 5, C["pbb"]),
    ]

    draw_donut(ax, donut_cx, donut_cy, 2.0, 1.2, segments)

    # Center text
    ax.text(
        donut_cx, donut_cy + 0.15,
        "R18.4B",
        ha="center", va="center",
        fontsize=10, fontweight="bold",
        color=C["text_primary"],
        zorder=6,
    )

    ax.text(
        donut_cx, donut_cy - 0.25,
        "Total",
        ha="center", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=6,
    )

    # Legend with details
    legend_x = p1_x + 6.0
    legend_start_y = row2_top - 1.2

    domain_details = [
        ("CIB", "R9.6B", "52%", C["cib"], "+8%", "2,847 clients"),
        ("Forex", "R4.2B", "23%", C["forex"], "+18%", "1,420 clients"),
        ("Insurance", "R2.2B", "12%", C["insurance"], "+5%", "890 policies"),
        ("Cell / MoMo", "R1.5B", "8%", C["cell"], "+42%", "MTN partnership"),
        ("PBB", "R0.9B", "5%", C["pbb"], "+3%", "12,400 accounts"),
    ]

    for di, (dname, dval, dpct, dcolor, dtrend, dsub) in enumerate(domain_details):
        dy = legend_start_y - di * 0.95

        # Color dot
        circle = Circle(
            (legend_x + 0.15, dy + 0.15), 0.12,
            facecolor=dcolor,
            edgecolor=C["card_bg"],
            linewidth=0.5,
            zorder=4,
        )
        ax.add_patch(circle)

        # Domain name
        ax.text(
            legend_x + 0.4, dy + 0.25,
            dname,
            ha="left", va="center",
            fontsize=5.5, fontweight="bold",
            color=C["text_primary"],
            zorder=3,
        )

        # Value and percentage
        ax.text(
            legend_x + 0.4, dy,
            f"{dval} ({dpct})",
            ha="left", va="center",
            fontsize=5,
            color=C["text_secondary"],
            zorder=3,
        )

        # Trend
        tc = C["positive"] if dtrend.startswith("+") else C["negative"]
        ax.text(
            legend_x + 3.5, dy + 0.25,
            dtrend,
            ha="left", va="center",
            fontsize=5.5, fontweight="bold",
            color=tc,
            zorder=3,
        )

        # Sub detail
        ax.text(
            legend_x + 3.5, dy,
            dsub,
            ha="left", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

    # MTN Partnership callout
    mtn_y = row2_top - panel_h + 0.5

    draw_box(
        ax, p1_x + 0.2, mtn_y,
        p1_w - 0.4, 1.0,
        "#1A2A1A",
        corner_radius=0.06,
        border_color=C["cell"],
        border_width=0.8,
    )

    ax.text(
        p1_x + 0.4, mtn_y + 0.7,
        "MTN PARTNERSHIP SIGNAL VALUE",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["cell"],
        zorder=3,
    )

    ax.text(
        p1_x + 0.4, mtn_y + 0.4,
        "47 expansion signals sourced from cell data",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_secondary"],
        zorder=3,
    )

    ax.text(
        p1_x + 0.4, mtn_y + 0.15,
        "R340M in new facilities attributed to cell intelligence",
        ha="left", va="center",
        fontsize=4.5,
        color=C["accent_green"],
        zorder=3,
    )

    # ===================================================
    # PANEL 2: Corridor Heatmap + Leakage Map
    # ===================================================

    draw_box(
        ax, p2_x, row2_top - panel_h,
        p2_w, panel_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    draw_box(
        ax, p2_x, row2_top - 0.5,
        p2_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        p2_x + 0.15, row2_top - 0.25,
        "CORRIDOR REVENUE AND LEAKAGE MATRIX",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Heatmap: Source countries (rows) x Product capture (columns)
    hm_x = p2_x + 0.3
    hm_y = row2_top - 1.0

    products = ["CIB", "FX", "INS", "CELL", "PBB", "Revenue", "Leakage"]
    countries_hm = [
        "Nigeria",
        "Kenya",
        "Ghana",
        "Tanzania",
        "Mozambique",
        "Zambia",
        "Angola",
        "DRC",
        "Uganda",
    ]

    cell_w = 1.5
    cell_h = 0.6
    label_w = 1.8

    # Column headers
    for pi, prod in enumerate(products):
        px = hm_x + label_w + pi * cell_w

        prod_colors = {
            "CIB": C["cib"],
            "FX": C["forex"],
            "INS": C["insurance"],
            "CELL": C["cell"],
            "PBB": C["pbb"],
            "Revenue": C["accent_green"],
            "Leakage": C["accent_red"],
        }

        ax.text(
            px + cell_w / 2, hm_y + 0.15,
            prod,
            ha="center", va="center",
            fontsize=5, fontweight="bold",
            color=prod_colors.get(prod, C["text_secondary"]),
            zorder=3,
        )

    # Revenue and leakage data per country
    # Format: [CIB%, FX%, INS%, CELL%, PBB%, Revenue, Leakage]
    heatmap_data = [
        [100, 13, 0, 85, 0, "R4.2B", "R1.8B"],
        [100, 65, 80, 90, 30, "R2.8B", "R420M"],
        [100, 60, 20, 0, 0, "R1.1B", "R680M"],
        [100, 40, 30, 70, 0, "R580M", "R340M"],
        [100, 35, 45, 60, 0, "R420M", "R280M"],
        [100, 55, 50, 75, 25, "R380M", "R190M"],
        [100, 20, 10, 40, 0, "R350M", "R520M"],
        [100, 10, 5, 30, 0, "R180M", "R290M"],
        [100, 45, 35, 80, 15, "R240M", "R120M"],
    ]

    for ci_r, (country, data) in enumerate(zip(countries_hm, heatmap_data)):
        cy_r = hm_y - (ci_r + 1) * cell_h

        # Country label
        row_bg = C["card_bg"] if ci_r % 2 == 0 else C["card_header"]

        draw_box(
            ax, hm_x, cy_r,
            label_w + len(products) * cell_w, cell_h,
            row_bg,
            corner_radius=0.0,
            border_color=C["card_bg"],
            border_width=0.3,
            zorder=1,
        )

        ax.text(
            hm_x + 0.1, cy_r + cell_h / 2,
            country,
            ha="left", va="center",
            fontsize=5,
            color=C["text_primary"],
            zorder=3,
        )

        # Product capture percentages (first 5 columns)
        for pi in range(5):
            px = hm_x + label_w + pi * cell_w
            val = data[pi]

            draw_heatmap_cell(
                ax, px + 0.05, cy_r + 0.05,
                cell_w - 0.1, cell_h - 0.1,
                val, 100,
                val_label=f"{val}%" if val > 0 else "--",
            )

        # Revenue column
        rx = hm_x + label_w + 5 * cell_w

        ax.text(
            rx + cell_w / 2, cy_r + cell_h / 2,
            data[5],
            ha="center", va="center",
            fontsize=5, fontweight="bold",
            color=C["accent_green"],
            zorder=3,
        )

        # Leakage column
        lx = hm_x + label_w + 6 * cell_w

        ax.text(
            lx + cell_w / 2, cy_r + cell_h / 2,
            data[6],
            ha="center", va="center",
            fontsize=5, fontweight="bold",
            color=C["accent_red"],
            zorder=3,
        )

    # Heatmap legend
    hm_legend_y = row2_top - panel_h + 0.4

    ax.text(
        hm_x, hm_legend_y + 0.4,
        "Product capture rate:  ",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_secondary"],
    )

    legend_colors = [
        ("0%", C["progress_bg"]),
        ("25%", C["heatmap_low"]),
        ("50%", C["heatmap_med"]),
        ("75%", C["heatmap_high"]),
        ("100%", C["heatmap_critical"]),
    ]

    for li, (llabel, lcolor) in enumerate(legend_colors):
        lx = hm_x + 3.0 + li * 1.5

        draw_box(
            ax, lx, hm_legend_y + 0.3,
            0.4, 0.2,
            lcolor,
            corner_radius=0.02,
        )

        ax.text(
            lx + 0.5, hm_legend_y + 0.4,
            llabel,
            ha="left", va="center",
            fontsize=4,
            color=C["text_muted"],
        )

    # Key insight callout
    ax.text(
        p2_x + 0.3, hm_legend_y + 0.05,
        "INSIGHT: Nigeria generates R4.2B in CIB revenue "
        "but only 13% FX capture. R1.8B leakage to competitors.",
        ha="left", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["accent_amber"],
        zorder=3,
    )

    # ===================================================
    # PANEL 3: Signal Performance + Risk + Seasonal
    # ===================================================

    draw_box(
        ax, p3_x, row2_top - panel_h,
        p3_w, panel_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    draw_box(
        ax, p3_x, row2_top - 0.5,
        p3_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        p3_x + 0.15, row2_top - 0.25,
        "SIGNAL PERFORMANCE",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Signal performance table
    signal_perf = [
        ("Geographic Expansion", 47, 34, "R340M", C["accent_green"]),
        ("Competitive Leakage", 89, 23, "R280M", C["accent_amber"]),
        ("Hedge Gap", 156, 78, "R84M", C["accent_green"]),
        ("Insurance Gap", 112, 45, "R52M", C["accent_green"]),
        ("Workforce Capture", 234, 120, "R48M", C["accent_amber"]),
        ("Currency Cascade", 8, 8, "R12M", C["accent_green"]),
        ("Supply Chain Risk", 23, 9, "R28M", C["accent_amber"]),
        ("Seasonal Filter", 342, "N/A", "Trust", C["accent_teal"]),
    ]

    # Headers
    sp_y = row2_top - 0.8
    sp_x = p3_x + 0.15
    col_w_signal = [4.0, 1.2, 1.2, 1.5, 1.5]

    headers = ["Signal Type", "Fired", "Acted", "Revenue", "Status"]

    for hi, (header, cw) in enumerate(zip(headers, col_w_signal)):
        hx = sp_x + sum(col_w_signal[:hi])

        ax.text(
            hx, sp_y,
            header,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_secondary"],
            zorder=3,
        )

    # Signal rows
    for si, (sname, sfired, sacted, srev, scolor) in enumerate(signal_perf):
        sy = sp_y - 0.35 - si * 0.5

        row_bg = C["card_bg"] if si % 2 == 0 else C["card_header"]

        draw_box(
            ax, p3_x + 0.1, sy - 0.18,
            p3_w - 0.2, 0.42,
            row_bg,
            corner_radius=0.03,
            border_color=C["card_border"],
            border_width=0.3,
        )

        # Signal name
        ax.text(
            sp_x, sy,
            sname,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_primary"],
            zorder=3,
        )

        # Fired count
        ax.text(
            sp_x + col_w_signal[0], sy,
            str(sfired),
            ha="left", va="center",
            fontsize=5, fontweight="bold",
            color=C["accent_blue"],
            zorder=3,
        )

        # Acted count
        ax.text(
            sp_x + sum(col_w_signal[:2]), sy,
            str(sacted),
            ha="left", va="center",
            fontsize=5,
            color=C["text_primary"] if sacted != "N/A" else C["text_muted"],
            zorder=3,
        )

        # Revenue
        ax.text(
            sp_x + sum(col_w_signal[:3]), sy,
            srev,
            ha="left", va="center",
            fontsize=5, fontweight="bold",
            color=scolor,
            zorder=3,
        )

    # Risk summary below signals
    risk_y = row2_top - panel_h + 2.2

    draw_box(
        ax, p3_x + 0.15, risk_y,
        p3_w - 0.3, 1.8,
        "#1A1A2A",
        corner_radius=0.06,
        border_color=C["accent_red"],
        border_width=0.8,
    )

    ax.text(
        p3_x + 0.3, risk_y + 1.55,
        "PORTFOLIO RISK SUMMARY",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_red"],
        zorder=3,
    )

    risk_items = [
        ("Unhedged FX exposure (group)", "R8.4B", C["accent_red"]),
        ("Insurance coverage gaps", "312 clients", C["accent_amber"]),
        ("Attrition risk (Platinum)", "23 clients", C["accent_red"]),
        ("Government payment delays", "NG, AO, MZ", C["accent_amber"]),
    ]

    for ri, (rlabel, rval, rcolor) in enumerate(risk_items):
        ry = risk_y + 1.2 - ri * 0.3

        ax.text(
            p3_x + 0.3, ry,
            rlabel,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_secondary"],
            zorder=3,
        )

        ax.text(
            p3_x + p3_w - 0.3, ry,
            rval,
            ha="right", va="center",
            fontsize=5, fontweight="bold",
            color=rcolor,
            zorder=3,
        )

    # ===================================================
    # ROW 3: Bottom panels
    # ===================================================

    row3_top = row2_top - panel_h - 0.2
    row3_h = 5.2

    # Bottom left: Top 10 clients by cross-sell opportunity
    bl_w = 12.0

    draw_box(
        ax, 0.3, row3_top - row3_h,
        bl_w, row3_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    draw_box(
        ax, 0.3, row3_top - 0.5,
        bl_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        0.45, row3_top - 0.25,
        "TOP 10 CROSS-SELL OPPORTUNITIES",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    top_clients = [
        ("Dangote Industries", "Platinum", "R151M", 4, "GH expansion + FX + INS + PBB"),
        ("Shoprite Holdings", "Platinum", "R89M", 3, "MZ/TZ insurance + payroll capture"),
        ("MTN Group", "Platinum", "R74M", 2, "FX hedging + trade finance"),
        ("Sasol Ltd", "Platinum", "R62M", 3, "MZ gas corridor + insurance"),
        ("Nedbank (CIB client)", "Gold", "R48M", 2, "Cross-border FX structuring"),
        ("Vodacom Tanzania", "Gold", "R41M", 3, "TZ payroll + insurance"),
        ("Zambia Sugar", "Gold", "R35M", 2, "ZM hedging + seasonal WC"),
        ("Tullow Oil Ghana", "Gold", "R32M", 3, "GH insurance + FX + payroll"),
        ("Equity Bank Kenya", "Silver", "R28M", 2, "KE corridor FX products"),
        ("Illovo Sugar", "Gold", "R24M", 2, "MZ/ZM seasonal facilities"),
    ]

    tc_y = row3_top - 0.8
    tc_spacing = 0.42

    # Column headers
    tc_cols = ["Client", "Tier", "Opportunity", "Gaps", "Primary Action"]
    tc_col_x = [0.45, 4.0, 5.2, 6.8, 7.8]

    for hi, header in enumerate(tc_cols):
        ax.text(
            tc_col_x[hi], tc_y,
            header,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_secondary"],
            zorder=3,
        )

    for ci_c, (cname, ctier, copp, cgaps, caction) in enumerate(top_clients):
        cy_c = tc_y - 0.3 - ci_c * tc_spacing

        # Alternating row
        if ci_c % 2 == 1:
            draw_box(
                ax, 0.4, cy_c - 0.15,
                bl_w - 0.2, 0.38,
                C["card_header"],
                corner_radius=0.02,
                zorder=1,
            )

        ax.text(tc_col_x[0], cy_c, cname, ha="left", va="center",
                fontsize=4.5, color=C["text_primary"], zorder=3)

        tier_colors = {"Platinum": C["accent_blue"], "Gold": C["accent_gold"], "Silver": C["text_secondary"]}
        ax.text(tc_col_x[1], cy_c, ctier, ha="left", va="center",
                fontsize=4.5, color=tier_colors.get(ctier, C["text_muted"]), zorder=3)

        ax.text(tc_col_x[2], cy_c, copp, ha="left", va="center",
                fontsize=5, fontweight="bold", color=C["accent_green"], zorder=3)

        ax.text(tc_col_x[3], cy_c, str(cgaps), ha="left", va="center",
                fontsize=5, fontweight="bold", color=C["accent_amber"], zorder=3)

        ax.text(tc_col_x[4], cy_c, caction, ha="left", va="center",
                fontsize=4, color=C["text_secondary"], zorder=3)

    # Bottom centre: Seasonal forecast
    bc_x = 0.3 + bl_w + panel_gap
    bc_w = 11.5

    draw_box(
        ax, bc_x, row3_top - row3_h,
        bc_w, row3_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    draw_box(
        ax, bc_x, row3_top - 0.5,
        bc_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        bc_x + 0.15, row3_top - 0.25,
        "SEASONAL OUTLOOK (NEXT 90 DAYS)",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Seasonal bars
    seasonal_data = [
        ("GH Cocoa", "Oct to Dec", "Peak", 1.8, C["accent_green"], "Payment volumes +80%. Pre-position FX and trade finance."),
        ("CI Cocoa", "Oct to Dec", "Peak", 1.5, C["accent_green"], "CFA zone corridor spike expected."),
        ("KE Flowers", "Pre-Valentines", "Rising", 1.3, C["accent_amber"], "Air freight and EUR/KES demand."),
        ("ZA Maize", "Off season", "Low", 0.5, C["accent_red"], "Expect reduced agri CIB volumes. Not attrition."),
        ("NG Oil", "Maintenance", "Dip", 0.6, C["accent_amber"], "Pipeline shutdown Q4. Cash flow delays for clients."),
        ("ZM Copper", "Dry season", "Peak", 1.4, C["accent_green"], "Mining output peak. USD/ZMW demand."),
        ("MZ Sugar", "End season", "Declining", 0.8, C["accent_amber"], "Crushing season ending. Payment normalisation."),
        ("TZ Gold", "Stable", "Normal", 1.0, C["text_muted"], "No significant seasonal effect."),
    ]

    bar_y = row3_top - 0.9
    bar_spacing = 0.52
    max_weight = 2.0
    bar_max_w = 2.5

    for si, (sname, speriod, sphase, sweight, scolor, snote) in enumerate(seasonal_data):
        sy = bar_y - si * bar_spacing

        # Name
        ax.text(
            bc_x + 0.2, sy,
            sname,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_primary"],
            zorder=3,
        )

        # Bar
        bar_x = bc_x + 2.5
        bw = bar_max_w * (sweight / max_weight)

        draw_box(
            ax, bar_x, sy - 0.1,
            bar_max_w, 0.2,
            C["progress_bg"],
            corner_radius=0.02,
        )

        if bw > 0.05:
            draw_box(
                ax, bar_x, sy - 0.1,
                bw, 0.2,
                scolor,
                corner_radius=0.02,
            )

        # Phase label
        ax.text(
            bar_x + bar_max_w + 0.15, sy,
            sphase,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=scolor,
            zorder=3,
        )

        # Note
        ax.text(
            bar_x + bar_max_w + 1.2, sy,
            snote,
            ha="left", va="center",
            fontsize=3.5,
            color=C["text_muted"],
            zorder=3,
        )

    # Bottom right: Currency exposure
    br_x = bc_x + bc_w + panel_gap
    br_w = 36 - br_x - 0.3

    draw_box(
        ax, br_x, row3_top - row3_h,
        br_w, row3_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    draw_box(
        ax, br_x, row3_top - 0.5,
        br_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        br_x + 0.15, row3_top - 0.25,
        "FX EXPOSURE",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    fx_data = [
        ("NGN", "R3.2B", "R420M", "13%", C["accent_red"], "Strict", "Oil r=0.78"),
        ("KES", "R1.8B", "R900M", "50%", C["accent_amber"], "Moderate", "Tea r=0.35"),
        ("GHS", "R1.1B", "R660M", "60%", C["accent_amber"], "Moderate", "Gold r=0.55"),
        ("ZMW", "R890M", "R534M", "60%", C["accent_amber"], "Moderate", "Copper r=0.82"),
        ("MZN", "R620M", "R186M", "30%", C["accent_red"], "Strict", "Gas r=0.60"),
        ("TZS", "R480M", "R240M", "50%", C["accent_amber"], "Moderate", "Gold r=0.35"),
        ("AOA", "R350M", "R35M", "10%", C["accent_red"], "Very strict", "Oil r=0.91"),
        ("UGX", "R240M", "R168M", "70%", C["accent_green"], "Liberal", "Agri"),
    ]

    fx_y = row3_top - 0.9
    fx_spacing = 0.52

    # Headers
    fx_cols = ["CCY", "Exposure", "Hedged", "Ratio", "Controls"]
    fx_col_x = [br_x + 0.15, br_x + 1.0, br_x + 2.8, br_x + 4.3, br_x + 5.2]

    for hi, header in enumerate(fx_cols):
        ax.text(
            fx_col_x[hi], fx_y,
            header,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_secondary"],
            zorder=3,
        )

    for fi, (fccy, fexp, fhedged, fratio, fcolor, fctrl, fcorr) in enumerate(fx_data):
        fy = fx_y - 0.3 - fi * fx_spacing

        ax.text(fx_col_x[0], fy, fccy, ha="left", va="center",
                fontsize=5, fontweight="bold", color=C["text_primary"], zorder=3)

        ax.text(fx_col_x[1], fy, fexp, ha="left", va="center",
                fontsize=4.5, color=C["text_primary"], zorder=3)

        ax.text(fx_col_x[2], fy, fhedged, ha="left", va="center",
                fontsize=4.5, color=C["text_secondary"], zorder=3)

        ax.text(fx_col_x[3], fy, fratio, ha="left", va="center",
                fontsize=5, fontweight="bold", color=fcolor, zorder=3)

        ax.text(fx_col_x[4], fy, fctrl, ha="left", va="center",
                fontsize=4, color=fcolor, zorder=3)

    # ===================================================
    # BOTTOM STATUS BAR
    # ===================================================

    draw_box(
        ax, 0, 0, 36, 0.6,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    ax.text(
        0.5, 0.3,
        "AfriFlow v1.0  |  2,847 integrated clients  |  "
        "20 country pods active  |  40 tables  |  12 signal types  |  "
        "Last entity resolution: 14 Jun 09:12 UTC  |  "
        "Next refresh: 09:19 UTC",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    ax.text(
        35.5, 0.3,
        "CONCEPT MOCKUP",
        ha="right", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["text_muted"],
        zorder=3,
    )

    # ===================================================
    # SAVE
    # ===================================================

    output_dir = os.path.dirname(os.path.abspath(__file__))

    output_path = os.path.join(
        output_dir, "exco_dashboard.png"
    )
    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
        pad_inches=0.1,
        facecolor=C["bg"],
        edgecolor="none",
    )
    print(f"ExCo Dashboard saved to: {output_path}")

    small_path = os.path.join(
        output_dir, "exco_dashboard_small.png"
    )
    fig.savefig(
        small_path,
        dpi=100,
        bbox_inches="tight",
        pad_inches=0.1,
        facecolor=C["bg"],
        edgecolor="none",
    )
    print(f"Small version saved to: {small_path}")

    plt.close(fig)


# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":

    print("Generating AfriFlow ExCo Dashboard Mockup...")
    print()

    generate_exco_dashboard()

    print()
    print("ExCo Dashboard mockup generated.")
    print(
        "Files ready for embedding in README.md "
        "and the Strategic Analysis document."
    )
