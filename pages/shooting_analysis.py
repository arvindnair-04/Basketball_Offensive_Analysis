from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import ZONE_CONFIG, load_data
from ui import BOLD_PALETTE, COLORS, PERFORMANCE_SCALE, chart_heading, metric_glossary_block, page_header, style_figure
from usage_tracking import track_page_view


track_page_view("Shooting Analysis")


def pct(value):
    return None if pd.isna(value) else round(float(value) * 100, 2)


def percent_copy(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column in out:
            out[column] = (out[column] * 100).round(2)
    return out


try:
    bundle = load_data()
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()

shots = bundle.shots.copy()
page_header(
    "Liga ACB · 2024–25",
    "Shooting Analysis",
    "",
)

with st.sidebar:
    st.markdown("### Shooting filters")
    min_appearances = st.slider("Minimum appearances", 1, 35, 10)
    min_attempts = st.slider("Minimum field-goal attempts", 0, 300, 50, step=10)
    min_zone_attempts = st.slider("Minimum attempts in selected zone", 1, 100, 20, step=5)
    team_filter = st.multiselect("Teams", sorted(shots["team_name"].dropna().unique()), placeholder="All teams")
    available_styles = sorted(shots.loc[shots["shot_archetype"].ne("Limited sample"), "shot_archetype"].dropna().unique())
    style_filter = st.multiselect("Shot styles", available_styles, placeholder="All styles")
    traded = st.selectbox("Trade status", ["All", "Current team only", "Traded only"])

filtered = shots[shots["appearances"].ge(min_appearances) & shots["attempts"].ge(min_attempts)].copy()
if team_filter:
    filtered = filtered[filtered["team_name"].isin(team_filter)]
if style_filter:
    filtered = filtered[filtered["shot_archetype"].isin(style_filter)]
if traded == "Current team only":
    filtered = filtered[~filtered["is_traded"].fillna(False).astype(bool)]
elif traded == "Traded only":
    filtered = filtered[filtered["is_traded"].fillna(False).astype(bool)]

if filtered.empty:
    st.warning("No shooters meet the current filters. Lower a sample threshold or broaden the filters.")
    st.stop()

kpis = st.columns(4)
kpis[0].metric("Players in view", f"{len(filtered)}")
kpis[1].metric("Tracked attempts", f"{filtered['attempts'].sum():,.0f}")
kpis[2].metric("Median eFG%", f"{pct(filtered['efg_percentage'].median()):.2f}%")
kpis[3].metric("Median 3PA rate", f"{pct(filtered['three_pa_rate'].median()):.2f}%")

st.divider()
chart_heading("League map", "Compare any two shooting measures across qualified players; bubble size shows shot volume and dotted lines mark the medians.")
metric_options = {
    "Attempts per game": ("attempts_per_game", "number"),
    "Effective FG%": ("efg_percentage", "percent"),
    "True shooting%": ("true_shooting_pct", "percent"),
    "Shot-making above expectation": ("shotmaking_over_expected", "number"),
    "Three-point attempt rate": ("three_pa_rate", "percent"),
    "Rim attempt rate": ("rim_attempt_rate", "percent"),
    "Free-throw rate": ("ft_rate", "percent"),
    "Contested eFG%": ("contested_efg_percentage", "percent"),
    "Pressure delta": ("pressure_delta", "percent"),
    "Shot variety": ("shot_diet_entropy", "percent"),
}
control_a, control_b, control_c = st.columns(3)
with control_a:
    x_label = st.selectbox("Horizontal axis", metric_options, index=0)
with control_b:
    y_label = st.selectbox("Vertical axis", metric_options, index=1)
with control_c:
    color_by = st.selectbox("Color", ["Shot style", "Team"])

x_column, x_format = metric_options[x_label]
y_column, y_format = metric_options[y_label]
plot_data = filtered.dropna(subset=[x_column, y_column]).copy()
plot_data["True shooting %"] = (plot_data["true_shooting_pct"] * 100).round(2)
x_plot = x_column
y_plot = y_column
if x_format == "percent":
    x_plot = f"{x_column}_pct"
    plot_data[x_plot] = (plot_data[x_column] * 100).round(2)
if y_format == "percent":
    y_plot = f"{y_column}_pct"
    plot_data[y_plot] = (plot_data[y_column] * 100).round(2)

fig = px.scatter(
    plot_data,
    x=x_plot,
    y=y_plot,
    color="shot_archetype" if color_by == "Shot style" else "team_name",
    size="attempts",
    hover_name="player_name",
    hover_data={"team_name": True, "attempts": ":,.0f", "appearances": True, "True shooting %": ":.2f", x_plot: ":.2f", y_plot: ":.2f"},
    labels={x_plot: x_label + (" (%)" if x_format == "percent" else ""), y_plot: y_label + (" (%)" if y_format == "percent" else ""), "shot_archetype": "Shot style", "team_name": "Team", "attempts": "Field-goal attempts", "appearances": "Games played", "player_name": "Player"},
    color_discrete_sequence=BOLD_PALETTE,
)
fig.add_vline(x=plot_data[x_plot].median(), line_dash="dot", line_color=COLORS["muted"], opacity=0.65)
fig.add_hline(y=plot_data[y_plot].median(), line_dash="dot", line_color=COLORS["muted"], opacity=0.65)
fig = style_figure(fig, height=540)
fig.update_layout(title_text="")
st.plotly_chart(fig, width="stretch", key="shooting_league_map")

leaders_tab, zones_tab, context_tab = st.tabs(["Leaderboards", "League zone profile", "Pressure & creation"])

with leaders_tab:
    leader_metrics = {
        "Overall scoring impact": ("scoring_impact_score", "score"),
        "Effective FG%": ("efg_percentage", "percent"),
        "True shooting%": ("true_shooting_pct", "percent"),
        "Shot-making above expectation": ("shotmaking_over_expected", "number"),
        "Floor-spacing score": ("spacing_score", "score"),
        "Rim attack score": ("rim_pressure_score", "score"),
        "Attempts per game": ("attempts_per_game", "number"),
    }
    leader_label = st.selectbox("Rank by", leader_metrics)
    leader_column, leader_format = leader_metrics[leader_label]
    leaders = filtered.dropna(subset=[leader_column]).nlargest(25, leader_column).copy()
    percent_cols = ["efg_percentage", "three_pa_rate", "rim_attempt_rate"]
    if leader_format == "percent" and leader_column not in percent_cols:
        percent_cols.append(leader_column)
    leaders = percent_copy(leaders, percent_cols)
    leader_columns = list(dict.fromkeys([
        "player_name", "team_name", "shot_archetype", leader_column,
        "attempts", "efg_percentage", "three_pa_rate", "rim_attempt_rate", "shooting_reliability",
    ]))
    st.dataframe(
        leaders[leader_columns], width="stretch", hide_index=True,
        column_config={
            "player_name": "Player", "team_name": "Team", "shot_archetype": "Shot style",
            leader_column: st.column_config.NumberColumn(leader_label, format="%.2f" if leader_format != "score" else "%.0f"),
            "attempts": st.column_config.NumberColumn("FGA", format="%d"),
            "efg_percentage": st.column_config.NumberColumn("eFG%", format="%.2f%%"),
            "three_pa_rate": st.column_config.NumberColumn("3PA rate", format="%.2f%%"),
            "rim_attempt_rate": st.column_config.NumberColumn("Rim rate", format="%.2f%%"),
            "shooting_reliability": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%.0f"),
        },
    )

with zones_tab:
    chart_heading("League shot distribution", "Shows what share of all filtered shot attempts comes from each court zone.")
    zone_rows = []
    total_filtered_attempts = filtered["attempts"].sum()
    for zone, (attempt_col, made_col, pct_col, point_value) in ZONE_CONFIG.items():
        attempts = filtered[attempt_col].sum()
        mades = filtered[made_col].sum()
        zone_rows.append({
            "Zone": zone,
            "Attempts": attempts,
            "League attempt share": round(attempts / total_filtered_attempts * 100, 2) if total_filtered_attempts else 0,
            "League FG%": round(mades / attempts * 100, 2) if attempts else 0,
            "Point value": point_value,
        })
    league_zones = pd.DataFrame(zone_rows)
    zone_fig = px.bar(
        league_zones, x="Zone", y="League attempt share", text="League FG%", color="Zone",
        hover_data={"Attempts": ":,.0f", "League attempt share": ":.2f", "League FG%": ":.2f"},
        labels={"League attempt share": "Share of league attempts (%)", "League FG%": "League FG%"},
        title="Where the filtered league takes its shots",
        color_discrete_sequence=BOLD_PALETTE,
    )
    zone_fig.update_traces(texttemplate="%{text:.2f}% FG", textposition="outside")
    zone_fig.update_layout(showlegend=False)
    zone_fig = style_figure(zone_fig, height=430)
    zone_fig.update_layout(title_text="")
    st.plotly_chart(zone_fig, width="stretch", key="league_zone_distribution")

    chart_heading("High-value scoring producers by zone", "Ranks efficient scorers by the points they produced from the selected shot zone.")
    selected_zone = st.selectbox("Select a shot zone", list(ZONE_CONFIG), key="league_zone_producer")
    attempt_col, made_col, pct_col, point_value = ZONE_CONFIG[selected_zone]
    zone_players = filtered[filtered[attempt_col].ge(min_zone_attempts)].copy()
    if zone_players.empty:
        st.info("No players meet the selected zone-attempt threshold.")
    else:
        median_fg = zone_players[pct_col].median()
        zone_players = zone_players[zone_players[pct_col].ge(median_fg)].copy()
        zone_players["Zone FG%"] = (zone_players[pct_col] * 100).round(2)
        zone_players["Field-goal points"] = zone_players[made_col] * point_value
        leaders = zone_players.nlargest(10, "Field-goal points").sort_values("Field-goal points")
        fig = px.bar(
            leaders, x="Field-goal points", y="player_name", orientation="h", text="Zone FG%",
            hover_data={"team_name": True, attempt_col: ":,.0f", "Zone FG%": ":.2f"},
            labels={"player_name": "Player", "team_name": "Team", attempt_col: "Attempts in zone", "Zone FG%": "Field-goal %", "Field-goal points": "Points scored from zone"},
            title=f"High-value producers — {selected_zone}",
            color="player_name", color_discrete_sequence=BOLD_PALETTE,
        )
        fig.update_layout(showlegend=False)
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        fig = style_figure(fig, height=440)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key="zone_producers")

    chart_heading("Zone reliance vs blocked-shot rate", "Shows whether players who rely more on the selected zone also have more of their shots blocked overall.")
    selected_block_zone = st.selectbox("Select zone for blocked-shot analysis", list(ZONE_CONFIG), key="league_block_zone")
    block_attempt_col = ZONE_CONFIG[selected_block_zone][0]
    blocked = filtered[filtered[block_attempt_col].ge(min_zone_attempts)].copy()
    blocked["Zone attempt rate"] = (blocked[block_attempt_col] / blocked["attempts"] * 100).round(2)
    blocked["Blocked-shot rate"] = (blocked["block_rate"] * 100).round(2)
    blocked["eFG%"] = (blocked["efg_percentage"] * 100).round(2)
    blocked = blocked.dropna(subset=["Zone attempt rate", "Blocked-shot rate"])
    if blocked.empty:
        st.info("No players meet the blocked-shot chart requirements.")
    else:
        fig = px.scatter(
            blocked, x="Zone attempt rate", y="Blocked-shot rate", size="attempts", color="eFG%",
            hover_name="player_name", hover_data={"team_name": True, "attempts": ":,.0f", "blocked_shots": ":,.0f", "Zone attempt rate": ":.2f", "Blocked-shot rate": ":.2f", "eFG%": ":.2f"},
            labels={"Zone attempt rate": f"{selected_block_zone} shot share (%)", "Blocked-shot rate": "Shots blocked (%)", "team_name": "Team", "attempts": "Field-goal attempts", "blocked_shots": "Blocked attempts", "eFG%": "Effective FG%", "player_name": "Player"},
            title=f"{selected_block_zone} reliance vs overall blocked-shot rate",
            color_continuous_scale=PERFORMANCE_SCALE,
        )
        fig = style_figure(fig, height=440)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key="zone_block_scatter")

with context_tab:
    pressure_col, creation_col = st.columns(2, gap="large")
    pressure_data = filtered[filtered["contested_attempts"].ge(25) & filtered["uncontested_attempts"].ge(15)].dropna(subset=["contested_efg_percentage", "uncontested_efg_percentage"]).copy()
    with pressure_col:
        chart_heading("Pressure response", "Compares each player's shooting efficiency on open shots versus contested shots; the lines mark league medians.")
        if pressure_data.empty:
            st.info("No players meet the pressure-context thresholds.")
        else:
            pressure_data["Uncontested eFG%"] = (pressure_data["uncontested_efg_percentage"] * 100).round(2)
            pressure_data["Contested eFG%"] = (pressure_data["contested_efg_percentage"] * 100).round(2)
            pressure_fig = px.scatter(
                pressure_data, x="Uncontested eFG%", y="Contested eFG%", color="shot_archetype", size="attempts", hover_name="player_name",
                hover_data={"team_name": True, "attempts": ":,.0f", "Uncontested eFG%": ":.2f", "Contested eFG%": ":.2f"},
                labels={"player_name": "Player", "team_name": "Team", "shot_archetype": "Shot style", "attempts": "Field-goal attempts", "Uncontested eFG%": "Open-shot eFG%", "Contested eFG%": "Contested-shot eFG%"},
                color_discrete_sequence=BOLD_PALETTE,
            )
            pressure_fig.add_vline(x=pressure_data["Uncontested eFG%"].median(), line_dash="dot", line_color=COLORS["muted"], opacity=0.75)
            pressure_fig.add_hline(y=pressure_data["Contested eFG%"].median(), line_dash="dot", line_color=COLORS["muted"], opacity=0.75)
            pressure_fig = style_figure(pressure_fig, height=390)
            pressure_fig.update_layout(title_text="")
            st.plotly_chart(pressure_fig, width="stretch", key="pressure_scatter")
    with creation_col:
        chart_heading("Catch vs off the dribble", "Compares shooting efficiency when a player shoots after a catch versus after creating the shot off the dribble.")
        creation_data = filtered[filtered["cns_attempts"].ge(25) & filtered["od_attempts"].ge(25)].dropna(subset=["cns_efg_percentage", "od_efg_percentage"]).copy()
        if creation_data.empty:
            st.info("No players meet both creation-context thresholds.")
        else:
            creation_data["Catch-and-shoot eFG%"] = (creation_data["cns_efg_percentage"] * 100).round(2)
            creation_data["Off-dribble eFG%"] = (creation_data["od_efg_percentage"] * 100).round(2)
            creation_fig = px.scatter(
                creation_data, x="Catch-and-shoot eFG%", y="Off-dribble eFG%", color="shot_archetype", size="attempts", hover_name="player_name",
                hover_data={"team_name": True, "attempts": ":,.0f", "Catch-and-shoot eFG%": ":.2f", "Off-dribble eFG%": ":.2f"},
                labels={"player_name": "Player", "team_name": "Team", "shot_archetype": "Shot style", "attempts": "Field-goal attempts", "Catch-and-shoot eFG%": "Catch-and-shoot eFG%", "Off-dribble eFG%": "Off-the-dribble eFG%"},
                color_discrete_sequence=BOLD_PALETTE,
            )
            creation_fig = style_figure(creation_fig, height=390)
            creation_fig.update_layout(title_text="")
            st.plotly_chart(creation_fig, width="stretch", key="creation_scatter")

metric_glossary_block([
    ("eFG%", "Shooting percentage adjusted so made three-pointers receive extra credit for being worth three points."),
    ("True shooting %", "Overall scoring efficiency that accounts for two-pointers, three-pointers and free throws."),
    ("Shot share", "The percentage of a player's shots that come from a particular area or type."),
    ("Blocked-shot rate", "The percentage of a player's field-goal attempts that were blocked."),
    ("Contested", "A shot taken with meaningful defensive pressure."),
    ("Uncontested", "A shot taken with little or no immediate defensive pressure."),
    ("Catch-and-shoot", "A shot taken shortly after receiving a pass, without first creating off the dribble."),
    ("Off the dribble", "A shot created after the player has dribbled the ball."),
])
