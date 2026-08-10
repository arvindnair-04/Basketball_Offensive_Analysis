from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import ZONE_CONFIG, closest_comparisons, load_data
from ui import BOLD_PALETTE, COLORS, PERFORMANCE_SCALE, chart_heading, insight_card, metric_glossary_block, page_header, style_figure, value_or_dash
from usage_tracking import track_page_view, track_player_comparison, track_player_view


track_page_view("Player Profile")


def pct(value):
    return None if pd.isna(value) else round(float(value) * 100, 2)


try:
    bundle = load_data()
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()

profiles = bundle.profiles.copy()
page_header(
    "Liga ACB · 2024–25",
    "Player Profile",
    "",
)

with st.sidebar:
    st.markdown("### Player finder")
    team = st.selectbox("Team", ["All teams", *sorted(profiles["team_name"].dropna().unique())])
    available = profiles if team == "All teams" else profiles[profiles["team_name"].eq(team)]
    include_low_sample = st.toggle("Include low-sample players", value=True)
    if not include_low_sample:
        available = available[available["appearances"].ge(10)]

if available.empty:
    st.warning("No players meet the current finder settings.")
    st.stop()

label_lookup = {
    int(row.player_id): f"{row.player_name} · {row.team_name}"
    for row in available[["player_id", "player_name", "team_name"]].itertuples(index=False)
}
selected_id = st.selectbox(
    "Player", sorted(label_lookup, key=lambda value: label_lookup[value]),
    format_func=lambda value: label_lookup[value], key="profile_player"
)
selected = profiles.loc[profiles["player_id"].eq(selected_id)].iloc[0]
track_player_view(int(selected_id), str(selected["player_name"]))

st.markdown(f"## {selected['player_name']}")
pill_values = [selected.get("team_name"), selected.get("shot_archetype"), selected.get("pnr_role")]
st.markdown(" ".join(f'<span class="pill">{value}</span>' for value in pill_values if pd.notna(value)), unsafe_allow_html=True)
if bool(selected.get("is_traded", False)):
    st.caption("Marked as traded; the supplied row aggregates the season while team name reflects the recorded team field.")

overview_top = st.columns(4)
overview_top[0].metric("Appearances", value_or_dash(selected.get("appearances"), ".0f"))
overview_top[1].metric("Points / game", value_or_dash(selected.get("points_per_game"), ".1f"))
overview_top[2].metric("FGA / game", value_or_dash(selected.get("attempts_per_game"), ".1f"))
overview_top[3].metric("eFG%", "—" if pd.isna(selected.get("efg_percentage")) else f"{pct(selected.get('efg_percentage')):.2f}%")
overview_bottom = st.columns(3)
overview_bottom[0].metric("True shooting %", "—" if pd.isna(selected.get("true_shooting_pct")) else f"{pct(selected.get('true_shooting_pct')):.2f}%")
overview_bottom[1].metric("Handler picks / game", value_or_dash(selected.get("handler_picks_per_game"), ".1f"))
overview_bottom[2].metric("Screener picks / game", value_or_dash(selected.get("screener_picks_per_game"), ".1f"))

stats_tab, shooting_tab, pnr_tab, similar_tab = st.tabs(
    ["Player Stats", "Shooting Profile", "Pick-and-Roll Profile", "Similarity & Comparison"]
)

PERCENTILE_METRICS = {
    "Shot volume": "shot_volume_percentile",
    "Shot efficiency": "shot_efficiency_percentile",
    "Shot-making": "shotmaking_percentile",
    "Three volume": "three_volume_percentile",
    "Rim frequency": "rim_rate_percentile",
    "Pressure response": "pressure_resilience_percentile",
    "Handler creation": "handler_creation_percentile",
    "Screener creation": "screener_creation_percentile",
}


def available_percentiles(row: pd.Series) -> list[tuple[str, float]]:
    result = []
    for label, column in PERCENTILE_METRICS.items():
        value = row.get(column)
        if pd.notna(value):
            result.append((label, float(value)))
    return result


def radar_figure(rows: list[pd.Series]) -> go.Figure:
    labels = list(PERCENTILE_METRICS)
    columns = list(PERCENTILE_METRICS.values())
    fig = go.Figure()
    for index, row in enumerate(rows):
        values = [round(float(row.get(column)) * 100, 2) if pd.notna(row.get(column)) else None for column in columns]
        fig.add_trace(go.Scatterpolar(
            r=[*values, values[0]], theta=[*labels, labels[0]], fill="toself", opacity=0.66,
            name=row["player_name"], line=dict(color=COLORS["blue"] if index == 0 else COLORS["orange"], width=2), connectgaps=False,
        ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="th", gridcolor=COLORS["grid"])), showlegend=len(rows) > 1)
    fig = style_figure(fig, height=520)
    fig.update_layout(title_text="")
    return fig


comparison = None
comparison_id = None

with stats_tab:
    st.markdown("#### Player comparison")
    all_labels = {
        int(row.player_id): f"{row.player_name} · {row.team_name}"
        for row in profiles[["player_id", "player_name", "team_name"]].itertuples(index=False)
    }
    other_ids = [int(value) for value in profiles["player_id"] if int(value) != selected_id]
    comparison_id = st.selectbox(
        "Compare with", [None, *sorted(other_ids, key=lambda value: all_labels[value])],
        format_func=lambda value: "No comparison" if value is None else all_labels[value], key="profile_compare",
    )
    if comparison_id is not None:
        comparison = profiles.loc[profiles["player_id"].eq(comparison_id)].iloc[0]
        track_player_comparison(int(comparison_id), str(comparison["player_name"]))

    percentiles = available_percentiles(selected)
    if not percentiles:
        st.info("This player does not meet enough qualified samples for a league-relative scouting read.")
    else:
        strengths = sorted(percentiles, key=lambda item: item[1], reverse=True)[:3]
        concerns = sorted(percentiles, key=lambda item: item[1])[:2]
        st.markdown("#### Strongest league-relative signals")
        strength_columns = st.columns(len(strengths))
        for container, (label, value) in zip(strength_columns, strengths):
            with container:
                insight_card("Strength", label, f"{value * 100:.2f} percentile among qualified league players.")
        low_signals = ", ".join(f"**{label}** ({value * 100:.2f})" for label, value in concerns if value < 0.45)
        if low_signals:
            st.warning(f"Lower relative signals to review: {low_signals}. These describe the supplied season, not future potential.")

    radar_rows = [selected] + ([comparison] if comparison is not None else [])
    chart_heading("League-relative player profile", "Shows where the player ranks compared with qualified league players across the main scouting measures.")
    st.plotly_chart(radar_figure(radar_rows), width="stretch", key="profile_radar")

    score_columns = st.columns(4)
    score_columns[0].metric("Scoring impact", value_or_dash(selected.get("scoring_impact_score"), ".0f"))
    score_columns[1].metric("Spacing", value_or_dash(selected.get("spacing_score"), ".0f"))
    score_columns[2].metric("Rim pressure", value_or_dash(selected.get("rim_pressure_score"), ".0f"))
    score_columns[3].metric("Shot sample confidence", value_or_dash(selected.get("shooting_reliability"), ".0f"))

    if comparison is not None:
        rows = []
        for label, col, is_percent in [
            ("Points / game", "points_per_game", False), ("FGA / game", "attempts_per_game", False),
            ("eFG%", "efg_percentage", True), ("3PA rate", "three_pa_rate", True), ("Rim rate", "rim_attempt_rate", True),
            ("Handler picks / game", "handler_picks_per_game", False), ("Handler PPP", "handler_ppp", False),
            ("Screener picks / game", "screener_picks_per_game", False), ("Screener PPP", "screener_ppp", False),
        ]:
            a, b = selected.get(col), comparison.get(col)
            rows.append({"Metric": label, selected["player_name"]: pct(a) if is_percent else a, comparison["player_name"]: pct(b) if is_percent else b})
        st.dataframe(pd.DataFrame(rows).round(2), width="stretch", hide_index=True)

with shooting_tab:
    if pd.isna(selected.get("attempts")):
        st.info("This player is not present in the supplied shooting file.")
    else:
        rows = []
        classified_attempts = sum(float(selected.get(cfg[0], 0) or 0) for cfg in ZONE_CONFIG.values())
        for zone, (attempt_col, _made_col, pct_col, point_value) in ZONE_CONFIG.items():
            attempts = float(selected.get(attempt_col, 0) or 0)
            zone_fg = pct(selected.get(pct_col))
            zone_efg = round(zone_fg * (point_value / 2), 2) if zone_fg is not None else np.nan
            rows.append({
                "Zone": zone,
                "Attempts": attempts,
                "Attempt share %": round(attempts / classified_attempts * 100, 2) if classified_attempts else np.nan,
                "Zone FG%": zone_fg,
                "Zone eFG%": zone_efg,
            })
        zone_profile = pd.DataFrame(rows)

        chart_heading("Shot diet and zone efficiency", "Shows where the player takes shots most often; bar length is shot share and color represents zone eFG%.")
        diet_plot = zone_profile.sort_values("Attempt share %", ascending=True).copy()
        diet_fig = px.bar(
            diet_plot,
            x="Attempt share %",
            y="Zone",
            orientation="h",
            color="Zone eFG%",
            text="Attempt share %",
            hover_data={
                "Attempts": ":.0f",
                "Attempt share %": ":.2f",
                "Zone FG%": ":.2f",
                "Zone eFG%": ":.2f",
            },
            color_continuous_scale=PERFORMANCE_SCALE,
            title="Shot distribution by zone",
        )
        diet_fig.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside",
            cliponaxis=False,
            marker_line_width=1,
            marker_line_color="white",
        )
        diet_fig.update_layout(
            showlegend=False,
            coloraxis_colorbar=dict(title="Zone eFG%", ticksuffix="%"),
            xaxis_title="Share of classified attempts",
            yaxis_title=None,
        )
        diet_fig.update_xaxes(ticksuffix="%", range=[0, max(100, float(diet_plot["Attempt share %"].max()) * 1.18)])
        diet_fig = style_figure(diet_fig, height=400)
        diet_fig.update_layout(title_text="")
        st.plotly_chart(diet_fig, width="stretch", key="profile_shot_diet")
        coverage = classified_attempts / float(selected.get("attempts", 0) or 1) * 100

        chart_heading("Blocked-shot vulnerability", "Shows how often players shoot versus how often those shots are blocked, with the selected player highlighted.")
        block_league = profiles.dropna(subset=["attempts_per_game", "blocked_shots", "appearances", "efg_percentage"]).copy()
        block_league = block_league[block_league["appearances"].gt(0)]
        block_league["Blocked shots / game"] = (block_league["blocked_shots"] / block_league["appearances"]).round(2)
        block_league["eFG%"] = (block_league["efg_percentage"] * 100).round(2)
        block_league["Points / game"] = block_league["points_per_game"].fillna(0).clip(lower=0.1)
        block_fig = px.scatter(
            block_league, x="attempts_per_game", y="Blocked shots / game", size="Points / game", color="eFG%",
            hover_name="player_name", hover_data={"team_name": True, "attempts_per_game": ":.2f", "Blocked shots / game": ":.2f", "blocked_shots": ":.0f", "eFG%": ":.2f", "Points / game": ":.2f"},
            labels={"attempts_per_game": "Shot attempts per game", "Blocked shots / game": "Blocked attempts per game", "team_name": "Team", "blocked_shots": "Total blocked attempts", "eFG%": "Effective FG%", "Points / game": "Points per game", "player_name": "Player"}, title="Shot volume vs blocked attempts",
            color_continuous_scale=PERFORMANCE_SCALE,
        )
        selected_block = block_league[block_league["player_id"].eq(selected_id)]
        if not selected_block.empty:
            block_fig.add_trace(go.Scatter(
                x=selected_block["attempts_per_game"], y=selected_block["Blocked shots / game"], mode="markers+text",
                text=selected_block["player_name"], textposition="top center", name="Selected player",
                marker=dict(size=18, symbol="diamond", color=COLORS["orange"], line=dict(width=2, color=COLORS["navy"])),
                hovertemplate="Selected player<br>Shot attempts per game: %{x:.2f}<br>Blocked attempts per game: %{y:.2f}<extra></extra>",
            ))
        block_fig = style_figure(block_fig, height=430)
        block_fig.update_layout(title_text="")
        st.plotly_chart(block_fig, width="stretch", key="profile_block_vulnerability")

        context_rows = pd.DataFrame({
            "Context": ["Catch and shoot", "Off the dribble", "Contested", "Uncontested"],
            "Attempts": [selected.get("cns_attempts"), selected.get("od_attempts"), selected.get("contested_attempts"), selected.get("uncontested_attempts")],
            "eFG%": [pct(selected.get("cns_efg_percentage")), pct(selected.get("od_efg_percentage")), pct(selected.get("contested_efg_percentage")), pct(selected.get("uncontested_efg_percentage"))],
        }).dropna(subset=["eFG%"])
        context_rows = context_rows.sort_values("eFG%", ascending=True)
        chart_heading("Creation and pressure context", "Compares the player's eFG% across open, contested, catch-and-shoot, and off-the-dribble situations.")
        context_fig = px.bar(
            context_rows, x="eFG%", y="Context", orientation="h", color="Context", text="eFG%",
            hover_data={"Attempts": ":.0f", "eFG%": ":.2f"},
            color_discrete_sequence=BOLD_PALETTE, title="Creation and pressure context",
        )
        context_fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside", cliponaxis=False)
        context_fig.update_layout(showlegend=False, xaxis_title="eFG%", yaxis_title=None)
        context_fig.update_xaxes(ticksuffix="%")
        context_fig = style_figure(context_fig, height=390)
        context_fig.update_layout(title_text="")
        st.plotly_chart(context_fig, width="stretch", key="profile_shot_context")
        st.dataframe(
            zone_profile, width="stretch", hide_index=True,
            column_config={
                "Attempts": st.column_config.NumberColumn(format="%d"),
                "Attempt share %": st.column_config.NumberColumn(format="%.2f%%"),
                "Zone FG%": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

with pnr_tab:
    if pd.isna(selected.get("handler_total_picks")):
        st.info("This player is not present in the supplied pick-and-roll file.")
    else:
        handler_picks = selected.get("handler_total_picks", 0) or 0
        screener_picks = selected.get("screener_total_picks", 0) or 0
        if handler_picks + screener_picks < 20:
            role = "Low PnR sample"
        elif handler_picks >= 0.72 * (handler_picks + screener_picks):
            role = "Ball handler"
        elif screener_picks >= 0.72 * (handler_picks + screener_picks):
            role = "Screener"
        else:
            role = "Dual role"

        st.markdown(f"### Primary pick-and-roll role: **{role}**")
        role_cards = st.columns(6)
        role_cards[0].metric("Handler picks", f"{handler_picks:,.0f}")
        role_cards[1].metric("Screener picks", f"{screener_picks:,.0f}")
        role_cards[2].metric("Handler PPP", value_or_dash(selected.get("handler_ppp"), ".2f"))
        role_cards[3].metric("Screener PPP", value_or_dash(selected.get("screener_ppp"), ".2f"))
        role_cards[4].metric("Handler success", "—" if pd.isna(selected.get("handler_success_rate")) else f"{pct(selected.get('handler_success_rate')):.2f}%")
        role_cards[5].metric("Screener success", "—" if pd.isna(selected.get("screener_success_rate")) else f"{pct(selected.get('screener_success_rate')):.2f}%")

        roles_to_show = ["handler", "screener"] if role == "Dual role" else (["handler"] if role == "Ball handler" else (["screener"] if role == "Screener" else []))
        if not roles_to_show:
            st.info("The player's pick-and-roll involvement is too small for a reliable role-specific breakdown.")

        for role_key in roles_to_show:
            role_name = "Ball handler" if role_key == "handler" else "Screener"
            chart_heading(f"{role_name} decision profile", "Shows how often the player shoots, passes, or creates an assist opportunity in this pick-and-roll role.")
            shot_pct = pct(selected.get(f"{role_key}_shot_taken_pct"))
            pass_only_pct = pct(selected.get(f"{role_key}_only_pass_pick_pct"))
            assist_opp_pct = pct(selected.get(f"{role_key}_assist_opportunity_pct"))
            decision_rows = [
                {"Decision": "Shot taken", "Rate %": shot_pct, "Count": selected.get(f"{role_key}_shot_taken")},
                {"Decision": "Pass only", "Rate %": pass_only_pct, "Count": selected.get(f"{role_key}_only_pass_pick")},
                {"Decision": "Assist opportunity", "Rate %": assist_opp_pct, "Count": selected.get(f"{role_key}_assist_opportunity")},
            ]
            if role_key == "handler":
                decision_rows.extend([
                    {"Decision": "Assist to screener", "Rate %": pct(selected.get("handler_assist_to_screener_pct")), "Count": selected.get("handler_assist_to_screener")},
                    {"Decision": "Assist to other", "Rate %": pct(selected.get("handler_assist_to_other_pct")), "Count": selected.get("handler_assist_to_other")},
                ])
            decision_df = pd.DataFrame(decision_rows).dropna()
            decision_df["Role picks"] = selected.get(f"{role_key}_total_picks")
            decision_df["PPP"] = selected.get(f"{role_key}_ppp")
            decision_df["Success %"] = pct(selected.get(f"{role_key}_success_rate"))
            decision_df["Turnover %"] = pct(selected.get(f"{role_key}_turnover_rate"))
            fig = px.bar(decision_df, x="Decision", y="Rate %", color="Decision", text="Rate %", title=f"{role_name} decisions", color_discrete_sequence=BOLD_PALETTE, hover_data={"Count": ":.0f", "Role picks": ":.0f", "PPP": ":.2f", "Success %": ":.2f", "Turnover %": ":.2f"})
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig.update_layout(showlegend=False)
            fig = style_figure(fig, height=390)
            fig.update_layout(title_text="")
            st.plotly_chart(fig, width="stretch", key=f"profile_{role_key}_decisions")

            chart_heading(f"{role_name} shot type when a shot is taken", "Shows the share of pick-and-roll shots that are two-pointers versus three-pointers.")
            shot_type = pd.DataFrame({
                "Shot type": ["2PT", "3PT"],
                "Share of PnR shots %": [pct(selected.get(f"{role_key}_shot_rate_2pt")), pct(selected.get(f"{role_key}_shot_rate_3pt"))],
            }).dropna()
            if shot_type.empty:
                st.info("No qualified shot-type split is available for this role.")
            else:
                shot_type["Role picks"] = selected.get(f"{role_key}_total_picks")
                shot_type["Shots taken"] = selected.get(f"{role_key}_shot_taken")
                shot_type["PPP"] = selected.get(f"{role_key}_ppp")
                fig = px.bar(shot_type, x="Shot type", y="Share of PnR shots %", color="Shot type", text="Share of PnR shots %", title=f"{role_name} two-point vs three-point shot mix", color_discrete_sequence=BOLD_PALETTE, hover_data={"Role picks": ":.0f", "Shots taken": ":.0f", "PPP": ":.2f"})
                fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
                fig.update_layout(showlegend=False)
                fig = style_figure(fig, height=350)
                fig.update_layout(title_text="")
                st.plotly_chart(fig, width="stretch", key=f"profile_{role_key}_shot_type")


            outcome_rows = pd.DataFrame({
                "Outcome": ["Success", "Turnover"],
                "Rate %": [pct(selected.get(f"{role_key}_success_rate")), pct(selected.get(f"{role_key}_turnover_rate"))],
            }).dropna()
            outcome_rows["Role picks"] = selected.get(f"{role_key}_total_picks")
            outcome_rows["PPP"] = selected.get(f"{role_key}_ppp")
            outcome_rows["Shot taken %"] = pct(selected.get(f"{role_key}_shot_taken_pct"))
            outcome_rows["Assist opportunity %"] = pct(selected.get(f"{role_key}_assist_opportunity_pct"))
            chart_heading(f"{role_name} successful plays and turnovers", "Shows the player's success rate and turnover rate in this pick-and-roll role.")
            fig = px.bar(outcome_rows, x="Outcome", y="Rate %", color="Outcome", text="Rate %", title=f"{role_name} successful plays and turnovers", color_discrete_sequence=[COLORS["green"], COLORS["red"]], hover_data={"Role picks": ":.0f", "PPP": ":.2f", "Shot taken %": ":.2f", "Assist opportunity %": ":.2f"})
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig.update_layout(showlegend=False)
            fig = style_figure(fig, height=340)
            fig.update_layout(title_text="")
            st.plotly_chart(fig, width="stretch", key=f"profile_{role_key}_outcomes")

with similar_tab:
    chart_heading("Similar Players", "Uses euclidean distance to get similar player profile.")
    comparisons = closest_comparisons(profiles, selected_id, limit=8)
    if comparisons.empty:
        st.info("Not enough qualified dimensions are available to find reliable comparisons.")
    else:
        st.dataframe(
            comparisons, width="stretch", hide_index=True,
            column_config={
                "player_name": "Player", "team_name": "Team",
                "similarity": st.column_config.ProgressColumn("Similarity", min_value=0, max_value=100, format="%.0f"),
                "shared_dimensions": "Measures compared", "shot_archetype": "Shot style", "pnr_role": "PnR role",
            },
        )

metric_glossary_block([
    ("eFG%", "Shooting percentage adjusted to give extra credit for made three-pointers."),
    ("True shooting %", "Overall scoring efficiency including field goals and free throws."),
    ("Shot diet", "Where a player chooses to take most of their shots."),
    ("Blocked attempts", "Field-goal attempts that were blocked by a defender."),
    ("Points per pick", "Average points produced from a tracked pick-and-roll action."),
    ("Handler", "The player with the ball who uses the screen."),
    ("Screener", "The player who sets the screen."),
    ("Similarity", "How closely another player's statistical profile matches the selected player across shared measures."),
])
