# diagrams/generate_signal_flow.py

"""
AfriFlow Signal Flow Diagram

We generate a detailed visual walkthrough showing
how a single cross-domain signal (Geographic
Expansion) is detected by correlating evidence
from four domains, building confidence at each
stage, and producing an actionable RM alert.

This diagram proves the core thesis: no single
domain can detect what we detect. The intelligence
emerges only from cross-domain correlation.

Usage:
    python diagrams/generate_signal_flow.py

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
from matplotlib.patches import FancyArrowPatch
from matplotlib.patches import Circle
from matplotlib.patches import Wedge
import numpy as np
import os


# -------------------------------------------------------
# Colour palette
# -------------------------------------------------------
C = {
    "bg": "#FAFBFC",
    "title": "#1B2631",
    "subtitle": "#566573",
    "annotation": "#7F8C8D",
    "cib": "#1B4F72",
    "cib_light": "#D4E6F1",
    "forex": "#1A5276",
    "forex_light": "#D6EAF8",
    "insurance": "#1E8449",
    "insurance_light": "#D5F5E3",
    "cell": "#7D6608",
    "cell_light": "#FEF9E7",
    "pbb": "#A93226",
    "pbb_light": "#FDEDEC",
    "conf_low": "#E74C3C",
    "conf_low_light": "#FDEDEC",
    "conf_med": "#F39C12",
    "conf_med_light": "#FEF9E7",
    "conf_high": "#27AE60",
    "conf_high_light": "#D5F5E3",
    "conf_very_high": "#1E8449",
    "conf_very_high_light": "#D5F5E3",
    "arrow_data": "#2C3E50",
    "arrow_correlation": "#27AE60",
    "arrow_output": "#8E44AD",
    "engine_bg": "#1C2833",
    "engine_border": "#566573",
    "engine_text": "#FFFFFF",
    "output_bg": "#0B5345",
    "output_text": "#FFFFFF",
    "evidence_bg": "#FFFFFF",
    "evidence_border": "#BDC3C7",
    "connector": "#2C3E50",
    "section_border": "#D5D8DC",
    "section_label": "#2C3E50",
    "white": "#FFFFFF",
    "plus": "#27AE60",
    "question": "#E74C3C",
    "gap": "#E74C3C",
    "gap_light": "#FDEDEC",
    "seasonal": "#00897B",
    "seasonal_light": "#E0F2F1",
    "shadow": "#8E44AD",
    "shadow_light": "#F3E5F5",
    "timeline": "#BDC3C7",
    "timeline_dot": "#2C3E50",
    "lekgotla_gold": "#D4A017",
    "accent_blue": "#2196F3",
}


def draw_box(
    ax, x, y, w, h, facecolor,
    text_lines=None, text_color="#FFFFFF",
    fontsize=7, bold_first=False,
    corner_radius=0.12, alpha=1.0,
    border_color=None, border_width=0.8,
    zorder=2, text_ha="center",
    shadow=False, linestyle="-",
):
    """Draw a rounded rectangle."""

    if shadow:
        s = FancyBboxPatch(
            (x + 0.06, y - 0.06), w, h,
            boxstyle=(
                f"round,pad=0.03,"
                f"rounding_size={corner_radius}"
            ),
            facecolor="#00000015",
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
            f"round,pad=0.03,"
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
        0.28, (h * 0.85) / max(n, 1)
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
            fontsize + 1
            if (i == 0 and bold_first)
            else fontsize
        )
        tx = (
            x + w / 2
            if text_ha == "center"
            else x + 0.15
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


def draw_arrow(
    ax, x1, y1, x2, y2,
    color="#2C3E50", linewidth=1.5,
    style="-|>", rad=0.0, zorder=3,
    linestyle="-",
):
    """Draw an arrow."""

    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style,
        connectionstyle=f"arc3,rad={rad}",
        color=color,
        linewidth=linewidth,
        linestyle=linestyle,
        mutation_scale=12,
        zorder=zorder,
    )
    ax.add_patch(arrow)


def draw_confidence_gauge(
    ax, cx, cy, pct, label,
    size=1.2,
):
    """Draw a semi-circular confidence gauge."""

    # Background arc
    bg_angles = np.linspace(180, 0, 100)
    bg_r = size
    bg_xs = cx + bg_r * np.cos(np.radians(bg_angles))
    bg_ys = cy + bg_r * np.sin(np.radians(bg_angles))

    ax.plot(
        bg_xs, bg_ys,
        color="#D5D8DC",
        linewidth=6,
        solid_capstyle="round",
        zorder=3,
    )

    # Filled arc
    if pct >= 80:
        fill_color = C["conf_very_high"]
    elif pct >= 60:
        fill_color = C["conf_high"]
    elif pct >= 40:
        fill_color = C["conf_med"]
    else:
        fill_color = C["conf_low"]

    fill_angle = 180 - (pct / 100) * 180
    fill_angles = np.linspace(
        180, fill_angle, max(int(pct), 2)
    )
    fill_xs = cx + bg_r * np.cos(
        np.radians(fill_angles)
    )
    fill_ys = cy + bg_r * np.sin(
        np.radians(fill_angles)
    )

    ax.plot(
        fill_xs, fill_ys,
        color=fill_color,
        linewidth=6,
        solid_capstyle="round",
        zorder=4,
    )

    # Percentage text
    ax.text(
        cx, cy + 0.15,
        f"{pct}%",
        ha="center", va="center",
        fontsize=14, fontweight="bold",
        color=fill_color,
        zorder=5,
    )

    # Label
    ax.text(
        cx, cy - 0.3,
        label,
        ha="center", va="center",
        fontsize=6,
        color=C["subtitle"],
        zorder=5,
    )


def draw_evidence_card(
    ax, x, y, w, h,
    domain_name, domain_color,
    domain_light, evidence_lines,
    is_gap=False, is_present=True,
):
    """Draw an evidence card from a domain."""

    bg = domain_light if is_present else C["gap_light"]
    border = domain_color if is_present else C["gap"]
    bw = 1.5 if is_present else 1.5

    draw_box(
        ax, x, y, w, h,
        bg,
        corner_radius=0.1,
        border_color=border,
        border_width=bw,
        shadow=True,
    )

    # Domain header
    header_h = 0.55

    draw_box(
        ax, x, y + h - header_h,
        w, header_h,
        domain_color if is_present else C["gap"],
        corner_radius=0.08,
    )

    ax.text(
        x + w / 2,
        y + h - header_h / 2,
        domain_name,
        ha="center", va="center",
        fontsize=8, fontweight="bold",
        color=C["white"],
        zorder=4,
    )

    # Evidence lines
    start_y = y + h - header_h - 0.35

    for ei, eline in enumerate(evidence_lines):
        ey = start_y - ei * 0.32

        # Detect value highlights
        ec = C["section_label"]
        ew = "normal"

        if eline.startswith(">>"):
            ec = domain_color if is_present else C["gap"]
            ew = "bold"
            eline = eline[2:].strip()
        elif eline.startswith("!!"):
            ec = C["gap"]
            ew = "bold"
            eline = eline[2:].strip()

        ax.text(
            x + 0.2, ey,
            eline,
            ha="left", va="center",
            fontsize=6,
            fontweight=ew,
            color=ec,
            zorder=3,
        )

    # Status indicator (bottom)
    if is_gap:
        draw_box(
            ax, x + 0.15, y + 0.15,
            w - 0.3, 0.35,
            C["gap_light"],
            text_lines=["COVERAGE GAP DETECTED"],
            text_color=C["gap"],
            fontsize=5.5,
            bold_first=True,
            corner_radius=0.05,
            border_color=C["gap"],
            border_width=0.8,
        )


def draw_plus_connector(ax, x, y, size=0.35):
    """Draw a plus sign connector."""

    circle = Circle(
        (x, y), size,
        facecolor=C["white"],
        edgecolor=C["plus"],
        linewidth=2.0,
        zorder=6,
    )
    ax.add_patch(circle)

    ax.text(
        x, y,
        "+",
        ha="center", va="center",
        fontsize=16, fontweight="bold",
        color=C["plus"],
        zorder=7,
    )


def generate_signal_flow():
    """Generate the signal flow diagram."""

    fig, ax = plt.subplots(1, 1, figsize=(32, 24))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(-1, 33)
    ax.set_ylim(-1, 24)
    ax.set_aspect("equal")
    ax.axis("off")

    # ===================================================
    # TITLE
    # ===================================================

    ax.text(
        16, 23.3,
        "AfriFlow: Cross-Domain Signal "
        "Detection Flow",
        ha="center", va="center",
        fontsize=18, fontweight="bold",
        color=C["title"],
        fontfamily="sans-serif",
    )

    ax.text(
        16, 22.6,
        "How we detect corporate geographic "
        "expansion 4 to 8 weeks before "
        "competitors",
        ha="center", va="center",
        fontsize=10,
        color=C["subtitle"],
        fontfamily="sans-serif",
    )

    ax.text(
        16, 22.0,
        "DISCLAIMER: Concept demonstration by "
        "Thabo Kunene. Not a sanctioned "
        "initiative of Standard Bank Group "
        "or MTN.",
        ha="center", va="center",
        fontsize=6.5,
        color=C["annotation"],
        fontstyle="italic",
        fontfamily="sans-serif",
    )

    # ===================================================
    # PHASE 1: RAW DOMAIN EVIDENCE (top row)
    # ===================================================

    ax.text(
        0.5, 21.0,
        "PHASE 1: DOMAIN EVIDENCE COLLECTION",
        ha="left", va="center",
        fontsize=9, fontweight="bold",
        color=C["section_label"],
    )

    ax.text(
        0.5, 20.6,
        "Each domain sees its own fragment. "
        "Alone, none is conclusive.",
        ha="left", va="center",
        fontsize=7,
        color=C["annotation"],
        fontstyle="italic",
    )

    card_w = 6.8
    card_h = 4.5
    card_gap = 0.8
    card_y = 15.5

    # CIB Evidence
    draw_evidence_card(
        ax, 0.5, card_y, card_w, card_h,
        "CIB (Corporate Investment Banking)",
        C["cib"], C["cib_light"],
        [
            "Payment activity detected:",
            "",
            ">> 5 new payments to Kenya",
            ">> R45M total in 30 days",
            ">> 3 new Kenyan counterparties",
            ">> First payment: 14 May 2025",
            "",
            "Pattern: New corridor opening",
            "",
            "Alone, this could be a one-off",
            "supplier payment. Not conclusive.",
        ],
    )

    # Plus connector
    draw_plus_connector(
        ax, 0.5 + card_w + card_gap / 2,
        card_y + card_h / 2,
    )

    # Cell Evidence
    draw_evidence_card(
        ax,
        0.5 + card_w + card_gap,
        card_y, card_w, card_h,
        "CELL NETWORK (MTN Partnership)",
        C["cell"], C["cell_light"],
        [
            "SIM activation spike detected:",
            "",
            ">> 200 new corporate SIMs",
            ">> Location: Nairobi, Kenya",
            ">> Growth: 340% month on month",
            ">> SIM deflation (KE: 0.48):",
            ">>   ~96 estimated employees",
            "",
            "Pattern: Workforce deployment",
            "",
            "Alone, could be a temporary",
            "project. Not conclusive.",
        ],
    )

    # Plus connector
    draw_plus_connector(
        ax,
        0.5 + 2 * card_w + 1.5 * card_gap,
        card_y + card_h / 2,
    )

    # Forex Evidence
    draw_evidence_card(
        ax,
        0.5 + 2 * (card_w + card_gap),
        card_y, card_w, card_h,
        "FOREX (Foreign Exchange / Treasury)",
        C["forex"], C["forex_light"],
        [
            "Hedging check result:",
            "",
            "!! ZERO KES hedging in place",
            "!! No forward contracts for KES",
            "!! No option contracts for KES",
            "!! R45M unhedged KES exposure",
            "",
            "Pattern: Unprotected exposure",
            "",
            "The client is operating in Kenya",
            "without currency protection.",
        ],
        is_gap=True,
    )

    # Plus connector
    draw_plus_connector(
        ax,
        0.5 + 3 * card_w + 2.5 * card_gap,
        card_y + card_h / 2,
    )

    # Insurance Evidence
    draw_evidence_card(
        ax,
        0.5 + 3 * (card_w + card_gap),
        card_y, card_w, card_h,
        "INSURANCE (Liberty / Std Bank)",
        C["insurance"], C["insurance_light"],
        [
            "Coverage check result:",
            "",
            "!! ZERO policies in Kenya",
            "!! No asset insurance",
            "!! No trade credit insurance",
            "!! No liability coverage",
            "",
            "Pattern: Unprotected operations",
            "",
            "The client has operations and",
            "employees in Kenya with no",
            "insurance coverage whatsoever.",
        ],
        is_gap=True,
    )

    # ===================================================
    # CONFIDENCE ARROWS (Phase 1 to Phase 2)
    # ===================================================

    # Arrow labels showing confidence building
    arrow_y = card_y - 0.5

    confidence_stages = [
        (
            0.5 + card_w / 2,
            "CIB alone",
            "40%",
            C["conf_low"],
            "Maybe a one-off",
        ),
        (
            0.5 + card_w + card_gap + card_w / 2,
            "CIB + Cell",
            "75%",
            C["conf_high"],
            "Likely expanding",
        ),
        (
            0.5 + 2 * (card_w + card_gap) + card_w / 2,
            "CIB + Cell + FX",
            "88%",
            C["conf_high"],
            "Expanding AND unprotected",
        ),
        (
            0.5 + 3 * (card_w + card_gap) + card_w / 2,
            "All 4 domains",
            "95%",
            C["conf_very_high"],
            "Expansion confirmed,\nmultiple product gaps",
        ),
    ]

    for cx, clabel, cpct, ccolor, cdesc in confidence_stages:
        # Down arrow from card
        draw_arrow(
            ax,
            cx, card_y,
            cx, arrow_y - 0.2,
            color=ccolor,
            linewidth=2.0,
        )

        # Confidence box
        draw_box(
            ax,
            cx - 1.8, arrow_y - 1.5,
            3.6, 1.2,
            ccolor,
            text_lines=[
                clabel,
                f"Confidence: {cpct}",
                cdesc,
            ],
            text_color=C["white"],
            fontsize=6,
            bold_first=True,
            corner_radius=0.08,
            shadow=True,
        )

    # Horizontal arrows between confidence stages
    for i in range(len(confidence_stages) - 1):
        x1 = confidence_stages[i][0] + 1.8
        x2 = confidence_stages[i + 1][0] - 1.8
        y = arrow_y - 0.9

        draw_arrow(
            ax, x1, y, x2, y,
            color=C["arrow_correlation"],
            linewidth=2.5,
            style="-|>",
        )

        ax.text(
            (x1 + x2) / 2, y + 0.25,
            "correlate",
            ha="center", va="center",
            fontsize=5.5,
            color=C["arrow_correlation"],
            fontweight="bold",
            fontstyle="italic",
        )

    # ===================================================
    # PHASE 2: CORRELATION ENGINE (centre)
    # ===================================================

    engine_y = 9.2
    engine_h = 3.5
    engine_w = 22.0
    engine_x = 5.5

    ax.text(
        0.5, engine_y + engine_h + 0.6,
        "PHASE 2: CROSS-DOMAIN CORRELATION ENGINE",
        ha="left", va="center",
        fontsize=9, fontweight="bold",
        color=C["section_label"],
    )

    ax.text(
        0.5, engine_y + engine_h + 0.2,
        "The intelligence emerges from "
        "combining evidence across domains. "
        "No single domain triggers this alone.",
        ha="left", va="center",
        fontsize=7,
        color=C["annotation"],
        fontstyle="italic",
    )

    # Arrows from confidence boxes to engine
    for cx, _, _, ccolor, _ in confidence_stages:
        draw_arrow(
            ax,
            cx, arrow_y - 1.5,
            engine_x + engine_w / 2,
            engine_y + engine_h,
            color=ccolor,
            linewidth=1.5,
            rad=0.0,
            style="-|>",
            linestyle=(0, (4, 2)),
        )

    draw_box(
        ax,
        engine_x, engine_y,
        engine_w, engine_h,
        C["engine_bg"],
        corner_radius=0.15,
        border_color=C["engine_border"],
        border_width=2.0,
        shadow=True,
    )

    # Engine title
    ax.text(
        engine_x + engine_w / 2,
        engine_y + engine_h - 0.45,
        "EXPANSION SIGNAL DETECTOR",
        ha="center", va="center",
        fontsize=11, fontweight="bold",
        color=C["engine_text"],
        zorder=3,
    )

    # Engine components (horizontal)
    components = [
        (
            "Entity\nResolution",
            "Match client\nacross domains",
            C["cib"],
        ),
        (
            "Seasonal\nAdjustment",
            "Is this drop\nnormal for season?",
            C["seasonal"],
        ),
        (
            "SIM\nDeflation",
            "200 SIMs x 0.48\n= 96 employees",
            C["cell"],
        ),
        (
            "Data Shadow\nCheck",
            "What is MISSING\nthat should be there?",
            C["shadow"],
        ),
        (
            "Confidence\nCalculation",
            "Weight evidence\nacross domains",
            C["conf_very_high"],
        ),
    ]

    comp_w = 3.6
    comp_h = 1.8
    comp_gap = 0.5
    comp_total_w = (
        len(components) * comp_w
        + (len(components) - 1) * comp_gap
    )
    comp_start_x = (
        engine_x
        + (engine_w - comp_total_w) / 2
    )

    for ci, (ctitle, cdesc, ccolor) in enumerate(
        components
    ):
        cx = comp_start_x + ci * (comp_w + comp_gap)
        cy = engine_y + 0.4

        draw_box(
            ax, cx, cy,
            comp_w, comp_h,
            ccolor,
            text_lines=[ctitle, "", cdesc],
            text_color=C["white"],
            fontsize=5.5,
            bold_first=True,
            corner_radius=0.08,
        )

        # Arrows between components
        if ci < len(components) - 1:
            draw_arrow(
                ax,
                cx + comp_w, cy + comp_h / 2,
                cx + comp_w + comp_gap,
                cy + comp_h / 2,
                color=C["engine_text"],
                linewidth=1.5,
                style="-|>",
            )

    # ===================================================
    # PHASE 3: CONFIDENCE GAUGE
    # ===================================================

    gauge_y = 5.5

    ax.text(
        0.5, gauge_y + 2.5,
        "PHASE 3: CONFIDENCE ASSESSMENT",
        ha="left", va="center",
        fontsize=9, fontweight="bold",
        color=C["section_label"],
    )

    # Arrow from engine to gauge
    draw_arrow(
        ax,
        engine_x + engine_w / 2, engine_y,
        16, gauge_y + 2.0,
        color=C["arrow_output"],
        linewidth=3.0,
        style="-|>",
    )

    # Confidence gauge
    draw_confidence_gauge(
        ax, 16, gauge_y, 95,
        "EXPANSION CONFIDENCE",
        size=1.5,
    )

    # Evidence summary boxes around gauge
    evidence_summary = [
        (
            5.0, gauge_y + 1.0, 4.5, 1.8,
            "CIB EVIDENCE",
            C["cib"],
            [
                "5 new payments to Kenya",
                "R45M in 30 days",
                "3 new counterparties",
                "Score: +30 points",
            ],
        ),
        (
            5.0, gauge_y - 1.2, 4.5, 1.8,
            "CELL EVIDENCE",
            C["cell"],
            [
                "200 SIMs in Nairobi",
                "340% MoM growth",
                "96 est. employees (deflated)",
                "Score: +25 points",
            ],
        ),
        (
            22.5, gauge_y + 1.0, 4.5, 1.8,
            "FX GAP EVIDENCE",
            C["forex"],
            [
                "ZERO KES hedging",
                "R45M unhedged",
                "No forwards or options",
                "Score: +15 points (gap)",
            ],
        ),
        (
            22.5, gauge_y - 1.2, 4.5, 1.8,
            "INSURANCE GAP",
            C["insurance"],
            [
                "ZERO Kenya coverage",
                "No asset insurance",
                "No liability coverage",
                "Score: +10 points (gap)",
            ],
        ),
    ]

    for (
        ex, ey, ew, eh,
        elabel, ecolor, elines,
    ) in evidence_summary:

        draw_box(
            ax, ex, ey, ew, eh,
            C["white"],
            corner_radius=0.08,
            border_color=ecolor,
            border_width=1.5,
            shadow=True,
        )

        ax.text(
            ex + 0.2, ey + eh - 0.25,
            elabel,
            ha="left", va="center",
            fontsize=6, fontweight="bold",
            color=ecolor,
            zorder=3,
        )

        for li, line in enumerate(elines):
            ly = ey + eh - 0.6 - li * 0.28

            lc = C["section_label"]
            lw = "normal"

            if "Score:" in line:
                lc = ecolor
                lw = "bold"
            elif "ZERO" in line:
                lc = C["gap"]
                lw = "bold"

            ax.text(
                ex + 0.2, ly,
                line,
                ha="left", va="center",
                fontsize=5.5,
                fontweight=lw,
                color=lc,
                zorder=3,
            )

        # Arrows to gauge
        if ex < 16:
            draw_arrow(
                ax,
                ex + ew, ey + eh / 2,
                14.5, gauge_y + 0.3,
                color=ecolor,
                linewidth=1.0,
                style="->",
                rad=0.1 if ey > gauge_y else -0.1,
                linestyle=(0, (3, 2)),
            )
        else:
            draw_arrow(
                ax,
                ex, ey + eh / 2,
                17.5, gauge_y + 0.3,
                color=ecolor,
                linewidth=1.0,
                style="->",
                rad=-0.1 if ey > gauge_y else 0.1,
                linestyle=(0, (3, 2)),
            )

    # Scoring breakdown
    ax.text(
        16, gauge_y - 1.8,
        "CONFIDENCE SCORING",
        ha="center", va="center",
        fontsize=7, fontweight="bold",
        color=C["section_label"],
    )

    scoring = [
        ("CIB: 5+ payments", "+30", C["cib"]),
        ("Cell: 100+ SIMs", "+25", C["cell"]),
        ("FX: hedging absent", "+15", C["forex"]),
        ("INS: coverage absent", "+10", C["insurance"]),
        ("PBB: payroll check", "+15", C["pbb"]),
    ]

    for si, (slabel, spoints, scolor) in enumerate(
        scoring
    ):
        sx = 12.0 + (si % 3) * 3.2
        sy = (
            gauge_y - 2.2
            if si < 3
            else gauge_y - 2.7
        )

        ax.text(
            sx, sy,
            f"{slabel}: ",
            ha="left", va="center",
            fontsize=5.5,
            color=C["section_label"],
            zorder=3,
        )

        ax.text(
            sx + 2.5, sy,
            spoints,
            ha="left", va="center",
            fontsize=6, fontweight="bold",
            color=scolor,
            zorder=3,
        )

    ax.text(
        21.2, gauge_y - 2.7,
        "TOTAL: 95/99",
        ha="left", va="center",
        fontsize=7, fontweight="bold",
        color=C["conf_very_high"],
    )

    # ===================================================
    # PHASE 4: OUTPUT (bottom)
    # ===================================================

    output_y = 0.5
    output_h = 3.0

    ax.text(
        0.5, output_y + output_h + 0.6,
        "PHASE 4: ACTIONABLE OUTPUT",
        ha="left", va="center",
        fontsize=9, fontweight="bold",
        color=C["section_label"],
    )

    ax.text(
        0.5, output_y + output_h + 0.2,
        "The signal generates three outputs "
        "simultaneously: RM alert, Salesforce "
        "task, and Lekgotla thread.",
        ha="left", va="center",
        fontsize=7,
        color=C["annotation"],
        fontstyle="italic",
    )

    # Arrow from gauge to output
    draw_arrow(
        ax,
        16, gauge_y - 2.9,
        16, output_y + output_h,
        color=C["arrow_output"],
        linewidth=3.0,
        style="-|>",
    )

    # RM Alert output
    alert_w = 10.0

    draw_box(
        ax,
        0.5, output_y,
        alert_w, output_h,
        C["output_bg"],
        corner_radius=0.12,
        border_color="#0E6655",
        border_width=2.0,
        shadow=True,
    )

    ax.text(
        0.5 + alert_w / 2,
        output_y + output_h - 0.35,
        "RM PUSH ALERT",
        ha="center", va="center",
        fontsize=9, fontweight="bold",
        color=C["output_text"],
        zorder=3,
    )

    alert_lines = [
        "EXPANSION DETECTED: Acme Corp",
        "expanding into Kenya",
        "",
        "Confidence: 95%  |  Urgency: IMMEDIATE",
        "",
        "Evidence: 5 new CIB payments (R45M)",
        "+ 200 new SIMs in Nairobi",
        "+ ZERO KES hedging + ZERO insurance",
        "",
        "Estimated opportunity: R120M",
        "",
        "ACTION: Contact CFO within 48 hours.",
        "You are 4 to 6 weeks ahead of",
        "competitors.",
    ]

    for li, line in enumerate(alert_lines):
        ly = (
            output_y + output_h - 0.7
            - li * 0.18
        )

        lc = C["output_text"]
        lw = "normal"
        lfs = 5

        if "EXPANSION" in line:
            lc = "#A3E4D7"
            lw = "bold"
            lfs = 5.5
        elif "Confidence" in line:
            lc = "#A3E4D7"
            lw = "bold"
        elif "R120M" in line:
            lc = "#A3E4D7"
            lw = "bold"
        elif "ACTION" in line:
            lc = "#FFFFFF"
            lw = "bold"

        ax.text(
            1.0, ly,
            line,
            ha="left", va="center",
            fontsize=lfs,
            fontweight=lw,
            color=lc,
            zorder=3,
        )

    # Salesforce Task output
    sf_x = 0.5 + alert_w + 0.5
    sf_w = 7.0

    draw_box(
        ax, sf_x, output_y,
        sf_w, output_h,
        C["white"],
        corner_radius=0.12,
        border_color=C["accent_blue"],
        border_width=2.0,
        shadow=True,
    )

    ax.text(
        sf_x + sf_w / 2,
        output_y + output_h - 0.35,
        "SALESFORCE TASK (AUTO-CREATED)",
        ha="center", va="center",
        fontsize=8, fontweight="bold",
        color=C["accent_blue"],
        zorder=3,
    )

    sf_lines = [
        ("Subject:", "Kenya expansion follow-up"),
        ("Client:", "Acme Corp (Platinum)"),
        ("Owner:", "Sipho Mabena"),
        ("Due:", "48 hours"),
        ("Priority:", "Urgent"),
        ("", ""),
        ("Products:", "Working capital"),
        ("", "KES forward contract"),
        ("", "Asset insurance"),
        ("", "Payroll capture (96 staff)"),
    ]

    for li, (flabel, fval) in enumerate(sf_lines):
        ly = (
            output_y + output_h - 0.7
            - li * 0.22
        )

        if flabel:
            ax.text(
                sf_x + 0.2, ly,
                flabel,
                ha="left", va="center",
                fontsize=5, fontweight="bold",
                color=C["subtitle"],
                zorder=3,
            )

        ax.text(
            sf_x + 1.5, ly,
            fval,
            ha="left", va="center",
            fontsize=5,
            color=C["section_label"],
            zorder=3,
        )

    # Lekgotla output
    lk_x = sf_x + sf_w + 0.5
    lk_w = 32 - lk_x - 0.5

    draw_box(
        ax, lk_x, output_y,
        lk_w, output_h,
        C["white"],
        corner_radius=0.12,
        border_color=C["lekgotla_gold"],
        border_width=2.0,
        shadow=True,
    )

    ax.text(
        lk_x + lk_w / 2,
        output_y + output_h - 0.35,
        "LEKGOTLA CONTEXT",
        ha="center", va="center",
        fontsize=8, fontweight="bold",
        color=C["lekgotla_gold"],
        zorder=3,
    )

    lk_lines = [
        "This signal has been triggered",
        "23 times in the past 12 months.",
        "",
        "Top Knowledge Card:",
        "KC-GH-EXPANSION-001",
        "Bundle pricing approach",
        "Win rate: 64%  |  Revenue: R155M",
        "",
        "Key insight from practitioners:",
        "\"Bundle WC + FX + insurance in",
        " the first meeting. Do not lead",
        " with insurance separately.\"",
    ]

    for li, line in enumerate(lk_lines):
        ly = (
            output_y + output_h - 0.7
            - li * 0.19
        )

        lc = C["section_label"]
        lw = "normal"

        if "KC-GH" in line:
            lc = C["conf_very_high"]
            lw = "bold"
        elif "Win rate" in line:
            lc = C["conf_very_high"]
            lw = "bold"
        elif line.startswith('"') or line.startswith(' '):
            lc = C["lekgotla_gold"]
            lw = "normal"

        ax.text(
            lk_x + 0.2, ly,
            line,
            ha="left", va="center",
            fontsize=5,
            fontweight=lw,
            color=lc,
            zorder=3,
        )

    # ===================================================
    # TIMELINE (left side)
    # ===================================================

    tl_x = -0.3
    tl_top = 21.0
    tl_bottom = 0.5

    ax.plot(
        [tl_x, tl_x],
        [tl_bottom, tl_top],
        color=C["timeline"],
        linewidth=2.0,
        zorder=1,
        solid_capstyle="round",
    )

    timeline_events = [
        (20.0, "T+0", "CIB payment detected"),
        (17.0, "T+0", "Cell SIM data correlated"),
        (12.5, "T+1s", "FX and INS gaps checked"),
        (9.5, "T+3s", "Correlation engine runs"),
        (5.5, "T+5s", "Confidence calculated"),
        (2.0, "T+8s", "Alert delivered to RM"),
    ]

    for ty, tlabel, tdesc in timeline_events:
        dot = Circle(
            (tl_x, ty), 0.12,
            facecolor=C["timeline_dot"],
            edgecolor=C["white"],
            linewidth=1.0,
            zorder=5,
        )
        ax.add_patch(dot)

        ax.text(
            tl_x - 0.3, ty,
            tlabel,
            ha="right", va="center",
            fontsize=6, fontweight="bold",
            color=C["timeline_dot"],
            zorder=5,
        )

        ax.text(
            tl_x + 0.3, ty,
            tdesc,
            ha="left", va="center",
            fontsize=5.5,
            color=C["annotation"],
            fontstyle="italic",
            zorder=5,
        )

    ax.text(
        tl_x, tl_top + 0.4,
        "TIMELINE",
        ha="center", va="center",
        fontsize=7, fontweight="bold",
        color=C["annotation"],
    )

    # ===================================================
    # KEY INSIGHT CALLOUT
    # ===================================================

    ax.annotate(
        "THE KEY INSIGHT\n"
        "\n"
        "CIB alone: 40% confidence\n"
        "(could be one-off payment)\n"
        "\n"
        "CIB + Cell: 75% confidence\n"
        "(SIM deployment confirms intent)\n"
        "\n"
        "CIB + Cell + FX gap: 88%\n"
        "(expanding AND unprotected)\n"
        "\n"
        "All 4 domains: 95% confidence\n"
        "(confirmed with product gaps)\n"
        "\n"
        "No single domain reaches 95%.\n"
        "The intelligence is in the\n"
        "CORRELATION, not the data.",
        xy=(16, 12.7),
        xytext=(28.5, 16.5),
        fontsize=6,
        color="#922B21",
        fontfamily="sans-serif",
        fontweight="bold",
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor="#FDEDEC",
            edgecolor="#922B21",
            linewidth=1.5,
            alpha=0.95,
        ),
        arrowprops=dict(
            arrowstyle="-|>",
            connectionstyle="arc3,rad=-0.2",
            color="#922B21",
            linewidth=2.0,
        ),
        zorder=10,
    )

    # ===================================================
    # LEGEND
    # ===================================================

    legend_y = -0.5

    legend_items = [
        (C["cib"], "CIB domain evidence"),
        (C["cell"], "Cell domain evidence"),
        (C["forex"], "Forex gap (absent data)"),
        (C["insurance"], "Insurance gap (absent data)"),
        (C["conf_low"], "Low confidence (<50%)"),
        (C["conf_high"], "High confidence (60-80%)"),
        (C["conf_very_high"], "Very high confidence (>80%)"),
        (C["arrow_output"], "Output generation"),
    ]

    for li, (lcolor, llabel) in enumerate(
        legend_items
    ):
        lx = 1.0 + (li % 4) * 7.8
        ly = (
            legend_y
            if li < 4
            else legend_y - 0.5
        )

        draw_box(
            ax, lx - 0.25, ly - 0.1,
            0.4, 0.2,
            lcolor,
            corner_radius=0.04,
        )

        ax.text(
            lx + 0.3, ly,
            llabel,
            ha="left", va="center",
            fontsize=5.5,
            color=C["connector"],
            fontfamily="sans-serif",
        )

    # ===================================================
    # SAVE
    # ===================================================

    output_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    output_path = os.path.join(
        output_dir, "signal_flow_diagram.png"
    )
    fig.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        pad_inches=0.4,
        facecolor=C["bg"],
        edgecolor="none",
    )
    print(
        f"Signal flow diagram saved to: "
        f"{output_path}"
    )

    small_path = os.path.join(
        output_dir,
        "signal_flow_diagram_small.png",
    )
    fig.savefig(
        small_path,
        dpi=100,
        bbox_inches="tight",
        pad_inches=0.4,
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
        "Generating AfriFlow Signal Flow "
        "Diagram..."
    )
    print()

    generate_signal_flow()

    print()
    print("Signal flow diagram generated.")
    print(
        "Files ready for embedding in "
        "README.md, Strategic Analysis, "
        "and Development Brief."
    )
