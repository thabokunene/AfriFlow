# diagrams/generate_knowledge_card_library.py

"""
AfriFlow Lekgotla Knowledge Card Library

We generate a high fidelity mockup of the Knowledge
Card Library where practitioners search, browse, and
apply validated approaches that have been proven to
generate revenue or prevent risk.

Knowledge Cards are the distilled wisdom of Lekgotla.
A thread is a conversation. A Knowledge Card is the
conclusion of that conversation, validated by
confirmed outcomes.

This screen is the institutional memory of Standard
Bank Group. When Sipho Mabena retires, his 18
Knowledge Cards remain.

Usage:
    python diagrams/generate_knowledge_card_library.py

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
    "lekgotla_gold": "#D4A017",
    "kc_bg": "#162818",
    "kc_border": "#4CAF50",
    "kc_header": "#1A3A1A",
    "kc_verified": "#2E7D32",
    "kc_regulatory": "#4A148C",
    "kc_onboarding": "#01579B",
    "kc_product": "#E65100",
    "tag_bg": "#1A2A3A",
    "tag_border": "#2A4A6A",
    "tag_text": "#6A9ACA",
    "search_bg": "#0D1620",
    "search_border": "#1E3048",
    "filter_active": "#1A3050",
    "filter_active_border": "#1976D2",
    "filter_inactive": "#111D2E",
    "sidebar_bg": "#0D1620",
    "sidebar_border": "#1E3048",
    "star_active": "#FFD700",
    "star_inactive": "#2A3A4A",
    "doc_pdf": "#E53935",
    "doc_excel": "#43A047",
    "doc_pptx": "#FB8C00",
    "doc_link": "#1976D2",
    "white": "#FFFFFF",
    "avatar_colors": [
        "#1976D2", "#E53935", "#43A047",
        "#8E24AA", "#FB8C00", "#00897B",
        "#D81B60", "#5E35B1", "#00ACC1",
        "#F4511E",
    ],
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


def draw_avatar(
    ax, x, y, initials, color,
    size=0.2,
):
    """Draw a circular avatar."""

    circle = Circle(
        (x, y), size,
        facecolor=color,
        edgecolor=C["card_bg"],
        linewidth=0.5,
        zorder=5,
    )
    ax.add_patch(circle)

    ax.text(
        x, y,
        initials,
        ha="center", va="center",
        fontsize=4 if size <= 0.2 else 5,
        fontweight="bold",
        color="#FFFFFF",
        zorder=6,
    )


def draw_progress_bar(
    ax, x, y, w, h, pct, color,
    bg=None,
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


def draw_star_rating(ax, x, y, rating, max_stars=5):
    """Draw a star rating."""

    for i in range(max_stars):
        sx = x + i * 0.22
        filled = i < rating

        ax.text(
            sx, y,
            "*",
            ha="center", va="center",
            fontsize=7,
            color=(
                C["star_active"]
                if filled
                else C["star_inactive"]
            ),
            fontweight="bold",
            zorder=5,
        )


def draw_doc_badge(ax, x, y, filename, doc_type):
    """Draw a document attachment badge. Returns width."""

    type_colors = {
        "PDF": C["doc_pdf"],
        "XLSX": C["doc_excel"],
        "PPTX": C["doc_pptx"],
        "LINK": C["doc_link"],
    }

    tc = type_colors.get(doc_type, C["text_muted"])
    badge_w = len(filename) * 0.075 + 0.8

    draw_box(
        ax, x, y,
        badge_w, 0.25,
        C["card_header"],
        corner_radius=0.04,
        border_color=tc,
        border_width=0.5,
    )

    # Type indicator
    draw_box(
        ax, x + 0.03, y + 0.03,
        0.4, 0.19,
        tc,
        text_lines=[doc_type],
        text_color="#FFFFFF",
        fontsize=3.5,
        corner_radius=0.03,
    )

    ax.text(
        x + 0.5, y + 0.12,
        filename,
        ha="left", va="center",
        fontsize=3.5,
        color=C["text_secondary"],
        zorder=3,
    )

    return badge_w


def draw_filter_chip(
    ax, x, y, label, active=False,
    color=None,
):
    """Draw a filter chip. Returns width."""

    chip_w = len(label) * 0.1 + 0.35

    bg = (
        C["filter_active"]
        if active
        else C["filter_inactive"]
    )
    border = (
        C["filter_active_border"]
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
        chip_w, 0.28,
        bg,
        text_lines=[label],
        text_color=tc,
        fontsize=4.5,
        corner_radius=0.05,
        border_color=border,
        border_width=0.8 if active else 0.3,
    )

    return chip_w


def draw_knowledge_card(
    ax, x, y, w,
    card_id, title, subtitle,
    category, category_color,
    signal_type, countries,
    products, win_rate, uses,
    revenue, contributors,
    contributor_avatars,
    approach_lines,
    avoid_lines,
    documents,
    source_threads, last_updated,
    rating,
):
    """
    Draw a full Knowledge Card in the library.
    Returns height consumed.
    """

    # Calculate height
    approach_h = len(approach_lines) * 0.2
    avoid_h = len(avoid_lines) * 0.2
    docs_h = 0.35 if documents else 0
    base_h = 4.5 + approach_h + avoid_h + docs_h

    total_h = min(base_h, 6.5)

    # Card background
    draw_box(
        ax, x, y - total_h,
        w, total_h,
        C["kc_bg"],
        corner_radius=0.1,
        border_color=C["kc_border"],
        border_width=1.5,
        shadow=True,
    )

    # Header stripe
    draw_box(
        ax, x, y - 0.7,
        w, 0.7,
        C["kc_header"],
        corner_radius=0.08,
        border_color=C["kc_border"],
        border_width=0.8,
    )

    # KC icon
    draw_box(
        ax, x + 0.15, y - 0.55,
        0.5, 0.4,
        C["kc_verified"],
        text_lines=["KC"],
        text_color="#FFFFFF",
        fontsize=6,
        bold_first=True,
        corner_radius=0.05,
    )

    # Card ID
    ax.text(
        x + 0.8, y - 0.2,
        card_id,
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["kc_border"],
        zorder=3,
    )

    # Title
    ax.text(
        x + 0.8, y - 0.45,
        title,
        ha="left", va="center",
        fontsize=6.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Category badge
    cat_w = len(category) * 0.09 + 0.3

    draw_box(
        ax,
        x + w - cat_w - 0.15,
        y - 0.55,
        cat_w, 0.25,
        category_color,
        text_lines=[category],
        text_color="#FFFFFF",
        fontsize=4,
        corner_radius=0.04,
    )

    # Metrics row
    metrics_y = y - 0.95

    metrics = [
        ("Win Rate", f"{win_rate}%",
         C["positive"] if win_rate >= 60
         else C["accent_amber"]),
        ("Used By", f"{uses} RMs",
         C["accent_blue"]),
        ("Revenue", revenue,
         C["positive"]),
        ("Rating",  None, None),
    ]

    metric_w = (w - 0.6) / len(metrics)

    for mi, (mlabel, mval, mcolor) in enumerate(
        metrics
    ):
        mx = x + 0.15 + mi * metric_w

        if mlabel == "Rating":
            ax.text(
                mx, metrics_y + 0.1,
                mlabel,
                ha="left", va="center",
                fontsize=4,
                color=C["text_muted"],
                zorder=3,
            )
            draw_star_rating(
                ax, mx + 0.05,
                metrics_y - 0.12,
                rating,
            )
        else:
            ax.text(
                mx, metrics_y + 0.1,
                mlabel,
                ha="left", va="center",
                fontsize=4,
                color=C["text_muted"],
                zorder=3,
            )

            ax.text(
                mx, metrics_y - 0.12,
                mval,
                ha="left", va="center",
                fontsize=6, fontweight="bold",
                color=mcolor,
                zorder=3,
            )

    # Divider
    ax.plot(
        [x + 0.15, x + w - 0.15],
        [metrics_y - 0.3, metrics_y - 0.3],
        color=C["divider"],
        linewidth=0.5,
        zorder=3,
    )

    # Signal + Country + Product tags
    tags_y = metrics_y - 0.5

    # Signal
    sig_colors = {
        "Expansion": C["accent_green"],
        "Hedge Gap": C["forex"],
        "Leakage": C["accent_amber"],
        "Insurance": C["insurance"],
        "Workforce": C["pbb"],
        "Currency": C["accent_red"],
        "Seasonal": C["accent_teal"],
        "Regulation": C["accent_purple"],
        "Onboarding": C["accent_cyan"],
        "Supply Chain": C["accent_purple"],
    }

    sc = sig_colors.get(
        signal_type, C["accent_blue"]
    )
    sig_w = len(signal_type) * 0.09 + 0.25

    draw_box(
        ax, x + 0.15, tags_y - 0.1,
        sig_w, 0.22,
        sc,
        text_lines=[signal_type],
        text_color="#FFFFFF",
        fontsize=4,
        corner_radius=0.03,
    )

    # Countries
    ctag_x = x + 0.15 + sig_w + 0.1

    for country in countries:
        cw = 0.4

        draw_box(
            ax, ctag_x, tags_y - 0.1,
            cw, 0.22,
            C["tag_bg"],
            text_lines=[country],
            text_color=C["tag_text"],
            fontsize=4,
            corner_radius=0.03,
            border_color=C["tag_border"],
            border_width=0.3,
        )

        ctag_x += cw + 0.06

    # Products
    for product in products:
        prod_colors = {
            "CIB": C["cib"],
            "FX": C["forex"],
            "INS": C["insurance"],
            "CELL": C["cell"],
            "PBB": C["pbb"],
        }

        pc = prod_colors.get(
            product, C["text_muted"]
        )
        pw = len(product) * 0.1 + 0.2

        draw_box(
            ax, ctag_x, tags_y - 0.1,
            pw, 0.22,
            pc,
            text_lines=[product],
            text_color="#FFFFFF",
            fontsize=4,
            corner_radius=0.03,
            alpha=0.8,
        )

        ctag_x += pw + 0.06

    # APPROACH section
    approach_y = tags_y - 0.45

    ax.text(
        x + 0.15, approach_y,
        "APPROACH:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["kc_border"],
        zorder=3,
    )

    for ai, aline in enumerate(
        approach_lines[:5]
    ):
        ay = approach_y - 0.25 - ai * 0.2

        bullet = Circle(
            (x + 0.25, ay), 0.04,
            facecolor=C["kc_border"],
            edgecolor="none",
            zorder=4,
        )
        ax.add_patch(bullet)

        ax.text(
            x + 0.4, ay,
            aline,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_primary"],
            zorder=3,
        )

    # AVOID section
    avoid_y = (
        approach_y - 0.25
        - len(approach_lines[:5]) * 0.2
        - 0.2
    )

    ax.text(
        x + 0.15, avoid_y,
        "AVOID:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["accent_red"],
        zorder=3,
    )

    for vi, vline in enumerate(
        avoid_lines[:3]
    ):
        vy = avoid_y - 0.25 - vi * 0.2

        ax.text(
            x + 0.25, vy,
            "x",
            ha="center", va="center",
            fontsize=5, fontweight="bold",
            color=C["accent_red"],
            zorder=4,
        )

        ax.text(
            x + 0.4, vy,
            vline,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_secondary"],
            zorder=3,
        )

    # Documents
    if documents:
        docs_y = (
            avoid_y - 0.25
            - len(avoid_lines[:3]) * 0.2
            - 0.15
        )

        doc_x = x + 0.15

        for doc_name, doc_type in documents[:3]:
            dw = draw_doc_badge(
                ax, doc_x, docs_y,
                doc_name, doc_type,
            )
            doc_x += dw + 0.1

    # Footer: contributors + metadata
    footer_y = y - total_h + 0.15

    # Contributors
    for ci, (cinit, ccolor) in enumerate(
        contributor_avatars[:5]
    ):
        cx = x + 0.3 + ci * 0.35
        draw_avatar(
            ax, cx, footer_y + 0.15,
            cinit, ccolor, 0.14,
        )

    ax.text(
        x + 0.3 + len(
            contributor_avatars[:5]
        ) * 0.35 + 0.1,
        footer_y + 0.15,
        f"{contributors} contributors",
        ha="left", va="center",
        fontsize=4,
        color=C["text_muted"],
        zorder=3,
    )

    # Source threads + last updated
    ax.text(
        x + w - 0.15,
        footer_y + 0.25,
        f"{source_threads} source threads",
        ha="right", va="center",
        fontsize=4,
        color=C["text_muted"],
        zorder=3,
    )

    ax.text(
        x + w - 0.15,
        footer_y + 0.05,
        f"Updated: {last_updated}",
        ha="right", va="center",
        fontsize=4,
        color=C["text_muted"],
        zorder=3,
    )

    return total_h


def generate_knowledge_card_library():
    """Generate the Knowledge Card Library."""

    fig, ax = plt.subplots(1, 1, figsize=(36, 32))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 36)
    ax.set_ylim(0, 32)
    ax.set_aspect("equal")
    ax.axis("off")

    # ===================================================
    # TOP BAR
    # ===================================================

    draw_box(
        ax, 0, 31.0, 36, 1.0,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    draw_box(
        ax, 0.3, 31.2,
        0.5, 0.5,
        C["lekgotla_gold"],
        text_lines=["L"],
        text_color="#1A1A1A",
        fontsize=9,
        bold_first=True,
        corner_radius=0.06,
    )

    ax.text(
        1.0, 31.55,
        "Lekgotla",
        ha="left", va="center",
        fontsize=12, fontweight="bold",
        color=C["lekgotla_gold"],
        zorder=3,
    )

    ax.text(
        1.0, 31.25,
        "Knowledge Card Library",
        ha="left", va="center",
        fontsize=7,
        color=C["text_secondary"],
        zorder=3,
    )

    # Tabs
    tabs = [
        ("Feed", False),
        ("My Threads", False),
        ("Knowledge Cards", True),
        ("Regulatory", False),
        ("Analytics", False),
    ]

    tab_x = 5.0

    for tlabel, tactive in tabs:
        tw = len(tlabel) * 0.12 + 0.5

        if tactive:
            draw_box(
                ax, tab_x, 31.2,
                tw, 0.4,
                C["kc_verified"],
                text_lines=[tlabel],
                text_color="#FFFFFF",
                fontsize=5.5,
                bold_first=True,
                corner_radius=0.05,
            )
        else:
            ax.text(
                tab_x + tw / 2, 31.4,
                tlabel,
                ha="center", va="center",
                fontsize=5.5,
                color=C["text_muted"],
                zorder=3,
            )

        tab_x += tw + 0.3

    # Search
    search_x = 16.0
    search_w = 10.0

    draw_box(
        ax, search_x, 31.2,
        search_w, 0.45,
        C["search_bg"],
        corner_radius=0.06,
        border_color=C["search_border"],
        border_width=0.5,
    )

    ax.text(
        search_x + 0.3, 31.42,
        "Search Knowledge Cards by approach, "
        "country, signal type, product...",
        ha="left", va="center",
        fontsize=5,
        color=C["text_muted"],
        fontstyle="italic",
        zorder=3,
    )

    # Card count
    ax.text(
        28.0, 31.42,
        "214 cards",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["kc_border"],
        zorder=3,
    )

    # View toggles
    views = [("Grid", True), ("List", False)]

    for vi, (vlabel, vactive) in enumerate(views):
        vx = 31.0 + vi * 1.2

        draw_box(
            ax, vx, 31.25,
            1.0, 0.3,
            (
                C["kc_verified"]
                if vactive
                else C["card_bg"]
            ),
            text_lines=[vlabel],
            text_color=(
                "#FFFFFF"
                if vactive
                else C["text_muted"]
            ),
            fontsize=5,
            corner_radius=0.04,
            border_color=(
                C["kc_border"]
                if vactive
                else C["card_border"]
            ),
            border_width=0.5,
        )

    # ===================================================
    # FILTER BAR
    # ===================================================

    filter_y = 30.3

    draw_box(
        ax, 0, filter_y,
        36, 0.6,
        C["card_header"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.3,
    )

    # Sort
    ax.text(
        0.3, filter_y + 0.3,
        "Sort:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["text_secondary"],
        zorder=3,
    )

    sorts = [
        ("Highest Win Rate", True),
        ("Most Used", False),
        ("Most Revenue", False),
        ("Newest", False),
        ("Highest Rated", False),
    ]

    sx = 1.2

    for slabel, sactive in sorts:
        sw = draw_filter_chip(
            ax, sx, filter_y + 0.16,
            slabel, sactive,
        )
        sx += sw + 0.1

    # Signal filter
    ax.text(
        9.5, filter_y + 0.3,
        "Signal:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["text_secondary"],
        zorder=3,
    )

    signals = [
        ("All", True, None),
        ("Expansion", False, C["accent_green"]),
        ("Hedge Gap", False, C["forex"]),
        ("Insurance", False, C["insurance"]),
        ("Regulation", False, C["accent_purple"]),
    ]

    sig_x = 10.8

    for flabel, factive, fcolor in signals:
        fw = draw_filter_chip(
            ax, sig_x, filter_y + 0.16,
            flabel, factive, fcolor,
        )
        sig_x += fw + 0.08

    # Country filter
    ax.text(
        18.0, filter_y + 0.3,
        "Country:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["text_secondary"],
        zorder=3,
    )

    countries_f = [
        "All", "GH", "NG", "KE",
        "ZM", "MZ", "AO",
    ]

    cf_x = 19.5

    for cf in countries_f:
        cfw = draw_filter_chip(
            ax, cf_x, filter_y + 0.16,
            cf, cf == "All",
        )
        cf_x += cfw + 0.06

    # Product filter
    ax.text(
        26.0, filter_y + 0.3,
        "Product:",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["text_secondary"],
        zorder=3,
    )

    products_f = [
        ("All", True, None),
        ("CIB", False, C["cib"]),
        ("FX", False, C["forex"]),
        ("INS", False, C["insurance"]),
        ("CELL", False, C["cell"]),
        ("PBB", False, C["pbb"]),
    ]

    pf_x = 27.5

    for plabel, pactive, pcolor in products_f:
        pfw = draw_filter_chip(
            ax, pf_x, filter_y + 0.16,
            plabel, pactive, pcolor,
        )
        pf_x += pfw + 0.06

    # ===================================================
    # SUMMARY METRICS BAR
    # ===================================================

    summary_y = filter_y - 0.5

    draw_box(
        ax, 0.3, summary_y - 0.6,
        35.4, 0.6,
        C["card_bg"],
        corner_radius=0.06,
        border_color=C["card_border"],
        border_width=0.3,
    )

    summary_stats = [
        ("214", "Total Cards", C["kc_border"]),
        ("64%", "Avg Win Rate", C["positive"]),
        ("R892M", "Total Revenue", C["positive"]),
        ("137", "Verified Wins", C["accent_amber"]),
        ("14", "Avg Uses/Card", C["accent_blue"]),
        ("4.2", "Avg Rating", C["star_active"]),
        ("42", "Contributors", C["accent_teal"]),
        ("18", "Countries", C["accent_cyan"]),
    ]

    stat_w = 35.4 / len(summary_stats)

    for si, (sval, slabel, scolor) in enumerate(
        summary_stats
    ):
        ssx = 0.3 + si * stat_w

        ax.text(
            ssx + stat_w / 2,
            summary_y - 0.15,
            sval,
            ha="center", va="center",
            fontsize=8, fontweight="bold",
            color=scolor,
            zorder=3,
        )

        ax.text(
            ssx + stat_w / 2,
            summary_y - 0.4,
            slabel,
            ha="center", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

    # ===================================================
    # KNOWLEDGE CARD GRID (2 columns x 3 rows)
    # ===================================================

    grid_top = summary_y - 0.8
    col_gap = 0.25
    row_gap = 0.25
    card_w = (36 - 0.6 - col_gap) / 2

    cards_data = [
        {
            "id": "KC-GH-EXPANSION-001",
            "title": "Bundle pricing for Ghana expansion signals",
            "subtitle": "Working capital + FX + Insurance in one meeting",
            "category": "PROVEN",
            "cat_color": C["kc_verified"],
            "signal": "Expansion",
            "countries": ["GH", "CI"],
            "products": ["CIB", "FX", "INS"],
            "win_rate": 64,
            "uses": 14,
            "revenue": "R155M",
            "contributors": 4,
            "avatars": [
                ("SM", C["avatar_colors"][0]),
                ("AO", C["avatar_colors"][1]),
                ("DM", C["avatar_colors"][2]),
                ("GA", C["avatar_colors"][9]),
            ],
            "approach": [
                "Bundle WC + FX forward + insurance in first meeting",
                "Cross-domain subsidy: 15% below individual pricing",
                "Lead with working capital, embed insurance naturally",
                "Flag BoG subsidiary registration early (trust builder)",
                "Route KES/GHS through Nairobi FX desk via USD",
            ],
            "avoid": [
                "Leading with insurance (perceived as upsell)",
                "Quoting FX forwards in isolation (lose on bps)",
                "Waiting for CIB booking before offering insurance",
            ],
            "docs": [
                ("Bundle_Pricing_Template.xlsx", "XLSX"),
                ("Client_Presentation.pptx", "PPTX"),
                ("BoG_Regulatory_Checklist.pdf", "PDF"),
            ],
            "threads": 4,
            "updated": "Mar 2025",
            "rating": 5,
        },
        {
            "id": "KC-NG-FX-REPAT-2025",
            "title": "CBN repatriation rule response playbook",
            "subtitle": "60-day window replacing 90-day for export proceeds",
            "category": "REGULATORY",
            "cat_color": C["kc_regulatory"],
            "signal": "Regulation",
            "countries": ["NG"],
            "products": ["FX", "CIB"],
            "win_rate": 0,
            "uses": 23,
            "revenue": "Risk",
            "contributors": 2,
            "avatars": [
                ("CE", C["avatar_colors"][3]),
                ("AO", C["avatar_colors"][1]),
            ],
            "approach": [
                "Contact affected clients before 1 July deadline",
                "Restructure FX forward tenors from 90d to 60d",
                "Start BoG application in parallel with client",
                "Frame as compliance + opportunity (shorter tenors)",
            ],
            "avoid": [
                "Waiting for client to discover the rule change",
                "Assuming existing forwards auto-comply (they do not)",
            ],
            "docs": [
                ("CBN_Circular_TED_FEM.pdf", "PDF"),
                ("Impact_Assessment.xlsx", "XLSX"),
            ],
            "threads": 2,
            "updated": "Jun 2025",
            "rating": 5,
        },
        {
            "id": "KC-KE-INS-BUNDLE",
            "title": "Insurance + FX bundle for East African expansion",
            "subtitle": "40% higher conversion when bundling INS with FX",
            "category": "PROVEN",
            "cat_color": C["kc_verified"],
            "signal": "Insurance",
            "countries": ["KE", "TZ", "UG"],
            "products": ["INS", "FX"],
            "win_rate": 72,
            "uses": 8,
            "revenue": "R89M",
            "contributors": 5,
            "avatars": [
                ("DM", C["avatar_colors"][2]),
                ("GA", C["avatar_colors"][9]),
                ("SM", C["avatar_colors"][0]),
            ],
            "approach": [
                "Frame insurance as closing a geographic exclusion gap",
                "Include coverage cost in total FX bundle pricing",
                "Present asset risk scenario (uninsured loss example)",
                "Use cell SIM data to estimate asset base by country",
            ],
            "avoid": [
                "Saying 'you should also consider insurance'",
                "Separating insurance into a follow-up meeting",
                "Quoting insurance as a standalone premium",
            ],
            "docs": [
                ("INS_FX_Bundle_Deck.pptx", "PPTX"),
                ("Coverage_Gap_Calculator.xlsx", "XLSX"),
            ],
            "threads": 3,
            "updated": "Apr 2025",
            "rating": 4,
        },
        {
            "id": "KC-ZM-SEASONAL-CU",
            "title": "Copper season working capital timing",
            "subtitle": "Optimal WC facility timing for Zambian miners",
            "category": "PROVEN",
            "cat_color": C["kc_verified"],
            "signal": "Seasonal",
            "countries": ["ZM"],
            "products": ["CIB", "FX"],
            "win_rate": 83,
            "uses": 6,
            "revenue": "R42M",
            "contributors": 3,
            "avatars": [
                ("SM", C["avatar_colors"][0]),
                ("CB", C["avatar_colors"][7]),
            ],
            "approach": [
                "Offer seasonal WC facility before dry season (May)",
                "Structure drawdown to match production ramp-up",
                "Bundle ZMW/USD hedging for export proceeds",
                "Align repayment with rainy season wind-down (Mar)",
            ],
            "avoid": [
                "Offering flat annual facilities (ignores cycle)",
                "Pricing ZMW forwards without copper price overlay",
            ],
            "docs": [
                ("ZM_Copper_Season_Model.xlsx", "XLSX"),
            ],
            "threads": 2,
            "updated": "Feb 2025",
            "rating": 5,
        },
        {
            "id": "KC-MZ-MOMO-SUPPLY",
            "title": "MoMo supplier health scoring for credit risk",
            "subtitle": "Using MoMo regularity as informal credit signal",
            "category": "EXPERIMENTAL",
            "cat_color": C["accent_amber"],
            "signal": "Supply Chain",
            "countries": ["MZ", "CD"],
            "products": ["CIB", "CELL"],
            "win_rate": 60,
            "uses": 5,
            "revenue": "R28M",
            "contributors": 4,
            "avatars": [
                ("LM", C["avatar_colors"][5]),
                ("CB", C["avatar_colors"][7]),
            ],
            "approach": [
                "Track MoMo disbursement regularity to top 50 suppliers",
                "Regularity drop >30% for 2 weeks = early warning",
                "Cross-reference with CIB trade finance utilisation",
                "Present to client as supply chain risk advisory",
            ],
            "avoid": [
                "Sharing raw MoMo data with the client (privacy)",
                "Using MoMo as sole credit signal (supplement only)",
            ],
            "docs": [
                ("MoMo_Scoring_Framework.pdf", "PDF"),
                ("Risk_Advisory_Template.pptx", "PPTX"),
            ],
            "threads": 3,
            "updated": "May 2025",
            "rating": 4,
        },
        {
            "id": "KC-ONBOARD-001",
            "title": "New RM quick start guide: first 30 days",
            "subtitle": "What experienced RMs wish they knew in week one",
            "category": "ONBOARDING",
            "cat_color": C["kc_onboarding"],
            "signal": "Onboarding",
            "countries": [],
            "products": ["CIB", "FX", "INS", "CELL", "PBB"],
            "win_rate": 0,
            "uses": 42,
            "revenue": "Trust",
            "contributors": 8,
            "avatars": [
                ("TN", C["avatar_colors"][4]),
                ("SM", C["avatar_colors"][0]),
                ("AO", C["avatar_colors"][1]),
                ("DM", C["avatar_colors"][2]),
            ],
            "approach": [
                "Read top 5 Knowledge Cards before first client meeting",
                "Set up AfriFlow signal notifications on day 1",
                "Shadow a senior RM for first 3 client meetings",
                "Join Lekgotla country channels for your markets",
                "Post your first question within the first week",
            ],
            "avoid": [
                "Ignoring signals for first month (bad habit forms)",
                "Cold-calling without checking client 360 first",
                "Pitching products without seasonal context",
            ],
            "docs": [
                ("New_RM_Checklist.pdf", "PDF"),
                ("AfriFlow_Quick_Guide.pdf", "PDF"),
                ("Signal_Types_Explainer.pdf", "PDF"),
            ],
            "threads": 5,
            "updated": "May 2025",
            "rating": 5,
        },
    ]

    for ci, card in enumerate(cards_data):
        col = ci % 2
        row = ci // 2

        cx = 0.3 + col * (card_w + col_gap)
        cy = grid_top - row * (6.5 + row_gap)

        draw_knowledge_card(
            ax, cx, cy, card_w,
            card_id=card["id"],
            title=card["title"],
            subtitle=card["subtitle"],
            category=card["category"],
            category_color=card["cat_color"],
            signal_type=card["signal"],
            countries=card["countries"],
            products=card["products"],
            win_rate=card["win_rate"],
            uses=card["uses"],
            revenue=card["revenue"],
            contributors=card["contributors"],
            contributor_avatars=card["avatars"],
            approach_lines=card["approach"],
            avoid_lines=card["avoid"],
            documents=card["docs"],
            source_threads=card["threads"],
            last_updated=card["updated"],
            rating=card["rating"],
        )

    # ===================================================
    # BOTTOM STATUS BAR
    # ===================================================

    draw_box(
        ax, 0, 0, 36, 0.5,
        C["topbar_bg"],
        corner_radius=0.0,
        border_color=C["divider"],
        border_width=0.5,
    )

    ax.text(
        0.5, 0.25,
        "Knowledge Card Library  |  "
        "214 cards  |  "
        "64% avg win rate  |  "
        "R892M attributed revenue  |  "
        "42 contributors across 18 countries  |  "
        "Institutional memory that stays when "
        "people leave",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    ax.text(
        35.5, 0.25,
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
        output_dir, "knowledge_card_library.png"
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
        f"Knowledge Card Library saved to: "
        f"{output_path}"
    )

    small_path = os.path.join(
        output_dir,
        "knowledge_card_library_small.png",
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
        "Generating AfriFlow Knowledge Card "
        "Library..."
    )
    print()

    generate_knowledge_card_library()

    print()
    print("Knowledge Card Library generated.")
    print(
        "Files ready for embedding in "
        "README.md and documentation."
    )
