from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ui import BOLD_PALETTE, COLORS, PERFORMANCE_SCALE, chart_heading, metric_glossary_block, page_header, style_figure
from admin_auth import is_admin_logged_in
from usage_tracking import APP_TIMEZONE_NAME, current_app_time, read_events, read_users


if not is_admin_logged_in():
    st.error("Administrator login is required for this page.")
    st.stop()

page_header(
    "Product Usage · Administrator",
    "Admin Analytics",
    "",
)

st.caption(f"Dashboard time: {current_app_time().strftime('%b %d, %Y · %I:%M %p')} ({APP_TIMEZONE_NAME})")

users = read_users()
events = read_events()

with st.sidebar:
    st.markdown("### Admin filters")
    date_window = st.selectbox(
        "Activity window",
        ["All time", "Last 7 days", "Last 30 days", "Last 90 days"],
        index=0,
        key="admin_date_window",
    )
    show_diagnostics = st.toggle("Show tracking diagnostics", value=False)

visible_users = users.copy()

now = current_app_time()
window_days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
if date_window in window_days:
    cutoff = now - pd.Timedelta(days=window_days[date_window])
    events = events[events["created_at"].ge(cutoff)].copy()

page_views = events[events["event_type"].eq("page_view")].copy()
player_views = events[events["event_type"].eq("player_view")].copy()
login_events = events[events["event_type"].eq("login")].copy()

active_users = events["user_id"].nunique() if not events.empty else 0
sessions = events["session_id"].nunique() if not events.empty else 0

kpis = st.columns(5)
kpis[0].metric("Registered users", f"{len(visible_users):,}")
kpis[1].metric("Active users", f"{active_users:,}")
kpis[2].metric("Sessions", f"{sessions:,}")
kpis[3].metric("Page visits", f"{len(page_views):,}")
kpis[4].metric("Player lookups", f"{len(player_views):,}")

if events.empty:
    st.warning(
        "No user activity has been recorded yet. The admin login is working, but analytics charts will populate only after a scout logs into app.py and navigates the dashboard."
    )

if show_diagnostics:
    st.code(
        f"Database: {str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'users.db')}\n"
        f"Registered users: {len(users)}\n"
        f"Recorded events in selected window: {len(events)}"
    )

st.divider()

left, right = st.columns(2, gap="large")
with left:
    chart_heading("Most visited analysis pages", "Shows which analysis pages users open most often during the selected period.")
    if page_views.empty:
        st.info("No page views recorded yet.")
    else:
        page_counts = (
            page_views.groupby("page_name", dropna=False)
            .size()
            .reset_index(name="Visits")
            .sort_values("Visits", ascending=True)
        )
        fig = px.bar(page_counts, x="Visits", y="page_name", orientation="h", text="Visits", color="page_name", labels={"page_name": "Analysis page", "Visits": "Visits"}, color_discrete_sequence=BOLD_PALETTE)
        fig.update_layout(showlegend=False)
        fig.update_layout(xaxis_title="Visits", yaxis_title="Page", showlegend=False)
        fig = style_figure(fig, height=390)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key="admin_page_counts")

with right:
    chart_heading("Most viewed players", "Shows which player profiles users open most often during the selected period.")
    if player_views.empty:
        st.info("No player-profile lookups recorded yet.")
    else:
        top_players = (
            player_views.groupby("player_name", dropna=False)
            .agg(Lookups=("event_id", "count"), Unique_users=("user_id", "nunique"))
            .reset_index()
            .sort_values(["Lookups", "Unique_users"], ascending=False)
            .head(12)
            .sort_values("Lookups")
        )
        fig = px.bar(top_players, x="Lookups", y="player_name", orientation="h", text="Lookups", hover_data={"Unique_users": True}, labels={"player_name": "Player", "Lookups": "Profile views", "Unique_users": "Different users"}, color="player_name", color_discrete_sequence=BOLD_PALETTE)
        fig.update_layout(showlegend=False)
        fig.update_layout(xaxis_title="Profile lookups", yaxis_title="Player", showlegend=False)
        fig = style_figure(fig, height=390)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key="admin_top_players")

chart_heading("Usage over time", "Shows how total activity, active users, and sessions change over time.")
if events.empty:
    st.info("Usage trend will appear after users begin navigating the scouting dashboard.")
else:
    daily = events.copy()
    daily["Date"] = daily["created_at"].dt.date
    daily_summary = (
        daily.groupby("Date")
        .agg(
            Activity=("event_id", "count"),
            Active_users=("user_id", "nunique"),
            Sessions=("session_id", "nunique"),
        )
        .reset_index()
    )
    fig = px.line(daily_summary, x="Date", y=["Activity", "Active_users", "Sessions"], markers=True, labels={"value": "Count", "variable": "Measure", "Active_users": "Active users"}, color_discrete_sequence=BOLD_PALETTE)
    fig.update_layout(yaxis_title="Count", legend_title="Metric")
    fig = style_figure(fig, height=390)
    fig.update_layout(title_text="")
    st.plotly_chart(fig, width="stretch", key="admin_usage_trend")

st.divider()
st.subheader("User engagement")

user_summary = visible_users[["user_id", "username", "first_name", "last_name", "created_at"]].copy()
user_summary["User"] = user_summary["first_name"].fillna("") + " " + user_summary["last_name"].fillna("")

if not events.empty:
    engagement = (
        events.groupby("user_id")
        .agg(
            Sessions=("session_id", "nunique"),
            Total_events=("event_id", "count"),
            Last_active=("created_at", "max"),
        )
        .reset_index()
    )
    pv = page_views.groupby("user_id").size().rename("Page_visits").reset_index()
    pl = player_views.groupby("user_id").size().rename("Player_lookups").reset_index()
    user_summary = user_summary.merge(engagement, on="user_id", how="left").merge(pv, on="user_id", how="left").merge(pl, on="user_id", how="left")

for col in ["Sessions", "Total_events", "Page_visits", "Player_lookups"]:
    if col not in user_summary:
        user_summary[col] = 0
    user_summary[col] = user_summary[col].fillna(0).astype(int)

user_summary["Last_active"] = user_summary.get("Last_active", pd.Series(pd.NaT, index=user_summary.index))
user_summary = user_summary.sort_values(["Page_visits", "Player_lookups"], ascending=False)

st.dataframe(
    user_summary[["User", "Sessions", "Page_visits", "Player_lookups", "Last_active"]],
    width="stretch",
    hide_index=True,
    column_config={
        "User": "User",
        "Sessions": st.column_config.NumberColumn("Sessions", format="%d"),
        "Page_visits": st.column_config.NumberColumn("Page visits", format="%d"),
        "Player_lookups": st.column_config.NumberColumn("Player profile views", format="%d"),
        "Last_active": st.column_config.DatetimeColumn("Last active", format="MMM D, YYYY h:mm a"),
    },
)

chart_heading("Page preference by user", "Shows which analysis pages each user visits most often.")
if page_views.empty:
    st.info("No page preference data yet.")
else:
    name_map = {int(row.user_id): f"{row.first_name} {row.last_name}".strip() for row in visible_users.itertuples(index=False)}
    page_views_named = page_views.copy()
    page_views_named["User"] = page_views_named["user_id"].map(name_map).fillna("Unknown user")
    usage_matrix = pd.crosstab(page_views_named["User"], page_views_named["page_name"])
    matrix_long = usage_matrix.reset_index().melt(id_vars="User", var_name="Page", value_name="Visits")
    fig = px.density_heatmap(
        matrix_long,
        x="Page",
        y="User",
        z="Visits",
        histfunc="sum",
        text_auto=True,
        color_continuous_scale=PERFORMANCE_SCALE,
    )
    fig.update_layout(xaxis_title="Analysis page", yaxis_title="User", coloraxis_colorbar_title="Visits")
    fig = style_figure(fig, height=max(360, 42 * len(usage_matrix) + 140))
    fig.update_layout(title_text="")
    st.plotly_chart(fig, width="stretch", key="admin_usage_matrix")

st.divider()
st.subheader("Individual user activity")

if visible_users.empty:
    st.info("No users are available under the current administrator filter.")
    st.stop()

user_lookup = {
    int(row.user_id): f"{row.first_name} {row.last_name}"
    for row in visible_users.itertuples(index=False)
}
selected_user_id = st.selectbox(
    "User",
    sorted(user_lookup, key=lambda uid: user_lookup[uid].lower()),
    format_func=lambda uid: user_lookup[uid],
    key="admin_selected_user",
)
user_events = events[events["user_id"].eq(selected_user_id)].copy()

if user_events.empty:
    st.info("This user has no activity in the selected date window.")
else:
    user_pages = user_events[user_events["event_type"].eq("page_view")]
    user_players = user_events[user_events["event_type"].eq("player_view")]

    a, b, c, d = st.columns(4)
    a.metric("Sessions", f"{user_events['session_id'].nunique():,}")
    b.metric("Page visits", f"{len(user_pages):,}")
    c.metric("Player lookups", f"{len(user_players):,}")
    favorite_page = user_pages["page_name"].mode().iat[0] if not user_pages.empty else "—"
    d.metric("Most visited page", favorite_page)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        chart_heading("Page visits", "Shows which dashboard pages this user visits most often.")
        if user_pages.empty:
            st.caption("No page visits recorded.")
        else:
            counts = user_pages["page_name"].value_counts().rename_axis("Page").reset_index(name="Visits")
            fig = px.bar(counts, x="Visits", y="Page", orientation="h", text="Visits", color="Page", color_discrete_sequence=BOLD_PALETTE)
            fig.update_layout(showlegend=False)
            fig.update_layout(showlegend=False)
            fig = style_figure(fig, height=330)
            fig.update_layout(title_text="")
            st.plotly_chart(fig, width="stretch", key="admin_user_pages")

    with col2:
        chart_heading("Most viewed players", "Shows which player profiles this user opens most often.")
        if user_players.empty:
            st.caption("No player lookups recorded.")
        else:
            counts = user_players["player_name"].value_counts().head(10).rename_axis("Player").reset_index(name="Lookups")
            fig = px.bar(counts, x="Lookups", y="Player", orientation="h", text="Lookups", color="Player", color_discrete_sequence=BOLD_PALETTE)
            fig.update_layout(showlegend=False)
            fig.update_layout(showlegend=False)
            fig = style_figure(fig, height=330)
            fig.update_layout(title_text="")
            st.plotly_chart(fig, width="stretch", key="admin_user_players")

    st.markdown("#### Recent activity")
    recent = user_events.sort_values("created_at", ascending=False).head(30).copy()
    recent["Activity"] = recent["event_type"].map({
        "login": "Logged in",
        "logout": "Logged out",
        "page_view": "Visited page",
        "player_view": "Viewed player",
        "player_compare": "Compared player",
    }).fillna(recent["event_type"])
    recent["Detail"] = recent["player_name"].fillna(recent["page_name"]).fillna("—")
    st.dataframe(
        recent[["created_at", "Activity", "Detail"]],
        width="stretch",
        hide_index=True,
        column_config={"created_at": st.column_config.DatetimeColumn("Time", format="MMM D, YYYY h:mm a")},
    )


metric_glossary_block([
    ("Registered user", "A person who has created an account for the scouting dashboard."),
    ("Active user", "A registered user who generated activity during the selected time window."),
    ("Session", "One period of dashboard use before the user leaves or signs out."),
    ("Page visit", "A recorded visit to one of the analysis pages."),
    ("Player profile view", "A recorded time when a user opened a player's profile."),
])
