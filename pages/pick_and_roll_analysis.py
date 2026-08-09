from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import load_data
from ui import BOLD_PALETTE, COLORS, PERFORMANCE_SCALE, chart_heading, metric_glossary_block, page_header, style_figure
from usage_tracking import track_page_view


track_page_view("Pick-and-Roll Analysis")


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

picks = bundle.picks.copy()
page_header(
    "Liga ACB · 2024–25",
    "Pick and Roll Analysis",
    "",
)

with st.sidebar:
    st.markdown("### Pick-and-roll filters")
    role_label = st.radio("Role", ["Ball handler", "Screener"], horizontal=True)
    role = "handler" if role_label == "Ball handler" else "screener"
    min_appearances = st.slider("Minimum appearances", 1, 35, 10, key="pnr_min_games")
    min_picks = st.slider("Minimum role picks", 0, 250, 30, step=10)
    coverage_min = st.slider("Minimum picks in a coverage", 1, 50, 10, key="pnr_coverage_min")
    location_min = st.slider("Minimum picks at a screen location", 1, 50, 10, key="pnr_location_min")
    team_filter = st.multiselect("Teams", sorted(picks["team_name"].dropna().unique()), placeholder="All teams", key="pnr_teams")
    traded = st.selectbox("Trade status", ["All", "Current team only", "Traded only"], key="pnr_trade")

volume_column = f"{role}_total_picks"
filtered = picks[picks["appearances"].ge(min_appearances) & picks[volume_column].ge(min_picks)].copy()
if team_filter:
    filtered = filtered[filtered["team_name"].isin(team_filter)]
if traded == "Current team only":
    filtered = filtered[~filtered["is_traded"].fillna(False).astype(bool)]
elif traded == "Traded only":
    filtered = filtered[filtered["is_traded"].fillna(False).astype(bool)]

if filtered.empty:
    st.warning("No players meet the current role and sample filters.")
    st.stop()

kpis = st.columns(4)
kpis[0].metric("Players in view", f"{len(filtered)}")
kpis[1].metric("Tracked picks", f"{filtered[volume_column].sum():,.0f}")
kpis[2].metric("Median points / pick", f"{filtered[f'{role}_ppp'].median():.2f}")
kpis[3].metric("Median success rate", f"{pct(filtered[f'{role}_success_rate'].median()):.2f}%")

st.divider()
chart_heading(f"{role_label} league map", "Compare any two pick-and-roll measures across qualified players; bubble size shows tracked pick volume and dotted lines mark the medians.")
metric_options = {
    "Picks per game": (f"{role}_picks_per_game", "number"),
    "Points produced per pick": (f"{role}_ppp", "number"),
    "Success rate": (f"{role}_success_rate", "percent"),
    "Turnover rate": (f"{role}_turnover_rate", "percent"),
    "Chance-creating pass rate": (f"{role}_assist_opportunity_rate", "percent"),
    "Shot rate": (f"{role}_shot_rate", "percent"),
    "Pass rate": (f"{role}_pass_rate", "percent"),
    "Playmaking score": (f"{role}_creation_score", "score"),
}
c1, c2, c3 = st.columns(3)
with c1:
    x_label = st.selectbox("Horizontal axis", metric_options, index=0, key="pnr_x")
with c2:
    y_label = st.selectbox("Vertical axis", metric_options, index=1, key="pnr_y")
with c3:
    color_by = st.selectbox("Color", ["PnR role", "Team"], key="pnr_color")
x_column, x_format = metric_options[x_label]
y_column, y_format = metric_options[y_label]
plot_data = filtered.dropna(subset=[x_column, y_column]).copy()
x_plot, y_plot = x_column, y_column
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
    color="pnr_role" if color_by == "PnR role" else "team_name",
    size=volume_column,
    hover_name="player_name",
    hover_data={"team_name": True, volume_column: ":,.0f", "appearances": True, x_plot: ":.2f", y_plot: ":.2f"},
    labels={x_plot: x_label + (" (%)" if x_format == "percent" else ""), y_plot: y_label + (" (%)" if y_format == "percent" else ""), "pnr_role": "Pick-and-roll role", "team_name": "Team", "player_name": "Player", volume_column: "Tracked picks", "appearances": "Games played"},
    color_discrete_sequence=BOLD_PALETTE,
)
fig.add_vline(x=plot_data[x_plot].median(), line_dash="dot", line_color=COLORS["muted"], opacity=0.65)
fig.add_hline(y=plot_data[y_plot].median(), line_dash="dot", line_color=COLORS["muted"], opacity=0.65)
fig = style_figure(fig, height=540)
fig.update_layout(title_text="")
st.plotly_chart(fig, width="stretch", key="pnr_league_map")

leaders_tab, coverage_tab, location_tab = st.tabs(["Leaderboards", "Coverage explorer", "Screen location"])

with leaders_tab:
    leader_options = {
        "Playmaking score": (f"{role}_creation_score", "score"),
        "Points produced per pick": (f"{role}_ppp", "number"),
        "Picks per game": (f"{role}_picks_per_game", "number"),
        "Success rate": (f"{role}_success_rate", "percent"),
        "Chance-creating pass rate": (f"{role}_assist_opportunity_rate", "percent"),
        "Ball-security percentile": (f"{role}_turnover_control_percentile", "percent"),
    }
    rank_label = st.selectbox("Rank by", leader_options, key="pnr_rank")
    rank_column, rank_type = leader_options[rank_label]
    leaders = filtered.dropna(subset=[rank_column]).nlargest(25, rank_column).copy()
    percent_cols = [f"{role}_success_rate", f"{role}_turnover_rate"]
    if rank_type == "percent" and rank_column not in percent_cols:
        percent_cols.append(rank_column)
    leaders = percent_copy(leaders, percent_cols)
    leader_columns = list(dict.fromkeys([
        "player_name", "team_name", "pnr_role", rank_column, volume_column,
        f"{role}_ppp", f"{role}_success_rate", f"{role}_turnover_rate", f"{role}_reliability",
    ]))
    st.dataframe(
        leaders[leader_columns], width="stretch", hide_index=True,
        column_config={
            "player_name": "Player", "team_name": "Team", "pnr_role": "Overall role",
            rank_column: st.column_config.NumberColumn(rank_label, format="%.2f" if rank_type != "score" else "%.0f"),
            volume_column: st.column_config.NumberColumn("Picks", format="%d"),
            f"{role}_ppp": st.column_config.NumberColumn("Points / pick", format="%.2f"),
            f"{role}_success_rate": st.column_config.NumberColumn("Success %", format="%.2f%%"),
            f"{role}_turnover_rate": st.column_config.NumberColumn("Turnover %", format="%.2f%%"),
            f"{role}_reliability": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%.0f"),
        },
    )

with coverage_tab:
    chart_heading("League response to defensive coverages", "Shows how often each defensive coverage appears and how efficiently the filtered league performs against it.")
    coverages = ["switch", "blitz", "ice", "over", "under"] if role == "handler" else ["switch", "blitz", "ice", "show", "soft"]

    summary_rows = []
    for coverage in coverages:
        picks_col = f"{role}_picks_vs_{coverage}"
        ppp_col = f"{role}_ppp_vs_{coverage}"
        success_count_col = f"{role}_successful_pick_vs_{coverage}"
        turnover_count_col = f"{role}_turnover_vs_{coverage}"
        assist_count_col = f"{role}_assist_vs_{coverage}"
        if picks_col not in filtered:
            continue
        eligible = filtered[filtered[picks_col].ge(coverage_min)].copy()
        if eligible.empty:
            continue
        total_picks = eligible[picks_col].sum()
        valid_ppp = eligible[ppp_col].notna() & eligible[picks_col].gt(0)
        league_ppp = (
            (eligible.loc[valid_ppp, ppp_col] * eligible.loc[valid_ppp, picks_col]).sum()
            / eligible.loc[valid_ppp, picks_col].sum()
            if valid_ppp.any() else None
        )
        summary_rows.append({
            "Coverage": coverage.title(),
            "Qualified players": len(eligible),
            "Tracked picks": int(total_picks),
            "League PPP": round(league_ppp, 2) if league_ppp is not None else None,
            "Success %": round(eligible[success_count_col].sum() / total_picks * 100, 2) if total_picks else None,
            "Turnover %": round(eligible[turnover_count_col].sum() / total_picks * 100, 2) if total_picks else None,
            "Assist %": round(eligible[assist_count_col].sum() / total_picks * 100, 2) if total_picks else None,
        })

    coverage_summary = pd.DataFrame(summary_rows)
    if coverage_summary.empty:
        st.info("No coverage splits meet the current sample threshold.")
    else:
        fig = px.pie(
            coverage_summary, names="Coverage", values="Tracked picks", hole=0.40,
            hover_data={"Qualified players": True, "League PPP": ":.2f", "Success %": ":.2f", "Turnover %": ":.2f", "Assist %": ":.2f"},
            title=f"Tracked {role_label.lower()} picks by defensive coverage",
            color_discrete_sequence=BOLD_PALETTE,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig = style_figure(fig, height=430)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key=f"{role}_coverage_summary")
        st.dataframe(
            coverage_summary, width="stretch", hide_index=True,
            column_config={
                "League PPP": st.column_config.NumberColumn(format="%.2f"),
                "Success %": st.column_config.NumberColumn(format="%.2f%%"),
                "Turnover %": st.column_config.NumberColumn(format="%.2f%%"),
                "Assist %": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

        selected_coverage = st.selectbox("Explore league players against", coverage_summary["Coverage"].tolist(), key=f"{role}_league_coverage")
        coverage = selected_coverage.lower()
        picks_col = f"{role}_picks_vs_{coverage}"
        ppp_col = f"{role}_ppp_vs_{coverage}"
        success_count_col = f"{role}_successful_pick_vs_{coverage}"
        league_coverage = filtered[filtered[picks_col].ge(coverage_min)].dropna(subset=[ppp_col]).copy()
        league_coverage["Success %"] = (league_coverage[success_count_col] / league_coverage[picks_col] * 100).round(2)
        if not league_coverage.empty:
            chart_heading(f"Players vs {selected_coverage}", "Shows player volume and points produced per pick against the selected defensive coverage.")
            fig = px.scatter(
                league_coverage, x=picks_col, y=ppp_col, color="Success %", size=volume_column,
                hover_name="player_name", hover_data={"team_name": True, picks_col: ":,.0f", ppp_col: ":.2f", "Success %": ":.2f"},
                labels={picks_col: f"Picks vs {selected_coverage}", ppp_col: "Points produced per pick"},
                title=f"Qualified {role_label.lower()}s vs {selected_coverage}",
                color_continuous_scale=PERFORMANCE_SCALE,
            )
            fig.add_hline(y=league_coverage[ppp_col].median(), line_dash="dot", line_color=COLORS["muted"])
            fig = style_figure(fig, height=460)
            fig.update_layout(title_text="")
            st.plotly_chart(fig, width="stretch", key=f"{role}_coverage_players")

with location_tab:
    chart_heading("League screen-location profile", "Shows where pick-and-roll screens are set most often and how the league performs from those locations.")
    locations = {"Middle": "middle", "Step-up": "stepUp", "Wing": "wing"}
    rows = []
    for display, token in locations.items():
        picks_col = f"{role}_picks_at_{token}"
        ppp_col = f"{role}_ppp_at_{token}"
        score_col = f"{role}_score_rate_at_{token}"
        eligible = filtered[filtered[picks_col].ge(location_min)].copy()
        if eligible.empty:
            continue
        weights = eligible[picks_col].fillna(0)
        valid_ppp = eligible[ppp_col].notna() & weights.gt(0)
        valid_score = eligible[score_col].notna() & weights.gt(0)
        ppp = (eligible.loc[valid_ppp, ppp_col] * weights.loc[valid_ppp]).sum() / weights.loc[valid_ppp].sum() if valid_ppp.any() else None
        score = (eligible.loc[valid_score, score_col] * weights.loc[valid_score]).sum() / weights.loc[valid_score].sum() if valid_score.any() else None
        total_picks = eligible[picks_col].sum()
        rows.append({
            "Location": display,
            "Qualified players": len(eligible),
            "Tracked picks": int(total_picks),
            "League PPP": round(ppp, 2) if ppp is not None else None,
            "Score %": pct(score),
        })
    location_profile = pd.DataFrame(rows)
    if location_profile.empty:
        st.info("No screen locations meet the current sample threshold.")
    else:
        total = location_profile["Tracked picks"].sum()
        location_profile["Pick share %"] = (location_profile["Tracked picks"] / total * 100).round(2) if total else 0
        fig = px.pie(
            location_profile, names="Location", values="Tracked picks", hole=0.40,
            hover_data={"Qualified players": True, "League PPP": ":.2f", "Pick share %": ":.2f", "Score %": ":.2f"},
            title=f"Tracked {role_label.lower()} picks by screen location",
            color_discrete_sequence=BOLD_PALETTE,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig = style_figure(fig, height=430)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key=f"{role}_location_chart")
        st.dataframe(
            location_profile, width="stretch", hide_index=True,
            column_config={
                "League PPP": st.column_config.NumberColumn(format="%.2f"),
                "Score %": st.column_config.NumberColumn(format="%.2f%%"),
                "Pick share %": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

metric_glossary_block([
    ("Pick-and-roll", "A two-player action where one player uses a teammate's screen to create an advantage."),
    ("Ball handler", "The player controlling the ball and using the screen."),
    ("Screener", "The player setting the screen for the ball handler."),
    ("Points per pick", "How many points the action produces on average for each tracked pick-and-roll."),
    ("Success rate", "The percentage of tracked pick-and-rolls counted as successful in the source data."),
    ("Turnover rate", "The percentage of tracked pick-and-rolls that end in a turnover."),
    ("Chance-creating pass", "A pass from the pick-and-roll that creates an assist opportunity."),
    ("Coverage", "The defensive strategy used to guard the pick-and-roll, such as switch, blitz, ice, over or under."),
])
