# diagrams/generate_lekgotla_analytics.py

"""
AfriFlow Lekgotla Analytics Dashboard

We generate a high fidelity mockup of the Lekgotla
Analytics screen that Suri Sobrun would present to
ExCo and HR leadership to demonstrate the return on
institutional knowledge sharing.

This screen answers the executive questions:

  "Is the knowledge sharing platform working?"
  "Which insights are generating revenue?"
  "Where are the knowledge gaps?"
  "Who are our most valuable knowledge contributors?"
  "Are new RMs onboarding faster because of Lekgotla?"

Usage:
    python diagrams/generate_lekgotla_analytics.py

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
from matplotlib.patches import Wedge
import numpy as np
import os


# -------------------------------------------------------
# Colour palette
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
    "accent_lime": "#9CCC65",
    "accent_pink": "#EC407A",
    "cib": "#1565C0",
    "forex": "#0D47A1",
    "insurance": "#2E7D32",
    "cell": "#F9A825",
    "pbb": "#C62828",
    "topbar_bg": "#0D1824",
    "divider": "#1E3048",
    "progress_bg": "#152238",
    "positive": "#43A047",
    "negative": "#E53935",
    "sb_blue": "#003DA5",
    "lekgotla_gold": "#D4A017",
    "lekgotla_bg": "#1A1A0A",
    "knowledge_card": "#2E4A1A",
    "knowledge_border": "#4CAF50",
    "thread_bg": "#1A2A3A",
    "contributor_1": "#FFD700",
    "contributor_2": "#C0C0C0",
    "contributor_3": "#CD7F32",
    "network_node": "#1976D2",
    "network_edge": "#1976D240",
    "heatmap_0": "#152238",
    "heatmap_1": "#1A3A26",
    "heatmap_2": "#2A5A36",
    "heatmap_3": "#4A8A4F",
    "heatmap_4": "#7BC67F",
    "heatmap_5": "#A5D6A7",
    "funnel_1": "#1976D2",
    "funnel_2": "#2196F3",
    "funnel_3": "#42A5F5",
    "funnel_4": "#64B5F6",
    "funnel_5": "#43A047",
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
    spacing = min(0.22, (h * 0.85) / max(n, 1))
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
    fill=True,
):
    """Draw a sparkline chart."""

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
        linewidth=1.0,
        zorder=5,
        solid_capstyle="round",
    )

    if fill:
        fill_xs = list(xs) + [xs[-1], xs[0]]
        fill_ys = list(ys) + [y, y]
        ax.fill(
            fill_xs, fill_ys,
            color=color,
            alpha=0.08,
            zorder=4,
        )

    ax.plot(
        xs[-1], ys[-1], "o",
        color=color,
        markersize=2.5,
        zorder=6,
    )


def draw_progress_bar(
    ax, x, y, w, h, pct, color,
    bg=None, label_right=None,
):
    """Draw a horizontal progress bar."""

    bg_c = bg if bg else C["progress_bg"]
    draw_box(
        ax, x, y, w, h, bg_c,
        corner_radius=0.02,
    )
    fill_w = w * min(pct / 100, 1.0)
    if fill_w > 0.03:
        draw_box(
            ax, x, y, fill_w, h, color,
            corner_radius=0.02,
        )

    if label_right:
        ax.text(
            x + w + 0.1, y + h / 2,
            label_right,
            ha="left", va="center",
            fontsize=4.5,
            color=color,
            fontweight="bold",
            zorder=5,
        )


def draw_donut(
    ax, cx, cy, r_outer, r_inner,
    segments, start_angle=90,
):
    """Draw a donut chart."""

    total = sum(s[1] for s in segments)
    current = start_angle

    for label, value, color in segments:
        angle = (
            (value / total) * 360
            if total > 0
            else 0
        )
        wedge = Wedge(
            (cx, cy), r_outer,
            current, current + angle,
            facecolor=color,
            edgecolor=C["card_bg"],
            linewidth=1.0,
            zorder=4,
        )
        ax.add_patch(wedge)
        current += angle

    inner = Circle(
        (cx, cy), r_inner,
        facecolor=C["card_bg"],
        edgecolor="none",
        zorder=5,
    )
    ax.add_patch(inner)


def draw_bar_horizontal(
    ax, x, y, max_w, h,
    value, max_val, color,
    label_left=None,
    label_right=None,
):
    """Draw a horizontal bar with labels."""

    bar_w = max_w * (value / max_val) if max_val > 0 else 0

    draw_box(
        ax, x, y, max_w, h,
        C["progress_bg"],
        corner_radius=0.02,
    )

    if bar_w > 0.03:
        draw_box(
            ax, x, y, bar_w, h,
            color,
            corner_radius=0.02,
        )

    if label_left:
        ax.text(
            x - 0.1, y + h / 2,
            label_left,
            ha="right", va="center",
            fontsize=4.5,
            color=C["text_primary"],
            zorder=3,
        )

    if label_right:
        ax.text(
            x + max_w + 0.1, y + h / 2,
            label_right,
            ha="left", va="center",
            fontsize=4.5,
            fontweight="bold",
            color=color,
            zorder=3,
        )


def draw_contributor_row(
    ax, x, y, w, h,
    rank, name, role, country,
    posts, cards, wins, revenue,
    medal_color,
):
    """Draw a contributor leaderboard row."""

    row_bg = (
        C["card_bg"]
        if rank % 2 == 1
        else C["card_header"]
    )

    draw_box(
        ax, x, y, w, h,
        row_bg,
        corner_radius=0.03,
        border_color=C["card_border"],
        border_width=0.3,
    )

    # Medal
    circle = Circle(
        (x + 0.3, y + h / 2), 0.15,
        facecolor=medal_color,
        edgecolor=C["card_bg"],
        linewidth=0.8,
        zorder=5,
    )
    ax.add_patch(circle)

    ax.text(
        x + 0.3, y + h / 2,
        str(rank),
        ha="center", va="center",
        fontsize=5, fontweight="bold",
        color="#1A1A1A" if rank <= 3 else "#FFFFFF",
        zorder=6,
    )

    # Name and role
    ax.text(
        x + 0.6, y + h / 2 + 0.1,
        name,
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    ax.text(
        x + 0.6, y + h / 2 - 0.12,
        f"{role}, {country}",
        ha="left", va="center",
        fontsize=4,
        color=C["text_muted"],
        zorder=3,
    )

    # Metrics columns
    col_x = [
        x + w * 0.42,
        x + w * 0.55,
        x + w * 0.68,
        x + w * 0.82,
    ]

    vals = [
        (str(posts), C["accent_blue"]),
        (str(cards), C["accent_green"]),
        (str(wins), C["accent_amber"]),
        (revenue, C["positive"]),
    ]

    for ci, (val, vc) in enumerate(vals):
        ax.text(
            col_x[ci], y + h / 2,
            val,
            ha="center", va="center",
            fontsize=5.5, fontweight="bold",
            color=vc,
            zorder=3,
        )


def draw_funnel_step(
    ax, x, y, w, h,
    label, value, pct, color,
    conversion_label=None,
):
    """Draw a single funnel step."""

    draw_box(
        ax, x, y, w, h,
        color,
        corner_radius=0.04,
        border_color=color,
        border_width=0.5,
        alpha=0.85,
    )

    ax.text(
        x + 0.15, y + h / 2,
        label,
        ha="left", va="center",
        fontsize=5,
        color="#FFFFFF",
        zorder=3,
    )

    ax.text(
        x + w - 0.15, y + h / 2,
        value,
        ha="right", va="center",
        fontsize=6, fontweight="bold",
        color="#FFFFFF",
        zorder=3,
    )

    if conversion_label:
        ax.text(
            x + w + 0.15, y + h / 2,
            conversion_label,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_muted"],
            zorder=3,
        )


def generate_lekgotla_analytics():
    """Generate the Lekgotla Analytics dashboard."""

    fig, ax = plt.subplots(1, 1, figsize=(36, 24))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 36)
    ax.set_ylim(0, 24)
    ax.set_aspect("equal")
    ax.axis("off")

    # ===================================================
    # TOP BAR
    # ===================================================

    draw_box(
        ax, 0, 23.0, 36, 1.0,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    # Lekgotla icon (tree symbol)
    draw_box(
        ax, 0.3, 23.2,
        0.6, 0.6,
        C["lekgotla_gold"],
        text_lines=["L"],
        text_color="#1A1A1A",
        fontsize=10,
        bold_first=True,
        corner_radius=0.08,
    )

    ax.text(
        1.1, 23.55,
        "Lekgotla Analytics",
        ha="left", va="center",
        fontsize=14, fontweight="bold",
        color=C["lekgotla_gold"],
        zorder=3,
    )

    ax.text(
        1.1, 23.22,
        "Collective Intelligence Performance",
        ha="left", va="center",
        fontsize=7,
        color=C["text_secondary"],
        zorder=3,
    )

    # Setswana subtitle
    ax.text(
        6.0, 23.22,
        "Ntlha ya Lekgotla: wisdom emerges "
        "from the conversation",
        ha="left", va="center",
        fontsize=5.5,
        color=C["text_muted"],
        fontstyle="italic",
        zorder=3,
    )

    # Period selector
    periods = [
        "30D", "90D", "6M", "YTD", "12M",
    ]
    for pi, period in enumerate(periods):
        px = 22.0 + pi * 1.0
        active = period == "12M"

        draw_box(
            ax, px, 23.25,
            0.8, 0.35,
            (
                C["lekgotla_gold"]
                if active
                else C["card_bg"]
            ),
            text_lines=[period],
            text_color=(
                "#1A1A1A"
                if active
                else C["text_muted"]
            ),
            fontsize=5.5,
            corner_radius=0.04,
            border_color=(
                C["lekgotla_gold"]
                if active
                else C["card_border"]
            ),
            border_width=0.5,
        )

    # Navigation breadcrumb
    ax.text(
        28.0, 23.5,
        "AfriFlow  >  Lekgotla  >  Analytics",
        ha="left", va="center",
        fontsize=5,
        color=C["text_muted"],
        zorder=3,
    )

    # Export button
    draw_box(
        ax, 33.5, 23.25,
        2.0, 0.4,
        C["accent_blue"],
        text_lines=["Export Report"],
        text_color="#FFFFFF",
        fontsize=5.5,
        corner_radius=0.04,
    )

    # ===================================================
    # ROW 1: HEADLINE METRICS (7 cards)
    # ===================================================

    row1_y = 21.3
    metric_h = 1.35
    metric_gap = 0.18

    headlines = [
        {
            "label": "TOTAL THREADS",
            "value": "2,847",
            "sub": "Active discussions",
            "trend": "+342",
            "spark": [
                180, 420, 680, 1020,
                1480, 1890, 2340, 2847,
            ],
            "color": C["accent_blue"],
        },
        {
            "label": "KNOWLEDGE CARDS",
            "value": "214",
            "sub": "Validated approaches",
            "trend": "+38",
            "spark": [
                12, 28, 45, 72,
                108, 142, 178, 214,
            ],
            "color": C["accent_green"],
        },
        {
            "label": "ACTIVE CONTRIBUTORS",
            "value": "187",
            "sub": "Of 242 practitioners",
            "trend": "77%",
            "spark": [
                45, 62, 78, 98,
                120, 145, 168, 187,
            ],
            "color": C["accent_teal"],
        },
        {
            "label": "REVENUE ATTRIBUTED",
            "value": "R892M",
            "sub": "From Lekgotla insights",
            "trend": "+R240M",
            "spark": [
                20, 85, 180, 310,
                440, 580, 720, 892,
            ],
            "color": C["positive"],
        },
        {
            "label": "AVG WIN RATE",
            "value": "64%",
            "sub": "On Knowledge Card approaches",
            "trend": "+8pp",
            "spark": [
                42, 45, 48, 52,
                55, 58, 61, 64,
            ],
            "color": C["accent_amber"],
        },
        {
            "label": "ONBOARDING TIME",
            "value": "4.2 mo",
            "sub": "New RM to first win",
            "trend": "-3.8 mo",
            "spark": [
                8.0, 7.5, 7.0, 6.2,
                5.8, 5.2, 4.8, 4.2,
            ],
            "color": C["accent_cyan"],
        },
        {
            "label": "KNOWLEDGE GAPS",
            "value": "12",
            "sub": "Unanswered challenges",
            "trend": "Action needed",
            "spark": None,
            "color": C["accent_red"],
        },
    ]

    metric_w = (
        (36 - 0.6 - (len(headlines) - 1) * metric_gap)
        / len(headlines)
    )

    for mi, m in enumerate(headlines):
        mx = 0.3 + mi * (metric_w + metric_gap)

        draw_box(
            ax, mx, row1_y,
            metric_w, metric_h,
            C["card_bg"],
            corner_radius=0.06,
            border_color=C["card_border"],
            border_width=0.5,
            shadow=True,
        )

        ax.text(
            mx + 0.12, row1_y + metric_h - 0.18,
            m["label"],
            ha="left", va="center",
            fontsize=4,
            color=C["text_secondary"],
            zorder=3,
        )

        ax.text(
            mx + 0.12,
            row1_y + metric_h - 0.5,
            m["value"],
            ha="left", va="center",
            fontsize=10, fontweight="bold",
            color=m["color"],
            zorder=3,
        )

        ax.text(
            mx + 0.12,
            row1_y + metric_h - 0.78,
            m["sub"],
            ha="left", va="center",
            fontsize=3.5,
            color=C["text_muted"],
            zorder=3,
        )

        trend_c = m["color"]
        if m["label"] == "ONBOARDING TIME":
            trend_c = C["positive"]
        elif m["label"] == "KNOWLEDGE GAPS":
            trend_c = C["accent_red"]

        ax.text(
            mx + metric_w - 0.12,
            row1_y + metric_h - 0.5,
            m["trend"],
            ha="right", va="center",
            fontsize=5.5, fontweight="bold",
            color=trend_c,
            zorder=3,
        )

        if m["spark"]:
            draw_sparkline(
                ax,
                mx + 0.08,
                row1_y + 0.05,
                metric_w - 0.16,
                metric_h * 0.18,
                m["spark"],
                m["color"],
            )

    # ===================================================
    # ROW 2: Four main panels
    # ===================================================

    row2_top = 20.9
    panel_gap = 0.2

    p1_w = 8.5
    p2_w = 9.5
    p3_w = 8.5
    p4_w = 8.5

    p1_x = 0.3
    p2_x = p1_x + p1_w + panel_gap
    p3_x = p2_x + p2_w + panel_gap
    p4_x = p3_x + p3_w + panel_gap

    panel_h = 9.0

    # ===================================================
    # PANEL 1: Knowledge Funnel + Win Rate by Signal
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
        "KNOWLEDGE CONVERSION FUNNEL",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Funnel steps
    funnel_steps = [
        (
            "Challenge posted",
            "2,847",
            "100%",
            C["funnel_1"],
            None,
        ),
        (
            "Received responses",
            "2,134",
            "75%",
            C["funnel_2"],
            "75% response rate",
        ),
        (
            "Upvoted to consensus",
            "892",
            "31%",
            C["funnel_3"],
            "42% consensus rate",
        ),
        (
            "Graduated to Knowledge Card",
            "214",
            "7.5%",
            C["funnel_4"],
            "24% graduation rate",
        ),
        (
            "Confirmed revenue win",
            "137",
            "4.8%",
            C["funnel_5"],
            "64% win rate",
        ),
    ]

    funnel_y = row2_top - 1.0
    funnel_h = 0.5
    funnel_gap = 0.12
    funnel_max_w = p1_w - 0.6

    for fi, (fl, fv, fp, fc, fconv) in enumerate(
        funnel_steps
    ):
        fy = funnel_y - fi * (funnel_h + funnel_gap)
        fw = funnel_max_w * (1 - fi * 0.12)
        fx = p1_x + 0.3 + (funnel_max_w - fw) / 2

        draw_funnel_step(
            ax, fx, fy - funnel_h,
            fw, funnel_h,
            fl, fv, fp, fc,
            fconv,
        )

    # Arrow between steps
    for fi in range(len(funnel_steps) - 1):
        fy1 = (
            funnel_y
            - fi * (funnel_h + funnel_gap)
            - funnel_h
        )
        fy2 = (
            funnel_y
            - (fi + 1) * (funnel_h + funnel_gap)
        )

        ax.annotate(
            "",
            xy=(
                p1_x + p1_w / 2,
                fy2,
            ),
            xytext=(
                p1_x + p1_w / 2,
                fy1,
            ),
            arrowprops=dict(
                arrowstyle="-|>",
                color=C["text_muted"],
                linewidth=0.8,
            ),
            zorder=3,
        )

    # Win rate by signal type (bottom half)
    wr_title_y = row2_top - panel_h + 4.5

    ax.text(
        p1_x + 0.15, wr_title_y,
        "WIN RATE BY SIGNAL TYPE",
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    signal_winrates = [
        ("Expansion", 72, 47, C["accent_green"]),
        ("Hedge Gap", 68, 156, C["accent_green"]),
        ("Leakage", 58, 89, C["accent_amber"]),
        ("Insurance Gap", 55, 112, C["accent_amber"]),
        ("Workforce", 51, 234, C["accent_amber"]),
        ("Supply Chain", 45, 23, C["accent_amber"]),
        ("Corridor P&L", 62, 78, C["accent_green"]),
    ]

    wr_y = wr_title_y - 0.4
    wr_spacing = 0.52
    bar_max = p1_w - 3.5

    for wi, (wname, wrate, wcount, wcolor) in enumerate(
        signal_winrates
    ):
        wy = wr_y - wi * wr_spacing

        ax.text(
            p1_x + 0.15, wy,
            wname,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_secondary"],
            zorder=3,
        )

        draw_progress_bar(
            ax,
            p1_x + 2.5, wy - 0.08,
            bar_max, 0.16,
            wrate, wcolor,
            label_right=f"{wrate}% ({wcount})",
        )

    # ===================================================
    # PANEL 2: Top Contributors Leaderboard
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
        "LEKGOTLA LEADERS",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["lekgotla_gold"],
        zorder=3,
    )

    ax.text(
        p2_x + p2_w - 0.15, row2_top - 0.25,
        "Top knowledge contributors",
        ha="right", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    # Column headers
    col_headers = [
        "Posts", "Cards", "Wins", "Revenue",
    ]
    col_fracs = [0.42, 0.55, 0.68, 0.82]

    for chi, ch in enumerate(col_headers):
        ax.text(
            p2_x + p2_w * col_fracs[chi],
            row2_top - 0.7,
            ch,
            ha="center", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_muted"],
            zorder=3,
        )

    contributors = [
        (
            1, "Sipho Mabena",
            "Senior RM", "ZA",
            142, 18, 12, "R124M",
            C["contributor_1"],
        ),
        (
            2, "Amina Okafor",
            "RM", "NG",
            128, 15, 9, "R98M",
            C["contributor_2"],
        ),
        (
            3, "David Mwangi",
            "FX Advisor", "KE",
            98, 12, 11, "R87M",
            C["contributor_3"],
        ),
        (
            4, "Fatima Al-Hassan",
            "FX Desk", "ZA",
            87, 14, 8, "R72M",
            C["accent_blue"],
        ),
        (
            5, "Chidi Emenike",
            "Compliance", "NG",
            76, 8, "N/A", "Trust",
            C["accent_blue"],
        ),
        (
            6, "Lucia Machava",
            "RM", "MZ",
            65, 6, 5, "R38M",
            C["accent_blue"],
        ),
        (
            7, "Thandiwe Nkosi",
            "RM", "ZA",
            58, 5, 7, "R42M",
            C["accent_blue"],
        ),
        (
            8, "Carlos Brito",
            "FX Advisor", "MZ",
            52, 7, 4, "R28M",
            C["accent_blue"],
        ),
        (
            9, "James Osei",
            "FX Advisor", "GH",
            48, 4, 6, "R35M",
            C["accent_blue"],
        ),
        (
            10, "Grace Akinola",
            "Insurance", "NG",
            45, 6, 3, "R22M",
            C["accent_blue"],
        ),
    ]

    row_h = 0.58
    start_y = row2_top - 1.0

    for ci, cont in enumerate(contributors):
        (
            rank, name, role, country,
            posts, cards, wins, revenue,
            medal,
        ) = cont

        ry = start_y - ci * (row_h + 0.06)

        draw_contributor_row(
            ax,
            p2_x + 0.1, ry - row_h,
            p2_w - 0.2, row_h,
            rank, name, role, country,
            posts, cards, wins, revenue,
            medal,
        )

    # Contribution distribution note
    ax.text(
        p2_x + 0.15,
        row2_top - panel_h + 0.55,
        "Top 10 contributors account for 42% "
        "of all Lekgotla content",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        fontstyle="italic",
        zorder=3,
    )

    ax.text(
        p2_x + 0.15,
        row2_top - panel_h + 0.25,
        "Chidi Emenike (Compliance, NG) prevented "
        "3 regulatory violations through early alerts",
        ha="left", va="center",
        fontsize=4.5,
        color=C["accent_amber"],
        fontweight="bold",
        zorder=3,
    )

    # ===================================================
    # PANEL 3: Country Knowledge Heatmap
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
        "KNOWLEDGE DENSITY BY COUNTRY",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Country knowledge data
    # [threads, cards, gaps, depth_score]
    countries_kd = [
        ("South Africa", "ZA", 820, 68, 1, 95),
        ("Nigeria", "NG", 580, 42, 2, 82),
        ("Kenya", "KE", 420, 35, 1, 78),
        ("Ghana", "GH", 280, 22, 2, 65),
        ("Tanzania", "TZ", 180, 14, 3, 48),
        ("Mozambique", "MZ", 145, 11, 2, 42),
        ("Zambia", "ZM", 120, 8, 2, 38),
        ("Angola", "AO", 85, 5, 4, 25),
        ("DRC", "CD", 62, 3, 5, 18),
        ("Uganda", "UG", 95, 6, 2, 35),
        ("Cote d'Ivoire", "CI", 30, 2, 4, 12),
        ("Cameroon", "CM", 18, 1, 3, 8),
        ("South Sudan", "SS", 12, 0, 5, 5),
    ]

    kd_y = row2_top - 0.8
    kd_spacing = 0.6
    kd_bar_x = p3_x + 2.8
    kd_bar_w = p3_w - 4.0

    # Column headers
    ax.text(
        p3_x + 0.15, kd_y + 0.2,
        "Country",
        ha="left", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["text_muted"],
    )

    ax.text(
        kd_bar_x + kd_bar_w / 2, kd_y + 0.2,
        "Knowledge Depth",
        ha="center", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["text_muted"],
    )

    ax.text(
        p3_x + p3_w - 0.4, kd_y + 0.2,
        "Gaps",
        ha="center", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["text_muted"],
    )

    for ki, (
        cname, ccode, threads, cards,
        gaps, depth
    ) in enumerate(countries_kd):

        ky = kd_y - ki * kd_spacing

        # Country label
        ax.text(
            p3_x + 0.15, ky - 0.05,
            f"{ccode}  {cname}",
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_primary"],
            zorder=3,
        )

        # Depth bar
        depth_color = (
            C["positive"]
            if depth >= 60
            else C["accent_amber"]
            if depth >= 30
            else C["accent_red"]
        )

        draw_progress_bar(
            ax,
            kd_bar_x, ky - 0.13,
            kd_bar_w, 0.16,
            depth, depth_color,
            label_right=f"{depth}%",
        )

        # Gap count
        gap_color = (
            C["positive"]
            if gaps <= 1
            else C["accent_amber"]
            if gaps <= 3
            else C["accent_red"]
        )

        ax.text(
            p3_x + p3_w - 0.4, ky - 0.05,
            str(gaps),
            ha="center", va="center",
            fontsize=5.5, fontweight="bold",
            color=gap_color,
            zorder=3,
        )

    # Bottom insight
    draw_box(
        ax,
        p3_x + 0.15,
        row2_top - panel_h + 0.3,
        p3_w - 0.3, 0.8,
        "#2A1A1A",
        corner_radius=0.06,
        border_color=C["accent_red"],
        border_width=0.8,
    )

    ax.text(
        p3_x + 0.3,
        row2_top - panel_h + 0.85,
        "KNOWLEDGE GAPS REQUIRING ACTION",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["accent_red"],
        zorder=3,
    )

    ax.text(
        p3_x + 0.3,
        row2_top - panel_h + 0.55,
        "Angola (4 gaps), DRC (5 gaps), "
        "Cote d'Ivoire (4 gaps), "
        "South Sudan (5 gaps)",
        ha="left", va="center",
        fontsize=4.5,
        color=C["accent_amber"],
        zorder=3,
    )

    # ===================================================
    # PANEL 4: Cross-Border Knowledge Flow + Themes
    # ===================================================

    draw_box(
        ax, p4_x, row2_top - panel_h,
        p4_w, panel_h,
        C["card_bg"],
        corner_radius=0.08,
        border_color=C["card_border"],
        border_width=0.5,
        shadow=True,
    )

    draw_box(
        ax, p4_x, row2_top - 0.5,
        p4_w, 0.5,
        C["card_header"],
        corner_radius=0.06,
    )

    ax.text(
        p4_x + 0.15, row2_top - 0.25,
        "KNOWLEDGE FLOW AND THEMES",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Cross-border sharing network
    ax.text(
        p4_x + 0.15, row2_top - 0.75,
        "CROSS-BORDER KNOWLEDGE SHARING",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_cyan"],
        zorder=3,
    )

    # Simplified network visualisation
    network_cx = p4_x + p4_w / 2
    network_cy = row2_top - 3.0
    network_r = 1.8

    network_nodes = [
        ("ZA", 0, 1.8, 0.35, 820),
        ("NG", 60, 1.8, 0.30, 580),
        ("KE", 120, 1.8, 0.25, 420),
        ("GH", 180, 1.5, 0.20, 280),
        ("TZ", 240, 1.5, 0.18, 180),
        ("MZ", 300, 1.5, 0.16, 145),
    ]

    node_positions = {}

    for nname, angle, nr, nsize, ncount in network_nodes:
        rad = np.radians(angle)
        nx = network_cx + nr * np.cos(rad)
        ny = network_cy + nr * np.sin(rad)
        node_positions[nname] = (nx, ny)

        circle = Circle(
            (nx, ny), nsize,
            facecolor=C["network_node"],
            edgecolor=C["accent_cyan"],
            linewidth=1.0,
            alpha=0.8,
            zorder=5,
        )
        ax.add_patch(circle)

        ax.text(
            nx, ny,
            nname,
            ha="center", va="center",
            fontsize=5, fontweight="bold",
            color="#FFFFFF",
            zorder=6,
        )

    # Network edges (knowledge flows)
    edges = [
        ("ZA", "NG", 2.0),
        ("ZA", "KE", 1.8),
        ("ZA", "GH", 1.2),
        ("NG", "GH", 1.5),
        ("KE", "TZ", 1.4),
        ("ZA", "MZ", 0.8),
        ("KE", "NG", 0.6),
        ("MZ", "TZ", 0.5),
    ]

    for n1, n2, weight in edges:
        x1, y1 = node_positions[n1]
        x2, y2 = node_positions[n2]

        ax.plot(
            [x1, x2], [y1, y2],
            color=C["network_edge"],
            linewidth=weight,
            zorder=3,
        )

    ax.text(
        network_cx,
        network_cy - 2.3,
        "Node size = thread volume. "
        "Line thickness = knowledge flow.",
        ha="center", va="center",
        fontsize=4,
        color=C["text_muted"],
    )

    # Trending themes
    themes_y = row2_top - 5.8

    ax.text(
        p4_x + 0.15, themes_y + 0.3,
        "TRENDING THEMES (30 DAYS)",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_amber"],
        zorder=3,
    )

    themes = [
        ("#bundling", 89, C["accent_green"],
         "Bundle pricing wins. Most discussed."),
        ("#ghana-expansion", 67, C["accent_blue"],
         "Driven by 23 new expansion signals."),
        ("#ngn-regulation", 54, C["accent_red"],
         "CBN repatriation rule changes."),
        ("#fx-pricing", 48, C["accent_amber"],
         "Competitive pricing conversations."),
        ("#seasonal-cocoa", 42, C["accent_teal"],
         "Preparing for Oct-Dec harvest."),
        ("#momo-signals", 38, C["cell"],
         "MoMo patterns as credit signals."),
        ("#insurance-timing", 35, C["insurance"],
         "When to introduce coverage."),
        ("#onboarding-tips", 28, C["accent_cyan"],
         "New RM quick-start guides."),
    ]

    theme_y = themes_y - 0.1
    theme_spacing = 0.42

    for ti, (tag, count, tcolor, tdesc) in enumerate(
        themes
    ):
        ty = theme_y - ti * theme_spacing

        # Tag badge
        tag_w = len(tag) * 0.12 + 0.3

        draw_box(
            ax,
            p4_x + 0.15, ty - 0.12,
            tag_w, 0.28,
            tcolor,
            text_lines=[tag],
            text_color="#FFFFFF",
            fontsize=4.5,
            corner_radius=0.04,
            alpha=0.85,
        )

        # Count
        ax.text(
            p4_x + 0.2 + tag_w + 0.1,
            ty + 0.02,
            f"{count} posts",
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=tcolor,
            zorder=3,
        )

        # Description
        ax.text(
            p4_x + 0.2 + tag_w + 1.3,
            ty + 0.02,
            tdesc,
            ha="left", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

    # ===================================================
    # ROW 3: Bottom panels
    # ===================================================

    row3_top = row2_top - panel_h - 0.2
    row3_h = 4.8

    # Bottom left: Top Knowledge Cards by Impact
    bl_w = 17.5

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
        "HIGHEST IMPACT KNOWLEDGE CARDS",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["knowledge_border"],
        zorder=3,
    )

    top_cards = [
        (
            "KC-GH-EXPANSION-001",
            "Bundle pricing for Ghana expansion",
            "3 contributors",
            "14 RMs used",
            "64% win rate",
            "R155M",
            "4 months",
        ),
        (
            "KC-NG-FX-REPAT-2025",
            "CBN repatriation rule response",
            "2 contributors",
            "23 RMs notified",
            "Compliance",
            "R0 (risk)",
            "1 week",
        ),
        (
            "KC-KE-INS-BUNDLE",
            "Insurance + FX bundle for East Africa",
            "5 contributors",
            "8 RMs used",
            "72% win rate",
            "R89M",
            "6 months",
        ),
        (
            "KC-ZM-SEASONAL-CU",
            "Copper season working capital timing",
            "3 contributors",
            "6 RMs used",
            "83% win rate",
            "R42M",
            "3 months",
        ),
        (
            "KC-MZ-MOMO-SUPPLY",
            "MoMo supplier health scoring",
            "4 contributors",
            "5 RMs used",
            "60% win rate",
            "R28M",
            "2 months",
        ),
    ]

    kc_cols = [
        "Card ID", "Title", "Contributors",
        "Used By", "Win Rate", "Revenue", "Age",
    ]
    kc_col_x = [
        0.45, 2.8, 8.0, 10.0,
        11.8, 13.5, 15.2,
    ]

    for hi, header in enumerate(kc_cols):
        ax.text(
            kc_col_x[hi], row3_top - 0.75,
            header,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_muted"],
            zorder=3,
        )

    kc_spacing = 0.7

    for kci, kc in enumerate(top_cards):
        (
            kc_id, kc_title, kc_contrib,
            kc_used, kc_win, kc_rev, kc_age,
        ) = kc

        ky = row3_top - 1.1 - kci * kc_spacing

        row_bg = (
            C["card_bg"]
            if kci % 2 == 0
            else C["card_header"]
        )

        draw_box(
            ax, 0.4, ky - 0.22,
            bl_w - 0.2, 0.55,
            row_bg,
            corner_radius=0.03,
            zorder=1,
        )

        # Knowledge Card icon
        draw_box(
            ax, 0.45, ky - 0.12,
            0.25, 0.3,
            C["knowledge_card"],
            text_lines=["KC"],
            text_color=C["knowledge_border"],
            fontsize=4,
            corner_radius=0.03,
            border_color=C["knowledge_border"],
            border_width=0.5,
        )

        vals = [
            (kc_id, C["knowledge_border"]),
            (kc_title, C["text_primary"]),
            (kc_contrib, C["text_secondary"]),
            (kc_used, C["accent_blue"]),
            (kc_win, C["accent_amber"]),
            (kc_rev, C["positive"]),
            (kc_age, C["text_muted"]),
        ]

        for vi, (vtext, vcolor) in enumerate(vals):
            vx = kc_col_x[vi]
            if vi == 0:
                vx = 0.8

            fs = 4.5
            fw = "bold" if vi in (0, 5) else "normal"
            if vi == 1:
                fs = 4.5
                fw = "bold"

            ax.text(
                vx, ky,
                vtext,
                ha="left", va="center",
                fontsize=fs, fontweight=fw,
                color=vcolor,
                zorder=3,
            )

    # Bottom right: Onboarding Acceleration
    br_x = 0.3 + bl_w + panel_gap
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
        "ONBOARDING ACCELERATION",
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["accent_cyan"],
        zorder=3,
    )

    # Before / After comparison
    ax.text(
        br_x + br_w / 2, row3_top - 0.8,
        "Time to First Win (New RMs)",
        ha="center", va="center",
        fontsize=6, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Before bar
    before_y = row3_top - 1.3
    bar_x = br_x + 2.5
    bar_w = br_w - 3.0

    ax.text(
        br_x + 0.15, before_y + 0.05,
        "Before Lekgotla",
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    draw_box(
        ax, bar_x, before_y - 0.1,
        bar_w, 0.25,
        C["accent_red"],
        corner_radius=0.03,
        alpha=0.7,
    )

    ax.text(
        bar_x + bar_w / 2, before_y + 0.02,
        "8.0 months average",
        ha="center", va="center",
        fontsize=5.5, fontweight="bold",
        color="#FFFFFF",
        zorder=3,
    )

    # After bar
    after_y = before_y - 0.55

    ax.text(
        br_x + 0.15, after_y + 0.05,
        "With Lekgotla",
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    after_w = bar_w * (4.2 / 8.0)

    draw_box(
        ax, bar_x, after_y - 0.1,
        after_w, 0.25,
        C["accent_green"],
        corner_radius=0.03,
    )

    ax.text(
        bar_x + after_w / 2, after_y + 0.02,
        "4.2 months",
        ha="center", va="center",
        fontsize=5.5, fontweight="bold",
        color="#FFFFFF",
        zorder=3,
    )

    # Reduction label
    ax.text(
        bar_x + after_w + 0.3, after_y + 0.02,
        "-47% reduction",
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["accent_green"],
        zorder=3,
    )

    # New RM performance table
    ax.text(
        br_x + 0.15, after_y - 0.6,
        "NEW RM COHORT PERFORMANCE",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    cohorts = [
        (
            "2024 Q1 (no Lekgotla)",
            "8.2 mo", "42%", "R12M",
            C["text_muted"],
        ),
        (
            "2024 Q2 (early Lekgotla)",
            "6.8 mo", "48%", "R18M",
            C["accent_amber"],
        ),
        (
            "2024 Q3 (active Lekgotla)",
            "5.1 mo", "56%", "R28M",
            C["accent_amber"],
        ),
        (
            "2024 Q4 (mature Lekgotla)",
            "4.2 mo", "64%", "R38M",
            C["accent_green"],
        ),
    ]

    coh_headers = [
        "Cohort", "Time to Win", "Win Rate",
        "First Year Rev",
    ]
    coh_x = [
        br_x + 0.15,
        br_x + br_w * 0.5,
        br_x + br_w * 0.65,
        br_x + br_w * 0.8,
    ]

    for chi, ch in enumerate(coh_headers):
        ax.text(
            coh_x[chi], after_y - 0.9,
            ch,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_muted"],
            zorder=3,
        )

    for coi, (
        cname, ctime, cwin, crev, ccolor,
    ) in enumerate(cohorts):
        cy = after_y - 1.2 - coi * 0.4

        vals = [cname, ctime, cwin, crev]

        for vi, val in enumerate(vals):
            vc = ccolor if vi > 0 else C["text_secondary"]
            fw = "bold" if vi == 3 else "normal"

            ax.text(
                coh_x[vi], cy,
                val,
                ha="left", va="center",
                fontsize=4.5, fontweight=fw,
                color=vc,
                zorder=3,
            )

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
        "Lekgotla Analytics  |  "
        "2,847 threads  |  214 Knowledge Cards  |  "
        "187 active contributors  |  "
        "R892M attributed revenue  |  "
        "12 knowledge gaps requiring action  |  "
        "Ntlha ya Lekgotla: wisdom emerges from "
        "the conversation",
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

    output_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    output_path = os.path.join(
        output_dir, "lekgotla_analytics.png"
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
        f"Lekgotla Analytics saved to: {output_path}"
    )

    small_path = os.path.join(
        output_dir, "lekgotla_analytics_small.png"
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

    print(
        "Generating AfriFlow Lekgotla Analytics "
        "Dashboard..."
    )
    print()

    generate_lekgotla_analytics()

    print()
    print("Lekgotla Analytics dashboard generated.")
    print(
        "Files ready for embedding in README.md "
        "and the Strategic Analysis document."
    )
