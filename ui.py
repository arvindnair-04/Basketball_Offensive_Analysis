from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st


COLORS = {
    "navy": "#0b172a",
    "blue": "#2563EB",
    "orange": "#F97316",
    "teal": "#14B8A6",
    "green": "#22C55E",
    "red": "#EF4444",
    "purple": "#A855F7",
    "cyan": "#06B6D4",
    "yellow": "#FACC15",
    "pink": "#EC4899",
    "muted": "#667085",
    "grid": "rgba(148, 163, 184, 0.18)",
}

# High-contrast categorical palette used throughout the scouting dashboard.
BOLD_PALETTE = [
    COLORS["blue"], COLORS["orange"], COLORS["green"], COLORS["red"],
    COLORS["purple"], COLORS["cyan"], COLORS["yellow"], COLORS["pink"],
    COLORS["teal"], "#8B5CF6", "#0EA5E9", "#84CC16",
]

# Use this when color carries a low-to-high performance meaning.
PERFORMANCE_SCALE = [
    [0.00, "#EF4444"],
    [0.35, "#F97316"],
    [0.55, "#FACC15"],
    [0.75, "#22C55E"],
    [1.00, "#06B6D4"],
]


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container {max-width: 1440px; padding-top: 1.6rem; padding-bottom: 3rem;}
        [data-testid="stSidebar"] {border-right: 1px solid rgba(148,163,184,.20);}
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(37,99,235,.09), rgba(20,184,166,.05));
            border: 1px solid rgba(148,163,184,.22); border-radius: 14px; padding: .8rem 1rem;
        }
        [data-testid="stMetricLabel"] {color: #667085;}
        .app-kicker {color: #2f6fed; font-size: .78rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase;}
        .app-title {font-size: clamp(2rem, 4vw, 3.35rem); line-height: 1.02; font-weight: 850; letter-spacing: -.045em; margin: .25rem 0 .65rem;}
        .app-subtitle {max-width: 820px; color: #667085; font-size: 1.02rem; line-height: 1.6; margin-bottom: 1.25rem;}
        .app-header.compact .app-title {font-size: clamp(1.65rem, 3vw, 2.45rem); line-height: 1.08; margin-bottom: .45rem;}
        .app-header.compact .app-subtitle {font-size: .94rem; line-height: 1.5; margin-bottom: 1rem;}
        .insight-card {border: 1px solid rgba(148,163,184,.22); border-radius: 14px; padding: 1rem 1.1rem; height: 100%; background: rgba(37,99,235,.035);}
        .insight-label {font-size: .72rem; color: #667085; font-weight: 800; letter-spacing: .08em; text-transform: uppercase;}
        .insight-title {font-size: 1.08rem; font-weight: 750; margin: .25rem 0;}
        .insight-copy {font-size: .88rem; color: #667085; line-height: 1.45;}
        .pill {display:inline-block; padding:.22rem .6rem; margin:.1rem .2rem .1rem 0; border-radius:999px; background:rgba(37,99,235,.11); color:#2563EB; font-size:.78rem; font-weight:700;}
        div[data-testid="stDataFrame"] {border: 1px solid rgba(148,163,184,.18); border-radius: 12px; overflow: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, subtitle: str, *, compact: bool = False) -> None:
    header_class = "app-header compact" if compact else "app-header"
    st.markdown(
        f'<div class="{header_class}">'
        f'<div class="app-kicker">{escape(kicker)}</div>'
        f'<div class="app-title">{escape(title)}</div>'
        f'<div class="app-subtitle">{escape(subtitle)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def insight_card(label: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="insight-card"><div class="insight-label">{escape(label)}</div>'
        f'<div class="insight-title">{escape(title)}</div>'
        f'<div class="insight-copy">{escape(copy)}</div></div>',
        unsafe_allow_html=True,
    )


def style_figure(fig: go.Figure, *, height: int = 480) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=55, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, ui-sans-serif, system-ui", color=COLORS["navy"]),
        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_color=COLORS["navy"]),
        title=None,
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False)
    return fig


def player_label(name: str, team: str | None) -> str:
    return f"{name} · {team}" if team else name


def value_or_dash(value: float, fmt: str) -> str:
    if value is None:
        return "—"
    try:
        if value != value:
            return "—"
        return format(value, fmt)
    except (TypeError, ValueError):
        return "—"


def chart_heading(title: str, help_text: str) -> None:
    """Show a clean chart title with an optional one-line hover explanation."""
    st.subheader(title, help=help_text, divider=False)


def metric_glossary_block(items: list[tuple[str, str]]) -> None:
    """Keep page metric definitions available without adding visual clutter."""
    if not items:
        return
    st.divider()
    with st.expander("Quick Metric Guide", expanded=False):
        rows = "".join(
            f'<div style="margin:.35rem 0"><strong>{escape(term)}</strong> — {escape(description)}</div>'
            for term, description in items
        )
        st.markdown(rows, unsafe_allow_html=True)
