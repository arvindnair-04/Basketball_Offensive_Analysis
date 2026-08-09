from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
from pathlib import Path
import streamlit as st

from usage_tracking import initialize_usage_tracking, log_event
from admin_auth import (authenticate_admin, clear_admin_session, initialize_admin_database, initialize_admin_session, is_admin_logged_in, set_admin_session,)

# Streamlit page configuration
st.set_page_config(page_title="Basketball Offensive Scouting Dashboard", page_icon="🏀", layout="wide", initial_sidebar_state="expanded")

# Database configuration
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "users.db"

PASSWORD_ITERATIONS = 600_000

# Database helpers
def get_database_connection() -> sqlite3.Connection:
    """ Open a connection to the user database."""
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database() -> None:
    """Create the users table if it does not already exist."""
    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()

# Input normalization and validation
def normalize_username(username: str) -> str:
    """Normalize usernames so capitalization cannot create duplicates."""
    return username.strip().lower()

def normalize_name(name: str) -> str:
    """Remove extra spaces and apply normal title capitalization."""
    return " ".join(name.strip().split()).title()

def is_valid_username(username: str) -> bool:
    """Allow usernames containing letters, numbers and underscores. Length must be between 3 and 30 characters."""
    return bool(re.fullmatch(r"[a-z0-9_]{3,30}", username))

def is_valid_name(name: str) -> bool:
    """Allow letters, spaces, apostrophes and hyphens in names."""
    return bool(re.fullmatch( r"[A-Za-zÀ-ÖØ-öø-ÿ' -]{1,50}", name.strip()))

def validate_password(password: str) -> tuple[bool, str]:
    """Apply basic password requirements."""
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    if not any(character.isalpha() for character in password):
        return False, "Password must contain at least one letter."
    if not any(character.isdigit() for character in password):
        return False, "Password must contain at least one number."
    return True, ""

# Password security
def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = os.urandom(32)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return password_hash.hex(), salt.hex()

def verify_password(submitted_password: str, stored_hash_hex: str, stored_salt_hex: str) -> bool:
    """Compare the submitted password with the stored password hash."""
    salt = bytes.fromhex(stored_salt_hex)
    submitted_hash, _ = hash_password(submitted_password, salt=salt)
    return hmac.compare_digest(submitted_hash, stored_hash_hex)

# Account database operations
def username_exists(username: str) -> bool:
    """Return True when an account already uses the username."""
    normalized_username = normalize_username(username)
    with get_database_connection() as connection:
        existing_user = connection.execute(
            """
            SELECT user_id
            FROM users
            WHERE username = ?
            """,
            (normalized_username,),
        ).fetchone()
    return existing_user is not None

def create_user(username: str, first_name: str, last_name: str, password: str) -> tuple[bool, str]:
    """Validate and create a new account."""
    normalized_username = normalize_username(username)
    normalized_first_name = normalize_name(first_name)
    normalized_last_name = normalize_name(last_name)
    if not normalized_username:
        return False, "Enter a username."
    if not is_valid_username(normalized_username):
        return (False,"Username must contain 3–30 lowercase letters, numbers or underscores.")
    if not is_valid_name(normalized_first_name):
        return False, "Enter a valid first name."
    if not is_valid_name(normalized_last_name):
        return False, "Enter a valid last name."
    password_is_valid, password_error = validate_password(password)
    if not password_is_valid:
        return False, password_error
    if username_exists(normalized_username):
        return False, "That username is already in use."
    password_hash, password_salt = hash_password(password)
    try:
        with get_database_connection() as connection:
            role = "user"
            connection.execute(
                """
                INSERT INTO users (
                    username,
                    first_name,
                    last_name,
                    password_hash,
                    password_salt,
                    role
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized_username, normalized_first_name, normalized_last_name, password_hash, password_salt, role))
            connection.commit()
    except sqlite3.IntegrityError:
        return False, "That username is already in use."
    return True, "Account created successfully."

def authenticate_user(username: str, password: str) -> sqlite3.Row | None:
    """Return the user record when the submitted credentials match."""
    normalized_username = normalize_username(username)
    with get_database_connection() as connection:
        user = connection.execute(
            """
            SELECT
                user_id,
                username,
                first_name,
                last_name,
                password_hash,
                password_salt,
                role
            FROM users
            WHERE username = ?
            """,
            (normalized_username,)
        ).fetchone()
    if user is None:
        return None
    password_matches = verify_password(submitted_password=password, stored_hash_hex=user["password_hash"], stored_salt_hex=user["password_salt"])
    if not password_matches:
        return None
    return user

# Session-state helpers
def initialize_session_state() -> None:
    """Initialize authentication state once per browser session."""
    default_values = {
        "logged_in": False,
        "user_id": None,
        "username": None,
        "first_name": None,
        "last_name": None,
        "full_name": None,
        "role": None,
        "show_admin_login": False,
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

def set_authenticated_user(user: sqlite3.Row) -> None:
    """Save the authenticated user's information in session state."""
    first_name = user["first_name"]
    last_name = user["last_name"]
    st.session_state.logged_in = True
    st.session_state.user_id = user["user_id"]
    st.session_state.username = user["username"]
    st.session_state.first_name = first_name
    st.session_state.last_name = last_name
    st.session_state.full_name = f"{first_name} {last_name}"
    st.session_state.role = user["role"]
    log_event("login")

def log_out() -> None:
    """Clear all authentication information."""
    if st.session_state.get("logged_in"):
        log_event("logout")
    authentication_keys = [
        "logged_in",
        "user_id",
        "username",
        "first_name",
        "last_name",
        "full_name",
        "role"
    ]
    for key in authentication_keys:
        if key in st.session_state:
            del st.session_state[key]
    initialize_session_state()
    st.rerun()

# Authentication page
def authentication_page() -> None:
    """Display user login/registration or the administrator login form."""
    left_space, content_column, right_space = st.columns([1, 1.3, 1])
    with content_column:
        st.markdown(
            """
            <div style="text-align: center; padding-top: 2rem;">
                <div style="font-size: 4rem;">🏀</div>
                <h1>Offensive Scouting Dashboard</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Administrator login is intentionally separated from normal scout accounts, while still running inside the same Streamlit deployment/database.
        if st.session_state.get("show_admin_login", False):
            st.markdown("### 🔐 Administrator Login")
            st.caption("Administrator access is restricted to product-usage analytics.")

            with st.form(key="embedded_admin_login_form", clear_on_submit=False):
                admin_username = st.text_input(
                    "Admin username",
                    placeholder="Enter administrator username",
                    key="embedded_admin_username",
                )
                admin_password = st.text_input(
                    "Admin password",
                    type="password",
                    placeholder="Enter administrator password",
                    key="embedded_admin_password",
                )
                admin_submitted = st.form_submit_button(
                    "Log in as administrator",
                    use_container_width=True,
                    type="primary",
                )

            if admin_submitted:
                if not admin_username.strip() or not admin_password:
                    st.warning("Enter both the administrator username and password.")
                elif authenticate_admin(admin_username, admin_password):
                    set_admin_session(admin_username)
                    st.session_state.show_admin_login = False
                    st.rerun()
                else:
                    st.error("Incorrect administrator username or password.")

            if st.button(
                "← Back to user login",
                use_container_width=True,
                key="back_to_user_login",
            ):
                st.session_state.show_admin_login = False
                st.rerun()

            return

        login_tab, register_tab = st.tabs(["Log in", "Create profile"])

        # Normal scout/user login form
        with login_tab:
            with st.form(key="login_form", clear_on_submit=False):
                username = st.text_input(
                    "Username",
                    placeholder="Enter your username",
                    key="login_username",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="login_password",
                )
                login_submitted = st.form_submit_button(
                    "Log in",
                    use_container_width=True,
                    type="primary",
                )

            if login_submitted:
                if not username.strip() or not password:
                    st.warning("Enter both your username and password.")
                else:
                    user = authenticate_user(username=username, password=password)
                    if user is None:
                        st.error("Incorrect username or password.")
                    else:
                        set_authenticated_user(user)
                        st.rerun()

        # Registration form
        with register_tab:
            with st.form(key="registration_form", clear_on_submit=True):
                first_name = st.text_input("First name", placeholder="Enter your first name")
                last_name = st.text_input("Last name", placeholder="Enter your last name")
                new_username = st.text_input(
                    "Username",
                    placeholder="Choose a unique username",
                    help="Use 3–30 letters, numbers or underscores. Usernames are not case-sensitive.",
                )
                new_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Create a password",
                    help="Use at least 8 characters, including one letter and one number.",
                )
                confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                    placeholder="Enter the password again",
                )
                registration_submitted = st.form_submit_button(
                    "Create profile",
                    use_container_width=True,
                    type="primary",
                )

            if registration_submitted:
                if new_password != confirm_password:
                    st.error("The passwords do not match.")
                else:
                    account_created, message = create_user(
                        username=new_username,
                        first_name=first_name,
                        last_name=last_name,
                        password=new_password,
                    )
                    if account_created:
                        st.success(f"{message} You can now log in.")
                    else:
                        st.error(message)

        st.caption("Create a profile or sign in to access the dashboard.")
        st.divider()
        if st.button(
            "🔐 Administrator Login",
            use_container_width=True,
            key="open_admin_login",
        ):
            st.session_state.show_admin_login = True
            st.rerun()


# Application initialization
initialize_database()
initialize_usage_tracking()
initialize_admin_database()
initialize_session_state()
initialize_admin_session()

# Shared dashboard theme and overview
from analytics import load_data
from ui import chart_heading, metric_glossary_block, BOLD_PALETTE, inject_theme, page_header, style_figure
from usage_tracking import track_page_view
import plotly.express as px

inject_theme()


def render_overview() -> None:
    """Basic orientation to the supplied offensive datasets and their league coverage."""
    track_page_view("Overview")
    try:
        bundle = load_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        st.stop()

    profiles = bundle.profiles.copy()
    shots = bundle.shots.copy()
    picks = bundle.picks.copy()
    quality = bundle.quality

    page_header(
        "Liga ACB · 2024–25",
        "Offensive Analysis",
        "",
    )

    st.markdown(
        """
        This dashboard studies **season-level offensive behavior** for the 2024–25 Spanish season.  
        The shooting file describes where and how players shoot, their efficiency, pressure context and creation style.  
        The pick-and-roll file describes ball-handler and screener volume, decisions, outcomes, defensive coverage splits and screen locations.
        """
    )

    kpi = st.columns(5)
    kpi[0].metric("Players", f"{len(profiles):,}")
    kpi[1].metric("Teams", f"{quality['teams']:,}")
    kpi[2].metric("Shooting rows", f"{quality['shot_rows']:,}")
    kpi[3].metric("PnR rows", f"{quality['pick_rows']:,}")

    st.divider()
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("What the shooting data covers")
        st.markdown(
            """
            - Overall shot volume, points and eFG%
            - 2PT and 3PT usage
            - Rim, short-midrange, long-midrange and three-point zones
            - Catch-and-shoot and off-dribble creation
            - Contested and uncontested shooting
            - Blocked-shot outcomes
            """
        )
    with right:
        st.subheader("What the pick-and-roll data covers")
        st.markdown(
            """
            - Ball-handler and screener usage
            - Points created per pick, success and turnover rates
            - Shoot, pass and assist tendencies
            - Defensive coverage splits
            - Middle, step-up and wing screen locations
            - Role-specific offensive outcomes
            """
        )

    st.divider()
    st.subheader("How the league data is distributed")

    shooting_style_definitions = {
        "Limited sample": "Fewer than 20 tracked field-goal attempts; style is not treated as stable.",
        "Catch-and-shoot spacer": "Three-heavy profile with at least 55% of attempts from three and at least 55% of tracked creation from catch-and-shoot.",
        "Perimeter creator": "Three-heavy scorer with at least 55% of attempts from three, without being catch-and-shoot dominated.",
        "Rim attacker": "Rim-focused scorer with at least 45% of attempts coming at the rim.",
        "Interior / mid-range": "At least half of attempts come from short-paint or long-midrange areas.",
        "Balanced modern": "Meaningful pressure at both the rim and from three: at least 28% rim rate and 32% three-point rate.",
        "Balanced scorer": "No single tracked zone/style threshold dominates the player's shot profile.",
        "Unclassified": "The supplied row does not have enough information for a shooting-style label.",
    }
    pnr_role_definitions = {
        "Low PnR sample": "Fewer than 20 total tracked handler + screener picks.",
        "Ball handler": "At least 72% of the player's tracked PnR actions are as the handler.",
        "Screener": "At least 72% of the player's tracked PnR actions are as the screener.",
        "Dual role": "Meaningful tracked usage in both handler and screener roles.",
        "Unclassified": "The supplied row does not have enough information for a PnR-role label.",
    }

    c1, c2 = st.columns(2, gap="large", vertical_alignment="top")
    with c1:
        archetypes = shots["shot_archetype"].fillna("Unclassified").value_counts().rename_axis("Shot style").reset_index(name="Players")
        archetypes["Definition"] = archetypes["Shot style"].map(shooting_style_definitions).fillna("Shooting usage profile derived from the supplied season aggregates.")
        fig = px.pie(
            archetypes, names="Shot style", values="Players", hole=0.42, custom_data=["Definition"],
            title="Shooting-style distribution", color_discrete_sequence=BOLD_PALETTE,
        )
        fig.update_traces(
            textposition="inside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br>Players: %{value}<br>Share: %{percent}<extra></extra>",
        )
        fig.update_layout(showlegend=False)
        chart_heading("Shooting-style distribution", "Shows how players in the league are grouped by their typical shot-selection style.")
        fig = style_figure(fig, height=440)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key="overview_shot_styles")
    with c2:
        roles = picks["pnr_role"].fillna("Unclassified").value_counts().rename_axis("PnR role").reset_index(name="Players")
        roles["Definition"] = roles["PnR role"].map(pnr_role_definitions).fillna("Pick-and-roll usage profile derived from tracked handler and screener volume.")
        fig = px.pie(
            roles, names="PnR role", values="Players", hole=0.42, custom_data=["Definition"],
            title="Pick-and-roll role distribution", color_discrete_sequence=BOLD_PALETTE,
        )
        fig.update_traces(
            textposition="inside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br>Players: %{value}<br>Share: %{percent}<extra></extra>",
        )
        fig.update_layout(showlegend=False)
        chart_heading("Pick-and-roll role distribution", "Shows how players are grouped by whether they mainly handle the ball, set screens, or do both.")
        fig = style_figure(fig, height=440)
        fig.update_layout(title_text="")
        st.plotly_chart(fig, width="stretch", key="overview_pnr_roles")

    metric_glossary_block([
        ("Shooting style", "A simple label describing where and how a player usually takes shots."),
        ("Pick-and-roll role", "Whether a player is mainly the ball handler, mainly the screener, or regularly does both."),
        ("Ball handler", "The player with the ball who uses a teammate's screen."),
        ("Screener", "The player who sets the screen to help create space or an advantage."),
        ("Dual role", "A player with meaningful pick-and-roll usage as both handler and screener."),
        ("Limited sample", "There are too few tracked actions to treat the role or style as stable."),
    ])


# Page definitions
authentication = st.Page(authentication_page, title="Account", icon=":material/account_circle:")
overview = st.Page(render_overview, title="Overview", icon=":material/dashboard:", default=True)
shooting = st.Page("pages/shooting_analysis.py", title="Shooting Analysis", icon=":material/sports_basketball:")
pick_and_roll = st.Page("pages/pick_and_roll_analysis.py", title="Pick-and-Roll Analysis", icon=":material/schema:")
player_profiles = st.Page("pages/player_profiles.py", title="Player Profile", icon=":material/groups:")
admin_analytics = st.Page("pages/admin_analytics.py", title="Admin Analytics", icon=":material/analytics:", default=True)


def admin_log_out() -> None:
    """End only the administrator session and return to the shared login page."""
    clear_admin_session()
    st.session_state.show_admin_login = False
    st.rerun()


# Authenticated navigation
if is_admin_logged_in():
    with st.sidebar:
        st.markdown("## 🔐 Administration")
        st.write(f"Signed in as **{st.session_state.admin_username}**")
        st.caption("Product usage analytics")
        st.divider()
        if st.button("Log out of admin", use_container_width=True, icon=":material/logout:"):
            admin_log_out()
    navigation = st.navigation({"Administration": [admin_analytics]})
elif st.session_state.logged_in:
    with st.sidebar:
        st.markdown("## 🏀 Offensive Scouting")
        st.write(f"Welcome, **{st.session_state.full_name}**")
        st.caption(f"@{st.session_state.username}")
        st.divider()
        if st.button("Log out", use_container_width=True, icon=":material/logout:"):
            log_out()
    navigation = st.navigation({"Analysis": [overview, shooting, pick_and_roll, player_profiles]})
else:
    navigation = st.navigation([authentication], position="hidden")

navigation.run()
