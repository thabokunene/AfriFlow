# diagrams/generate_entity_resolution_console.py

"""
AfriFlow Entity Resolution Console

We generate a high fidelity mockup of the Data
Steward's entity resolution console where human
analysts verify, confirm, or reject low-confidence
client matches across Standard Bank's five domains.

This is the screen that prevents false matches from
destroying RM trust in the platform. Without it,
two different companies named "Africa Mining
Solutions" get merged into one golden record and
every downstream signal is wrong.

Entity resolution is not a one-time computation.
It is a continuous process with human oversight.
This screen is the human-in-the-loop.

Usage:
    python diagrams/generate_entity_resolution_console.py

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
    "accent_teal": "#009688",
    "accent_cyan": "#00ACC1",
    "cib": "#1565C0",
    "forex": "#0D47A1",
    "insurance": "#2E7D32",
    "cell": "#F9A825",
    "pbb": "#C62828",
    "topbar_bg": "#0D1824",
    "divider": "#1E3048",
    "sidebar_bg": "#141E2A",
    "sidebar_active": "#1A3A5C",
    "sidebar_text": "#8899AA",
    "progress_bg": "#152238",
    "positive": "#43A047",
    "negative": "#E53935",
    "warning": "#FF9800",
    "white": "#FFFFFF",
    "match_exact": "#43A047",
    "match_fuzzy": "#FF9800",
    "match_none": "#E53935",
    "match_missing": "#37474F",
    "field_match": "#1A2E1A",
    "field_mismatch": "#2E1A1A",
    "field_missing": "#1A1A2E",
    "field_highlight": "#2A4A2A",
    "conf_high": "#43A047",
    "conf_medium": "#FF9800",
    "conf_low": "#E53935",
    "queue_pending": "#1976D2",
    "queue_assigned": "#FF9800",
    "queue_confirmed": "#43A047",
    "queue_rejected": "#E53935",
    "golden_bg": "#0B5345",
    "golden_border": "#4CAF50",
    "golden_text": "#A3E4D7",
    "compare_left": "#1A2A4A",
    "compare_right": "#1A2A4A",
    "compare_border": "#2A4A6A",
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
    if shadow:
        s = FancyBboxPatch(
            (x + 0.03, y - 0.03), w, h,
            boxstyle=f"round,pad=0.02,rounding_size={corner_radius}",
            facecolor="#00000025", edgecolor="none",
            zorder=zorder - 1)
        ax.add_patch(s)
    edge = border_color if border_color else facecolor
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={corner_radius}",
        facecolor=facecolor, edgecolor=edge,
        linewidth=border_width, linestyle=linestyle,
        alpha=alpha, zorder=zorder)
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
        ax.text(tx, start_y - i * spacing, line,
                ha=text_ha, va="center", fontsize=fs,
                fontweight=weight, color=text_color,
                zorder=zorder + 1, fontfamily="sans-serif")


def draw_sparkline(ax, x, y, w, h, data, color):
    n = len(data)
    xs = np.linspace(x, x + w, n)
    d_min, d_max = min(data), max(data)
    d_range = d_max - d_min if d_max != d_min else 1
    ys = [y + (d - d_min) / d_range * h for d in data]
    ax.plot(xs, ys, color=color, linewidth=0.8,
            zorder=5, solid_capstyle="round")
    ax.fill_between(xs, [y] * n, ys, color=color,
                     alpha=0.06, zorder=4)
    ax.plot(xs[-1], ys[-1], "o", color=color,
            markersize=2, zorder=6)


def draw_progress_bar(ax, x, y, w, h, pct, color):
    draw_box(ax, x, y, w, h, C["progress_bg"],
             corner_radius=0.02)
    fill_w = w * min(pct / 100, 1.0)
    if fill_w > 0.03:
        draw_box(ax, x, y, fill_w, h, color,
                 corner_radius=0.02)


def draw_field_comparison(
    ax, x, y, w,
    field_name, left_value, right_value,
    match_status,
):
    """
    Draw a single field comparison row.
    match_status: 'exact', 'fuzzy', 'mismatch',
                  'missing_left', 'missing_right',
                  'missing_both'
    Returns height consumed.
    """
    row_h = 0.42

    status_config = {
        "exact": (C["field_match"], C["match_exact"], "EXACT"),
        "fuzzy": (C["field_highlight"], C["match_fuzzy"], "FUZZY"),
        "mismatch": (C["field_mismatch"], C["match_none"], "DIFF"),
        "missing_left": (C["field_missing"], C["match_missing"], "MISS L"),
        "missing_right": (C["field_missing"], C["match_missing"], "MISS R"),
        "missing_both": (C["field_missing"], C["match_missing"], "MISS"),
    }

    bg, indicator_c, indicator_label = status_config.get(
        match_status,
        (C["card_bg"], C["text_muted"], "?"),
    )

    # Row background
    draw_box(ax, x, y, w, row_h, bg,
             corner_radius=0.03,
             border_color=C["card_border"],
             border_width=0.3)

    # Field name
    ax.text(x + 0.15, y + row_h / 2,
            field_name,
            ha="left", va="center", fontsize=5,
            fontweight="bold", color=C["text_secondary"],
            zorder=3)

    # Left value
    left_x = x + 2.5
    left_w = (w - 5.0) / 2

    lv_color = C["text_primary"] if left_value else C["match_missing"]
    lv_text = left_value if left_value else "(empty)"

    ax.text(left_x, y + row_h / 2,
            lv_text, ha="left", va="center",
            fontsize=5,
            color=lv_color,
            fontfamily="monospace",
            fontstyle="italic" if not left_value else "normal",
            zorder=3)

    # Indicator
    ind_x = x + w / 2 - 0.4

    draw_box(ax, ind_x, y + 0.08,
             0.8, 0.26, indicator_c,
             text_lines=[indicator_label],
             text_color="#FFFFFF",
             fontsize=3.5, corner_radius=0.03)

    # Right value
    right_x = x + w / 2 + 0.6

    rv_color = C["text_primary"] if right_value else C["match_missing"]
    rv_text = right_value if right_value else "(empty)"

    ax.text(right_x, y + row_h / 2,
            rv_text, ha="left", va="center",
            fontsize=5,
            color=rv_color,
            fontfamily="monospace",
            fontstyle="italic" if not right_value else "normal",
            zorder=3)

    return row_h


def generate_entity_resolution_console():
    fig, ax = plt.subplots(1, 1, figsize=(36, 30))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 36)
    ax.set_ylim(0, 30)
    ax.set_aspect("equal")
    ax.axis("off")

    # ===================================================
    # TOP BAR
    # ===================================================
    draw_box(ax, 0, 29.0, 36, 1.0, C["topbar_bg"],
             corner_radius=0.0, border_color=C["divider"],
             border_width=0.5)

    ax.text(0.5, 29.6, "Entity Resolution Console",
            ha="left", va="center", fontsize=14,
            fontweight="bold", color=C["text_primary"],
            zorder=3)

    ax.text(0.5, 29.25,
            "Human-in-the-loop verification for "
            "cross-domain client matching. "
            "Matches below 90% confidence require "
            "analyst review.",
            ha="left", va="center", fontsize=6,
            color=C["text_secondary"], zorder=3)

    # Search
    draw_box(ax, 22.0, 29.28, 7.0, 0.4, C["card_bg"],
             corner_radius=0.06,
             border_color=C["card_border"],
             border_width=0.5)

    ax.text(22.3, 29.48,
            "Search by name, golden ID, "
            "domain ID, reg number...",
            ha="left", va="center", fontsize=5,
            color=C["text_muted"], fontstyle="italic",
            zorder=3)

    # Auto-match button
    draw_box(ax, 30.0, 29.25, 2.5, 0.4, C["accent_blue"],
             text_lines=["Run Auto-Match"],
             text_color="#FFFFFF", fontsize=5,
             corner_radius=0.04)

    # Export
    draw_box(ax, 33.0, 29.25, 2.5, 0.4, C["card_bg"],
             text_lines=["Export Audit Log"],
             text_color=C["text_secondary"],
             fontsize=5, corner_radius=0.04,
             border_color=C["card_border"],
             border_width=0.5)

    # ===================================================
    # ROW 1: HEADLINE METRICS
    # ===================================================
    row1_y = 27.5
    metric_h = 1.15

    headlines = [
        ("TOTAL ENTITIES", "14,287", "Across 5 domains",
         C["accent_blue"],
         [8500, 9800, 11000, 12200, 13000, 13500, 14000, 14287]),
        ("RESOLVED", "2,847", "Unique golden IDs",
         C["accent_green"],
         [1200, 1500, 1800, 2100, 2300, 2500, 2700, 2847]),
        ("MATCH RATE", "87%", "Across 3+ domains",
         C["accent_green"],
         [62, 68, 72, 76, 79, 82, 85, 87]),
        ("PENDING REVIEW", "34", "In verification queue",
         C["accent_amber"], None),
        ("HIGH PRIORITY", "8", "Platinum clients unmatched",
         C["accent_red"], None),
        ("AVG CONFIDENCE", "91.2%", "Across all matches",
         C["conf_high"],
         [82, 84, 86, 87, 88, 89, 90, 91.2]),
        ("CONFIRMED TODAY", "12", "By analyst team",
         C["accent_green"], None),
        ("REJECTED TODAY", "3", "False matches caught",
         C["accent_red"], None),
    ]

    metric_w = (36 - 0.6 - 0.12 * 7) / 8

    for mi, (mlabel, mval, msub, mcolor, mspark) in enumerate(headlines):
        mx = 0.3 + mi * (metric_w + 0.12)
        draw_box(ax, mx, row1_y, metric_w, metric_h,
                 C["card_bg"], corner_radius=0.06,
                 border_color=C["card_border"],
                 border_width=0.5, shadow=True)
        ax.text(mx + 0.08, row1_y + metric_h - 0.18, mlabel,
                ha="left", va="center", fontsize=3.5,
                color=C["text_secondary"], zorder=3)
        ax.text(mx + 0.08, row1_y + metric_h - 0.48, mval,
                ha="left", va="center", fontsize=9,
                fontweight="bold", color=mcolor, zorder=3)
        ax.text(mx + 0.08, row1_y + metric_h - 0.7, msub,
                ha="left", va="center", fontsize=3.5,
                color=C["text_muted"], zorder=3)
        if mspark:
            draw_sparkline(ax, mx + 0.08, row1_y + 0.05,
                           metric_w - 0.16, 0.2,
                           mspark, mcolor)

    # ===================================================
    # LAYOUT: Queue (left) + Comparison (centre+right)
    # ===================================================
    content_top = 27.0
    queue_w = 8.0
    compare_w = 36 - queue_w - 0.6
    queue_x = 0.3
    compare_x = queue_x + queue_w + 0.3

    # ===================================================
    # LEFT: VERIFICATION QUEUE
    # ===================================================
    queue_h = content_top - 0.8

    draw_box(ax, queue_x, 0.6, queue_w, queue_h,
             C["card_bg"], corner_radius=0.08,
             border_color=C["card_border"],
             border_width=0.5, shadow=True)

    draw_box(ax, queue_x, content_top - 0.5,
             queue_w, 0.5, C["card_header"],
             corner_radius=0.06)

    ax.text(queue_x + 0.15, content_top - 0.25,
            "VERIFICATION QUEUE",
            ha="left", va="center", fontsize=7,
            fontweight="bold", color=C["text_primary"],
            zorder=3)

    draw_box(ax, queue_x + queue_w - 1.0,
             content_top - 0.42, 0.8, 0.28,
             C["accent_amber"],
             text_lines=["34"],
             text_color="#FFFFFF", fontsize=6,
             bold_first=True, corner_radius=0.04)

    # Queue filter tabs
    qtabs = [
        ("All", True, 34),
        ("High", False, 8),
        ("Medium", False, 18),
        ("Low", False, 8),
    ]

    qtab_x = queue_x + 0.15
    qtab_y = content_top - 0.9

    for qlabel, qactive, qcount in qtabs:
        qw = len(f"{qlabel} ({qcount})") * 0.09 + 0.3

        bg = C["sidebar_active"] if qactive else C["card_bg"]
        border = C["accent_blue"] if qactive else C["card_border"]
        tc = C["white"] if qactive else C["text_muted"]

        draw_box(ax, qtab_x, qtab_y, qw, 0.28,
                 bg, text_lines=[f"{qlabel} ({qcount})"],
                 text_color=tc, fontsize=4.5,
                 corner_radius=0.04,
                 border_color=border,
                 border_width=0.5 if qactive else 0.3)

        qtab_x += qw + 0.08

    # Queue items
    queue_items = [
        {
            "name_a": "Acme Mining Corp (Pty) Ltd",
            "domain_a": "CIB",
            "name_b": "ACME MINING CORPORATION",
            "domain_b": "INSURANCE",
            "confidence": 78,
            "method": "Fuzzy name + country",
            "priority": "HIGH",
            "tier": "Platinum",
            "active": True,
        },
        {
            "name_a": "Continental Resources Ltd",
            "domain_a": "CIB",
            "name_b": "Continental Resources NG",
            "domain_b": "CELL",
            "confidence": 72,
            "method": "Fuzzy name",
            "priority": "HIGH",
            "tier": "Gold",
            "active": False,
        },
        {
            "name_a": "SNEL DRC",
            "domain_a": "CIB",
            "name_b": "Societe Nationale d'Electricite",
            "domain_b": "FOREX",
            "confidence": 45,
            "method": "Fuzzy name",
            "priority": "HIGH",
            "tier": "Gold",
            "active": False,
        },
        {
            "name_a": "Africa Solutions SA",
            "domain_a": "CIB",
            "name_b": "Africa Solutions Zambia",
            "domain_b": "PBB",
            "confidence": 82,
            "method": "Fuzzy name + country",
            "priority": "MEDIUM",
            "tier": "Silver",
            "active": False,
        },
        {
            "name_a": "MTN Nigeria Ltd",
            "domain_a": "CELL",
            "name_b": "MTN Group Operations NG",
            "domain_b": "CIB",
            "confidence": 68,
            "method": "Fuzzy name",
            "priority": "MEDIUM",
            "tier": "Platinum",
            "active": False,
        },
        {
            "name_a": "Shoprite Checkers MZ",
            "domain_a": "PBB",
            "name_b": "Shoprite Holdings Moz",
            "domain_b": "INSURANCE",
            "confidence": 85,
            "method": "Fuzzy name + country",
            "priority": "MEDIUM",
            "tier": "Platinum",
            "active": False,
        },
        {
            "name_a": "Illovo Sugar SA",
            "domain_a": "CIB",
            "name_b": "Illovo Sugar Zambia",
            "domain_b": "FOREX",
            "confidence": 75,
            "method": "Fuzzy name",
            "priority": "MEDIUM",
            "tier": "Gold",
            "active": False,
        },
        {
            "name_a": "Lafarge Cement Nigeria",
            "domain_a": "CIB",
            "name_b": "LAFARGE AFRICA NG",
            "domain_b": "CELL",
            "confidence": 80,
            "method": "Fuzzy name + country",
            "priority": "MEDIUM",
            "tier": "Gold",
            "active": False,
        },
        {
            "name_a": "Tiger Brands (Pty) Ltd",
            "domain_a": "CIB",
            "name_b": "Tiger Consumer Brands",
            "domain_b": "INSURANCE",
            "confidence": 62,
            "method": "Fuzzy name",
            "priority": "LOW",
            "tier": "Gold",
            "active": False,
        },
        {
            "name_a": "Standard Chartered KE",
            "domain_a": "FOREX",
            "name_b": "Stanchart Kenya Ltd",
            "domain_b": "PBB",
            "confidence": 58,
            "method": "Fuzzy name",
            "priority": "LOW",
            "tier": "Silver",
            "active": False,
        },
    ]

    item_h = 1.6
    item_gap = 0.1
    item_y = qtab_y - 0.4

    for qi, item in enumerate(queue_items):
        iy = item_y - qi * (item_h + item_gap)

        if iy - item_h < 0.8:
            break

        # Item background
        bg = C["sidebar_active"] if item["active"] else C["card_bg"]
        border = C["accent_blue"] if item["active"] else C["card_border"]
        bw = 1.5 if item["active"] else 0.3

        draw_box(ax, queue_x + 0.1, iy - item_h,
                 queue_w - 0.2, item_h, bg,
                 corner_radius=0.06,
                 border_color=border,
                 border_width=bw)

        # Active indicator
        if item["active"]:
            draw_box(ax, queue_x + 0.1, iy - item_h,
                     0.08, item_h, C["accent_blue"],
                     corner_radius=0.02)

        # Priority badge
        pri_colors = {
            "HIGH": C["accent_red"],
            "MEDIUM": C["accent_amber"],
            "LOW": C["accent_teal"],
        }
        pc = pri_colors.get(item["priority"], C["text_muted"])

        draw_box(ax, queue_x + 0.3, iy - 0.15,
                 0.7, 0.2, pc,
                 text_lines=[item["priority"]],
                 text_color="#FFFFFF", fontsize=3.5,
                 corner_radius=0.03)

        # Tier badge
        tier_colors = {
            "Platinum": C["accent_blue"],
            "Gold": C["accent_amber"],
            "Silver": C["text_muted"],
        }
        ttc = tier_colors.get(item["tier"], C["text_muted"])

        draw_box(ax, queue_x + 1.1, iy - 0.15,
                 0.9, 0.2, ttc,
                 text_lines=[item["tier"]],
                 text_color="#FFFFFF", fontsize=3.5,
                 corner_radius=0.03)

        # Confidence
        conf_c = (C["conf_high"] if item["confidence"] >= 80
                  else C["conf_medium"] if item["confidence"] >= 60
                  else C["conf_low"])

        ax.text(queue_x + queue_w - 0.3, iy - 0.05,
                f"{item['confidence']}%",
                ha="right", va="center", fontsize=7,
                fontweight="bold", color=conf_c, zorder=3)

        # Names
        domain_colors = {
            "CIB": C["cib"], "FOREX": C["forex"],
            "INSURANCE": C["insurance"],
            "CELL": C["cell"], "PBB": C["pbb"],
        }

        dc_a = domain_colors.get(item["domain_a"], C["text_muted"])
        dc_b = domain_colors.get(item["domain_b"], C["text_muted"])

        # Entity A
        ax.text(queue_x + 0.3, iy - 0.5,
                item["domain_a"], ha="left", va="center",
                fontsize=4, fontweight="bold",
                color=dc_a, zorder=3)

        ax.text(queue_x + 1.2, iy - 0.5,
                item["name_a"][:28], ha="left", va="center",
                fontsize=4.5, color=C["text_primary"], zorder=3)

        # Entity B
        ax.text(queue_x + 0.3, iy - 0.8,
                item["domain_b"], ha="left", va="center",
                fontsize=4, fontweight="bold",
                color=dc_b, zorder=3)

        ax.text(queue_x + 1.2, iy - 0.8,
                item["name_b"][:28], ha="left", va="center",
                fontsize=4.5, color=C["text_primary"], zorder=3)

        # Method
        ax.text(queue_x + 0.3, iy - 1.1,
                item["method"], ha="left", va="center",
                fontsize=4, color=C["text_muted"], zorder=3)

        # Connecting line between names
        ax.text(queue_x + 0.65, iy - 0.65,
                "?", ha="center", va="center",
                fontsize=6, fontweight="bold",
                color=conf_c, zorder=3)

    # Queue footer
    ax.text(queue_x + 0.15, 1.0,
            "Showing 10 of 34. "
            "Sorted by priority, then confidence.",
            ha="left", va="center", fontsize=4.5,
            color=C["text_muted"], zorder=3)

    # ===================================================
    # RIGHT: COMPARISON VIEW (currently selected match)
    # ===================================================
    compare_h = content_top - 0.8

    draw_box(ax, compare_x, 0.6, compare_w, compare_h,
             C["card_bg"], corner_radius=0.08,
             border_color=C["accent_blue"],
             border_width=1.0, shadow=True)

    # Header
    draw_box(ax, compare_x, content_top - 0.5,
             compare_w, 0.5, C["card_header"],
             corner_radius=0.06,
             border_color=C["accent_blue"],
             border_width=0.5)

    ax.text(compare_x + 0.15, content_top - 0.25,
            "MATCH COMPARISON",
            ha="left", va="center", fontsize=7,
            fontweight="bold", color=C["text_primary"],
            zorder=3)

    ax.text(compare_x + compare_w - 0.15,
            content_top - 0.25,
            "Match #ER-2025-04872",
            ha="right", va="center", fontsize=5,
            color=C["text_muted"],
            fontfamily="monospace", zorder=3)

    # === ENTITY CARDS (side by side) ===
    entity_card_h = 3.0
    entity_card_w = (compare_w - 2.0) / 2
    entity_y = content_top - 1.0

    # Left entity (CIB)
    draw_box(ax, compare_x + 0.2,
             entity_y - entity_card_h,
             entity_card_w, entity_card_h,
             C["compare_left"],
             corner_radius=0.08,
             border_color=C["cib"],
             border_width=1.5, shadow=True)

    draw_box(ax, compare_x + 0.2,
             entity_y - 0.5,
             entity_card_w, 0.5,
             C["cib"], corner_radius=0.06)

    ax.text(compare_x + 0.2 + entity_card_w / 2,
            entity_y - 0.25,
            "ENTITY A: CIB",
            ha="center", va="center", fontsize=7,
            fontweight="bold", color="#FFFFFF", zorder=3)

    left_fields = [
        ("Domain ID:", "CIB-1234"),
        ("Name:", "Acme Mining Corp (Pty) Ltd"),
        ("Reg #:", "2010/012345/07"),
        ("Tax #:", "9012345678"),
        ("Country:", "ZA"),
        ("Address:", "Sandton, Johannesburg"),
        ("Email:", "cfo @acmemining.co.za"),
        ("Phone:", "+27 11 555 1234"),
    ]

    for fi, (flabel, fval) in enumerate(left_fields):
        fy = entity_y - 0.7 - fi * 0.28

        ax.text(compare_x + 0.4, fy,
                flabel, ha="left", va="center",
                fontsize=4.5, fontweight="bold",
                color=C["text_muted"], zorder=3)

        ax.text(compare_x + 1.8, fy,
                fval, ha="left", va="center",
                fontsize=5, color=C["text_primary"],
                fontfamily="monospace", zorder=3)

    # VS connector
    vs_cx = compare_x + 0.2 + entity_card_w + 1.0
    vs_cy = entity_y - entity_card_h / 2

    circle = Circle((vs_cx, vs_cy), 0.4,
                     facecolor=C["card_header"],
                     edgecolor=C["accent_amber"],
                     linewidth=2.0, zorder=5)
    ax.add_patch(circle)

    ax.text(vs_cx, vs_cy, "VS",
            ha="center", va="center", fontsize=9,
            fontweight="bold", color=C["accent_amber"],
            zorder=6)

    # Confidence below VS
    ax.text(vs_cx, vs_cy - 0.6,
            "78%", ha="center", va="center",
            fontsize=14, fontweight="bold",
            color=C["conf_medium"], zorder=5)

    ax.text(vs_cx, vs_cy - 0.95,
            "Confidence", ha="center", va="center",
            fontsize=5, color=C["text_muted"], zorder=5)

    ax.text(vs_cx, vs_cy - 1.2,
            "Fuzzy name + country",
            ha="center", va="center", fontsize=4.5,
            color=C["text_secondary"], zorder=5)

    # Right entity (Insurance)
    right_entity_x = compare_x + 0.2 + entity_card_w + 2.0

    draw_box(ax, right_entity_x,
             entity_y - entity_card_h,
             entity_card_w, entity_card_h,
             C["compare_right"],
             corner_radius=0.08,
             border_color=C["insurance"],
             border_width=1.5, shadow=True)

    draw_box(ax, right_entity_x,
             entity_y - 0.5,
             entity_card_w, 0.5,
             C["insurance"], corner_radius=0.06)

    ax.text(right_entity_x + entity_card_w / 2,
            entity_y - 0.25,
            "ENTITY B: INSURANCE",
            ha="center", va="center", fontsize=7,
            fontweight="bold", color="#FFFFFF", zorder=3)

    right_fields = [
        ("Domain ID:", "LIB-POL-98765"),
        ("Name:", "ACME MINING CORPORATION"),
        ("Reg #:", "(not provided)"),
        ("Tax #:", "9012345678"),
        ("Country:", "ZA"),
        ("Address:", "(not provided)"),
        ("Email:", "insurance @acmemining.co.za"),
        ("Phone:", "(not provided)"),
    ]

    for fi, (flabel, fval) in enumerate(right_fields):
        fy = entity_y - 0.7 - fi * 0.28

        is_missing = "not provided" in fval

        ax.text(right_entity_x + 0.2, fy,
                flabel, ha="left", va="center",
                fontsize=4.5, fontweight="bold",
                color=C["text_muted"], zorder=3)

        ax.text(right_entity_x + 1.6, fy,
                fval, ha="left", va="center",
                fontsize=5,
                color=C["match_missing"] if is_missing else C["text_primary"],
                fontfamily="monospace",
                fontstyle="italic" if is_missing else "normal",
                zorder=3)

    # === FIELD-BY-FIELD COMPARISON ===
    compare_detail_y = entity_y - entity_card_h - 0.5

    ax.text(compare_x + 0.2, compare_detail_y + 0.2,
            "FIELD-BY-FIELD MATCH ANALYSIS",
            ha="left", va="center", fontsize=7,
            fontweight="bold", color=C["text_primary"],
            zorder=3)

    # Column headers for comparison
    cmp_headers = ["Field", "Entity A (CIB)", "Match", "Entity B (Insurance)"]
    cmp_col_x = [compare_x + 0.35, compare_x + 2.7,
                 compare_x + compare_w / 2 - 0.4,
                 compare_x + compare_w / 2 + 0.8]

    for hi, header in enumerate(cmp_headers):
        ax.text(cmp_col_x[hi],
                compare_detail_y - 0.1,
                header, ha="left", va="center",
                fontsize=4.5, fontweight="bold",
                color=C["text_muted"], zorder=3)

    comparisons = [
        ("Name", "Acme Mining Corp (Pty) Ltd",
         "ACME MINING CORPORATION", "fuzzy"),
        ("Name (normalised)", "ACME MINING CORP",
         "ACME MINING CORPORATION", "fuzzy"),
        ("Reg #", "2010/012345/07",
         "", "missing_right"),
        ("Tax #", "9012345678",
         "9012345678", "exact"),
        ("Country", "ZA", "ZA", "exact"),
        ("Address", "Sandton, Johannesburg",
         "", "missing_right"),
        ("Email domain", " @acmemining.co.za",
         " @acmemining.co.za", "exact"),
        ("Phone", "+27 11 555 1234",
         "", "missing_right"),
    ]

    field_y = compare_detail_y - 0.4

    for ci, (fname, fval_l, fval_r, fstatus) in enumerate(comparisons):
        fy = field_y - ci * 0.45

        draw_field_comparison(
            ax, compare_x + 0.2, fy,
            compare_w - 0.4,
            fname, fval_l, fval_r, fstatus,
        )

    # === MATCH EVIDENCE SUMMARY ===
    evidence_y = field_y - len(comparisons) * 0.45 - 0.5

    draw_box(ax, compare_x + 0.2,
             evidence_y - 2.2,
             compare_w - 0.4, 2.2,
             C["card_header"],
             corner_radius=0.08,
             border_color=C["card_border"],
             border_width=0.5)

    ax.text(compare_x + 0.35, evidence_y - 0.2,
            "MATCH EVIDENCE SUMMARY",
            ha="left", va="center", fontsize=6.5,
            fontweight="bold", color=C["text_primary"],
            zorder=3)

    evidence_items = [
        ("Phase 1 (Registration #):", "PARTIAL",
         "CIB has reg number. Insurance does not. Cannot confirm.",
         C["match_fuzzy"]),
        ("Phase 2 (Tax #):", "MATCH",
         "9012345678 matches exactly across both domains.",
         C["match_exact"]),
        ("Phase 3 (Fuzzy name):", "MATCH (0.87 similarity)",
         "After normalisation: ACME MINING CORP vs ACME MINING CORPORATION. "
         "Levenshtein: 0.87 (threshold: 0.85).",
         C["match_fuzzy"]),
        ("Phase 4 (Contact):", "MATCH",
         "Email domain @acmemining.co.za matches across both domains.",
         C["match_exact"]),
    ]

    for ei, (elabel, estatus, edesc, ecolor) in enumerate(evidence_items):
        ey = evidence_y - 0.55 - ei * 0.4

        ax.text(compare_x + 0.35, ey + 0.05,
                elabel, ha="left", va="center",
                fontsize=5, fontweight="bold",
                color=C["text_secondary"], zorder=3)

        draw_box(ax, compare_x + 4.2, ey - 0.05,
                 len(estatus) * 0.09 + 0.3, 0.22,
                 ecolor,
                 text_lines=[estatus],
                 text_color="#FFFFFF", fontsize=3.5,
                 corner_radius=0.03)

        ax.text(compare_x + 4.2 + len(estatus) * 0.09 + 0.5,
                ey + 0.05,
                edesc[:75], ha="left", va="center",
                fontsize=4, color=C["text_muted"], zorder=3)

    # === RECOMMENDATION ===
    rec_y = evidence_y - 2.6

    draw_box(ax, compare_x + 0.2,
             rec_y - 0.8,
             compare_w - 0.4, 0.8,
             "#1A2A1A",
             corner_radius=0.08,
             border_color=C["accent_green"],
             border_width=1.0)

    ax.text(compare_x + 0.35, rec_y - 0.2,
            "SYSTEM RECOMMENDATION: LIKELY MATCH",
            ha="left", va="center", fontsize=6,
            fontweight="bold", color=C["accent_green"],
            zorder=3)

    ax.text(compare_x + 0.35, rec_y - 0.5,
            "Tax number exact match (Phase 2) provides 98% base confidence. "
            "Fuzzy name match (0.87) and email domain match provide supplementary "
            "confirmation. Recommend: CONFIRM with canonical name from CIB.",
            ha="left", va="center", fontsize=5,
            color=C["text_secondary"], zorder=3)

    # === ACTION BUTTONS ===
    btn_y = rec_y - 1.3

    # Confirm button
    draw_box(ax, compare_x + 0.2, btn_y,
             4.0, 0.6, C["accent_green"],
             text_lines=["CONFIRM MATCH"],
             text_color="#FFFFFF", fontsize=7,
             bold_first=True, corner_radius=0.06)

    ax.text(compare_x + 0.2 + 2.0, btn_y - 0.25,
            "Merge into golden record with CIB name",
            ha="center", va="center", fontsize=4,
            color=C["text_muted"], zorder=3)

    # Confirm with edit
    draw_box(ax, compare_x + 4.5, btn_y,
             4.5, 0.6, C["accent_amber"],
             text_lines=["CONFIRM WITH EDIT"],
             text_color="#FFFFFF", fontsize=7,
             bold_first=True, corner_radius=0.06)

    ax.text(compare_x + 4.5 + 2.25, btn_y - 0.25,
            "Merge but edit the canonical name first",
            ha="center", va="center", fontsize=4,
            color=C["text_muted"], zorder=3)

    # Reject button
    draw_box(ax, compare_x + 9.3, btn_y,
             3.5, 0.6, C["accent_red"],
             text_lines=["REJECT MATCH"],
             text_color="#FFFFFF", fontsize=7,
             bold_first=True, corner_radius=0.06)

    ax.text(compare_x + 9.3 + 1.75, btn_y - 0.25,
            "These are different entities",
            ha="center", va="center", fontsize=4,
            color=C["text_muted"], zorder=3)

    # Skip button
    draw_box(ax, compare_x + 13.1, btn_y,
             2.5, 0.6, C["card_bg"],
             text_lines=["SKIP"],
             text_color=C["text_secondary"],
             fontsize=7, corner_radius=0.06,
             border_color=C["card_border"],
             border_width=0.5)

    ax.text(compare_x + 13.1 + 1.25, btn_y - 0.25,
            "Need more info",
            ha="center", va="center", fontsize=4,
            color=C["text_muted"], zorder=3)

    # Escalate
    draw_box(ax, compare_x + 15.9, btn_y,
             3.0, 0.6, C["card_bg"],
             text_lines=["ESCALATE"],
             text_color=C["accent_purple"],
             fontsize=7, corner_radius=0.06,
             border_color=C["accent_purple"],
             border_width=0.5)

    ax.text(compare_x + 15.9 + 1.5, btn_y - 0.25,
            "Send to senior analyst",
            ha="center", va="center", fontsize=4,
            color=C["text_muted"], zorder=3)

    # === GOLDEN RECORD PREVIEW ===
    golden_y = btn_y - 0.8

    draw_box(ax, compare_x + 0.2,
             golden_y - 2.0,
             compare_w - 0.4, 2.0,
             C["golden_bg"],
             corner_radius=0.08,
             border_color=C["golden_border"],
             border_width=1.5, shadow=True)

    ax.text(compare_x + 0.35, golden_y - 0.2,
            "GOLDEN RECORD PREVIEW (if confirmed)",
            ha="left", va="center", fontsize=6.5,
            fontweight="bold", color=C["golden_text"],
            zorder=3)

    golden_fields = [
        ("Golden ID:", "GLD-A1B2C3D4E5F6 (auto-generated)"),
        ("Canonical Name:", "Acme Mining Corp (Pty) Ltd (from CIB)"),
        ("Registration #:", "2010/012345/07"),
        ("Tax #:", "9012345678"),
        ("Country:", "ZA"),
        ("Domains Linked:", "CIB (CIB-1234) + Insurance (LIB-POL-98765)"),
        ("Match Confidence:", "98% (tax number match)"),
    ]

    for gi, (glabel, gval) in enumerate(golden_fields):
        gy = golden_y - 0.5 - gi * 0.22

        ax.text(compare_x + 0.35, gy,
                glabel, ha="left", va="center",
                fontsize=5, fontweight="bold",
                color=C["golden_text"], zorder=3)

        ax.text(compare_x + 3.5, gy,
                gval, ha="left", va="center",
                fontsize=5, color=C["text_primary"],
                fontfamily="monospace", zorder=3)

    # Existing links note
    ax.text(compare_x + 0.35, golden_y - 1.8,
            "Note: This entity already has a golden record with "
            "Forex (FX-ACME-ZA) and Cell (MTN-CORP-5678) linked. "
            "Confirming will add Insurance as the 4th domain.",
            ha="left", va="center", fontsize=4.5,
            color=C["accent_cyan"], zorder=3)

    # === AUDIT LOG (bottom) ===
    audit_y = golden_y - 2.5

    ax.text(compare_x + 0.2, audit_y,
            "RECENT DECISIONS (Audit Trail)",
            ha="left", va="center", fontsize=6,
            fontweight="bold", color=C["text_primary"],
            zorder=3)

    audit_entries = [
        ("09:12", "Sipho M.", "CONFIRMED",
         "Dangote Industries CIB + CELL", "Reg # match",
         C["accent_green"]),
        ("09:08", "Sipho M.", "CONFIRMED",
         "Shoprite Holdings CIB + FX + INS", "Tax # match",
         C["accent_green"]),
        ("09:01", "Sipho M.", "REJECTED",
         "Africa Mining ZA vs Africa Mining GH",
         "Different countries, different entities",
         C["accent_red"]),
        ("08:52", "Amina O.", "CONFIRMED (edit)",
         "MTN Nigeria + MTN Group NG",
         "Canonical: MTN Nigeria Communications Ltd",
         C["accent_amber"]),
        ("08:45", "Amina O.", "ESCALATED",
         "Continental Resources vs Continental NG",
         "Need RM confirmation: parent vs subsidiary?",
         C["accent_purple"]),
    ]

    for ai, (atime, auser, adecision, aentities, areason, acolor) in enumerate(audit_entries):
        ay = audit_y - 0.35 - ai * 0.38

        if ay < 0.8:
            break

        ax.text(compare_x + 0.35, ay, atime,
                ha="left", va="center", fontsize=4.5,
                color=C["text_muted"], zorder=3)

        ax.text(compare_x + 1.0, ay, auser,
                ha="left", va="center", fontsize=4.5,
                fontweight="bold", color=C["text_secondary"],
                zorder=3)

        draw_box(ax, compare_x + 2.2, ay - 0.08,
                 len(adecision) * 0.08 + 0.3, 0.2,
                 acolor, text_lines=[adecision],
                 text_color="#FFFFFF", fontsize=3.5,
                 corner_radius=0.03)

        ax.text(compare_x + 2.2 + len(adecision) * 0.08 + 0.5,
                ay, aentities, ha="left", va="center",
                fontsize=4.5, color=C["text_primary"], zorder=3)

        ax.text(compare_x + compare_w - 0.2, ay,
                areason, ha="right", va="center",
                fontsize=4, color=C["text_muted"], zorder=3)

    # ===================================================
    # BOTTOM STATUS BAR
    # ===================================================
    draw_box(ax, 0, 0, 36, 0.5, C["topbar_bg"],
             corner_radius=0.0, border_color=C["divider"],
             border_width=0.5)

    ax.text(0.5, 0.25,
            "Entity Resolution Console  |  "
            "14,287 entities  |  "
            "2,847 golden records  |  "
            "87% coverage (3+ domains)  |  "
            "34 pending review  |  "
            "91.2% avg confidence  |  "
            "Without accurate matching, "
            "every downstream signal is wrong.",
            ha="left", va="center", fontsize=4.5,
            color=C["text_muted"], zorder=3)

    ax.text(35.5, 0.25, "CONCEPT MOCKUP",
            ha="right", va="center", fontsize=4.5,
            fontweight="bold", color=C["text_muted"],
            zorder=3)

    # ===================================================
    # SAVE
    # ===================================================
    output_dir = os.path.dirname(os.path.abspath(__file__))

    output_path = os.path.join(output_dir,
                                "entity_resolution_console.png")
    fig.savefig(output_path, dpi=200, bbox_inches="tight",
                pad_inches=0.1, facecolor=C["bg"],
                edgecolor="none")
    print(f"Entity Resolution Console saved to: {output_path}")

    small_path = os.path.join(output_dir,
                               "entity_resolution_console_small.png")
    fig.savefig(small_path, dpi=100, bbox_inches="tight",
                pad_inches=0.1, facecolor=C["bg"],
                edgecolor="none")
    print(f"Small version: {small_path}")

    plt.close(fig)


if __name__ == "__main__":
    print("Generating AfriFlow Entity Resolution Console...")
    print()
    generate_entity_resolution_console()
    print()
    print("Entity Resolution Console generated.")
    print("Files ready for embedding in README.md and documentation.")
