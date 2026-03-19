# diagrams/generate_rm_dashboard.py

"""
AfriFlow RM Dashboard Screen Design

We generate a high fidelity mockup of the Relationship
Manager dashboard that displays the unified golden
record, cross domain signals, data shadow gaps,
seasonal context, and recommended actions for a
single client.

This is the screen that makes an RM say "I cannot
go into a client meeting without this."

Usage:
    python diagrams/generate_rm_dashboard.py

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
from matplotlib.patches import Rectangle
import numpy as np
import os
from datetime import datetime


# -------------------------------------------------------
# Colour palette: Professional dark dashboard
# -------------------------------------------------------
C = {
    "bg": "#0F1923",
    "card_bg": "#1A2733",
    "card_border": "#2A3A4A",
    "card_header": "#1E3044",
    "text_primary": "#E8EDF2",
    "text_secondary": "#8899AA",
    "text_muted": "#556677",
    "accent_blue": "#2196F3",
    "accent_green": "#4CAF50",
    "accent_red": "#F44336",
    "accent_amber": "#FF9800",
    "accent_purple": "#9C27B0",
    "accent_teal": "#009688",
    "accent_cyan": "#00BCD4",
    "cib": "#1565C0",
    "forex": "#0D47A1",
    "insurance": "#2E7D32",
    "cell": "#F9A825",
    "pbb": "#C62828",
    "domain_active": "#4CAF50",
    "domain_inactive": "#37474F",
    "health_good": "#4CAF50",
    "health_warning": "#FF9800",
    "health_critical": "#F44336",
    "chart_line": "#2196F3",
    "chart_fill": "#2196F320",
    "chart_grid": "#1E3044",
    "sidebar_bg": "#141E2A",
    "sidebar_active": "#1A3A5C",
    "sidebar_text": "#8899AA",
    "topbar_bg": "#141E2A",
    "badge_green": "#1B5E20",
    "badge_red": "#B71C1C",
    "badge_amber": "#E65100",
    "divider": "#2A3A4A",
    "progress_bg": "#1E3044",
    "spark_up": "#4CAF50",
    "spark_down": "#F44336",
    "white": "#FFFFFF",
    "sb_blue": "#003DA5",
}


def draw_box(
    ax, x, y, w, h, facecolor,
    text_lines=None, text_color="#FFFFFF",
    fontsize=7, bold_first=False,
    corner_radius=0.08, alpha=1.0,
    border_color=None, border_width=0.5,
    zorder=2, text_ha="center",
    shadow=False, linestyle="-",
):
    """Draw a rounded rectangle with optional text."""

    if shadow:
        s = FancyBboxPatch(
            (x + 0.03, y - 0.03), w, h,
            boxstyle=f"round,pad=0.02,rounding_size={corner_radius}",
            facecolor="#00000030",
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
    data_min = min(data)
    data_max = max(data)
    data_range = data_max - data_min if data_max != data_min else 1

    ys = [y + (d - data_min) / data_range * h for d in data]

    ax.plot(xs, ys, color=color, linewidth=1.2, zorder=5, solid_capstyle="round")

    if fill:
        fill_xs = list(xs) + [xs[-1], xs[0]]
        fill_ys = list(ys) + [y, y]
        ax.fill(fill_xs, fill_ys, color=color, alpha=0.1, zorder=4)

    # End dot
    ax.plot(xs[-1], ys[-1], "o", color=color, markersize=3, zorder=6)


def draw_progress_bar(ax, x, y, w, h, pct, color, bg_color=None):
    """Draw a horizontal progress bar."""

    bg = bg_color if bg_color else C["progress_bg"]

    draw_box(ax, x, y, w, h, bg, corner_radius=0.03)

    fill_w = w * min(pct / 100, 1.0)
    if fill_w > 0.05:
        draw_box(ax, x, y, fill_w, h, color, corner_radius=0.03)


def draw_domain_indicator(ax, x, y, name, active, color):
    """Draw a domain status indicator dot with label."""

    dot_color = color if active else C["domain_inactive"]

    circle = Circle(
        (x, y), 0.12,
        facecolor=dot_color,
        edgecolor=C["card_bg"],
        linewidth=0.5,
        zorder=5,
    )
    ax.add_patch(circle)

    if active:
        # Checkmark approximation
        ax.text(
            x, y, "+",
            ha="center", va="center",
            fontsize=5, fontweight="bold",
            color="#FFFFFF",
            zorder=6,
        )

    ax.text(
        x, y - 0.22,
        name,
        ha="center", va="center",
        fontsize=4.5,
        color=C["text_secondary"] if active else C["text_muted"],
        zorder=5,
    )


def draw_metric_card(
    ax, x, y, w, h,
    label, value, sublabel=None,
    value_color=None, icon=None,
    trend=None, trend_value=None,
    sparkline_data=None, sparkline_color=None,
):
    """Draw a single metric card."""

    vc = value_color if value_color else C["text_primary"]

    draw_box(
        ax, x, y, w, h,
        C["card_bg"],
        corner_radius=0.06,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    # Label
    ax.text(
        x + 0.15, y + h - 0.2,
        label,
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    # Value
    ax.text(
        x + 0.15, y + h - 0.55,
        value,
        ha="left", va="center",
        fontsize=10, fontweight="bold",
        color=vc,
        zorder=3,
    )

    # Sublabel
    if sublabel:
        ax.text(
            x + 0.15, y + h - 0.82,
            sublabel,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_muted"],
            zorder=3,
        )

    # Trend indicator
    if trend and trend_value:
        trend_color = C["spark_up"] if trend == "up" else C["spark_down"]
        trend_symbol = "+" if trend == "up" else ""

        ax.text(
            x + w - 0.15, y + h - 0.55,
            f"{trend_symbol}{trend_value}",
            ha="right", va="center",
            fontsize=6, fontweight="bold",
            color=trend_color,
            zorder=3,
        )

    # Sparkline
    if sparkline_data:
        sc = sparkline_color if sparkline_color else C["chart_line"]
        spark_y = y + 0.08
        spark_h = h * 0.28
        draw_sparkline(
            ax, x + 0.1, spark_y,
            w - 0.2, spark_h,
            sparkline_data, sc,
        )


def draw_signal_row(
    ax, x, y, w, h,
    signal_name, urgency, description,
    opportunity, domains, age,
):
    """Draw a single signal alert row."""

    urgency_colors = {
        "CRITICAL": C["accent_red"],
        "HIGH": C["accent_amber"],
        "MEDIUM": C["accent_blue"],
    }

    uc = urgency_colors.get(urgency, C["accent_blue"])

    # Row background
    draw_box(
        ax, x, y, w, h,
        C["card_bg"],
        corner_radius=0.04,
        border_color=C["card_border"],
        border_width=0.3,
    )

    # Urgency stripe (left edge)
    draw_box(
        ax, x, y, 0.08, h,
        uc,
        corner_radius=0.02,
    )

    # Signal name
    ax.text(
        x + 0.25, y + h - 0.15,
        signal_name,
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Description
    ax.text(
        x + 0.25, y + h - 0.38,
        description,
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    # Urgency badge
    badge_w = 0.9
    draw_box(
        ax, x + w - badge_w - 0.15, y + h - 0.28,
        badge_w, 0.22,
        uc,
        text_lines=[urgency],
        text_color="#FFFFFF",
        fontsize=4.5,
        corner_radius=0.03,
    )

    # Opportunity value
    ax.text(
        x + w - 0.15, y + 0.15,
        opportunity,
        ha="right", va="center",
        fontsize=6, fontweight="bold",
        color=C["accent_green"],
        zorder=3,
    )

    # Age
    ax.text(
        x + 0.25, y + 0.15,
        age,
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )


def draw_shadow_gap_row(
    ax, x, y, w, h,
    rule_name, country, gap_type,
    opportunity, severity,
):
    """Draw a single data shadow gap row."""

    sev_colors = {
        "CRITICAL": C["accent_red"],
        "HIGH": C["accent_amber"],
        "MEDIUM": C["accent_blue"],
    }

    sc = sev_colors.get(severity, C["accent_blue"])

    draw_box(
        ax, x, y, w, h,
        C["card_bg"],
        corner_radius=0.04,
        border_color=sc,
        border_width=0.8,
        linestyle=(0, (3, 2)),
    )

    # Gap icon (dashed circle)
    circle = Circle(
        (x + 0.2, y + h / 2), 0.1,
        facecolor="none",
        edgecolor=sc,
        linewidth=1.0,
        linestyle=(0, (2, 1)),
        zorder=4,
    )
    ax.add_patch(circle)

    ax.text(
        x + 0.2, y + h / 2,
        "?",
        ha="center", va="center",
        fontsize=5, fontweight="bold",
        color=sc,
        zorder=5,
    )

    # Rule name
    ax.text(
        x + 0.45, y + h - 0.12,
        rule_name,
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Details
    ax.text(
        x + 0.45, y + 0.12,
        f"{country} | {gap_type}",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_secondary"],
        zorder=3,
    )

    # Opportunity
    ax.text(
        x + w - 0.1, y + h / 2,
        opportunity,
        ha="right", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_green"],
        zorder=3,
    )


def generate_rm_dashboard():
    """Generate the RM dashboard mockup."""

    fig, ax = plt.subplots(1, 1, figsize=(32, 20))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 32)
    ax.set_ylim(0, 20)
    ax.set_aspect("equal")
    ax.axis("off")

    # ===================================================
    # LEFT SIDEBAR
    # ===================================================

    sidebar_w = 2.8
    sidebar_h = 20

    draw_box(
        ax, 0, 0,
        sidebar_w, sidebar_h,
        C["sidebar_bg"],
        corner_radius=0.0,
    )

    # Logo area
    ax.text(
        sidebar_w / 2, 19.3,
        "AfriFlow",
        ha="center", va="center",
        fontsize=11, fontweight="bold",
        color=C["accent_blue"],
        zorder=3,
    )

    ax.text(
        sidebar_w / 2, 18.9,
        "Standard Bank Group",
        ha="center", va="center",
        fontsize=5,
        color=C["text_muted"],
        zorder=3,
    )

    # Divider
    ax.plot(
        [0.3, sidebar_w - 0.3], [18.5, 18.5],
        color=C["divider"], linewidth=0.5, zorder=3,
    )

    # Navigation items
    nav_items = [
        ("Client 360", True),
        ("Portfolio View", False),
        ("Signals", False),
        ("Corridors", False),
        ("Shadow Gaps", False),
        ("FX Events", False),
        ("Cross-Sell", False),
        ("Risk Heatmap", False),
        ("Briefings", False),
        ("Settings", False),
    ]

    for ni, (label, active) in enumerate(nav_items):
        ny = 17.8 - ni * 0.55

        if active:
            draw_box(
                ax, 0.1, ny - 0.15,
                sidebar_w - 0.2, 0.45,
                C["sidebar_active"],
                corner_radius=0.04,
                border_color=C["accent_blue"],
                border_width=0.5,
            )
            # Active indicator bar
            draw_box(
                ax, 0, ny - 0.15,
                0.06, 0.45,
                C["accent_blue"],
                corner_radius=0.02,
            )

        ax.text(
            0.5, ny + 0.08,
            label,
            ha="left", va="center",
            fontsize=5.5,
            fontweight="bold" if active else "normal",
            color=C["text_primary"] if active else C["sidebar_text"],
            zorder=3,
        )

    # User info at bottom
    ax.plot(
        [0.3, sidebar_w - 0.3], [2.0, 2.0],
        color=C["divider"], linewidth=0.5, zorder=3,
    )

    circle = Circle(
        (0.6, 1.3), 0.25,
        facecolor=C["accent_blue"],
        edgecolor=C["card_border"],
        linewidth=0.5,
        zorder=4,
    )
    ax.add_patch(circle)

    ax.text(
        0.6, 1.3, "SM",
        ha="center", va="center",
        fontsize=6, fontweight="bold",
        color="#FFFFFF",
        zorder=5,
    )

    ax.text(
        1.0, 1.45,
        "Sipho Mabena",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    ax.text(
        1.0, 1.15,
        "Senior RM, CIB",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_secondary"],
        zorder=3,
    )

    # ===================================================
    # TOP BAR
    # ===================================================

    topbar_x = sidebar_w
    topbar_y = 19.0
    topbar_h = 1.0

    draw_box(
        ax, topbar_x, topbar_y,
        32 - sidebar_w, topbar_h,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    # Client name and tier
    ax.text(
        topbar_x + 0.3, 19.65,
        "Dangote Industries Ltd",
        ha="left", va="center",
        fontsize=12, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Tier badge
    draw_box(
        ax, topbar_x + 5.5, 19.5,
        1.0, 0.3,
        C["sb_blue"],
        text_lines=["PLATINUM"],
        text_color="#FFFFFF",
        fontsize=5,
        corner_radius=0.04,
    )

    # Golden ID
    ax.text(
        topbar_x + 7.0, 19.65,
        "GLD-D4N6-0T3-1ND",
        ha="left", va="center",
        fontsize=6,
        color=C["text_muted"],
        fontfamily="monospace",
        zorder=3,
    )

    # Last updated
    ax.text(
        topbar_x + 0.3, 19.3,
        "Last updated: 2 minutes ago  |  Data freshness: ALL DOMAINS CURRENT",
        ha="left", va="center",
        fontsize=5,
        color=C["accent_green"],
        zorder=3,
    )

    # Domain indicators (top right)
    domains = [
        ("CIB", True, C["cib"]),
        ("FX", True, C["forex"]),
        ("INS", True, C["insurance"]),
        ("CELL", True, C["cell"]),
        ("PBB", False, C["pbb"]),
    ]

    for di, (dname, dactive, dcolor) in enumerate(domains):
        dx = 26.0 + di * 1.1
        draw_domain_indicator(
            ax, dx, 19.5,
            dname, dactive, dcolor,
        )

    # Action buttons (far right)
    draw_box(
        ax, 30.0, 19.4,
        1.6, 0.35,
        C["accent_blue"],
        text_lines=["Generate Brief"],
        text_color="#FFFFFF",
        fontsize=5,
        corner_radius=0.04,
    )

    # ===================================================
    # MAIN CONTENT AREA
    # ===================================================

    content_x = sidebar_w + 0.2
    content_y = 0.3
    content_w = 32 - sidebar_w - 0.4
    content_top = 18.8

    # ----- ROW 1: Key Metrics (top row) -----

    metrics_y = content_top - 1.3
    metric_w = (content_w - 0.6) / 5
    metric_h = 1.15

    metrics = [
        {
            "label": "Total Relationship Value",
            "value": "R4.2B",
            "sublabel": "Across 4 active domains",
            "color": C["accent_blue"],
            "trend": "up", "trend_value": "12%",
            "spark": [3.1, 3.3, 3.2, 3.5, 3.8, 3.7, 4.0, 4.2],
        },
        {
            "label": "CIB Annual Revenue",
            "value": "R28.4M",
            "sublabel": "Fee income (rolling 12m)",
            "color": C["cib"],
            "trend": "up", "trend_value": "8%",
            "spark": [22, 23, 24, 23, 25, 26, 27, 28.4],
        },
        {
            "label": "FX Hedge Ratio",
            "value": "22%",
            "sublabel": "R1.56B UNHEDGED",
            "color": C["accent_red"],
            "trend": "down", "trend_value": "-15%",
            "spark": [45, 40, 38, 35, 30, 28, 25, 22],
        },
        {
            "label": "Active Corridors",
            "value": "7",
            "sublabel": "ZA KE NG GH TZ MZ ZM",
            "color": C["accent_teal"],
            "trend": "up", "trend_value": "+2 new",
            "spark": [3, 3, 4, 4, 5, 5, 6, 7],
        },
        {
            "label": "Cross-Sell Score",
            "value": "CRITICAL",
            "sublabel": "4 product gaps detected",
            "color": C["accent_red"],
            "trend": None, "trend_value": None,
            "spark": None,
        },
    ]

    for mi, m in enumerate(metrics):
        mx = content_x + mi * (metric_w + 0.15)

        draw_metric_card(
            ax, mx, metrics_y,
            metric_w, metric_h,
            m["label"], m["value"],
            sublabel=m["sublabel"],
            value_color=m["color"],
            trend=m["trend"],
            trend_value=m["trend_value"],
            sparkline_data=m["spark"],
            sparkline_color=m["color"],
        )

    # ----- ROW 2: Three columns -----

    row2_y = metrics_y - 0.2
    col_gap = 0.2

    # Column widths
    col1_w = content_w * 0.38
    col2_w = content_w * 0.32
    col3_w = content_w * 0.28

    col1_x = content_x
    col2_x = col1_x + col1_w + col_gap
    col3_x = col2_x + col2_w + col_gap

    # ===================================================
    # COLUMN 1: Active Signals
    # ===================================================

    signals_top = row2_y
    signals_h = 8.5

    draw_box(
        ax, col1_x, signals_top - signals_h,
        col1_w, signals_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
    )

    # Header
    draw_box(
        ax, col1_x, signals_top - 0.5,
        col1_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        col1_x + 0.15, signals_top - 0.25,
        "ACTIVE SIGNALS",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Signal count badge
    draw_box(
        ax, col1_x + col1_w - 0.6, signals_top - 0.4,
        0.45, 0.25,
        C["accent_red"],
        text_lines=["4"],
        text_color="#FFFFFF",
        fontsize=5.5,
        corner_radius=0.04,
    )

    # Signal rows
    signals = [
        {
            "name": "GEOGRAPHIC EXPANSION",
            "urgency": "CRITICAL",
            "desc": "Expanding into Ghana. 847 new SIMs in Accra. 3 new payment corridors.",
            "opp": "R120M",
            "age": "Detected 3 days ago",
        },
        {
            "name": "UNHEDGED FX EXPOSURE",
            "urgency": "CRITICAL",
            "desc": "KES hedging lapsed. R180M unhedged across Kenya corridor.",
            "opp": "R8.4M",
            "age": "Detected 1 day ago",
        },
        {
            "name": "INSURANCE COVERAGE GAP",
            "urgency": "HIGH",
            "desc": "No coverage in Ghana, Tanzania, or Mozambique despite active CIB ops.",
            "opp": "R4.2M",
            "age": "Detected 5 days ago",
        },
        {
            "name": "COMPETITIVE LEAKAGE",
            "urgency": "HIGH",
            "desc": "Nigeria corridor: 100% CIB but only 13% FX capture. Zero insurance.",
            "opp": "R18M",
            "age": "Detected 7 days ago",
        },
        {
            "name": "WORKFORCE CAPTURE",
            "urgency": "MEDIUM",
            "desc": "800 MTN SIMs in Nigeria (est. 288 staff). Zero PBB payroll deposits.",
            "opp": "R720K/yr",
            "age": "Detected 12 days ago",
        },
    ]

    sig_row_h = 0.65
    sig_start_y = signals_top - 0.7

    for si, sig in enumerate(signals):
        sy = sig_start_y - si * (sig_row_h + 0.1)

        draw_signal_row(
            ax, col1_x + 0.1, sy - sig_row_h,
            col1_w - 0.2, sig_row_h,
            sig["name"], sig["urgency"],
            sig["desc"], sig["opp"],
            None, sig["age"],
        )

    # Total opportunity
    total_opp_y = signals_top - signals_h + 0.15

    ax.text(
        col1_x + 0.15, total_opp_y + 0.5,
        "TOTAL SIGNAL OPPORTUNITY",
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    ax.text(
        col1_x + col1_w - 0.15, total_opp_y + 0.5,
        "R151.1M",
        ha="right", va="center",
        fontsize=8, fontweight="bold",
        color=C["accent_green"],
        zorder=3,
    )

    # ===================================================
    # COLUMN 2: Corridor Revenue Map + Domain Breakdown
    # ===================================================

    col2_top = row2_y
    col2_upper_h = 4.5
    col2_lower_h = 3.8

    # Upper card: Corridor Revenue
    draw_box(
        ax, col2_x, col2_top - col2_upper_h,
        col2_w, col2_upper_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
    )

    draw_box(
        ax, col2_x, col2_top - 0.5,
        col2_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        col2_x + 0.15, col2_top - 0.25,
        "CORRIDOR REVENUE (90 DAY)",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Corridor bars
    corridors = [
        ("ZA > NG", 890, 100, 28, "R18.2M"),
        ("ZA > KE", 520, 85, 65, "R14.1M"),
        ("ZA > GH", 180, 60, 20, "R4.8M"),
        ("ZA > TZ", 95, 40, 30, "R2.9M"),
        ("ZA > MZ", 72, 35, 45, "R2.1M"),
        ("ZA > ZM", 65, 30, 55, "R1.8M"),
        ("KE > TZ", 45, 20, 40, "R0.9M"),
    ]

    bar_start_y = col2_top - 0.9
    bar_h = 0.25
    bar_spacing = 0.42
    max_val = 890

    for ci_r, (corridor, value, fx_pct, ins_pct, revenue) in enumerate(corridors):
        by = bar_start_y - ci_r * bar_spacing

        # Corridor label
        ax.text(
            col2_x + 0.15, by + bar_h / 2,
            corridor,
            ha="left", va="center",
            fontsize=5,
            color=C["text_secondary"],
            zorder=3,
        )

        # Bar background
        bar_x = col2_x + 1.6
        bar_w = col2_w - 3.0

        draw_box(
            ax, bar_x, by,
            bar_w, bar_h,
            C["progress_bg"],
            corner_radius=0.03,
        )

        # CIB portion (always full)
        cib_w = bar_w * (value / max_val)
        draw_box(
            ax, bar_x, by,
            cib_w, bar_h,
            C["cib"],
            corner_radius=0.03,
        )

        # FX overlay
        fx_w = cib_w * (fx_pct / 100)
        if fx_w > 0.05:
            draw_box(
                ax, bar_x, by,
                fx_w, bar_h * 0.5,
                C["forex"],
                corner_radius=0.02,
            )

        # Revenue label
        ax.text(
            col2_x + col2_w - 0.15, by + bar_h / 2,
            revenue,
            ha="right", va="center",
            fontsize=5, fontweight="bold",
            color=C["text_primary"],
            zorder=3,
        )

    # Legend for bars
    legend_y = col2_top - col2_upper_h + 0.3

    for li, (lname, lcolor) in enumerate([
        ("CIB", C["cib"]),
        ("FX Hedged", C["forex"]),
        ("Unhedged", C["progress_bg"]),
    ]):
        lx = col2_x + 0.15 + li * 1.8

        draw_box(
            ax, lx, legend_y,
            0.3, 0.15,
            lcolor,
            corner_radius=0.02,
        )

        ax.text(
            lx + 0.4, legend_y + 0.07,
            lname,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_muted"],
        )

    # Lower card: Domain Revenue Breakdown
    col2_lower_y = col2_top - col2_upper_h - 0.2

    draw_box(
        ax, col2_x, col2_lower_y - col2_lower_h,
        col2_w, col2_lower_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
    )

    draw_box(
        ax, col2_x, col2_lower_y - 0.5,
        col2_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        col2_x + 0.15, col2_lower_y - 0.25,
        "REVENUE BY DOMAIN (ANNUAL)",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    domain_revenue = [
        ("CIB", "R2.8B", "66%", C["cib"], 66),
        ("Forex", "R840M", "20%", C["forex"], 20),
        ("Insurance", "R380M", "9%", C["insurance"], 9),
        ("Cell / MoMo", "R180M", "4%", C["cell"], 4),
        ("PBB", "R0", "0%", C["pbb"], 0),
    ]

    dr_start_y = col2_lower_y - 0.8
    dr_spacing = 0.55

    for dri, (dname, dval, dpct, dcolor, dpct_num) in enumerate(domain_revenue):
        dry = dr_start_y - dri * dr_spacing

        ax.text(
            col2_x + 0.15, dry + 0.18,
            dname,
            ha="left", va="center",
            fontsize=5,
            color=C["text_secondary"],
            zorder=3,
        )

        ax.text(
            col2_x + col2_w - 0.15, dry + 0.18,
            f"{dval} ({dpct})",
            ha="right", va="center",
            fontsize=5.5, fontweight="bold",
            color=dcolor if dpct_num > 0 else C["text_muted"],
            zorder=3,
        )

        draw_progress_bar(
            ax, col2_x + 0.15, dry - 0.05,
            col2_w - 0.3, 0.12,
            dpct_num, dcolor,
        )

    # PBB callout
    ax.text(
        col2_x + 0.15, dr_start_y - 5 * dr_spacing + 0.6,
        "PBB: No payroll relationship.",
        ha="left", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["accent_red"],
        zorder=3,
    )

    ax.text(
        col2_x + 0.15, dr_start_y - 5 * dr_spacing + 0.35,
        "15,000 employees banking elsewhere.",
        ha="left", va="center",
        fontsize=4.5,
        color=C["accent_amber"],
        zorder=3,
    )

    # ===================================================
    # COLUMN 3: Data Shadow + Seasonal + Actions
    # ===================================================

    col3_top = row2_y

    # Data Shadow card
    shadow_h = 3.8

    draw_box(
        ax, col3_x, col3_top - shadow_h,
        col3_w, shadow_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
    )

    draw_box(
        ax, col3_x, col3_top - 0.5,
        col3_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        col3_x + 0.15, col3_top - 0.25,
        "DATA SHADOW GAPS",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Shadow health score
    ax.text(
        col3_x + col3_w - 0.15, col3_top - 0.25,
        "Health: 42/100",
        ha="right", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_red"],
        zorder=3,
    )

    gaps = [
        ("FX Hedging Gap", "NG", "Volume mismatch", "R6.0M"),
        ("Insurance Gap", "GH", "Geographic gap", "R4.2M"),
        ("Cell Absence", "GH, TZ", "Leakage", "R500K"),
        ("PBB Payroll", "NG, KE", "Capture gap", "R720K"),
    ]

    gap_h = 0.55
    gap_start_y = col3_top - 0.7

    for gi, (gname, gcountry, gtype, gopp) in enumerate(gaps):
        gy = gap_start_y - gi * (gap_h + 0.08)

        draw_shadow_gap_row(
            ax, col3_x + 0.1, gy - gap_h,
            col3_w - 0.2, gap_h,
            gname, gcountry, gtype, gopp,
            "HIGH" if gi < 2 else "MEDIUM",
        )

    # Shadow total
    ax.text(
        col3_x + 0.15, col3_top - shadow_h + 0.25,
        "TOTAL SHADOW OPPORTUNITY",
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    ax.text(
        col3_x + col3_w - 0.15, col3_top - shadow_h + 0.25,
        "R11.4M",
        ha="right", va="center",
        fontsize=7, fontweight="bold",
        color=C["accent_green"],
        zorder=3,
    )

    # Seasonal Context card
    seasonal_y = col3_top - shadow_h - 0.2
    seasonal_h = 2.0

    draw_box(
        ax, col3_x, seasonal_y - seasonal_h,
        col3_w, seasonal_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
    )

    draw_box(
        ax, col3_x, seasonal_y - 0.5,
        col3_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        col3_x + 0.15, seasonal_y - 0.25,
        "SEASONAL CONTEXT",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    seasonal_items = [
        ("Cocoa peak in 2 months (Oct to Dec)", C["accent_amber"]),
        ("GH payment volumes will rise 80%", C["accent_green"]),
        ("NG oil: pipeline maintenance season", C["accent_amber"]),
        ("ZM copper: dry season (peak output)", C["accent_green"]),
    ]

    for si_s, (stext, scolor) in enumerate(seasonal_items):
        sy_s = seasonal_y - 0.75 - si_s * 0.3

        bullet = Circle(
            (col3_x + 0.25, sy_s),
            0.06,
            facecolor=scolor,
            edgecolor="none",
            zorder=4,
        )
        ax.add_patch(bullet)

        ax.text(
            col3_x + 0.4, sy_s,
            stext,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_secondary"],
            zorder=3,
        )

    # Recommended Actions card
    actions_y = seasonal_y - seasonal_h - 0.2
    actions_h = 2.5

    draw_box(
        ax, col3_x, actions_y - actions_h,
        col3_w, actions_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["accent_green"],
        border_width=1.0,
    )

    draw_box(
        ax, col3_x, actions_y - 0.5,
        col3_w, 0.5,
        "#1B3D2F",
        corner_radius=0.06,
    )

    ax.text(
        col3_x + 0.15, actions_y - 0.25,
        "RECOMMENDED ACTIONS",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["accent_green"],
        zorder=3,
    )

    actions = [
        "1. Contact CFO re: Ghana expansion (48h)",
        "2. Offer KES forward contract (R180M)",
        "3. Quote GH/TZ/MZ insurance package",
        "4. Bundle NG FX + insurance proposal",
        "5. Present payroll capture to HR Director",
    ]

    for ai, action in enumerate(actions):
        ay = actions_y - 0.75 - ai * 0.3

        ax.text(
            col3_x + 0.15, ay,
            action,
            ha="left", va="center",
            fontsize=5,
            color=C["text_primary"],
            zorder=3,
        )

    # Action button
    draw_box(
        ax, col3_x + 0.15, actions_y - actions_h + 0.15,
        col3_w - 0.3, 0.35,
        C["accent_blue"],
        text_lines=["Create Salesforce Tasks"],
        text_color="#FFFFFF",
        fontsize=5.5,
        corner_radius=0.04,
    )

    # ===================================================
    # BOTTOM BAR: Currency Alert
    # ===================================================

    alert_y = content_y
    alert_h = 0.7
    alert_x = content_x
    alert_w = content_w

    draw_box(
        ax, alert_x, alert_y,
        alert_w, alert_h,
        "#2A1A1A",
        corner_radius=0.06,
        border_color=C["accent_red"],
        border_width=1.0,
    )

    # Pulsing dot
    for ring in range(3):
        r = 0.08 + ring * 0.04
        a = 0.6 - ring * 0.15
        circle = Circle(
            (alert_x + 0.4, alert_y + alert_h / 2), r,
            facecolor=C["accent_red"],
            edgecolor="none",
            alpha=a,
            zorder=5,
        )
        ax.add_patch(circle)

    ax.text(
        alert_x + 0.7, alert_y + alert_h / 2,
        "CURRENCY ALERT: NGN devalued 18.5% (06:14 UTC). "
        "This client has R500M unhedged NGN exposure. "
        "CIB facility impact: R92.5M. "
        "Recommend emergency hedging outreach.",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_red"],
        zorder=6,
    )

    draw_box(
        ax, alert_x + alert_w - 2.0, alert_y + 0.15,
        1.8, 0.4,
        C["accent_red"],
        text_lines=["View Full Impact"],
        text_color="#FFFFFF",
        fontsize=5.5,
        corner_radius=0.04,
    )

    # ===================================================
    # DISCLAIMER WATERMARK
    # ===================================================

    ax.text(
        16, 0.05,
        "CONCEPT MOCKUP | AfriFlow by Thabo Kunene | "
        "Not a sanctioned initiative of Standard Bank Group",
        ha="center", va="center",
        fontsize=4,
        color="#334455",
        fontstyle="italic",
        zorder=1,
    )

    # ===================================================
    # SAVE
    # ===================================================

    output_dir = os.path.dirname(os.path.abspath(__file__))

    output_path = os.path.join(
        output_dir, "rm_dashboard.png"
    )
    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
        pad_inches=0.1,
        facecolor=C["bg"],
        edgecolor="none",
    )
    print(f"RM Dashboard saved to: {output_path}")

    small_path = os.path.join(
        output_dir, "rm_dashboard_small.png"
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

    print("Generating AfriFlow RM Dashboard Mockup...")
    print()

    generate_rm_dashboard()

    print()
    print("RM Dashboard mockup generated.")
    print(
        "Files ready for embedding in README.md "
        "and the Strategic Analysis document."
    )
