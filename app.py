from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any
import base64
import html
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import Client, create_client
from streamlit_cookies_manager_ext import EncryptedCookieManager


st.set_page_config(
    page_title="Star Citizen Tracker",
    page_icon="🚀",
    layout="wide",
)

APP_TIMEZONE = "America/Chicago"
US_TIMEZONES = {
    "Eastern (ET)": "America/New_York",
    "Central (CT)": "America/Chicago",
    "Mountain (MT)": "America/Denver",
    "Pacific (PT)": "America/Los_Angeles",
    "Alaska (AKT)": "America/Anchorage",
    "Hawaii (HST)": "Pacific/Honolulu",
}
DEFAULT_TIMEZONE = "America/Chicago"
COOKIE_PREFIX = "star-citizen-tracker/"
COOKIE_REFRESH_TOKEN = "supabase_refresh_token"
COOKIE_REMEMBERED_EMAIL = "remembered_email"

CONTRACT_TYPES = [
    "Appointment / Mission Giver",
    "Bounty Hunting",
    "Cargo Recovery",
    "Collection / Retrieval",
    "Defend Location",
    "Delivery",
    "Escort / Security",
    "Hauling",
    "Hauling - Small Grade",
    "Hauling - Supply Grade",
    "Hauling - Bulk Grade",
    "Investigation",
    "Maintenance",
    "Mercenary",
    "Mining",
    "Priority / Dynamic Event",
    "Racing",
    "Salvage",
    "Search",
    "Service Beacon - Medical",
    "Service Beacon - Combat",
    "Service Beacon - Escort",
    "Tactical Strike Group",
    "Unverified / Criminal",
    "Other / Custom",
]

ORE_TYPES = [
    "Agricium",
    "Aluminum",
    "Aphorite",
    "Beryl",
    "Bexalite",
    "Borase",
    "Copper",
    "Corundum",
    "Diamond",
    "Dolivine",
    "Gold",
    "Hadanite",
    "Hephaestanite",
    "Inert Material",
    "Iron",
    "Janalite",
    "Laranite",
    "Quantanium",
    "Quartz",
    "Riccite",
    "Stileron",
    "Taranite",
    "Titanium",
    "Tungsten",
    "Other / Custom",
]

ASSETS_DIR = Path(__file__).parent / "assets"
DATA_DIR = Path(__file__).parent / "data"
MINING_LOCATIONS_FILE = DATA_DIR / "mining_locations.csv"

STAR_CITIZEN_COLORS = [
    "#00C8FF",
    "#FF8A2A",
    "#7CE7FF",
    "#EB4C5D",
    "#8DA4B8",
]


def apply_custom_theme() -> None:
    """Apply the bright, professional Star Citizen dashboard theme."""
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f4f7fb;
            --surface: #ffffff;
            --surface-2: #f8fafc;
            --surface-3: #eef4fb;
            --border: #dbe4ee;
            --border-strong: #8fc7ff;
            --accent: #1378e5;
            --accent-2: #11a7c8;
            --accent-soft: #eaf4ff;
            --text: #10233f;
            --muted: #607087;
            --subtle: #8492a6;
            --success: #20a36a;
        }

        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 88% -12%, rgba(19,120,229,.10), transparent 34rem),
                linear-gradient(180deg, #f8fbff 0%, var(--app-bg) 100%);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: rgba(248,251,255,.86);
            border-bottom: 1px solid rgba(219,228,238,.82);
            backdrop-filter: blur(16px);
        }

        .block-container {
            max-width: 1580px;
            padding-top: .8rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            background: rgba(255,255,255,.98);
            border-right: 1px solid var(--border);
            box-shadow: 10px 0 34px rgba(30,68,110,.06);
        }

        section[data-testid="stSidebar"] > div { padding-top: 1rem; }
        section[data-testid="stSidebar"] [data-testid="stImage"] img {
            max-height: 94px;
            width: 100%;
            object-fit: contain;
            border-radius: 0;
        }

        h1, h2, h3 { color: var(--text) !important; letter-spacing: -.018em; }
        p, label, .stCaption { color: var(--muted); }

        .sc-banner {
            position: relative;
            min-height: 300px;
            display: flex;
            align-items: flex-end;
            overflow: hidden;
            border-radius: 18px;
            border: 1px solid #cbd8e6;
            margin-bottom: 1.15rem;
            background-position: center;
            background-repeat: no-repeat;
            background-size: contain;
            background-color: #091827;
            box-shadow: 0 18px 44px rgba(24,62,103,.16);
        }

        .sc-banner::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(0deg, rgba(4,17,31,.88) 0%, rgba(4,17,31,.08) 66%);
        }

        .sc-banner-content { position: relative; z-index: 2; max-width: 830px; padding: 1.55rem 1.75rem; }
        .sc-kicker { color: #8fdcff; text-transform: uppercase; letter-spacing: .16em; font-size: .72rem; font-weight: 800; margin-bottom: .38rem; }
        .sc-banner-title { color: #fff; font-size: clamp(1.75rem,4vw,2.75rem); line-height: 1.04; font-weight: 800; margin: 0 0 .48rem; text-shadow: 0 3px 15px rgba(0,0,0,.42); }
        .sc-banner-subtitle { color: #e3edf7; font-size: .98rem; max-width: 720px; margin: 0; }

        /* Interior page banners use a split layout so the full supplied image
           remains visible instead of being cropped as a background. */
        .sc-page-banner {
            display: grid;
            grid-template-columns: minmax(300px, .74fr) minmax(520px, 1.26fr);
            align-items: center;
            overflow: hidden;
            border-radius: 20px;
            border: 1px solid #d9e3ee;
            margin-bottom: 1.15rem;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            box-shadow: 0 18px 44px rgba(24,62,103,.10);
        }

        .sc-page-banner-copy {
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-self: stretch;
            padding: 1.7rem 1.8rem 1.75rem;
            color: var(--text);
            background:
                radial-gradient(circle at top left, rgba(19,120,229,.12), transparent 14rem),
                linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(248,251,255,.98) 100%);
        }

        .sc-page-banner-image-wrap {
            position: relative;
            min-width: 0;
            padding: 1rem 1rem 1rem .35rem;
            background:
                radial-gradient(circle at 10% 50%, rgba(19,120,229,.10), transparent 15rem),
                linear-gradient(135deg, #edf5ff 0%, #f8fbff 100%);
        }

        .sc-page-banner-image-frame {
            width: 100%;
            overflow: hidden;
            border-radius: 16px;
            border: 1px solid rgba(143,199,255,.45);
            background: #081827;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 10px 24px rgba(24,62,103,.10);
        }

        .sc-page-banner-image {
            width: 100%;
            height: auto;
            object-fit: unset;
            object-position: initial;
            display: block;
        }

        .sc-page-banner .sc-kicker { margin-bottom: .5rem; }
        .sc-page-banner .sc-banner-title {
            font-size: clamp(1.8rem, 3vw, 2.55rem);
            color: var(--text);
            text-shadow: none;
        }
        .sc-page-banner .sc-banner-subtitle {
            max-width: 520px;
            line-height: 1.58;
            color: var(--muted);
        }

        .dashboard-hero-grid { display:grid; grid-template-columns:minmax(0,1fr) 230px; gap:14px; margin-bottom:1rem; }
        .dashboard-hero-grid .sc-banner { margin-bottom:0; min-height:315px; }
        .time-card { background:rgba(255,255,255,.97); border:1px solid var(--border); border-radius:18px; padding:1rem; box-shadow:0 16px 38px rgba(24,62,103,.12); color:var(--text); }
        .time-card .time-now { font-size:2rem; font-weight:800; margin:.15rem 0; }
        .time-card .time-date { font-size:.78rem; color:var(--muted); margin-bottom:.75rem; }
        .time-zone-row { display:flex; justify-content:space-between; gap:.75rem; padding:.23rem 0; font-size:.77rem; border-bottom:1px solid #edf2f7; }
        .time-zone-row:last-child { border-bottom:0; }
        .time-settings { margin-top:.75rem; padding-top:.7rem; border-top:1px solid var(--border); font-size:.77rem; color:var(--accent); font-weight:700; }

        .section-heading { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:1.25rem 0 .7rem; }
        .section-title { color:var(--text); font-size:1.18rem; font-weight:780; margin:0; }
        .section-copy { color:var(--muted); font-size:.84rem; margin:.15rem 0 0; }
        .chart-heading { color:var(--text); font-size:1.04rem; font-weight:760; margin:0 0 .12rem; }
        .chart-copy { color:var(--muted); font-size:.8rem; margin:0 0 .25rem; }

        div[data-testid="stMetric"] {
            background:var(--surface); border:1px solid var(--border); border-radius:15px;
            padding:1rem; min-height:118px; box-shadow:0 10px 26px rgba(24,62,103,.08);
        }
        [data-testid="stMetricLabel"] { color:#66768c !important; text-transform:uppercase; letter-spacing:.06em; font-size:.69rem !important; font-weight:760; }
        [data-testid="stMetricValue"] { color:var(--text) !important; font-weight:820; }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background:var(--surface); border:1px solid var(--border) !important;
            border-radius:16px !important; box-shadow:0 10px 26px rgba(24,62,103,.07);
        }

        .feature-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:.4rem 0 1rem; }

        .dashboard-feature-image {
            width: 100%;
            aspect-ratio: 3 / 1;
            height: auto;
            display: block;
            object-fit: cover;
            object-position: center center;
            border-radius: 12px;
            background: #081624;
        }

        .feature-card-title {
            color: var(--text);
            font-weight: 780;
            font-size: .95rem;
            min-height: 1.45rem;
            margin-top: .15rem;
        }

        .feature-card-copy {
            color: var(--muted);
            font-size: .78rem;
            line-height: 1.55;
            min-height: 3.75rem;
            margin: .3rem 0 .2rem;
        }

        [class*="st-key-dashboard_feature_card_"] {
            height: 100%;
        }

        [class*="st-key-dashboard_feature_card_"] > div {
            height: 100%;
        }

        [class*="st-key-dashboard_feature_card_"] [data-testid="stVerticalBlockBorderWrapper"] {
            height: 100%;
            min-height: 360px;
        }

        [class*="st-key-dashboard_feature_card_"] [data-testid="stVerticalBlock"] {
            height: 100%;
            display: flex;
            flex-direction: column;
        }

        [class*="st-key-dashboard_feature_card_"] .stButton {
            margin-top: auto;
        }

        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button, .stLinkButton > a {
            border:1px solid #85bfff; border-radius:10px; background:#f2f8ff; color:#1268c5 !important;
            font-weight:760; min-height:2.75rem; box-shadow:none;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover, .stLinkButton > a:hover {
            border-color:#1378e5; background:#e4f1ff; color:#0c57aa !important;
        }

        section[data-testid="stSidebar"] .stButton > button {
            width:100%; height:3.35rem; min-height:3.35rem; justify-content:flex-start;
            padding:.72rem .9rem; margin:.14rem 0; border-radius:11px; font-size:.9rem; text-align:left;
        }
        section[data-testid="stSidebar"] .stButton > button[kind="secondary"] { background:#fff; border:1px solid var(--border); color:#21354f !important; }
        section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover { background:#f2f8ff; border-color:#9ccaff; }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background:#e9f4ff; border:1px solid #87beff; color:#0f65c1 !important; box-shadow:inset 3px 0 0 var(--accent); }

        div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
            background:#fff !important; border-color:#cfdbe8 !important; color:#142941 !important; border-radius:9px !important;
        }
        div[data-baseweb="select"] > div:focus-within, .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
            border-color:#72b4fa !important; box-shadow:0 0 0 1px rgba(19,120,229,.18) !important;
        }
        [data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:13px; overflow:hidden; }
        div[data-testid="stAlert"] { border:1px solid var(--border); border-radius:12px; background:#fff; }
        [data-testid="stTabs"] button { color:var(--muted); }
        [data-testid="stTabs"] button[aria-selected="true"] { color:var(--accent); border-bottom-color:var(--accent); }
        hr { border-color:#e5ebf2; }

        @media (max-width:1050px) {
            .dashboard-hero-grid { grid-template-columns:1fr; }
            .feature-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
            .sc-page-banner {
                grid-template-columns: minmax(280px, .84fr) minmax(420px, 1.16fr);
            }
        }
        @media (max-width:820px) {
            .sc-page-banner {
                grid-template-columns: 1fr;
                min-height: 0;
            }
            .sc-page-banner-copy {
                padding: 1.45rem 1.4rem 1rem;
            }
            .sc-page-banner-image-wrap {
                min-height: 0;
                padding: 0 1rem 1rem;
            }
            .sc-page-banner-image-frame {
                min-height: 0;
            }
            .sc-page-banner-image {
                width: 100%;
                height: auto;
            }
        }
        @media (max-width:720px) {
            .sc-banner { min-height:220px; }
            .feature-grid { grid-template-columns:1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@lru_cache(maxsize=16)
def image_data_uri(filename: str) -> str:
    """Return a local image as a cached data URI for a CSS background."""
    image_path = ASSETS_DIR / filename
    if not image_path.exists():
        return ""
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    suffix = image_path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def page_banner(
    image_filename: str,
    title: str,
    subtitle: str,
    kicker: str,
) -> None:
    """Render a cleaner split page banner while preserving the image."""
    image_uri = image_data_uri(image_filename)
    st.markdown(
        f"""
        <section class="sc-page-banner" aria-label="{title}">
            <div class="sc-page-banner-copy">
                <div class="sc-kicker">{kicker}</div>
                <div class="sc-banner-title">{title}</div>
                <p class="sc-banner-subtitle">{subtitle}</p>
            </div>
            <div class="sc-page-banner-image-wrap">
                <div class="sc-page-banner-image-frame">
                    <img
                        class="sc-page-banner-image"
                        src="{image_uri}"
                        alt="{title}"
                    />
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def style_plotly_figure(figure, *, height: int = 430) -> None:
    """Give Plotly charts the same bright professional appearance as the app."""
    figure.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font={"color": "#243a55", "family": "Inter, sans-serif"},
        colorway=STAR_CITIZEN_COLORS,
        margin={"l": 30, "r": 26, "t": 42, "b": 30},
        legend_title_text="",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        hoverlabel={"bgcolor": "#ffffff", "bordercolor": "#87beff", "font_color": "#10233f"},
    )
    figure.update_xaxes(gridcolor="#e9eff6", zerolinecolor="#dfe7f0", linecolor="#d7e1ec", tickfont={"color": "#6f8095"}, title_font={"color": "#607087"})
    figure.update_yaxes(gridcolor="#e9eff6", zerolinecolor="#dfe7f0", linecolor="#d7e1ec", tickfont={"color": "#6f8095"}, title_font={"color": "#607087"})


def empty_dashboard_figure(message: str, *, donut: bool = False):
    """Return a visible chart shell when the current filters have no data."""
    figure = go.Figure()

    if donut:
        figure.add_shape(
            type="circle",
            xref="paper",
            yref="paper",
            x0=0.31,
            y0=0.16,
            x1=0.69,
            y1=0.84,
            line={"color": "rgba(137,157,181,0.20)", "width": 18},
        )
        figure.update_xaxes(visible=False, range=[0, 1])
        figure.update_yaxes(visible=False, range=[0, 1])
    else:
        figure.update_xaxes(
            title_text="",
            showgrid=True,
            range=[0, 6],
            tickvals=list(range(7)),
            ticktext=["" for _ in range(7)],
        )
        figure.update_yaxes(
            title_text="aUEC",
            showgrid=True,
            range=[0, 1],
            tickvals=[0, 0.5, 1],
            ticktext=["0", "", ""],
        )

    figure.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text=f"<b>No data yet</b><br><span style='color:#6f8095'>{message}</span>",
        showarrow=False,
        align="center",
        font={"size": 14, "color": "#243a55"},
    )
    style_plotly_figure(figure)
    return figure


def chart_card(title: str, subtitle: str, figure, key: str) -> None:
    """Render a dashboard chart inside a consistent card."""
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="chart-heading">{title}</div>
            <div class="chart-copy">{subtitle}</div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
            key=key,
        )



def get_supabase() -> Client:
    """Create one Supabase client for this browser session."""
    if "supabase_client" not in st.session_state:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except KeyError as exc:
            st.error(
                "Supabase secrets are missing. Add SUPABASE_URL and "
                "SUPABASE_KEY in Streamlit Secrets."
            )
            st.stop()
            raise RuntimeError("Missing Streamlit secrets") from exc

        st.session_state.supabase_client = create_client(url, key)

    return st.session_state.supabase_client


def get_cookie_manager() -> EncryptedCookieManager | None:
    """Load encrypted browser cookies without blocking the whole app."""
    try:
        cookie_password = st.secrets["COOKIE_PASSWORD"]
    except KeyError:
        return None

    if not cookie_password:
        return None

    try:
        if "cookie_manager" not in st.session_state:
            st.session_state.cookie_manager = EncryptedCookieManager(
                prefix=COOKIE_PREFIX,
                password=str(cookie_password),
            )

        cookies = st.session_state.cookie_manager

        # The browser cookie component may need one render cycle before it is
        # ready. Returning None keeps the login page visible instead of
        # stopping the entire Streamlit script on a blank screen.
        if not cookies.ready():
            return None

        return cookies
    except Exception:
        # Persistent login is optional. The app should still load and allow a
        # normal Supabase sign-in if browser cookie storage is unavailable.
        st.session_state.pop("cookie_manager", None)
        return None


def save_cookie_value(
    cookies: EncryptedCookieManager | None,
    key: str,
    value: str,
) -> None:
    if cookies is None:
        return
    cookies[key] = value
    cookies.save()


def remove_cookie_value(
    cookies: EncryptedCookieManager | None,
    key: str,
) -> None:
    if cookies is None:
        return
    cookies.pop(key, None)
    cookies.save()


def resolve_user_display_name(user: Any, email: str = "") -> str:
    """Return a friendly display name from Supabase metadata or the email."""
    metadata = (
        getattr(user, "user_metadata", None)
        or getattr(user, "raw_user_meta_data", None)
        or {}
    )

    if isinstance(metadata, dict):
        for key in ("display_name", "full_name", "name", "first_name"):
            value = str(metadata.get(key, "") or "").strip()
            if value:
                return value

    local_part = (email or "").split("@", 1)[0]
    first_piece = re.split(r"[._\-+]+", local_part)[0].strip()
    return first_piece.title() if first_piece else "Citizen"


def set_authenticated_user(user: Any, fallback_email: str = "") -> None:
    """Store the signed-in user's ID, email, and display name."""
    user_email = getattr(user, "email", None) or fallback_email or ""
    st.session_state.user_id = str(user.id)
    st.session_state.user_email = user_email or "Signed in"
    st.session_state.user_display_name = resolve_user_display_name(
        user,
        user_email,
    )


def profile_settings(client: Client) -> None:
    """Let the current user update the name shown in the app."""
    current_name = st.session_state.get("user_display_name", "Citizen")

    with st.form("profile_settings_form"):
        new_name = st.text_input(
            "Display name",
            value=current_name,
            help="This name appears in your dashboard greeting.",
        )
        submitted = st.form_submit_button(
            "Save display name",
            width="stretch",
        )

    if submitted:
        cleaned_name = new_name.strip()
        if not cleaned_name:
            st.error("Enter a display name.")
            return

        try:
            response = client.auth.update_user(
                {"data": {"display_name": cleaned_name}}
            )
            updated_user = getattr(response, "user", None)
            if updated_user is not None:
                set_authenticated_user(
                    updated_user,
                    st.session_state.get("user_email", ""),
                )
            else:
                st.session_state.user_display_name = cleaned_name
            st.success("Display name updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"The display name could not be updated: {exc}")


def remember_authenticated_session(
    response: Any,
    email: str,
    keep_signed_in: bool,
    cookies: EncryptedCookieManager | None,
) -> None:
    """Remember the email and, when selected, the Supabase refresh token."""
    if cookies is None:
        return

    cookies[COOKIE_REMEMBERED_EMAIL] = email.strip()
    session = getattr(response, "session", None)
    refresh_token = getattr(session, "refresh_token", None) if session else None

    if keep_signed_in and refresh_token:
        cookies[COOKIE_REFRESH_TOKEN] = refresh_token
    else:
        cookies.pop(COOKIE_REFRESH_TOKEN, None)
    cookies.save()


def restore_login_from_cookie(
    client: Client,
    cookies: EncryptedCookieManager | None,
) -> None:
    """Restore a Supabase session after a full browser refresh."""
    if cookies is None or "user_id" in st.session_state:
        return

    refresh_token = cookies.get(COOKIE_REFRESH_TOKEN)
    if not refresh_token:
        return

    try:
        response = client.auth.refresh_session(refresh_token)
        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if user is None and session is not None:
            user = getattr(session, "user", None)

        if user is None:
            raise RuntimeError("The saved session did not include a user.")

        user_email = getattr(user, "email", None) or cookies.get(
            COOKIE_REMEMBERED_EMAIL,
            "",
        )
        set_authenticated_user(user, user_email)

        new_refresh_token = (
            getattr(session, "refresh_token", None) if session else None
        )
        if new_refresh_token:
            cookies[COOKIE_REFRESH_TOKEN] = new_refresh_token
        if user_email:
            cookies[COOKIE_REMEMBERED_EMAIL] = user_email
        cookies.save()
    except Exception:
        remove_cookie_value(cookies, COOKIE_REFRESH_TOKEN)


def clear_login_state() -> None:
    for key in (
        "user_id",
        "user_email",
        "user_display_name",
        "supabase_client",
    ):
        st.session_state.pop(key, None)


def login_screen(
    client: Client,
    cookies: EncryptedCookieManager | None,
) -> None:
    page_banner(
        "hero_banner.jpg",
        "Star Citizen Tracker",
        "A private operations ledger for contracts, mining, trading, and performance analysis across the verse.",
        "Operations Console",
    )

    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    remembered_email = (
        cookies.get(COOKIE_REMEMBERED_EMAIL, "") if cookies is not None else ""
    )
    if "login_email" not in st.session_state:
        st.session_state.login_email = remembered_email

    with login_tab:
        if cookies is None:
            st.info(
                "The app is ready for a normal sign-in. Browser-based persistent "
                "login may take one page cycle to initialize."
            )

        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )
            keep_signed_in = st.checkbox(
                "Keep me signed in on this device",
                value=True,
                disabled=False,
                help=(
                    "Stores an encrypted Supabase refresh token in this browser. "
                    "Your password is never saved."
                ),
            )
            submitted = st.form_submit_button("Sign in", width="stretch")

        if submitted:
            try:
                response = client.auth.sign_in_with_password(
                    {"email": email.strip(), "password": password}
                )
                if response.user is None:
                    st.error("The sign-in response did not include a user.")
                else:
                    user_email = response.user.email or email.strip()
                    set_authenticated_user(response.user, user_email)
                    remember_authenticated_session(
                        response,
                        user_email,
                        keep_signed_in,
                        cookies,
                    )
                    st.rerun()
            except Exception as exc:
                st.error(f"Sign in failed: {exc}")

    with signup_tab:
        st.info(
            "Create one private account and use the same login on your "
            "computer, phone, and tablet."
        )
        with st.form("signup_form"):
            new_display_name = st.text_input(
                "Display name",
                key="signup_display_name",
                placeholder="How your name should appear",
            )
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
                help="Use at least 8 characters.",
            )
            submitted = st.form_submit_button(
                "Create account",
                width="stretch",
            )

        if submitted:
            try:
                cleaned_display_name = (
                    new_display_name.strip()
                    or resolve_user_display_name(None, new_email.strip())
                )
                response = client.auth.sign_up(
                    {
                        "email": new_email.strip(),
                        "password": new_password,
                        "options": {
                            "data": {
                                "display_name": cleaned_display_name,
                            }
                        },
                    }
                )
                if response.user is None:
                    st.error("The account could not be created.")
                elif response.session is None:
                    st.success(
                        "Account created. Check your email if Supabase email "
                        "confirmation is enabled, then sign in."
                    )
                else:
                    user_email = response.user.email or new_email.strip()
                    set_authenticated_user(response.user, user_email)
                    remember_authenticated_session(
                        response,
                        user_email,
                        True,
                        cookies,
                    )
                    st.rerun()
            except Exception as exc:
                st.error(f"Account creation failed: {exc}")


def fetch_table(table_name: str) -> pd.DataFrame:
    client = get_supabase()
    response = (
        client.table(table_name)
        .select("*")
        .order("date_saved", desc=True)
        .execute()
    )
    return pd.DataFrame(response.data or [])


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    contracts = fetch_table("contracts")
    ores = fetch_table("ore_transactions")

    for frame in (contracts, ores):
        if not frame.empty and "date_saved" in frame.columns:
            frame["date_saved"] = pd.to_datetime(
                frame["date_saved"],
                errors="coerce",
                utc=True,
            ).dt.tz_convert(APP_TIMEZONE)

    return contracts, ores


def format_money(value: float | int) -> str:
    return f"{float(value):,.0f} aUEC"


def insert_contract(payload: dict[str, Any]) -> None:
    get_supabase().table("contracts").insert(payload).execute()


def insert_ore(payload: dict[str, Any]) -> None:
    get_supabase().table("ore_transactions").insert(payload).execute()


def delete_record(table_name: str, record_id: int) -> None:
    (
        get_supabase()
        .table(table_name)
        .delete()
        .eq("id", record_id)
        .execute()
    )


def update_record(
    table_name: str,
    record_id: int,
    payload: dict[str, Any],
) -> None:
    (
        get_supabase()
        .table(table_name)
        .update(payload)
        .eq("id", record_id)
        .execute()
    )


def filter_data(
    frame: pd.DataFrame,
    date_range: str,
    search_text: str,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    filtered = frame.copy()

    days_lookup = {
        "Last 7 Days": 7,
        "Last 30 Days": 30,
        "Last 90 Days": 90,
    }

    if date_range in days_lookup and "date_saved" in filtered.columns:
        cutoff = pd.Timestamp.now(tz=APP_TIMEZONE) - pd.Timedelta(
            days=days_lookup[date_range]
        )
        filtered = filtered[filtered["date_saved"] >= cutoff]

    search_text = search_text.strip().lower()
    if search_text:
        searchable = (
            filtered.fillna("")
            .astype(str)
            .apply(lambda column: column.str.lower())
        )
        matching = searchable.apply(
            lambda row: row.str.contains(search_text, regex=False).any(),
            axis=1,
        )
        filtered = filtered[matching]

    return filtered


def display_contract_table(contracts: pd.DataFrame) -> None:
    if contracts.empty:
        st.info("No contract records match the current filters.")
        return

    table = contracts.rename(
        columns={
            "id": "ID",
            "date_saved": "Date",
            "contract_name": "Contract",
            "contract_type": "Type",
            "offer_group": "Offer Group",
            "system_name": "System / Area",
            "total_payout": "Total Payout",
            "expenses": "Expenses",
            "crew_members": "Crew",
            "net_payout": "Net Payout",
            "individual_share": "Individual Share",
            "notes": "Notes",
        }
    ).copy()

    ordered_columns = [
        "ID",
        "Date",
        "Contract",
        "Type",
        "Offer Group",
        "System / Area",
        "Total Payout",
        "Expenses",
        "Crew",
        "Net Payout",
        "Individual Share",
        "Notes",
    ]
    table = table[[column for column in ordered_columns if column in table.columns]]

    if "Date" in table.columns:
        table["Date"] = table["Date"].dt.strftime("%Y-%m-%d %I:%M %p")

    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "Total Payout": st.column_config.NumberColumn(format="%,.0f aUEC"),
            "Expenses": st.column_config.NumberColumn(format="%,.0f aUEC"),
            "Net Payout": st.column_config.NumberColumn(format="%,.0f aUEC"),
            "Individual Share": st.column_config.NumberColumn(
                format="%,.0f aUEC"
            ),
        },
    )


def display_ore_table(ores: pd.DataFrame) -> None:
    if ores.empty:
        st.info("No ore records match the current filters.")
        return

    table = ores.rename(
        columns={
            "id": "ID",
            "date_saved": "Date",
            "action": "Action",
            "ore_name": "Ore",
            "total_value": "Value",
            "location": "Location",
            "notes": "Notes",
        }
    ).copy()

    ordered_columns = [
        "ID",
        "Date",
        "Action",
        "Ore",
        "Value",
        "Location",
        "Notes",
    ]
    table = table[[column for column in ordered_columns if column in table.columns]]

    if "Date" in table.columns:
        table["Date"] = table["Date"].dt.strftime("%Y-%m-%d %I:%M %p")

    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "Value": st.column_config.NumberColumn(format="%,.0f aUEC"),
        },
    )


def selected_timezone() -> str:
    """Return the user's chosen IANA timezone, falling back safely."""
    return st.session_state.get("selected_timezone", DEFAULT_TIMEZONE)


def timezone_settings() -> None:
    """Render timezone controls in the sidebar settings section."""
    common_options = list(US_TIMEZONES.values())
    all_options = sorted(available_timezones())
    current = selected_timezone()
    mode = st.radio(
        "Timezone options",
        ["U.S. timezones", "All timezones"],
        horizontal=True,
        key="timezone_mode",
        label_visibility="collapsed",
    )
    choices = common_options if mode == "U.S. timezones" else all_options
    if current not in choices:
        choices = [current, *choices]
    chosen = st.selectbox(
        "Display timezone",
        choices,
        index=choices.index(current),
        key="timezone_selector",
    )
    st.session_state.selected_timezone = chosen
    st.caption(f"Current selection: {chosen}")


def dashboard_hero() -> None:
    """Render the dashboard banner and the U.S. timezone overview."""
    background = image_data_uri("dashboard_banner.jpg")
    now_utc = datetime.now(ZoneInfo("UTC"))
    preferred = selected_timezone()
    local_now = now_utc.astimezone(ZoneInfo(preferred))
    rows = "".join(
        f'<div class="time-zone-row"><span>{label}</span><strong>{now_utc.astimezone(ZoneInfo(zone)).strftime("%I:%M %p")}</strong></div>'
        for label, zone in US_TIMEZONES.items()
    )
    display_name = html.escape(
        st.session_state.get("user_display_name", "Citizen")
    )
    st.markdown(
        f"""
        <div class="dashboard-hero-grid">
            <section class="sc-banner" style="background-image:url('{background}');" aria-label="Operations Dashboard">
                <div class="sc-banner-content">
                    <div class="sc-kicker">Live Command Overview</div>
                    <div class="sc-banner-title">Welcome back, {display_name}</div>
                    <p class="sc-banner-subtitle">Track, analyze, and optimize contracts, mining, trade, and saved operations across the Verse.</p>
                </div>
            </section>
            <aside class="time-card">
                <div style="font-size:.76rem;color:#607087;font-weight:750;">SELECTED TIMEZONE</div>
                <div class="time-now">{local_now.strftime('%I:%M %p')}</div>
                <div class="time-date">{local_now.strftime('%A, %B %d, %Y')}<br>{preferred}</div>
                {rows}
                <div class="time-settings">⚙ Change timezone in Sidebar Settings</div>
            </aside>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_dashboard_cards() -> None:
    """Render equal-height dashboard shortcuts with working Streamlit buttons."""
    cards = [
        {
            "image": "contracts_feature.jpg",
            "title": "Contracts Snapshot",
            "copy": "Track active contracts, completions, reputation, and earnings.",
            "button": "View Contracts",
            "target": "Contract Calculator",
        },
        {
            "image": "ore_feature.jpg",
            "title": "Ore Trends",
            "copy": "Monitor mining output, refinery yields, and resource trends.",
            "button": "View Ore Ledger",
            "target": "Ore Ledger",
        },
        {
            "image": "records_feature.jpg",
            "title": "Saved Records",
            "copy": "Access saved routes, cargo logs, and complete operation history.",
            "button": "View Records",
            "target": "Saved Records",
        },
        {
            "image": "fleet_feature.jpg",
            "title": "Mining Locations",
            "copy": "Search ore and gem spawn locations by resource, system, and mining method.",
            "button": "View Mining Locations",
            "target": "Mining Locations",
        },
    ]

    columns = st.columns(4, gap="small")

    for index, (column, card) in enumerate(zip(columns, cards)):
        with column:
            with st.container(
                border=True,
                key=f"dashboard_feature_card_{index}",
            ):
                image_uri = image_data_uri(card["image"])
                st.markdown(
                    f"""
                    <img
                        class="dashboard-feature-image"
                        src="{image_uri}"
                        alt="{card["title"]}"
                    />
                    <div class="feature-card-title">{card["title"]}</div>
                    <div class="feature-card-copy">{card["copy"]}</div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    card["button"],
                    key=f'dashboard_shortcut_{card["target"].lower().replace(" ", "_")}',
                    width="stretch",
                ):
                    st.session_state.nav_page = card["target"]
                    st.rerun()

def dashboard_page() -> None:
    dashboard_hero()

    contracts, ores = load_data()

    with st.container(border=True):
        filter_col1, filter_col2 = st.columns([1, 2])
        with filter_col1:
            date_range = st.selectbox(
                "Date range",
                ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
                key="dashboard_date_range",
            )
        with filter_col2:
            search_text = st.text_input(
                "Search records",
                placeholder="Contract, ore, type, location, or notes",
                key="dashboard_search",
            )

    contracts = filter_data(contracts, date_range, search_text)
    ores = filter_data(ores, date_range, search_text)

    contract_net = (
        float(contracts["net_payout"].sum()) if not contracts.empty else 0.0
    )
    personal_share = (
        float(contracts["individual_share"].sum())
        if not contracts.empty
        else 0.0
    )
    mined_value = (
        float(ores.loc[ores["action"] == "Mined", "total_value"].sum())
        if not ores.empty
        else 0.0
    )
    ore_sales = (
        float(ores.loc[ores["action"] == "Sold", "total_value"].sum())
        if not ores.empty
        else 0.0
    )
    ore_purchases = (
        float(ores.loc[ores["action"] == "Bought", "total_value"].sum())
        if not ores.empty
        else 0.0
    )

    st.markdown("<div class='section-title'>Overview</div>", unsafe_allow_html=True)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Contracts Completed", f"{len(contracts):,}")
    metric_columns[1].metric("Ore Entries", f"{len(ores):,}")
    metric_columns[2].metric("Total Earnings (aUEC)", format_money(personal_share))
    metric_columns[3].metric("Ore Trade Net", format_money(ore_sales - ore_purchases))

    feature_dashboard_cards()

    st.markdown(
        """
        <div class="section-heading">
            <div>
                <div class="section-title">Performance overview</div>
                <div class="section-copy">All primary charts stay visible, including before the first record is entered.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if contracts.empty:
        contract_time_figure = empty_dashboard_figure(
            "Save a contract to begin tracking income over time."
        )
        contract_type_figure = empty_dashboard_figure(
            "Contract categories will appear here after your first mission."
        )
    else:
        contract_time_data = contracts.dropna(subset=["date_saved"]).copy()
        contract_time_data["Day"] = contract_time_data["date_saved"].dt.floor("D")
        contract_time_data = (
            contract_time_data.groupby("Day", as_index=False)
            .agg(
                net_payout=("net_payout", "sum"),
                contract_count=("id", "count"),
            )
            .sort_values("Day")
        )
        contract_time_data["plot_value"] = contract_time_data["net_payout"].abs()
        contract_time_data["value_label"] = contract_time_data["net_payout"].map(
            lambda value: f"{value:,.0f} aUEC"
        )

        contract_time_figure = px.area(
            contract_time_data,
            x="Day",
            y="plot_value",
            markers=True,
            custom_data=["net_payout", "contract_count", "value_label"],
            labels={
                "plot_value": "Payout magnitude in aUEC",
                "contract_count": "Contracts",
            },
        )
        contract_time_figure.update_traces(
            line={"width": 2.5},
            fillcolor="rgba(42,224,199,0.12)",
            mode="lines+markers+text",
            text=contract_time_data["value_label"],
            textposition="top center",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "Net payout: %{customdata[0]:,.0f} aUEC<br>"
                "Contracts: %{customdata[1]}<extra></extra>"
            ),
        )
        contract_time_figure.update_yaxes(rangemode="tozero")
        style_plotly_figure(contract_time_figure, height=430)

        contract_type_data = (
            contracts.groupby("contract_type", as_index=False)
            .agg(
                net_payout=("net_payout", "sum"),
                contract_count=("id", "count"),
            )
            .sort_values("net_payout", ascending=True)
            .tail(8)
        )
        contract_type_data["plot_value"] = contract_type_data["net_payout"].abs()
        contract_type_data["value_label"] = contract_type_data["net_payout"].map(
            lambda value: f"{value:,.0f} aUEC"
        )

        contract_type_figure = px.bar(
            contract_type_data,
            x="plot_value",
            y="contract_type",
            orientation="h",
            custom_data=["net_payout", "contract_count", "value_label"],
            text="value_label",
            labels={
                "plot_value": "Payout magnitude in aUEC",
                "contract_type": "Contract type",
                "contract_count": "Contracts",
            },
        )
        contract_type_colors = [
            "#20A36A" if value >= 0 else "#E5484D"
            for value in contract_type_data["net_payout"]
        ]
        contract_type_figure.update_traces(
            marker_color=contract_type_colors,
            textposition="inside",
            insidetextanchor="middle",
            textfont={"color": "#ffffff", "size": 13},
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Net payout: %{customdata[0]:,.0f} aUEC<br>"
                "Contracts: %{customdata[1]}<extra></extra>"
            ),
        )
        contract_type_figure.update_xaxes(
            rangemode="tozero",
            title_text="Payout magnitude in aUEC",
        )
        style_plotly_figure(contract_type_figure, height=430)
        contract_type_figure.update_layout(
            margin={"l": 38, "r": 28, "t": 54, "b": 42},
            showlegend=False,
        )
        contract_type_figure.add_annotation(
            x=0,
            y=1.08,
            xref="paper",
            yref="paper",
            text="<span style='color:#20A36A'>■ Positive</span>&nbsp;&nbsp;&nbsp;"
                 "<span style='color:#E5484D'>■ Negative</span>",
            showarrow=False,
            xanchor="left",
            font={"size": 12},
        )

    if ores.empty:
        ore_value_figure = empty_dashboard_figure(
            "Mined, bought, and sold mineral values will appear here."
        )
        ore_mix_figure = empty_dashboard_figure(
            "Your mining and trade activity mix will appear here.",
            donut=True,
        )
    else:
        ore_value_data = (
            ores.groupby(["ore_name", "action"], as_index=False)
            .agg(
                total_value=("total_value", "sum"),
                entry_count=("id", "count"),
            )
            .sort_values("total_value", ascending=False)
        )
        leading_ores = (
            ore_value_data.groupby("ore_name")["total_value"]
            .sum()
            .nlargest(8)
            .index
        )
        ore_value_data = ore_value_data[
            ore_value_data["ore_name"].isin(leading_ores)
        ]
        ore_value_data["plot_value"] = ore_value_data["total_value"].abs()
        ore_value_data["value_label"] = ore_value_data["total_value"].map(
            lambda value: f"{value:,.0f}"
        )

        ore_value_figure = px.bar(
            ore_value_data,
            x="ore_name",
            y="plot_value",
            color="action",
            barmode="group",
            custom_data=["total_value", "entry_count", "value_label"],
            text="value_label",
            labels={
                "ore_name": "Ore or mineral",
                "plot_value": "Value magnitude in aUEC",
                "action": "Entry type",
                "entry_count": "Entries",
            },
        )
        ore_value_figure.update_traces(
            textposition="inside",
            insidetextanchor="middle",
            textfont={"color": "#ffffff", "size": 12},
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Type: %{fullData.name}<br>"
                "Recorded value: %{customdata[0]:,.0f} aUEC<br>"
                "Entries: %{customdata[1]}<extra></extra>"
            ),
        )
        ore_value_figure.update_yaxes(
            rangemode="tozero",
            title_text="Value in aUEC",
        )
        ore_value_figure.update_xaxes(title_text="Ore or mineral")
        style_plotly_figure(ore_value_figure, height=430)
        ore_value_figure.update_layout(
            margin={"l": 38, "r": 24, "t": 32, "b": 88},
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": -0.20,
                "xanchor": "center",
                "x": 0.5,
                "title_text": "",
            },
            bargap=0.18,
            bargroupgap=0.06,
        )

        ore_mix_data = (
            ores.groupby("action", as_index=False)
            .agg(
                total_value=("total_value", "sum"),
                entry_count=("id", "count"),
            )
        )
        ore_mix_figure = px.pie(
            ore_mix_data,
            names="action",
            values="total_value",
            hole=0.62,
            hover_data=["entry_count"],
        )
        ore_mix_figure.update_traces(
            textinfo="label+percent+value",
            texttemplate="%{label}<br>%{value:,.0f} aUEC<br>%{percent}",
            textposition="inside",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Value: %{value:,.0f} aUEC<br>"
                "Share: %{percent}<extra></extra>"
            ),
            marker={"line": {"color": "#ffffff", "width": 3}},
        )
        style_plotly_figure(ore_mix_figure, height=430)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        chart_card(
            "Contract earnings over time",
            "Daily net contract payout for the selected date range.",
            contract_time_figure,
            "dashboard_contract_time",
        )
    with chart_col2:
        chart_card(
            "Contract earnings by type",
            "Top contract categories ranked by total net payout.",
            contract_type_figure,
            "dashboard_contract_type",
        )

    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        chart_card(
            "Ore value by mineral",
            "Compare mined, purchased, and sold value by resource.",
            ore_value_figure,
            "dashboard_ore_value",
        )
    with chart_col4:
        chart_card(
            "Ore activity mix",
            "Share of total recorded ore value by activity type.",
            ore_mix_figure,
            "dashboard_ore_mix",
        )

    st.markdown(
        """
        <div class="section-heading">
            <div>
                <div class="section-title">Recent records</div>
                <div class="section-copy">Review the underlying contract and ore entries without leaving the dashboard.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    contract_tab, ore_tab = st.tabs(["Contracts", "Ore ledger"])
    with contract_tab:
        display_contract_table(contracts)
    with ore_tab:
        display_ore_table(ores)



def contract_page() -> None:
    page_banner(
        "contracts_banner.jpg",
        "Contract Pay Calculator",
        "Record mission payouts, account for operating expenses, and calculate a fair crew split.",
        "Mission Operations",
    )

    with st.form("contract_form", clear_on_submit=True):
        contract_name = st.text_input(
            "Contract name",
            placeholder="Example: ERT Group Bounty",
        )
        selected_type = st.selectbox("Contract type", CONTRACT_TYPES)
        custom_type = ""
        if selected_type == "Other / Custom":
            custom_type = st.text_input("Custom contract type")

        offer_group = st.selectbox(
            "Offer group",
            [
                "Verified",
                "Unverified",
                "Priority / Event",
                "Player Service Beacon",
                "Personal / Other",
            ],
        )
        system_name = st.text_input(
            "System / area",
            placeholder="Example: Stanton, Pyro, Nyx, ArcCorp",
        )

        money_col1, money_col2, money_col3 = st.columns(3)
        with money_col1:
            total_payout = st.number_input(
                "Total payout",
                min_value=0.0,
                step=1000.0,
            )
        with money_col2:
            expenses = st.number_input(
                "Expenses",
                min_value=0.0,
                step=1000.0,
            )
        with money_col3:
            crew_members = st.number_input(
                "Crew members",
                min_value=1,
                max_value=100,
                value=1,
                step=1,
            )

        notes = st.text_area("Notes")
        submitted = st.form_submit_button(
            "Calculate and Save Contract",
            width="stretch",
        )

    if submitted:
        contract_type = (
            custom_type.strip()
            if selected_type == "Other / Custom"
            else selected_type
        )

        if not contract_name.strip():
            st.error("Enter a contract name.")
            return
        if not contract_type:
            st.error("Enter a custom contract type.")
            return
        if total_payout <= 0:
            st.error("Enter a payout greater than zero.")
            return

        net_payout = total_payout - expenses
        individual_share = net_payout / int(crew_members)

        payload = {
            "user_id": st.session_state.user_id,
            "contract_name": contract_name.strip(),
            "contract_type": contract_type,
            "offer_group": offer_group,
            "system_name": system_name.strip(),
            "total_payout": total_payout,
            "expenses": expenses,
            "crew_members": int(crew_members),
            "net_payout": net_payout,
            "individual_share": individual_share,
            "notes": notes.strip(),
        }

        try:
            insert_contract(payload)
            st.success("Contract saved.")
            summary_columns = st.columns(3)
            summary_columns[0].metric("Net payout", format_money(net_payout))
            summary_columns[1].metric(
                "Crew members",
                f"{int(crew_members)}",
            )
            summary_columns[2].metric(
                "Pay per person",
                format_money(individual_share),
            )
        except Exception as exc:
            st.error(f"The contract could not be saved: {exc}")


def ore_page() -> None:
    page_banner(
        "ore_banner.jpg",
        "Mining and Ore Ledger",
        "Track mined, purchased, and sold resources across Stanton, Pyro, Nyx, and future systems.",
        "Industrial Operations",
    )

    with st.form("ore_form", clear_on_submit=True):
        action = st.selectbox("Entry type", ["Mined", "Bought", "Sold"])
        selected_ore = st.selectbox("Ore or mineral", ORE_TYPES)
        custom_ore = ""
        if selected_ore == "Other / Custom":
            custom_ore = st.text_input("Custom ore or mineral")

        total_value = st.number_input(
            "Total value",
            min_value=0.0,
            step=1000.0,
        )
        location = st.text_input(
            "Location",
            placeholder="Example: Aberdeen, ARC-L1, Levski",
        )
        notes = st.text_area(
            "Notes",
            placeholder="Raw, refined, ship used, buyer, seller, or other details",
        )
        submitted = st.form_submit_button(
            "Save Ore Entry",
            width="stretch",
        )

    if submitted:
        ore_name = (
            custom_ore.strip()
            if selected_ore == "Other / Custom"
            else selected_ore
        )

        if not ore_name:
            st.error("Enter a custom ore or mineral.")
            return
        if total_value <= 0:
            st.error("Enter a value greater than zero.")
            return

        payload = {
            "user_id": st.session_state.user_id,
            "action": action,
            "ore_name": ore_name,
            "total_value": total_value,
            "location": location.strip(),
            "notes": notes.strip(),
        }

        try:
            insert_ore(payload)
            st.success(
                f"{action} entry saved: {ore_name} | "
                f"{format_money(total_value)}"
            )
        except Exception as exc:
            st.error(f"The ore entry could not be saved: {exc}")


def prepare_contract_export(contracts: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "date_saved": "Date",
        "contract_name": "Contract",
        "contract_type": "Type",
        "offer_group": "Offer Group",
        "system_name": "System / Area",
        "total_payout": "Total Payout",
        "expenses": "Expenses",
        "crew_members": "Crew Members",
        "net_payout": "Net Payout",
        "individual_share": "Individual Share",
        "notes": "Notes",
    }
    export = contracts.rename(columns=columns).copy()
    ordered = [
        "Date",
        "Contract",
        "Type",
        "Offer Group",
        "System / Area",
        "Total Payout",
        "Expenses",
        "Crew Members",
        "Net Payout",
        "Individual Share",
        "Notes",
    ]
    export = export[[column for column in ordered if column in export.columns]]
    if "Date" in export.columns:
        export["Date"] = pd.to_datetime(export["Date"], errors="coerce")
        if getattr(export["Date"].dt, "tz", None) is not None:
            export["Date"] = export["Date"].dt.tz_localize(None)
    return export


def prepare_ore_export(ores: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "date_saved": "Date",
        "action": "Action",
        "ore_name": "Ore / Mineral",
        "total_value": "Total Value",
        "location": "Location",
        "notes": "Notes",
    }
    export = ores.rename(columns=columns).copy()
    ordered = [
        "Date",
        "Action",
        "Ore / Mineral",
        "Total Value",
        "Location",
        "Notes",
    ]
    export = export[[column for column in ordered if column in export.columns]]
    if "Date" in export.columns:
        export["Date"] = pd.to_datetime(export["Date"], errors="coerce")
        if getattr(export["Date"].dt, "tz", None) is not None:
            export["Date"] = export["Date"].dt.tz_localize(None)
    return export


def set_export_column_widths(worksheet: Any, frame: pd.DataFrame) -> None:
    for column_index, column_name in enumerate(frame.columns):
        values = frame[column_name].fillna("").astype(str)
        maximum = max([len(str(column_name)), *values.map(len).tolist()])
        worksheet.set_column(column_index, column_index, min(maximum + 2, 42))


def build_excel_export(
    contracts: pd.DataFrame,
    ores: pd.DataFrame,
) -> bytes:
    """Create one formatted workbook that opens in Excel or Google Sheets."""
    contract_export = prepare_contract_export(contracts)
    ore_export = prepare_ore_export(ores)

    gross_payout = (
        float(contracts["total_payout"].sum())
        if not contracts.empty and "total_payout" in contracts.columns
        else 0.0
    )
    net_payout = (
        float(contracts["net_payout"].sum())
        if not contracts.empty and "net_payout" in contracts.columns
        else 0.0
    )
    ore_value = (
        float(ores["total_value"].sum())
        if not ores.empty and "total_value" in ores.columns
        else 0.0
    )

    output = BytesIO()
    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
        datetime_format="yyyy-mm-dd hh:mm AM/PM",
    ) as writer:
        workbook = writer.book
        summary = workbook.add_worksheet("Summary")
        writer.sheets["Summary"] = summary

        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 20,
                "font_color": "#FFFFFF",
                "bg_color": "#0B0E13",
                "align": "left",
                "valign": "vcenter",
            }
        )
        label_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#8E9AAA",
                "bg_color": "#11151C",
                "border": 1,
                "border_color": "#28313D",
            }
        )
        value_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 14,
                "font_color": "#2AE0C7",
                "bg_color": "#11151C",
                "border": 1,
                "border_color": "#28313D",
            }
        )
        money_value_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 14,
                "font_color": "#2AE0C7",
                "bg_color": "#11151C",
                "border": 1,
                "border_color": "#28313D",
                "num_format": '#,##0 "aUEC"',
            }
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#116B68",
                "border": 1,
                "border_color": "#2AE0C7",
                "align": "center",
                "valign": "vcenter",
            }
        )
        money_format = workbook.add_format({"num_format": '#,##0 "aUEC"'})
        date_format = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm AM/PM"})

        summary.set_tab_color("#2AE0C7")
        summary.set_column("A:A", 23)
        summary.set_column("B:B", 24)
        summary.set_column("D:H", 15)
        summary.set_row(0, 34)
        summary.merge_range("A1:H1", "STAR CITIZEN TRACKER EXPORT", title_format)
        summary.write("A3", "Account", label_format)
        summary.write("B3", st.session_state.get("user_email", ""), value_format)
        summary.write("A4", "Generated", label_format)
        summary.write(
            "B4",
            datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            value_format,
        )
        summary.write("A6", "Contract Records", label_format)
        summary.write_number("B6", len(contracts), value_format)
        summary.write("A7", "Gross Contract Payout", label_format)
        summary.write_number("B7", gross_payout, money_value_format)
        summary.write("A8", "Net Contract Payout", label_format)
        summary.write_number("B8", net_payout, money_value_format)
        summary.write("A9", "Ore Ledger Entries", label_format)
        summary.write_number("B9", len(ores), value_format)
        summary.write("A10", "Recorded Ore Value", label_format)
        summary.write_number("B10", ore_value, money_value_format)
        summary.write(
            "A12",
            "This .xlsx file can be opened directly in Microsoft Excel or "
            "uploaded into Google Sheets.",
        )

        contract_export.to_excel(
            writer,
            sheet_name="Contracts",
            index=False,
            startrow=0,
        )
        contract_sheet = writer.sheets["Contracts"]
        contract_sheet.freeze_panes(1, 0)
        contract_sheet.set_row(0, 24, header_format)
        set_export_column_widths(contract_sheet, contract_export)
        for column_index, column_name in enumerate(contract_export.columns):
            contract_sheet.write(0, column_index, column_name, header_format)
            if column_name == "Date":
                contract_sheet.set_column(column_index, column_index, 22, date_format)
            elif column_name in {
                "Total Payout",
                "Expenses",
                "Net Payout",
                "Individual Share",
            }:
                contract_sheet.set_column(column_index, column_index, 18, money_format)
        if len(contract_export):
            contract_sheet.add_table(
                0,
                0,
                len(contract_export),
                len(contract_export.columns) - 1,
                {
                    "name": "ContractsTable",
                    "style": "Table Style Medium 2",
                    "columns": [
                        {"header": column} for column in contract_export.columns
                    ],
                },
            )
        elif len(contract_export.columns):
            contract_sheet.autofilter(0, 0, 0, len(contract_export.columns) - 1)

        ore_export.to_excel(
            writer,
            sheet_name="Ore Ledger",
            index=False,
            startrow=0,
        )
        ore_sheet = writer.sheets["Ore Ledger"]
        ore_sheet.freeze_panes(1, 0)
        ore_sheet.set_row(0, 24, header_format)
        set_export_column_widths(ore_sheet, ore_export)
        for column_index, column_name in enumerate(ore_export.columns):
            ore_sheet.write(0, column_index, column_name, header_format)
            if column_name == "Date":
                ore_sheet.set_column(column_index, column_index, 22, date_format)
            elif column_name == "Total Value":
                ore_sheet.set_column(column_index, column_index, 18, money_format)
        if len(ore_export):
            ore_sheet.add_table(
                0,
                0,
                len(ore_export),
                len(ore_export.columns) - 1,
                {
                    "name": "OreLedgerTable",
                    "style": "Table Style Medium 2",
                    "columns": [
                        {"header": column} for column in ore_export.columns
                    ],
                },
            )
        elif len(ore_export.columns):
            ore_sheet.autofilter(0, 0, 0, len(ore_export.columns) - 1)

    return output.getvalue()


def records_page() -> None:
    page_banner(
        "records_banner.jpg",
        "Records & Export",
        "Search, review, and export your complete contract and resource transaction history.",
        "Records Archive",
    )

    contracts, ores = load_data()

    st.markdown(
        """
        <div class="section-heading">
            <div>
                <div class="section-title">Export all data</div>
                <div class="section-copy">Download one formatted workbook with a summary, contracts, and ore ledger. The same file opens in Excel and imports directly into Google Sheets.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    export_col1, export_col2 = st.columns([1.2, 1])
    with export_col1:
        workbook_bytes = build_excel_export(contracts, ores)
        st.download_button(
            "Download Excel / Google Sheets Workbook",
            data=workbook_bytes,
            file_name=(
                "star_citizen_tracker_export_"
                f"{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            width="stretch",
        )
    with export_col2:
        st.link_button(
            "Open Google Sheets",
            "https://sheets.new",
            width="stretch",
        )
    st.caption(
        "For Google Sheets, download the workbook, open Google Sheets, "
        "then choose File > Import > Upload."
    )

    contract_tab, ore_tab = st.tabs(["Contracts", "Ore Ledger"])

    with contract_tab:
        display_contract_table(contracts)
        if not contracts.empty:
            export = contracts.copy()
            export["date_saved"] = export["date_saved"].astype(str)
            st.download_button(
                "Download Contracts CSV",
                data=export.to_csv(index=False).encode("utf-8"),
                file_name="star_citizen_contracts.csv",
                mime="text/csv",
            )

    with ore_tab:
        display_ore_table(ores)
        if not ores.empty:
            export = ores.copy()
            export["date_saved"] = export["date_saved"].astype(str)
            st.download_button(
                "Download Ore Ledger CSV",
                data=export.to_csv(index=False).encode("utf-8"),
                file_name="star_citizen_ore_ledger.csv",
                mime="text/csv",
            )


def saved_records_page() -> None:
    page_banner(
        "records_banner.jpg",
        "Saved Records",
        "Search, review, edit, and delete your complete contract and ore transaction history from one command page.",
        "Records Archive",
    )
    contracts, ores = load_data()

    view_tab, manage_tab = st.tabs(["View Records", "Manage Records"])

    with view_tab:
        contract_tab, ore_tab = st.tabs(["Contracts", "Ore Ledger"])
        with contract_tab:
            display_contract_table(contracts)
        with ore_tab:
            display_ore_table(ores)

    with manage_tab:
        st.markdown("### Edit or Delete Records")
        st.caption("Select a saved contract or ore entry, update the values you need, or permanently remove duplicate and outdated entries.")
        manage_records_section(contracts, ores)


def manage_records_section(contracts: pd.DataFrame, ores: pd.DataFrame) -> None:
    record_type = st.radio(
        "Record type",
        ["Contract", "Ore Entry"],
        horizontal=True,
        key="manage_record_type",
    )

    if record_type == "Contract":
        if contracts.empty:
            st.info("No contracts are available to edit.")
            return

        contract_options = {
            int(row["id"]): (
                f'ID {int(row["id"])} | {row["contract_name"]} | '
                f'{format_money(row["net_payout"])}'
            )
            for _, row in contracts.iterrows()
        }
        selected_id = st.selectbox(
            "Select contract",
            options=list(contract_options),
            format_func=lambda value: contract_options[value],
            key="manage_contract_select",
        )
        record = contracts.loc[contracts["id"] == selected_id].iloc[0]

        with st.form("edit_contract_form"):
            name = st.text_input("Contract name", value=record["contract_name"])
            type_value = st.text_input(
                "Contract type",
                value=record["contract_type"],
            )
            offer = st.text_input(
                "Offer group",
                value=record.get("offer_group", "") or "",
            )
            system = st.text_input(
                "System / area",
                value=record.get("system_name", "") or "",
            )

            edit_col1, edit_col2, edit_col3 = st.columns(3)
            with edit_col1:
                payout = st.number_input(
                    "Total payout",
                    min_value=0.0,
                    value=float(record["total_payout"]),
                )
            with edit_col2:
                expenses = st.number_input(
                    "Expenses",
                    min_value=0.0,
                    value=float(record["expenses"]),
                )
            with edit_col3:
                crew = st.number_input(
                    "Crew members",
                    min_value=1,
                    max_value=100,
                    value=int(record["crew_members"]),
                )

            notes = st.text_area(
                "Notes",
                value=record.get("notes", "") or "",
            )
            update_submitted = st.form_submit_button(
                "Update Contract",
                width="stretch",
            )

        if update_submitted:
            if not name.strip() or not type_value.strip() or payout <= 0:
                st.error(
                    "Contract name, contract type, and a positive payout are required."
                )
            else:
                net = payout - expenses
                payload = {
                    "contract_name": name.strip(),
                    "contract_type": type_value.strip(),
                    "offer_group": offer.strip(),
                    "system_name": system.strip(),
                    "total_payout": payout,
                    "expenses": expenses,
                    "crew_members": int(crew),
                    "net_payout": net,
                    "individual_share": net / int(crew),
                    "notes": notes.strip(),
                }
                try:
                    update_record("contracts", selected_id, payload)
                    st.success("Contract updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"The contract could not be updated: {exc}")

        confirm = st.checkbox(
            "I understand this permanently deletes the selected contract.",
            key="delete_contract_confirm",
        )
        if st.button(
            "Delete Contract",
            type="primary",
            disabled=not confirm,
            width="stretch",
            key="delete_contract_button",
        ):
            try:
                delete_record("contracts", selected_id)
                st.success("Contract deleted.")
                st.rerun()
            except Exception as exc:
                st.error(f"The contract could not be deleted: {exc}")

    else:
        if ores.empty:
            st.info("No ore entries are available to edit.")
            return

        ore_options = {
            int(row["id"]): (
                f'ID {int(row["id"])} | {row["action"]} | '
                f'{row["ore_name"]} | {format_money(row["total_value"])}'
            )
            for _, row in ores.iterrows()
        }
        selected_id = st.selectbox(
            "Select ore entry",
            options=list(ore_options),
            format_func=lambda value: ore_options[value],
            key="manage_ore_select",
        )
        record = ores.loc[ores["id"] == selected_id].iloc[0]

        with st.form("edit_ore_form"):
            action = st.selectbox(
                "Entry type",
                ["Mined", "Bought", "Sold"],
                index=["Mined", "Bought", "Sold"].index(record["action"]),
            )
            ore_name = st.text_input("Ore or mineral", value=record["ore_name"])
            value = st.number_input(
                "Total value",
                min_value=0.0,
                value=float(record["total_value"]),
            )
            location = st.text_input(
                "Location",
                value=record.get("location", "") or "",
            )
            notes = st.text_area(
                "Notes",
                value=record.get("notes", "") or "",
            )
            update_submitted = st.form_submit_button(
                "Update Ore Entry",
                width="stretch",
            )

        if update_submitted:
            if not ore_name.strip() or value <= 0:
                st.error("Ore name and a positive value are required.")
            else:
                payload = {
                    "action": action,
                    "ore_name": ore_name.strip(),
                    "total_value": value,
                    "location": location.strip(),
                    "notes": notes.strip(),
                }
                try:
                    update_record("ore_transactions", selected_id, payload)
                    st.success("Ore entry updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"The ore entry could not be updated: {exc}")

        confirm = st.checkbox(
            "I understand this permanently deletes the selected ore entry.",
            key="delete_ore_confirm",
        )
        if st.button(
            "Delete Ore Entry",
            type="primary",
            disabled=not confirm,
            width="stretch",
            key="delete_ore_button",
        ):
            try:
                delete_record("ore_transactions", selected_id)
                st.success("Ore entry deleted.")
                st.rerun()
            except Exception as exc:
                st.error(f"The ore entry could not be deleted: {exc}")


def load_mining_locations() -> pd.DataFrame:
    """Load the packaged ore and gem location reference."""
    if not MINING_LOCATIONS_FILE.exists():
        return pd.DataFrame(
            columns=[
                "Resource",
                "Category",
                "System",
                "Location",
                "Site Type",
                "Spawn Rate",
                "Mining Method",
                "Notes",
            ]
        )
    return pd.read_csv(MINING_LOCATIONS_FILE)


def mining_locations_page() -> None:
    page_banner(
        "ore_banner.jpg",
        "Ore and Gem Locations",
        "Search reported mining locations, compare spawn rates, and filter resources by category and star system.",
        "Mining Intelligence",
    )

    locations = load_mining_locations()

    st.caption(
        "Spawn information is a community-maintained reference and can change after Star Citizen patches. "
        "Use it as a planning guide and verify unusually rare resources in the current live build."
    )

    search_text = st.text_input(
        "Search locations and resources",
        placeholder="Search for Gold, Aberdeen, Pyro, cave, asteroid, ROC...",
        key="mining_location_search",
    )

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        category_choices = sorted(locations["Category"].dropna().unique().tolist())
        selected_categories = st.multiselect(
            "Resource category",
            category_choices,
            default=category_choices,
            key="mining_category_filter",
        )

    with filter_col2:
        system_choices = sorted(locations["System"].dropna().unique().tolist())
        selected_systems = st.multiselect(
            "System",
            system_choices,
            default=system_choices,
            key="mining_system_filter",
        )

    with filter_col3:
        resource_choices = sorted(locations["Resource"].dropna().unique().tolist())
        selected_resources = st.multiselect(
            "Specific resources",
            resource_choices,
            key="mining_resource_filter",
            placeholder="All resources",
        )

    filtered = locations.copy()

    if selected_categories:
        filtered = filtered[filtered["Category"].isin(selected_categories)]
    else:
        filtered = filtered.iloc[0:0]

    if selected_systems:
        filtered = filtered[filtered["System"].isin(selected_systems)]
    else:
        filtered = filtered.iloc[0:0]

    if selected_resources:
        filtered = filtered[filtered["Resource"].isin(selected_resources)]

    if search_text.strip():
        query = search_text.strip()
        search_mask = filtered.astype(str).apply(
            lambda column: column.str.contains(
                query,
                case=False,
                na=False,
                regex=False,
            )
        ).any(axis=1)
        filtered = filtered[search_mask]

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Matching Locations", f"{len(filtered):,}")
    metric_col2.metric(
        "Resources",
        f"{filtered['Resource'].nunique():,}" if not filtered.empty else "0",
    )
    metric_col3.metric(
        "Systems",
        f"{filtered['System'].nunique():,}" if not filtered.empty else "0",
    )
    metric_col4.metric(
        "Gem Entries",
        f"{(filtered['Category'] == 'Gem').sum():,}" if not filtered.empty else "0",
    )

    st.markdown("### Location Reference")

    if filtered.empty:
        st.info("No locations match the current search and filters.")
    else:
        display_columns = [
            "Resource",
            "Category",
            "System",
            "Location",
            "Site Type",
            "Spawn Rate",
            "Mining Method",
            "Notes",
        ]
        st.dataframe(
            filtered[display_columns].sort_values(
                ["Category", "Resource", "System", "Location"]
            ),
            width="stretch",
            hide_index=True,
            column_config={
                "Resource": st.column_config.TextColumn("Resource", width="medium"),
                "Category": st.column_config.TextColumn("Type", width="small"),
                "System": st.column_config.TextColumn("System", width="small"),
                "Location": st.column_config.TextColumn("Location", width="large"),
                "Site Type": st.column_config.TextColumn("Spawn Area", width="medium"),
                "Spawn Rate": st.column_config.TextColumn("Spawn Rate", width="medium"),
                "Mining Method": st.column_config.TextColumn("Method", width="small"),
                "Notes": st.column_config.TextColumn("Notes", width="large"),
            },
        )

    st.download_button(
        "Download Filtered Mining Locations CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="star_citizen_mining_locations.csv",
        mime="text/csv",
        width="stretch",
    )

    with st.expander("How to use spawn-rate information"):
        st.markdown(
            """
            Numeric percentages are reported rates for the listed body or deposit type.
            Labels such as **Common**, **Uncommon**, **Rare**, and **Extremely rare**
            are used where a stable numeric rate was not available. Spawn distributions
            can change between live patches, so the page is designed to be updated by
            replacing `data/mining_locations.csv`.
            """
        )


def export_page() -> None:
    page_banner(
        "export_banner.jpg",
        "Export Data",
        "Download a polished workbook for Microsoft Excel or import it directly into Google Sheets.",
        "Data Portability",
    )
    contracts, ores = load_data()
    workbook_bytes = build_excel_export(contracts, ores)
    st.markdown("### Complete workbook")
    st.caption("Includes Summary, Contracts, and Ore Ledger worksheets.")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download Excel / Google Sheets Workbook",
            data=workbook_bytes,
            file_name=f"star_citizen_tracker_export_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with col2:
        st.link_button("Open Google Sheets", "https://sheets.new", width="stretch")
    st.info("In Google Sheets, choose File > Import > Upload, then select the downloaded workbook.")
    st.markdown("### Individual CSV files")
    csv1, csv2 = st.columns(2)
    with csv1:
        contract_export = contracts.copy()
        if "date_saved" in contract_export.columns:
            contract_export["date_saved"] = contract_export["date_saved"].astype(str)
        st.download_button("Download Contracts CSV", contract_export.to_csv(index=False).encode("utf-8"), "star_citizen_contracts.csv", "text/csv", width="stretch")
    with csv2:
        ore_export = ores.copy()
        if "date_saved" in ore_export.columns:
            ore_export["date_saved"] = ore_export["date_saved"].astype(str)
        st.download_button("Download Ore Ledger CSV", ore_export.to_csv(index=False).encode("utf-8"), "star_citizen_ore_ledger.csv", "text/csv", width="stretch")


def edit_records_page() -> None:
    """Backward-compatible wrapper kept in case a direct link still targets this page."""
    saved_records_page()


def main() -> None:
    apply_custom_theme()
    cookies = get_cookie_manager()
    client = get_supabase()
    restore_login_from_cookie(client, cookies)

    if "user_id" not in st.session_state:
        login_screen(client, cookies)
        return

    with st.sidebar:
        logo_path = ASSETS_DIR / "star_citizen_logo_black.png"
        if logo_path.exists():
            st.image(str(logo_path), width="stretch")
        st.markdown("### Star Citizen Tracker")
        st.caption("Private operations console")
        st.markdown(
            f"**{html.escape(st.session_state.get('user_display_name', 'Citizen'))}**"
        )
        st.caption(st.session_state.get("user_email", "Signed in"))

        navigation_pages = [
            "Dashboard",
            "Contract Calculator",
            "Ore Ledger",
            "Mining Locations",
            "Saved Records",
            "Export Data",
        ]
        if "nav_page" not in st.session_state:
            st.session_state.nav_page = "Dashboard"

        for navigation_page in navigation_pages:
            is_active = st.session_state.nav_page == navigation_page
            if st.button(
                navigation_page,
                key=f"nav_{navigation_page.lower().replace(' ', '_')}",
                type="primary" if is_active else "secondary",
                width="stretch",
            ):
                st.session_state.nav_page = navigation_page
                st.rerun()

        with st.expander("⚙ Settings", expanded=False):
            st.markdown("#### Profile")
            profile_settings(client)
            st.divider()
            st.markdown("#### Timezone")
            timezone_settings()

        st.divider()
        st.caption("System status: All systems operational")
        if st.button("Sign out", width="stretch"):
            try:
                client.auth.sign_out()
            finally:
                remove_cookie_value(cookies, COOKIE_REFRESH_TOKEN)
                clear_login_state()
                st.rerun()

    page = st.session_state.nav_page
    if page == "Dashboard":
        dashboard_page()
    elif page == "Contract Calculator":
        contract_page()
    elif page == "Ore Ledger":
        ore_page()
    elif page == "Mining Locations":
        mining_locations_page()
    elif page == "Saved Records":
        saved_records_page()
    elif page == "Export Data":
        export_page()


if __name__ == "__main__":
    main()
