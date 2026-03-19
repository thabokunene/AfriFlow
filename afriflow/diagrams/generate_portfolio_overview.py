# diagrams/generate_portfolio_overview.py

"""
AfriFlow Portfolio Overview Screen

We generate a high fidelity mockup of the
Relationship Manager's morning view: a complete
portfolio of assigned clients ranked by urgency,
filterable by tier, country, corridor, risk level,
and signal count.

This is the screen an RM opens at 07:00 with coffee.
It answers: "Which clients need my attention today?"

Usage:
    python diagrams/generate_portfolio_overview.py

DISCLAIMER: This project is not a sanctioned
initiative of Standard Bank Group, MTN, or any
affiliated entity. It is a demonstration of
concept, domain knowledge, and data engineering
skill by Thabo Kunene.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.patches import Circle
import numpy as np
import os


# -------------------------------------------------------
# Colour palette
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
    "topbar_bg": "#141E2A",
    "divider": "#2A3A4A",
    "sidebar_bg": "#141E2A",
    "sidebar_active": "#1A3A5C",
    "sidebar_text": "#8899AA",
    "progress_bg": "#1E3044",
    "health_good": "#4CAF50",
    "health_warning": "#FF9800",
    "health_critical": "#F44336",
    "health_stable": "#2196F3",
    "sb_blue": "#003DA5",
    "platinum": "#1565C0",
    "gold_tier": "#FFB300",
    "silver_tier": "#78909C",
    "bronze_tier": "#8D6E63",
    "row_even": "#1A2733",
    "row_odd": "#162230",
    "row_hover": "#1E3044",
    "row_urgent": "#2A1A1A",
    "white": "#FFFFFF",
    "signal_badge": "#F44336",
    "lekgotla_gold": "#D4A017",
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
            boxstyle=(
                f"round,pad=0.02,"
                f"rounding_size={corner_radius}"
            ),
            facecolor="#00000025",
            edgecolor="none",
            zorder=zorder - 1,
        )
        ax.add_patch(s)

    edge = (
        border_color if border_color
        else facecolor
    )
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=(
            f"round,pad=0.02,"
            f"rounding_size={corner_radius}"
        ),
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
    spacing = min(
        0.22, (h * 0.85) / max(n, 1)
    )
    start_y = (
        y + h / 2 + (n - 1) * spacing / 2
    )

    for i, line in enumerate(text_lines):
        weight = (
            "bold"
            if (i == 0 and bold_first)
            else "normal"
        )
        fs = (
            fontsize + 0.5
            if (i == 0 and bold_first)
            else fontsize
        )
        tx = (
            x + w / 2
            if text_ha == "center"
            else x + 0.1
        )

        ax.text(
            tx, start_y - i * spacing,
            line,
            ha=text_ha, va="center",
            fontsize=fs, fontweight=weight,
            color=text_color,
            zorder=zorder + 1,
            fontfamily="sans-serif",
        )


def draw_sparkline(
    ax, x, y, w, h, data, color,
):
    """Draw a small sparkline."""

    n = len(data)
    xs = np.linspace(x, x + w, n)
    d_min = min(data)
    d_max = max(data)
    d_range = (
        d_max - d_min
        if d_max != d_min
        else 1
    )
    ys = [
        y + (d - d_min) / d_range * h
        for d in data
    ]

    ax.plot(
        xs, ys,
        color=color,
        linewidth=0.8,
        zorder=5,
        solid_capstyle="round",
    )

    ax.fill_between(
        xs, [y] * n, ys,
        color=color,
        alpha=0.06,
        zorder=4,
    )

    ax.plot(
        xs[-1], ys[-1], "o",
        color=color,
        markersize=2,
        zorder=6,
    )


def draw_progress_bar(
    ax, x, y, w, h, pct, color,
):
    """Draw a horizontal progress bar."""

    draw_box(
        ax, x, y, w, h,
        C["progress_bg"],
        corner_radius=0.02,
    )

    fill_w = w * min(pct / 100, 1.0)
    if fill_w > 0.03:
        draw_box(
            ax, x, y, fill_w, h,
            color,
            corner_radius=0.02,
        )


def draw_health_dot(ax, x, y, status):
    """Draw a health status indicator dot."""

    colors = {
        "HEALTHY": C["health_good"],
        "AT_RISK": C["health_warning"],
        "CRITICAL": C["health_critical"],
        "STABLE": C["health_stable"],
    }

    c = colors.get(status, C["text_muted"])

    # Outer glow
    glow = Circle(
        (x, y), 0.14,
        facecolor=c,
        edgecolor="none",
        alpha=0.2,
        zorder=4,
    )
    ax.add_patch(glow)

    # Inner dot
    dot = Circle(
        (x, y), 0.08,
        facecolor=c,
        edgecolor=C["card_bg"],
        linewidth=0.5,
        zorder=5,
    )
    ax.add_patch(dot)


def draw_domain_dots(ax, x, y, domains_active):
    """Draw 5 small domain indicator dots."""

    domain_list = [
        ("CIB", C["cib"]),
        ("FX", C["forex"]),
        ("INS", C["insurance"]),
        ("CELL", C["cell"]),
        ("PBB", C["pbb"]),
    ]

    for di, (dname, dcolor) in enumerate(
        domain_list
    ):
        dx = x + di * 0.28
        active = dname in domains_active

        dot = Circle(
            (dx, y), 0.08,
            facecolor=(
                dcolor if active
                else C["text_muted"]
            ),
            edgecolor=C["card_bg"],
            linewidth=0.3,
            alpha=1.0 if active else 0.3,
            zorder=5,
        )
        ax.add_patch(dot)


def draw_filter_chip(
    ax, x, y, label, active=False,
    color=None, count=None,
):
    """Draw a filter chip. Returns width."""

    text = label
    if count is not None:
        text = f"{label} ({count})"

    chip_w = len(text) * 0.09 + 0.35

    bg = (
        C["sidebar_active"]
        if active
        else C["card_bg"]
    )
    border = (
        C["accent_blue"]
        if active
        else C["card_border"]
    )
    tc = (
        C["white"]
        if active
        else C["text_muted"]
    )

    if color and active:
        border = color

    draw_box(
        ax, x, y,
        chip_w, 0.3,
        bg,
        text_lines=[text],
        text_color=tc,
        fontsize=4.5,
        corner_radius=0.05,
        border_color=border,
        border_width=0.8 if active else 0.3,
    )

    return chip_w


def generate_portfolio_overview():
    """Generate the Portfolio Overview screen."""

    fig, ax = plt.subplots(1, 1, figsize=(34, 22))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 34)
    ax.set_ylim(0, 22)
    ax.set_aspect("equal")
    ax.axis("off")

    # ===================================================
    # LEFT SIDEBAR
    # ===================================================

    sidebar_w = 2.8

    draw_box(
        ax, 0, 0,
        sidebar_w, 22,
        C["sidebar_bg"],
        corner_radius=0.0,
    )

    # Logo
    ax.text(
        sidebar_w / 2, 21.3,
        "AfriFlow",
        ha="center", va="center",
        fontsize=11, fontweight="bold",
        color=C["accent_blue"],
        zorder=3,
    )

    ax.text(
        sidebar_w / 2, 20.95,
        "Standard Bank Group",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    ax.plot(
        [0.3, sidebar_w - 0.3],
        [20.6, 20.6],
        color=C["divider"],
        linewidth=0.5,
        zorder=3,
    )

    # Navigation
    nav_items = [
        ("Client 360", False),
        ("Portfolio", True),
        ("Signals", False),
        ("Corridors", False),
        ("Shadow Gaps", False),
        ("FX Events", False),
        ("Cross-Sell", False),
        ("Risk Heatmap", False),
        ("Lekgotla", False),
        ("Briefings", False),
        ("Settings", False),
    ]

    for ni, (label, active) in enumerate(
        nav_items
    ):
        ny = 19.9 - ni * 0.55

        if active:
            draw_box(
                ax, 0.1, ny - 0.15,
                sidebar_w - 0.2, 0.45,
                C["sidebar_active"],
                corner_radius=0.04,
                border_color=C["accent_blue"],
                border_width=0.5,
            )

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
            fontweight=(
                "bold" if active else "normal"
            ),
            color=(
                C["text_primary"]
                if active
                else C["sidebar_text"]
            ),
            zorder=3,
        )

    # User
    ax.plot(
        [0.3, sidebar_w - 0.3],
        [2.0, 2.0],
        color=C["divider"],
        linewidth=0.5,
        zorder=3,
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
    topbar_h = 1.0

    draw_box(
        ax, topbar_x, 21.0,
        34 - sidebar_w, topbar_h,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    ax.text(
        topbar_x + 0.3, 21.6,
        "Portfolio Overview",
        ha="left", va="center",
        fontsize=12, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    ax.text(
        topbar_x + 0.3, 21.25,
        "Good morning, Sipho. "
        "You have 48 assigned clients. "
        "7 need your attention today.",
        ha="left", va="center",
        fontsize=6,
        color=C["text_secondary"],
        zorder=3,
    )

    # Search bar
    search_x = 18.0
    search_w = 7.0

    draw_box(
        ax, search_x, 21.28,
        search_w, 0.4,
        C["card_bg"],
        corner_radius=0.06,
        border_color=C["card_border"],
        border_width=0.5,
    )

    ax.text(
        search_x + 0.3, 21.48,
        "Search clients by name, golden ID, "
        "country...",
        ha="left", va="center",
        fontsize=5,
        color=C["text_muted"],
        fontstyle="italic",
        zorder=3,
    )

    # Actions
    draw_box(
        ax, 26.0, 21.25,
        2.2, 0.4,
        C["accent_blue"],
        text_lines=["Generate All Briefs"],
        text_color="#FFFFFF",
        fontsize=5,
        corner_radius=0.04,
    )

    draw_box(
        ax, 28.5, 21.25,
        1.6, 0.4,
        C["card_bg"],
        text_lines=["Export CSV"],
        text_color=C["text_secondary"],
        fontsize=5,
        corner_radius=0.04,
        border_color=C["card_border"],
        border_width=0.5,
    )

    # Data freshness
    ax.text(
        33.5, 21.5,
        "All domains current",
        ha="right", va="center",
        fontsize=5,
        color=C["accent_green"],
        zorder=3,
    )

    ax.text(
        33.5, 21.25,
        "Updated: 07:02 UTC",
        ha="right", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    # ===================================================
    # SUMMARY METRICS BAR
    # ===================================================

    metrics_y = 19.8
    metrics_h = 1.0
    content_x = topbar_x + 0.2
    content_w = 34 - sidebar_w - 0.4

    draw_box(
        ax, content_x, metrics_y,
        content_w, metrics_h,
        C["card_bg"],
        corner_radius=0.06,
        border_color=C["card_border"],
        border_width=0.3,
    )

    portfolio_metrics = [
        ("48", "Total Clients", C["accent_blue"]),
        ("R18.4B", "Portfolio TRV", C["accent_blue"]),
        ("7", "Need Attention", C["accent_red"]),
        ("23", "Active Signals", C["accent_amber"]),
        ("4", "Platinum", C["platinum"]),
        ("18", "Gold", C["gold_tier"]),
        ("26", "Silver/Bronze", C["silver_tier"]),
        ("12", "Shadow Gaps", C["accent_purple"]),
        ("R2.1B", "Cross-Sell Opp", C["accent_green"]),
        ("87%", "Entity Coverage", C["accent_teal"]),
    ]

    pm_w = content_w / len(portfolio_metrics)

    for mi, (mval, mlabel, mcolor) in enumerate(
        portfolio_metrics
    ):
        mx = content_x + mi * pm_w

        ax.text(
            mx + pm_w / 2,
            metrics_y + metrics_h - 0.3,
            mval,
            ha="center", va="center",
            fontsize=8, fontweight="bold",
            color=mcolor,
            zorder=3,
        )

        ax.text(
            mx + pm_w / 2,
            metrics_y + 0.2,
            mlabel,
            ha="center", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

    # ===================================================
    # FILTER BAR
    # ===================================================

    filter_y = 19.1

    draw_box(
        ax, content_x, filter_y,
        content_w, 0.55,
        C["card_header"],
        corner_radius=0.04,
        border_color=C["divider"],
        border_width=0.3,
    )

    # Tier filters
    ax.text(
        content_x + 0.15, filter_y + 0.28,
        "Tier:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["text_secondary"],
        zorder=3,
    )

    tier_filters = [
        ("All", True, None, 48),
        ("Platinum", False, C["platinum"], 4),
        ("Gold", False, C["gold_tier"], 18),
        ("Silver", False, C["silver_tier"], 26),
    ]

    tx = content_x + 1.0

    for flabel, factive, fcolor, fcount in tier_filters:
        fw = draw_filter_chip(
            ax, tx, filter_y + 0.12,
            flabel, factive, fcolor, fcount,
        )
        tx += fw + 0.08

    # Country filters
    ax.text(
        tx + 0.3, filter_y + 0.28,
        "Country:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["text_secondary"],
        zorder=3,
    )

    tx += 1.5

    country_filters = [
        ("All", True, 48),
        ("ZA", False, 22),
        ("NG", False, 12),
        ("KE", False, 8),
        ("GH", False, 4),
        ("Other", False, 2),
    ]

    for clabel, cactive, ccount in country_filters:
        cw = draw_filter_chip(
            ax, tx, filter_y + 0.12,
            clabel, cactive, count=ccount,
        )
        tx += cw + 0.06

    # Risk filter
    ax.text(
        tx + 0.3, filter_y + 0.28,
        "Health:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["text_secondary"],
        zorder=3,
    )

    tx += 1.3

    health_filters = [
        ("All", True, None),
        ("Critical", False, C["health_critical"]),
        ("At Risk", False, C["health_warning"]),
        ("Healthy", False, C["health_good"]),
    ]

    for hlabel, hactive, hcolor in health_filters:
        hw = draw_filter_chip(
            ax, tx, filter_y + 0.12,
            hlabel, hactive, hcolor,
        )
        tx += hw + 0.06

    # Sort
    ax.text(
        content_x + content_w - 3.0,
        filter_y + 0.28,
        "Sort: Urgency (signals + risk)",
        ha="left", va="center",
        fontsize=5,
        color=C["accent_blue"],
        fontweight="bold",
        zorder=3,
    )

    # ===================================================
    # NEEDS ATTENTION SECTION
    # ===================================================

    attention_y = 18.3

    draw_box(
        ax, content_x, attention_y,
        content_w, 0.5,
        "#1A1018",
        corner_radius=0.04,
        border_color=C["accent_red"],
        border_width=0.8,
    )

    # Pulsing dot
    for ring in range(3):
        r = 0.06 + ring * 0.03
        a = 0.6 - ring * 0.15
        dot = Circle(
            (content_x + 0.3, attention_y + 0.25),
            r,
            facecolor=C["accent_red"],
            edgecolor="none",
            alpha=a,
            zorder=5,
        )
        ax.add_patch(dot)

    ax.text(
        content_x + 0.5, attention_y + 0.25,
        "NEEDS YOUR ATTENTION TODAY: "
        "7 clients with unactioned signals, "
        "expiring hedges, or critical risk "
        "changes",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_red"],
        zorder=3,
    )

    ax.text(
        content_x + content_w - 0.15,
        attention_y + 0.25,
        "View only urgent",
        ha="right", va="center",
        fontsize=5,
        color=C["accent_blue"],
        fontweight="bold",
        zorder=3,
    )

    # ===================================================
    # CLIENT TABLE
    # ===================================================

    table_top = attention_y - 0.2
    table_x = content_x

    # Column definitions
    columns = [
        ("", 0.5),
        ("Client", 4.5),
        ("Tier", 1.2),
        ("TRV", 2.0),
        ("Health", 1.2),
        ("Signals", 1.2),
        ("Domains", 1.8),
        ("Top Signal", 5.5),
        ("Shadow Gaps", 1.6),
        ("Cross-Sell", 2.2),
        ("Last Contact", 1.8),
        ("Trend (90d)", 2.2),
        ("Actions", 2.5),
    ]

    # Column header
    header_h = 0.45

    draw_box(
        ax, table_x, table_top - header_h,
        content_w, header_h,
        C["card_header"],
        corner_radius=0.04,
    )

    col_x = table_x + 0.1

    for clabel, cwidth in columns:
        ax.text(
            col_x + 0.1,
            table_top - header_h / 2,
            clabel,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_muted"],
            zorder=3,
        )
        col_x += cwidth

    # Client rows
    clients = [
        {
            "name": "Dangote Industries",
            "id": "GLD-D4N6-0T3",
            "tier": "Platinum",
            "tier_color": C["platinum"],
            "trv": "R4.2B",
            "health": "AT_RISK",
            "health_label": "At Risk",
            "signals": 4,
            "signal_urgent": True,
            "domains": ["CIB", "FX", "INS", "CELL"],
            "top_signal": "Expansion into Ghana (R120M)",
            "top_signal_color": C["accent_red"],
            "shadow_gaps": 8,
            "shadow_opp": "R24M",
            "cross_sell": "CRITICAL",
            "cross_sell_value": "R151M",
            "last_contact": "12 Jun",
            "days_ago": 2,
            "trend": [3.1, 3.3, 3.5, 3.8, 3.7, 4.0, 4.2],
            "trend_dir": "up",
            "urgent": True,
        },
        {
            "name": "Shoprite Holdings",
            "id": "GLD-SH0P-R1T",
            "tier": "Platinum",
            "tier_color": C["platinum"],
            "trv": "R2.8B",
            "health": "HEALTHY",
            "health_label": "Healthy",
            "signals": 2,
            "signal_urgent": False,
            "domains": ["CIB", "FX", "INS", "CELL", "PBB"],
            "top_signal": "MZ/TZ insurance gaps (R12M)",
            "top_signal_color": C["accent_amber"],
            "shadow_gaps": 3,
            "shadow_opp": "R8M",
            "cross_sell": "HIGH",
            "cross_sell_value": "R89M",
            "last_contact": "10 Jun",
            "days_ago": 4,
            "trend": [2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8],
            "trend_dir": "up",
            "urgent": False,
        },
        {
            "name": "MTN Group",
            "id": "GLD-MTN0-GRP",
            "tier": "Platinum",
            "tier_color": C["platinum"],
            "trv": "R2.1B",
            "health": "HEALTHY",
            "health_label": "Healthy",
            "signals": 1,
            "signal_urgent": False,
            "domains": ["CIB", "FX", "CELL"],
            "top_signal": "FX hedging opportunity (R8M)",
            "top_signal_color": C["accent_amber"],
            "shadow_gaps": 2,
            "shadow_opp": "R5M",
            "cross_sell": "HIGH",
            "cross_sell_value": "R74M",
            "last_contact": "8 Jun",
            "days_ago": 6,
            "trend": [1.8, 1.9, 1.9, 2.0, 2.0, 2.1, 2.1],
            "trend_dir": "stable",
            "urgent": False,
        },
        {
            "name": "Sasol Ltd",
            "id": "GLD-SAS0-LTD",
            "tier": "Platinum",
            "tier_color": C["platinum"],
            "trv": "R1.9B",
            "health": "AT_RISK",
            "health_label": "At Risk",
            "signals": 3,
            "signal_urgent": True,
            "domains": ["CIB", "FX", "INS"],
            "top_signal": "NGN devaluation impact (R92M)",
            "top_signal_color": C["accent_red"],
            "shadow_gaps": 5,
            "shadow_opp": "R18M",
            "cross_sell": "CRITICAL",
            "cross_sell_value": "R62M",
            "last_contact": "5 Jun",
            "days_ago": 9,
            "trend": [2.1, 2.0, 1.9, 1.9, 1.8, 1.9, 1.9],
            "trend_dir": "down",
            "urgent": True,
        },
        {
            "name": "Anglo American SA",
            "id": "GLD-ANGL-0SA",
            "tier": "Gold",
            "tier_color": C["gold_tier"],
            "trv": "R890M",
            "health": "CRITICAL",
            "health_label": "Critical",
            "signals": 5,
            "signal_urgent": True,
            "domains": ["CIB", "FX"],
            "top_signal": "Relationship attrition (R890M)",
            "top_signal_color": C["accent_red"],
            "shadow_gaps": 6,
            "shadow_opp": "R32M",
            "cross_sell": "CRITICAL",
            "cross_sell_value": "R48M",
            "last_contact": "28 May",
            "days_ago": 17,
            "trend": [1.2, 1.1, 1.0, 0.95, 0.92, 0.90, 0.89],
            "trend_dir": "down",
            "urgent": True,
        },
        {
            "name": "Vodacom Tanzania",
            "id": "GLD-V0DA-TZA",
            "tier": "Gold",
            "tier_color": C["gold_tier"],
            "trv": "R420M",
            "health": "HEALTHY",
            "health_label": "Healthy",
            "signals": 1,
            "signal_urgent": False,
            "domains": ["CIB", "FX", "CELL", "PBB"],
            "top_signal": "Payroll capture (R2.4M/yr)",
            "top_signal_color": C["accent_teal"],
            "shadow_gaps": 2,
            "shadow_opp": "R4M",
            "cross_sell": "STANDARD",
            "cross_sell_value": "R41M",
            "last_contact": "11 Jun",
            "days_ago": 3,
            "trend": [0.38, 0.39, 0.40, 0.40, 0.41, 0.42, 0.42],
            "trend_dir": "up",
            "urgent": False,
        },
        {
            "name": "Zambia Sugar",
            "id": "GLD-ZMSG-001",
            "tier": "Gold",
            "tier_color": C["gold_tier"],
            "trv": "R380M",
            "health": "AT_RISK",
            "health_label": "At Risk",
            "signals": 2,
            "signal_urgent": True,
            "domains": ["CIB", "FX"],
            "top_signal": "Unhedged ZMW (R180M exp)",
            "top_signal_color": C["accent_amber"],
            "shadow_gaps": 4,
            "shadow_opp": "R12M",
            "cross_sell": "HIGH",
            "cross_sell_value": "R35M",
            "last_contact": "1 Jun",
            "days_ago": 13,
            "trend": [0.42, 0.40, 0.39, 0.38, 0.38, 0.38, 0.38],
            "trend_dir": "down",
            "urgent": True,
        },
        {
            "name": "Tullow Oil Ghana",
            "id": "GLD-TLGH-001",
            "tier": "Gold",
            "tier_color": C["gold_tier"],
            "trv": "R340M",
            "health": "HEALTHY",
            "health_label": "Healthy",
            "signals": 1,
            "signal_urgent": False,
            "domains": ["CIB", "FX", "INS"],
            "top_signal": "Seasonal: cocoa peak in 8w",
            "top_signal_color": C["accent_teal"],
            "shadow_gaps": 1,
            "shadow_opp": "R2M",
            "cross_sell": "STANDARD",
            "cross_sell_value": "R32M",
            "last_contact": "9 Jun",
            "days_ago": 5,
            "trend": [0.30, 0.31, 0.32, 0.33, 0.34, 0.34, 0.34],
            "trend_dir": "up",
            "urgent": False,
        },
        {
            "name": "Equity Bank Kenya",
            "id": "GLD-EQKE-001",
            "tier": "Silver",
            "tier_color": C["silver_tier"],
            "trv": "R240M",
            "health": "HEALTHY",
            "health_label": "Healthy",
            "signals": 0,
            "signal_urgent": False,
            "domains": ["CIB", "FX"],
            "top_signal": "No active signals",
            "top_signal_color": C["text_muted"],
            "shadow_gaps": 3,
            "shadow_opp": "R6M",
            "cross_sell": "STANDARD",
            "cross_sell_value": "R28M",
            "last_contact": "7 Jun",
            "days_ago": 7,
            "trend": [0.22, 0.23, 0.23, 0.24, 0.24, 0.24, 0.24],
            "trend_dir": "stable",
            "urgent": False,
        },
        {
            "name": "Illovo Sugar",
            "id": "GLD-ILLV-001",
            "tier": "Gold",
            "tier_color": C["gold_tier"],
            "trv": "R220M",
            "health": "HEALTHY",
            "health_label": "Healthy",
            "signals": 1,
            "signal_urgent": False,
            "domains": ["CIB", "FX", "INS"],
            "top_signal": "MZ/ZM seasonal WC timing",
            "top_signal_color": C["accent_teal"],
            "shadow_gaps": 1,
            "shadow_opp": "R3M",
            "cross_sell": "STANDARD",
            "cross_sell_value": "R24M",
            "last_contact": "6 Jun",
            "days_ago": 8,
            "trend": [0.20, 0.20, 0.21, 0.21, 0.22, 0.22, 0.22],
            "trend_dir": "stable",
            "urgent": False,
        },
        {
            "name": "Lafarge Africa",
            "id": "GLD-LAFR-001",
            "tier": "Gold",
            "tier_color": C["gold_tier"],
            "trv": "R180M",
            "health": "AT_RISK",
            "health_label": "At Risk",
            "signals": 2,
            "signal_urgent": True,
            "domains": ["CIB", "FX"],
            "top_signal": "NG leakage: 8% FX capture",
            "top_signal_color": C["accent_red"],
            "shadow_gaps": 5,
            "shadow_opp": "R14M",
            "cross_sell": "CRITICAL",
            "cross_sell_value": "R22M",
            "last_contact": "20 May",
            "days_ago": 25,
            "trend": [0.22, 0.21, 0.20, 0.19, 0.18, 0.18, 0.18],
            "trend_dir": "down",
            "urgent": True,
        },
        {
            "name": "Tiger Brands",
            "id": "GLD-TIGB-001",
            "tier": "Gold",
            "tier_color": C["gold_tier"],
            "trv": "R160M",
            "health": "HEALTHY",
            "health_label": "Healthy",
            "signals": 0,
            "signal_urgent": False,
            "domains": ["CIB", "FX", "INS", "PBB"],
            "top_signal": "No active signals",
            "top_signal_color": C["text_muted"],
            "shadow_gaps": 1,
            "shadow_opp": "R1M",
            "cross_sell": "STANDARD",
            "cross_sell_value": "R18M",
            "last_contact": "12 Jun",
            "days_ago": 2,
            "trend": [0.15, 0.15, 0.16, 0.16, 0.16, 0.16, 0.16],
            "trend_dir": "stable",
            "urgent": False,
        },
    ]

    row_h = 0.62
    row_start_y = table_top - header_h - 0.05

    for ri, client in enumerate(clients):

        ry = row_start_y - ri * (row_h + 0.04)

        # Row background
        row_bg = (
            C["row_urgent"]
            if client["urgent"]
            else C["row_even"]
            if ri % 2 == 0
            else C["row_odd"]
        )

        row_border = (
            C["accent_red"]
            if client["urgent"]
            else C["card_border"]
        )

        draw_box(
            ax, table_x, ry - row_h,
            content_w, row_h,
            row_bg,
            corner_radius=0.03,
            border_color=row_border,
            border_width=(
                0.8 if client["urgent"] else 0.2
            ),
        )

        # Build column positions
        col_x = table_x + 0.1

        # Column: Urgency indicator
        if client["urgent"]:
            for ring in range(2):
                r = 0.05 + ring * 0.025
                a = 0.5 - ring * 0.15
                dot = Circle(
                    (col_x + 0.15, ry - row_h / 2),
                    r,
                    facecolor=C["accent_red"],
                    edgecolor="none",
                    alpha=a,
                    zorder=5,
                )
                ax.add_patch(dot)

        col_x += columns[0][1]

        # Column: Client name + ID
        ax.text(
            col_x + 0.05,
            ry - row_h / 2 + 0.1,
            client["name"],
            ha="left", va="center",
            fontsize=5.5, fontweight="bold",
            color=C["text_primary"],
            zorder=3,
        )

        ax.text(
            col_x + 0.05,
            ry - row_h / 2 - 0.12,
            client["id"],
            ha="left", va="center",
            fontsize=3.5,
            color=C["text_muted"],
            fontfamily="monospace",
            zorder=3,
        )

        col_x += columns[1][1]

        # Column: Tier
        draw_box(
            ax,
            col_x, ry - row_h / 2 - 0.1,
            0.9, 0.22,
            client["tier_color"],
            text_lines=[client["tier"]],
            text_color="#FFFFFF",
            fontsize=4,
            corner_radius=0.03,
        )

        col_x += columns[2][1]

        # Column: TRV
        ax.text(
            col_x + 0.05,
            ry - row_h / 2,
            client["trv"],
            ha="left", va="center",
            fontsize=6, fontweight="bold",
            color=C["accent_blue"],
            zorder=3,
        )

        col_x += columns[3][1]

        # Column: Health
        draw_health_dot(
            ax,
            col_x + 0.2,
            ry - row_h / 2,
            client["health"],
        )

        ax.text(
            col_x + 0.4,
            ry - row_h / 2,
            client["health_label"],
            ha="left", va="center",
            fontsize=4.5,
            color={
                "Healthy": C["health_good"],
                "At Risk": C["health_warning"],
                "Critical": C["health_critical"],
            }.get(
                client["health_label"],
                C["text_muted"],
            ),
            zorder=3,
        )

        col_x += columns[4][1]

        # Column: Signals
        sig_count = client["signals"]
        sig_color = (
            C["accent_red"]
            if sig_count >= 3
            else C["accent_amber"]
            if sig_count >= 1
            else C["text_muted"]
        )

        if sig_count > 0:
            draw_box(
                ax,
                col_x + 0.1,
                ry - row_h / 2 - 0.12,
                0.4, 0.24,
                sig_color,
                text_lines=[str(sig_count)],
                text_color="#FFFFFF",
                fontsize=5,
                corner_radius=0.04,
            )
        else:
            ax.text(
                col_x + 0.3,
                ry - row_h / 2,
                "0",
                ha="center", va="center",
                fontsize=5,
                color=C["text_muted"],
                zorder=3,
            )

        col_x += columns[5][1]

        # Column: Domains
        draw_domain_dots(
            ax,
            col_x + 0.1,
            ry - row_h / 2,
            client["domains"],
        )

        col_x += columns[6][1]

        # Column: Top Signal
        ax.text(
            col_x + 0.05,
            ry - row_h / 2,
            client["top_signal"],
            ha="left", va="center",
            fontsize=4.5,
            color=client["top_signal_color"],
            fontweight=(
                "bold"
                if client["signal_urgent"]
                else "normal"
            ),
            zorder=3,
        )

        col_x += columns[7][1]

        # Column: Shadow Gaps
        gap_color = (
            C["accent_red"]
            if client["shadow_gaps"] >= 5
            else C["accent_amber"]
            if client["shadow_gaps"] >= 3
            else C["accent_teal"]
        )

        ax.text(
            col_x + 0.05,
            ry - row_h / 2 + 0.08,
            str(client["shadow_gaps"]),
            ha="left", va="center",
            fontsize=5.5, fontweight="bold",
            color=gap_color,
            zorder=3,
        )

        ax.text(
            col_x + 0.4,
            ry - row_h / 2 + 0.08,
            client["shadow_opp"],
            ha="left", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

        col_x += columns[8][1]

        # Column: Cross-Sell
        cs_colors = {
            "CRITICAL": C["accent_red"],
            "HIGH": C["accent_amber"],
            "STANDARD": C["accent_teal"],
        }

        cs_c = cs_colors.get(
            client["cross_sell"], C["text_muted"]
        )

        ax.text(
            col_x + 0.05,
            ry - row_h / 2 + 0.08,
            client["cross_sell"],
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=cs_c,
            zorder=3,
        )

        ax.text(
            col_x + 0.05,
            ry - row_h / 2 - 0.1,
            client["cross_sell_value"],
            ha="left", va="center",
            fontsize=4.5,
            color=C["accent_green"],
            fontweight="bold",
            zorder=3,
        )

        col_x += columns[9][1]

        # Column: Last Contact
        contact_color = (
            C["accent_red"]
            if client["days_ago"] > 14
            else C["accent_amber"]
            if client["days_ago"] > 7
            else C["text_secondary"]
        )

        ax.text(
            col_x + 0.05,
            ry - row_h / 2 + 0.08,
            client["last_contact"],
            ha="left", va="center",
            fontsize=4.5,
            color=contact_color,
            zorder=3,
        )

        ax.text(
            col_x + 0.05,
            ry - row_h / 2 - 0.1,
            f"{client['days_ago']}d ago",
            ha="left", va="center",
            fontsize=3.5,
            color=C["text_muted"],
            zorder=3,
        )

        col_x += columns[10][1]

        # Column: Trend sparkline
        trend_color = {
            "up": C["accent_green"],
            "down": C["accent_red"],
            "stable": C["accent_blue"],
        }.get(client["trend_dir"], C["text_muted"])

        draw_sparkline(
            ax,
            col_x + 0.1,
            ry - row_h + 0.1,
            1.5, row_h - 0.2,
            client["trend"],
            trend_color,
        )

        col_x += columns[11][1]

        # Column: Actions
        draw_box(
            ax,
            col_x, ry - row_h / 2 - 0.1,
            1.0, 0.24,
            C["accent_blue"],
            text_lines=["View"],
            text_color="#FFFFFF",
            fontsize=4,
            corner_radius=0.03,
        )

        draw_box(
            ax,
            col_x + 1.1, ry - row_h / 2 - 0.1,
            1.0, 0.24,
            C["card_bg"],
            text_lines=["Brief"],
            text_color=C["accent_blue"],
            fontsize=4,
            corner_radius=0.03,
            border_color=C["accent_blue"],
            border_width=0.5,
        )

    # ===================================================
    # TABLE FOOTER
    # ===================================================

    footer_y = (
        row_start_y
        - len(clients) * (row_h + 0.04)
        - 0.15
    )

    draw_box(
        ax, table_x, footer_y - 0.45,
        content_w, 0.45,
        C["card_header"],
        corner_radius=0.04,
    )

    ax.text(
        table_x + 0.15, footer_y - 0.22,
        f"Showing {len(clients)} of 48 clients  |  "
        f"Sorted by urgency (signals + risk)  |  "
        f"Total portfolio TRV: R18.4B  |  "
        f"Total cross-sell opportunity: R2.1B  |  "
        f"Total shadow opportunity: R142M",
        ha="left", va="center",
        fontsize=5,
        color=C["text_muted"],
        zorder=3,
    )

    # Pagination
    ax.text(
        table_x + content_w - 0.15,
        footer_y - 0.22,
        "1  2  3  4  >",
        ha="right", va="center",
        fontsize=5.5,
        color=C["accent_blue"],
        fontweight="bold",
        zorder=3,
    )

    # ===================================================
    # BOTTOM STATUS BAR
    # ===================================================

    draw_box(
        ax, 0, 0, 34, 0.5,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    ax.text(
        0.5, 0.25,
        "AfriFlow Portfolio  |  "
        "48 clients  |  "
        "7 need attention  |  "
        "23 active signals  |  "
        "R18.4B total relationship value  |  "
        "Last entity resolution: 07:00 UTC  |  "
        "All 5 domains current",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    ax.text(
        33.5, 0.25,
        "CONCEPT MOCKUP",
        ha="right", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["text_muted"],
        zorder=3,
    )

    # ===================================================
    # SAVE
    # ===================================================

    output_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    output_path = os.path.join(
        output_dir, "portfolio_overview.png"
    )
    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
        pad_inches=0.1,
        facecolor=C["bg"],
        edgecolor="none",
    )
    print(
        f"Portfolio Overview saved to: "
        f"{output_path}"
    )

    small_path = os.path.join(
        output_dir,
        "portfolio_overview_small.png",
    )
    fig.savefig(
        small_path,
        dpi=100,
        bbox_inches="tight",
        pad_inches=0.1,
        facecolor=C["bg"],
        edgecolor="none",
    )
    print(f"Small version: {small_path}")

    plt.close(fig)


# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":

    print(
        "Generating AfriFlow Portfolio "
        "Overview..."
    )
    print()

    generate_portfolio_overview()

    print()
    print("Portfolio Overview generated.")
    print(
        "Files ready for embedding in "
        "README.md and documentation."
    )
