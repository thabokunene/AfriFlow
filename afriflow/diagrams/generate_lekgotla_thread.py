# diagrams/generate_lekgotla_thread.py

"""
AfriFlow Lekgotla Thread View

We generate a high fidelity mockup of a single
Lekgotla discussion thread, showing how
practitioners deliberate on a real challenge
anchored to an AfriFlow cross-domain signal.

This screen is where institutional wisdom is
created. It is the conversation under the tree.

Usage:
    python diagrams/generate_lekgotla_thread.py

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
from matplotlib.patches import FancyArrowPatch
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
    "knowledge_card": "#2E4A1A",
    "knowledge_border": "#4CAF50",
    "thread_bg": "#0F1A28",
    "post_bg": "#131F30",
    "post_border": "#1E3048",
    "post_op": "#142840",
    "post_op_border": "#1976D2",
    "post_best": "#1A2E1A",
    "post_best_border": "#43A047",
    "post_compliance": "#2A1A2A",
    "post_compliance_border": "#8E24AA",
    "reply_bg": "#0D1620",
    "reply_border": "#1E3048",
    "upvote_active": "#43A047",
    "upvote_inactive": "#2A3A4A",
    "tag_bg": "#1A2A3A",
    "tag_border": "#2A4A6A",
    "tag_text": "#6A9ACA",
    "signal_link_bg": "#1A1A2E",
    "signal_link_border": "#3A3ACA",
    "kc_link_bg": "#1A2E1A",
    "kc_link_border": "#4CAF50",
    "sidebar_bg": "#0D1620",
    "sidebar_border": "#1E3048",
    "composer_bg": "#0F1A28",
    "composer_border": "#2A4A6A",
    "avatar_1": "#1976D2",
    "avatar_2": "#E53935",
    "avatar_3": "#43A047",
    "avatar_4": "#8E24AA",
    "avatar_5": "#FB8C00",
    "avatar_6": "#00897B",
    "verified_bg": "#1A3A1A",
    "verified_border": "#43A047",
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


def draw_avatar(ax, x, y, initials, color, size=0.3):
    """Draw a circular avatar with initials."""

    circle = Circle(
        (x, y), size,
        facecolor=color,
        edgecolor=C["card_bg"],
        linewidth=0.8,
        zorder=5,
    )
    ax.add_patch(circle)

    ax.text(
        x, y,
        initials,
        ha="center", va="center",
        fontsize=5 if size >= 0.3 else 4,
        fontweight="bold",
        color="#FFFFFF",
        zorder=6,
    )


def draw_upvote_block(ax, x, y, count, user_voted=False):
    """Draw an upvote button with count."""

    # Up arrow
    arrow_color = (
        C["upvote_active"]
        if user_voted
        else C["upvote_inactive"]
    )

    ax.text(
        x, y + 0.15,
        "^",
        ha="center", va="center",
        fontsize=8, fontweight="bold",
        color=arrow_color,
        zorder=5,
    )

    # Count
    ax.text(
        x, y - 0.1,
        str(count),
        ha="center", va="center",
        fontsize=6, fontweight="bold",
        color=(
            C["upvote_active"]
            if user_voted or count >= 10
            else C["text_secondary"]
        ),
        zorder=5,
    )


def draw_tag(ax, x, y, text, color=None):
    """Draw a tag badge and return its width."""

    tc = color if color else C["tag_text"]
    tag_w = len(text) * 0.1 + 0.3

    draw_box(
        ax, x, y - 0.12,
        tag_w, 0.24,
        C["tag_bg"],
        text_lines=[text],
        text_color=tc,
        fontsize=4.5,
        corner_radius=0.04,
        border_color=C["tag_border"],
        border_width=0.3,
    )

    return tag_w


def draw_post(
    ax, x, y, w,
    author_name, author_role,
    author_country, author_initials,
    author_color, post_time,
    body_lines, upvotes,
    tags=None, is_op=False,
    is_best=False, is_compliance=False,
    verified_win=False, badge_text=None,
    attachments=None, user_voted=False,
    linked_signal=None, reply_count=None,
):
    """
    Draw a complete discussion post.
    Returns the total height consumed.
    """

    if tags is None:
        tags = []
    if attachments is None:
        attachments = []

    # Calculate height
    body_h = len(body_lines) * 0.24
    tags_h = 0.35 if tags else 0
    attach_h = 0.3 if attachments else 0
    signal_h = 0.45 if linked_signal else 0
    header_h = 0.6
    footer_h = 0.4
    padding = 0.3

    total_h = (
        header_h + body_h + tags_h
        + attach_h + signal_h + footer_h
        + padding
    )

    # Background
    if is_op:
        bg = C["post_op"]
        border = C["post_op_border"]
    elif is_best:
        bg = C["post_best"]
        border = C["post_best_border"]
    elif is_compliance:
        bg = C["post_compliance"]
        border = C["post_compliance_border"]
    else:
        bg = C["post_bg"]
        border = C["post_border"]

    draw_box(
        ax, x, y - total_h,
        w, total_h,
        bg,
        corner_radius=0.08,
        border_color=border,
        border_width=1.0 if (is_op or is_best) else 0.5,
        shadow=is_op or is_best,
    )

    # Badge (if any)
    if badge_text:
        badge_colors = {
            "ORIGINAL POST": C["accent_blue"],
            "BEST ANSWER": C["accent_green"],
            "COMPLIANCE": C["accent_purple"],
            "PROVEN APPROACH": C["accent_green"],
            "LOCAL CONTEXT": C["accent_teal"],
            "REGULATORY ALERT": C["accent_red"],
        }
        bc = badge_colors.get(
            badge_text, C["accent_blue"]
        )
        badge_w = len(badge_text) * 0.1 + 0.4

        draw_box(
            ax,
            x + w - badge_w - 0.15,
            y - 0.15,
            badge_w, 0.28,
            bc,
            text_lines=[badge_text],
            text_color="#FFFFFF",
            fontsize=4.5,
            corner_radius=0.04,
        )

    # Verified win badge
    if verified_win:
        draw_box(
            ax,
            x + w - 2.5,
            y - 0.15,
            1.2, 0.28,
            C["verified_bg"],
            text_lines=["VERIFIED WIN"],
            text_color=C["verified_border"],
            fontsize=4,
            corner_radius=0.04,
            border_color=C["verified_border"],
            border_width=0.5,
        )

    # Upvote block (left side)
    draw_upvote_block(
        ax,
        x + 0.35, y - 0.65,
        upvotes, user_voted,
    )

    # Avatar
    avatar_x = x + 0.9
    avatar_y = y - 0.5
    draw_avatar(
        ax, avatar_x, avatar_y,
        author_initials, author_color,
    )

    # Author info
    ax.text(
        avatar_x + 0.45, avatar_y + 0.1,
        author_name,
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    ax.text(
        avatar_x + 0.45, avatar_y - 0.15,
        f"{author_role}, {author_country}",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    # Post time
    ax.text(
        x + w - 0.15,
        avatar_y - 0.15,
        post_time,
        ha="right", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    # Body text
    body_start_y = y - header_h - 0.2

    for bi, line in enumerate(body_lines):
        by = body_start_y - bi * 0.24

        # Detect quoted text
        if line.startswith(">"):
            # Quote styling
            draw_box(
                ax,
                x + 0.7, by - 0.1,
                w - 1.0, 0.22,
                C["card_header"],
                corner_radius=0.03,
                border_color=C["divider"],
                border_width=0.3,
            )

            # Quote bar
            draw_box(
                ax,
                x + 0.7, by - 0.1,
                0.05, 0.22,
                C["accent_blue"],
                corner_radius=0.01,
            )

            ax.text(
                x + 0.9, by,
                line[2:],
                ha="left", va="center",
                fontsize=5,
                color=C["text_secondary"],
                fontstyle="italic",
                zorder=3,
            )
        else:
            fc = C["text_primary"]

            # Highlight key phrases
            if any(
                kw in line.lower()
                for kw in [
                    "lesson:", "tip:", "key:",
                    "important:", "warning:",
                ]
            ):
                fc = C["accent_amber"]

            ax.text(
                x + 0.7, by,
                line,
                ha="left", va="center",
                fontsize=5,
                color=fc,
                zorder=3,
            )

    # Linked signal (if any)
    if linked_signal:
        sig_y = (
            body_start_y
            - len(body_lines) * 0.24
            - 0.15
        )

        draw_box(
            ax,
            x + 0.7, sig_y - 0.35,
            w - 1.0, 0.4,
            C["signal_link_bg"],
            corner_radius=0.05,
            border_color=C["signal_link_border"],
            border_width=0.5,
        )

        ax.text(
            x + 0.85, sig_y - 0.15,
            f"Linked signal: {linked_signal}",
            ha="left", va="center",
            fontsize=4.5,
            color=C["accent_blue"],
            fontweight="bold",
            zorder=3,
        )

    # Tags
    if tags:
        tag_y = y - total_h + footer_h + tags_h
        tag_x = x + 0.7

        for tag in tags:
            tw = draw_tag(
                ax, tag_x, tag_y, tag,
            )
            tag_x += tw + 0.1

    # Attachments
    if attachments:
        att_y = y - total_h + footer_h + 0.15

        for ai, att in enumerate(attachments):
            att_x = x + 0.7 + ai * 3.5

            draw_box(
                ax,
                att_x, att_y - 0.12,
                3.2, 0.28,
                C["card_header"],
                text_lines=[att],
                text_color=C["accent_cyan"],
                fontsize=4,
                corner_radius=0.04,
                border_color=C["card_border"],
                border_width=0.3,
                text_ha="left",
            )

    # Footer (reply, bookmark, share)
    footer_y = y - total_h + 0.2

    footer_actions = [
        ("Reply", C["accent_blue"]),
        ("Bookmark", C["text_muted"]),
        ("Share", C["text_muted"]),
    ]

    if reply_count is not None:
        footer_actions[0] = (
            f"Reply ({reply_count})",
            C["accent_blue"],
        )

    for fi, (flabel, fcolor) in enumerate(
        footer_actions
    ):
        fx = x + 0.7 + fi * 1.5

        ax.text(
            fx, footer_y,
            flabel,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=fcolor,
            zorder=3,
        )

    return total_h


def generate_lekgotla_thread():
    """Generate the Lekgotla thread view."""

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
        "Thread View",
        ha="left", va="center",
        fontsize=7,
        color=C["text_secondary"],
        zorder=3,
    )

    # Breadcrumb
    ax.text(
        3.5, 31.5,
        "Lekgotla  >  #ghana-expansion  >  "
        "Bundle pricing for Ghana expansion "
        "signals",
        ha="left", va="center",
        fontsize=5,
        color=C["text_muted"],
        zorder=3,
    )

    # Back button
    draw_box(
        ax, 32.5, 31.3,
        1.5, 0.35,
        C["card_bg"],
        text_lines=["< Back to Feed"],
        text_color=C["accent_blue"],
        fontsize=5,
        corner_radius=0.04,
        border_color=C["accent_blue"],
        border_width=0.5,
    )

    # Follow button
    draw_box(
        ax, 34.2, 31.3,
        1.5, 0.35,
        C["accent_blue"],
        text_lines=["Following (24)"],
        text_color="#FFFFFF",
        fontsize=5,
        corner_radius=0.04,
    )

    # ===================================================
    # LAYOUT: Main thread (left) + Sidebar (right)
    # ===================================================

    sidebar_w = 7.5
    thread_w = 36 - sidebar_w - 0.6
    thread_x = 0.3
    sidebar_x = thread_x + thread_w + 0.3

    # ===================================================
    # THREAD HEADER
    # ===================================================

    header_y = 30.5
    header_h = 2.2

    draw_box(
        ax, thread_x, header_y - header_h,
        thread_w, header_h,
        C["card_bg"],
        corner_radius=0.1,
        border_color=C["lekgotla_gold"],
        border_width=1.5,
        shadow=True,
    )

    # Thread title
    ax.text(
        thread_x + 0.3,
        header_y - 0.35,
        "How to approach Ghana expansion signals: "
        "what works, what does not",
        ha="left", va="center",
        fontsize=10, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Thread metadata
    ax.text(
        thread_x + 0.3,
        header_y - 0.75,
        "Started by Sipho Mabena  |  "
        "4 months ago  |  "
        "Category: Geographic Expansion  |  "
        "Countries: GH, CI  |  "
        "8 replies  |  "
        "67 views",
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    # Signal anchor badge
    draw_box(
        ax, thread_x + 0.3,
        header_y - header_h + 0.6,
        5.5, 0.45,
        C["signal_link_bg"],
        corner_radius=0.06,
        border_color=C["signal_link_border"],
        border_width=0.8,
    )

    ax.text(
        thread_x + 0.5,
        header_y - header_h + 0.82,
        "ANCHORED TO SIGNAL:",
        ha="left", va="center",
        fontsize=4, fontweight="bold",
        color=C["text_muted"],
        zorder=3,
    )

    ax.text(
        thread_x + 2.5,
        header_y - header_h + 0.82,
        "SIG-001 Geographic Expansion "
        "(triggered 23 times in 12 months)",
        ha="left", va="center",
        fontsize=4.5,
        color=C["accent_blue"],
        fontweight="bold",
        zorder=3,
    )

    # Knowledge Card link
    draw_box(
        ax, thread_x + 6.3,
        header_y - header_h + 0.6,
        4.5, 0.45,
        C["kc_link_bg"],
        corner_radius=0.06,
        border_color=C["kc_link_border"],
        border_width=0.8,
    )

    ax.text(
        thread_x + 6.5,
        header_y - header_h + 0.82,
        "GRADUATED TO:",
        ha="left", va="center",
        fontsize=4, fontweight="bold",
        color=C["text_muted"],
        zorder=3,
    )

    ax.text(
        thread_x + 8.2,
        header_y - header_h + 0.82,
        "KC-GH-EXPANSION-001",
        ha="left", va="center",
        fontsize=5, fontweight="bold",
        color=C["knowledge_border"],
        zorder=3,
    )

    # Thread stats
    stats = [
        ("8", "Replies"),
        ("67", "Views"),
        ("42", "Upvotes"),
        ("R155M", "Revenue"),
        ("64%", "Win Rate"),
    ]

    for si, (sval, slabel) in enumerate(stats):
        sx = (
            thread_x + thread_w - 0.5
            - (len(stats) - si) * 2.2
        )
        sy = header_y - header_h + 0.82

        ax.text(
            sx, sy + 0.05,
            sval,
            ha="center", va="center",
            fontsize=7, fontweight="bold",
            color=C["accent_green"],
            zorder=3,
        )

        ax.text(
            sx, sy - 0.2,
            slabel,
            ha="center", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

    # ===================================================
    # POSTS
    # ===================================================

    post_y = header_y - header_h - 0.3

    # POST 1: Original post
    h1 = draw_post(
        ax, thread_x, post_y, thread_w,
        author_name="Sipho Mabena",
        author_role="Senior RM, CIB",
        author_country="South Africa",
        author_initials="SM",
        author_color=C["avatar_1"],
        post_time="4 months ago",
        body_lines=[
            "AfriFlow has started generating Ghana "
            "expansion signals for several of my",
            "Platinum clients. I successfully "
            "converted one (R85M facility) and want",
            "to share what worked and what did not "
            "so others can learn from my experience.",
            "",
            "WHAT WORKED:",
            "I approached the CFO with a bundled "
            "package: working capital + FX forward +",
            "asset insurance. The bundle pricing was "
            "key. I had tried individual product",
            "pitches twice before and both times the "
            "client said 'we will think about it'",
            "and then arranged with competitors.",
            "",
            "Key: the bundle pricing came in 15% "
            "below the sum of individual products.",
            "Our Product Pricing Committee approved "
            "a cross-domain subsidy (ref: PP-2024-0892).",
            "",
            "WHAT DID NOT WORK:",
            "On my first attempt, I led with "
            "insurance. The client perceived it as",
            "an upsell rather than a strategic "
            "recommendation. Insurance must be",
            "embedded in the overall expansion "
            "conversation, not presented separately.",
            "",
            "Has anyone else converted Ghana "
            "expansion signals? What approach worked?",
        ],
        upvotes=28,
        tags=[
            "#bundling", "#ghana",
            "#cib+fx+ins", "#pricing",
        ],
        is_op=True,
        badge_text="ORIGINAL POST",
        reply_count=8,
        user_voted=True,
        linked_signal=(
            "SIG-001: Geographic Expansion "
            "into Ghana"
        ),
    )

    post_y -= h1 + 0.2

    # POST 2: Best answer
    h2 = draw_post(
        ax, thread_x, post_y, thread_w,
        author_name="Amina Okafor",
        author_role="RM, CIB",
        author_country="Nigeria",
        author_initials="AO",
        author_color=C["avatar_2"],
        post_time="4 months ago",
        body_lines=[
            "Sipho, this mirrors my experience "
            "exactly. I have converted 3 Ghana",
            "expansion signals in the past 8 months. "
            "Adding one critical detail:",
            "",
            "Tip: Bank of Ghana requires a local "
            "subsidiary registration before you",
            "can open a GHS-denominated account. "
            "Many clients do not know this. If you",
            "flag this requirement in your first "
            "conversation, you become the advisor,",
            "not just the bank. The client trusts "
            "you because you saved them from a",
            "2-week delay they would have discovered "
            "painfully on their own.",
            "",
            "I have a regulatory checklist for "
            "Ghana onboarding that I send to every",
            "client. Attaching it here.",
        ],
        upvotes=34,
        tags=[
            "#regulation", "#ghana",
            "#onboarding", "#trust-building",
        ],
        is_best=True,
        badge_text="BEST ANSWER",
        verified_win=True,
        attachments=[
            "Ghana_Onboarding_Checklist.pdf",
            "BoG_Regulatory_Reference.pdf",
        ],
    )

    post_y -= h2 + 0.2

    # POST 3: FX desk insight
    h3 = draw_post(
        ax, thread_x, post_y, thread_w,
        author_name="David Mwangi",
        author_role="FX Advisor",
        author_country="Kenya",
        author_initials="DM",
        author_color=C["avatar_3"],
        post_time="3 months ago",
        body_lines=[
            "For East African clients expanding to "
            "Ghana, important FX note:",
            "",
            "The KES to GHS corridor is extremely "
            "thin. Do NOT try to quote a direct",
            "KES/GHS forward. Route through USD. "
            "Our FX desk in Nairobi can structure",
            "a KES/USD leg + USD/GHS leg that is "
            "30bps cheaper than any direct quote.",
            "",
            "Warning: the Johannesburg desk cannot "
            "do this because they do not hold the",
            "GHS forward book. Route through Nairobi "
            "for any KE-to-GH corridor FX.",
            "",
            "> Sipho: the bundle pricing came in "
            "15% below individual products",
            "",
            "Confirm. When I include the FX "
            "structure in the bundle, the effective",
            "spread drops from 280bps to 180bps "
            "because we offset the GHS forward",
            "cost against the working capital "
            "margin. Stanbic cannot offer this.",
        ],
        upvotes=18,
        tags=[
            "#fx", "#corridor",
            "#ke-gh", "#pricing",
        ],
        badge_text="LOCAL CONTEXT",
    )

    post_y -= h3 + 0.2

    # POST 4: Compliance input
    h4 = draw_post(
        ax, thread_x, post_y, thread_w,
        author_name="Chidi Emenike",
        author_role="Compliance Officer",
        author_country="Nigeria",
        author_initials="CE",
        author_color=C["avatar_4"],
        post_time="3 months ago",
        body_lines=[
            "Important regulatory note for everyone "
            "working Ghana expansion signals:",
            "",
            "Bank of Ghana Forex Act Section 12(b) "
            "requires PRIOR APPROVAL for forward",
            "contracts exceeding USD 5M equivalent. "
            "Processing time is 10 business days.",
            "",
            "If your client's expansion involves "
            "FX forwards above this threshold,",
            "start the BoG application in parallel "
            "with the client conversation. Do not",
            "wait for the client to confirm before "
            "beginning the regulatory process.",
            "",
            "I have seen two deals delayed by "
            "3 weeks because the RM did not",
            "anticipate this requirement.",
        ],
        upvotes=42,
        tags=[
            "#regulation", "#ghana",
            "#fx-threshold", "#compliance",
        ],
        is_compliance=True,
        badge_text="REGULATORY ALERT",
    )

    post_y -= h4 + 0.2

    # POST 5: Counter-example
    h5 = draw_post(
        ax, thread_x, post_y, thread_w,
        author_name="Thandiwe Nkosi",
        author_role="RM, CIB",
        author_country="South Africa",
        author_initials="TN",
        author_color=C["avatar_5"],
        post_time="2 months ago",
        body_lines=[
            "Sharing what went WRONG so others "
            "can avoid my mistake.",
            "",
            "I received a Ghana expansion signal "
            "and tried to sell insurance separately",
            "after the CIB facility was already "
            "booked. By the time I approached the",
            "client about coverage, they had already "
            "arranged with Allianz.",
            "",
            "Lesson: insurance MUST be in the first "
            "conversation, not the follow-up.",
            "Once the CIB facility is booked, the "
            "client's urgency for other products",
            "drops immediately. Bundle everything "
            "in meeting one.",
        ],
        upvotes=22,
        tags=[
            "#timing", "#insurance",
            "#ghana", "#lesson-learned",
        ],
        badge_text=None,
    )

    post_y -= h5 + 0.2

    # POST 6: Recent addition
    h6 = draw_post(
        ax, thread_x, post_y, thread_w,
        author_name="Grace Akinola",
        author_role="Insurance Broker",
        author_country="Nigeria",
        author_initials="GA",
        author_color=C["avatar_6"],
        post_time="2 weeks ago",
        body_lines=[
            "Adding to Thandiwe's point about "
            "insurance timing. I have found a",
            "specific framing that works:",
            "",
            "Do not say: 'You should also consider "
            "insurance for your Ghana operations.'",
            "",
            "Say: 'Your Ghana expansion means you "
            "now have assets outside South Africa",
            "that are not covered by your existing "
            "policy. Your current coverage has a",
            "geographic exclusion. Here is what "
            "closing that gap costs as part of the",
            "overall package.'",
            "",
            "Key: frame it as closing a gap, not "
            "adding a product. This converted",
            "3 of my last 4 attempts.",
        ],
        upvotes=15,
        tags=[
            "#insurance", "#framing",
            "#ghana", "#conversion",
        ],
        badge_text="PROVEN APPROACH",
        verified_win=True,
    )

    post_y -= h6 + 0.2

    # ===================================================
    # REPLY COMPOSER (bottom of thread)
    # ===================================================

    composer_h = 2.2

    draw_box(
        ax, thread_x, post_y - composer_h,
        thread_w, composer_h,
        C["composer_bg"],
        corner_radius=0.08,
        border_color=C["composer_border"],
        border_width=1.0,
    )

    # Composer header
    ax.text(
        thread_x + 0.3,
        post_y - 0.3,
        "Add your experience",
        ha="left", va="center",
        fontsize=7, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    # Avatar
    draw_avatar(
        ax,
        thread_x + 0.55,
        post_y - 0.85,
        "SM", C["avatar_1"], 0.25,
    )

    # Text area placeholder
    draw_box(
        ax,
        thread_x + 0.95,
        post_y - composer_h + 0.55,
        thread_w - 1.3, 1.15,
        C["reply_bg"],
        corner_radius=0.06,
        border_color=C["reply_border"],
        border_width=0.5,
    )

    ax.text(
        thread_x + 1.15,
        post_y - 0.85,
        "Share what worked, what did not, or "
        "ask a question. Your experience helps "
        "the next RM facing this signal...",
        ha="left", va="center",
        fontsize=5,
        color=C["text_muted"],
        fontstyle="italic",
        zorder=3,
    )

    # Composer actions
    actions = [
        ("Attach File", C["accent_cyan"]),
        ("Add Tag", C["tag_text"]),
        ("Link Signal", C["accent_blue"]),
        ("Mark Regulatory", C["accent_purple"]),
    ]

    for ai, (alabel, acolor) in enumerate(actions):
        ax_btn = (
            thread_x + 1.0 + ai * 2.5
        )

        draw_box(
            ax,
            ax_btn,
            post_y - composer_h + 0.15,
            2.2, 0.3,
            C["card_bg"],
            text_lines=[alabel],
            text_color=acolor,
            fontsize=4.5,
            corner_radius=0.04,
            border_color=C["card_border"],
            border_width=0.3,
        )

    # Post button
    draw_box(
        ax,
        thread_x + thread_w - 2.5,
        post_y - composer_h + 0.15,
        2.2, 0.3,
        C["lekgotla_gold"],
        text_lines=["Post to Lekgotla"],
        text_color="#1A1A1A",
        fontsize=5, bold_first=True,
        corner_radius=0.04,
    )

    # Anonymous toggle
    ax.text(
        thread_x + 11.5,
        post_y - composer_h + 0.3,
        "Post anonymously",
        ha="left", va="center",
        fontsize=4.5,
        color=C["text_muted"],
        zorder=3,
    )

    # Toggle switch
    draw_box(
        ax, thread_x + 14.0,
        post_y - composer_h + 0.2,
        0.6, 0.2,
        C["progress_bg"],
        corner_radius=0.04,
    )

    toggle_dot = Circle(
        (thread_x + 14.2, post_y - composer_h + 0.3),
        0.08,
        facecolor=C["text_muted"],
        edgecolor="none",
        zorder=5,
    )
    ax.add_patch(toggle_dot)

    # ===================================================
    # RIGHT SIDEBAR
    # ===================================================

    # Sidebar background
    draw_box(
        ax, sidebar_x, 0.6,
        sidebar_w, 30.3,
        C["sidebar_bg"],
        corner_radius=0.08,
        border_color=C["sidebar_border"],
        border_width=0.5,
    )

    sidebar_content_y = 30.5

    # --- SIGNAL CONTEXT ---
    ctx_y = sidebar_content_y
    ctx_h = 3.5

    draw_box(
        ax, sidebar_x + 0.15,
        ctx_y - ctx_h,
        sidebar_w - 0.3, ctx_h,
        C["signal_link_bg"],
        corner_radius=0.06,
        border_color=C["signal_link_border"],
        border_width=0.8,
    )

    ax.text(
        sidebar_x + 0.3,
        ctx_y - 0.25,
        "SIGNAL CONTEXT",
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["accent_blue"],
        zorder=3,
    )

    signal_details = [
        "Signal: Geographic Expansion",
        "Type: SIG-001",
        "Triggered: 23 times (12 months)",
        "Countries: Ghana (primary)",
        "Domains: CIB + Cell + FX + INS",
        "",
        "Avg opportunity: R85M",
        "Best outcome: R155M",
        "Worst outcome: R0 (missed)",
        "",
        "This thread contributed to:",
        "14 RM actions",
        "9 confirmed wins (64%)",
    ]

    for si, sline in enumerate(signal_details):
        sy = ctx_y - 0.55 - si * 0.22

        fc = C["text_secondary"]
        fw = "normal"

        if sline.startswith("Avg") or sline.startswith("Best"):
            fc = C["accent_green"]
            fw = "bold"
        elif sline.startswith("Worst"):
            fc = C["accent_red"]
            fw = "bold"
        elif sline.startswith("14 RM") or sline.startswith("9 confirmed"):
            fc = C["accent_amber"]
            fw = "bold"

        ax.text(
            sidebar_x + 0.3, sy,
            sline,
            ha="left", va="center",
            fontsize=4.5, fontweight=fw,
            color=fc,
            zorder=3,
        )

    # --- KNOWLEDGE CARD ---
    kc_y = ctx_y - ctx_h - 0.3
    kc_h = 3.2

    draw_box(
        ax, sidebar_x + 0.15,
        kc_y - kc_h,
        sidebar_w - 0.3, kc_h,
        C["kc_link_bg"],
        corner_radius=0.06,
        border_color=C["kc_link_border"],
        border_width=0.8,
    )

    ax.text(
        sidebar_x + 0.3,
        kc_y - 0.25,
        "KNOWLEDGE CARD",
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["knowledge_border"],
        zorder=3,
    )

    ax.text(
        sidebar_x + 0.3,
        kc_y - 0.55,
        "KC-GH-EXPANSION-001",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    ax.text(
        sidebar_x + 0.3,
        kc_y - 0.8,
        "Bundle pricing for Ghana",
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    ax.text(
        sidebar_x + 0.3,
        kc_y - 1.0,
        "expansion signals",
        ha="left", va="center",
        fontsize=5,
        color=C["text_secondary"],
        zorder=3,
    )

    kc_stats = [
        ("Contributors:", "4"),
        ("Used by:", "14 RMs"),
        ("Win rate:", "64%"),
        ("Revenue:", "R155M"),
        ("Last updated:", "2 months ago"),
    ]

    for ki, (klabel, kval) in enumerate(kc_stats):
        ky = kc_y - 1.35 - ki * 0.28

        ax.text(
            sidebar_x + 0.3, ky,
            klabel,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_muted"],
            zorder=3,
        )

        ax.text(
            sidebar_x + sidebar_w - 0.3, ky,
            kval,
            ha="right", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["accent_green"],
            zorder=3,
        )

    # View card button
    draw_box(
        ax, sidebar_x + 0.3,
        kc_y - kc_h + 0.2,
        sidebar_w - 0.6, 0.35,
        C["knowledge_border"],
        text_lines=["View Full Knowledge Card"],
        text_color="#FFFFFF",
        fontsize=5,
        corner_radius=0.04,
    )

    # --- RELATED THREADS ---
    rt_y = kc_y - kc_h - 0.3
    rt_h = 4.5

    draw_box(
        ax, sidebar_x + 0.15,
        rt_y - rt_h,
        sidebar_w - 0.3, rt_h,
        C["card_bg"],
        corner_radius=0.06,
        border_color=C["card_border"],
        border_width=0.5,
    )

    ax.text(
        sidebar_x + 0.3,
        rt_y - 0.25,
        "RELATED THREADS",
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    related = [
        (
            "Insurance timing: when to introduce "
            "coverage in expansion conversations",
            "12 replies  |  35 upvotes",
            C["insurance"],
        ),
        (
            "GHS/USD forward pricing: "
            "how to beat Stanbic",
            "8 replies  |  22 upvotes",
            C["forex"],
        ),
        (
            "CBN repatriation rule changes: "
            "impact on NG corridor clients",
            "15 replies  |  54 upvotes",
            C["accent_red"],
        ),
        (
            "Cocoa season preparation: "
            "pre-positioning for Oct harvest",
            "6 replies  |  18 upvotes",
            C["accent_teal"],
        ),
        (
            "Cote d Ivoire expansion: CFA zone "
            "regulatory differences vs Ghana",
            "4 replies  |  11 upvotes",
            C["accent_amber"],
        ),
    ]

    for ri, (rtitle, rmeta, rcolor) in enumerate(related):
        ry = rt_y - 0.6 - ri * 0.78

        # Color bar
        draw_box(
            ax, sidebar_x + 0.25, ry - 0.3,
            0.06, 0.55,
            rcolor,
            corner_radius=0.01,
        )

        ax.text(
            sidebar_x + 0.45, ry,
            rtitle,
            ha="left", va="center",
            fontsize=4.5,
            color=C["text_primary"],
            zorder=3,
        )

        ax.text(
            sidebar_x + 0.45, ry - 0.22,
            rmeta,
            ha="left", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

    # --- CONTRIBUTORS ---
    cont_y = rt_y - rt_h - 0.3
    cont_h = 3.5

    draw_box(
        ax, sidebar_x + 0.15,
        cont_y - cont_h,
        sidebar_w - 0.3, cont_h,
        C["card_bg"],
        corner_radius=0.06,
        border_color=C["card_border"],
        border_width=0.5,
    )

    ax.text(
        sidebar_x + 0.3,
        cont_y - 0.25,
        "THREAD CONTRIBUTORS (6)",
        ha="left", va="center",
        fontsize=6, fontweight="bold",
        color=C["text_primary"],
        zorder=3,
    )

    thread_contributors = [
        ("SM", "Sipho Mabena", "RM, ZA", C["avatar_1"]),
        ("AO", "Amina Okafor", "RM, NG", C["avatar_2"]),
        ("DM", "David Mwangi", "FX, KE", C["avatar_3"]),
        ("CE", "Chidi Emenike", "Compliance, NG", C["avatar_4"]),
        ("TN", "Thandiwe Nkosi", "RM, ZA", C["avatar_5"]),
        ("GA", "Grace Akinola", "Insurance, NG", C["avatar_6"]),
    ]

    for ci, (initials, cname, crole, ccolor) in enumerate(
        thread_contributors
    ):
        cy = cont_y - 0.6 - ci * 0.45

        draw_avatar(
            ax,
            sidebar_x + 0.5, cy,
            initials, ccolor, 0.18,
        )

        ax.text(
            sidebar_x + 0.8, cy + 0.05,
            cname,
            ha="left", va="center",
            fontsize=4.5, fontweight="bold",
            color=C["text_primary"],
            zorder=3,
        )

        ax.text(
            sidebar_x + 0.8, cy - 0.15,
            crole,
            ha="left", va="center",
            fontsize=4,
            color=C["text_muted"],
            zorder=3,
        )

    # Cross-border note
    ax.text(
        sidebar_x + 0.3,
        cont_y - cont_h + 0.35,
        "3 countries represented",
        ha="left", va="center",
        fontsize=4.5, fontweight="bold",
        color=C["accent_teal"],
        zorder=3,
    )

    ax.text(
        sidebar_x + 0.3,
        cont_y - cont_h + 0.12,
        "ZA, NG, KE (cross-border wisdom)",
        ha="left", va="center",
        fontsize=4,
        color=C["text_muted"],
        zorder=3,
    )

    # --- REGULATORY ALERTS ---
    reg_y = cont_y - cont_h - 0.3
    reg_h = 1.8

    draw_box(
        ax, sidebar_x + 0.15,
        reg_y - reg_h,
        sidebar_w - 0.3, reg_h,
        "#1A1020",
        corner_radius=0.06,
        border_color=C["accent_purple"],
        border_width=0.8,
    )

    ax.text(
        sidebar_x + 0.3,
        reg_y - 0.25,
        "ACTIVE REGULATORY NOTES",
        ha="left", va="center",
        fontsize=5.5, fontweight="bold",
        color=C["accent_purple"],
        zorder=3,
    )

    reg_notes = [
        "BoG Forex Act S.12(b): prior approval",
        "for forwards > USD 5M (10 bus. days)",
        "",
        "BoG subsidiary registration required",
        "before GHS account opening",
        "",
        "Last updated: 3 months ago by",
        "Chidi Emenike (Compliance, NG)",
    ]

    for ri, rline in enumerate(reg_notes):
        ry = reg_y - 0.5 - ri * 0.17

        fc = C["text_secondary"]
        if rline.startswith("BoG"):
            fc = C["accent_amber"]

        ax.text(
            sidebar_x + 0.3, ry,
            rline,
            ha="left", va="center",
            fontsize=4,
            color=fc,
            zorder=3,
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
        "Lekgotla Thread  |  "
        "6 contributors from 3 countries  |  "
        "Graduated to Knowledge Card "
        "KC-GH-EXPANSION-001  |  "
        "R155M attributed revenue  |  "
        "64% win rate  |  "
        "Motho ke motho ka batho",
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
        output_dir, "lekgotla_thread.png"
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
        f"Lekgotla Thread saved to: {output_path}"
    )

    small_path = os.path.join(
        output_dir, "lekgotla_thread_small.png"
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
        "Generating AfriFlow Lekgotla "
        "Thread View..."
    )
    print()

    generate_lekgotla_thread()

    print()
    print("Lekgotla Thread View generated.")
    print(
        "Files ready for embedding in README.md "
        "and documentation."
    )
