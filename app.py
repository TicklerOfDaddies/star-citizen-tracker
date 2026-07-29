from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
import base64

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import Client, create_client


st.set_page_config(
    page_title="Star Citizen Tracker",
    page_icon="🚀",
    layout="wide",
)

APP_TIMEZONE = "America/Chicago"

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

STAR_CITIZEN_COLORS = [
    "#00C8FF",
    "#FF8A2A",
    "#7CE7FF",
    "#EB4C5D",
    "#8DA4B8",
]


def apply_custom_theme() -> None:
    """Apply a polished dark operations-console theme."""
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #050608;
            --surface: #0b0e13;
            --surface-2: #11151c;
            --surface-3: #171c24;
            --border: rgba(148, 163, 184, 0.16);
            --border-strong: rgba(42, 224, 199, 0.34);
            --accent: #2ae0c7;
            --accent-2: #22c5e5;
            --accent-soft: rgba(42, 224, 199, 0.12);
            --text: #f7fafc;
            --muted: #8e9aaa;
            --subtle: #667181;
            --warning: #ff9b45;
        }

        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 78% -18%, rgba(34, 197, 229, 0.08), transparent 34rem),
                radial-gradient(circle at 10% 110%, rgba(42, 224, 199, 0.06), transparent 30rem),
                var(--app-bg);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: rgba(5, 6, 8, 0.78);
            border-bottom: 1px solid rgba(148, 163, 184, 0.08);
            backdrop-filter: blur(16px);
        }

        [data-testid="stAppViewContainer"] > .main {
            background: transparent;
        }

        .block-container {
            max-width: 1540px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #080a0e 0%, #06070a 100%);
            border-right: 1px solid var(--border);
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 1rem;
        }

        section[data-testid="stSidebar"] [data-testid="stImage"] img {
            border-radius: 14px;
            border: 1px solid var(--border);
            box-shadow: 0 18px 44px rgba(0, 0, 0, 0.38);
        }

        section[data-testid="stSidebar"] h1 {
            font-size: 1.35rem;
            margin-bottom: 0.1rem;
        }

        h1, h2, h3 {
            color: var(--text) !important;
            letter-spacing: -0.015em;
        }

        p, label, .stCaption {
            color: var(--muted);
        }

        .sc-banner {
            position: relative;
            min-height: 205px;
            display: flex;
            align-items: flex-end;
            overflow: hidden;
            border-radius: 18px;
            border: 1px solid var(--border);
            margin-bottom: 1.25rem;
            background-position: center;
            background-size: cover;
            box-shadow: 0 22px 55px rgba(0, 0, 0, 0.34);
        }

        .sc-banner::after {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(90deg, rgba(2, 4, 7, 0.96) 0%, rgba(5, 8, 12, 0.76) 44%, rgba(5, 8, 12, 0.18) 82%),
                linear-gradient(0deg, rgba(2, 4, 7, 0.93) 0%, transparent 66%);
        }

        .sc-banner-content {
            position: relative;
            z-index: 2;
            max-width: 820px;
            padding: 1.7rem 1.9rem;
        }

        .sc-kicker {
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.72rem;
            font-weight: 800;
            margin-bottom: 0.42rem;
        }

        .sc-banner-title {
            color: #ffffff;
            font-size: clamp(1.85rem, 4vw, 3rem);
            line-height: 1.02;
            font-weight: 790;
            margin: 0 0 0.55rem 0;
            text-shadow: 0 4px 18px rgba(0, 0, 0, 0.48);
        }

        .sc-banner-subtitle {
            color: #b9c4d0;
            font-size: 0.98rem;
            max-width: 720px;
            margin: 0;
        }

        .dashboard-toolbar {
            border: 1px solid var(--border);
            background: rgba(11, 14, 19, 0.92);
            border-radius: 14px;
            padding: 0.95rem 1rem 0.15rem;
            margin-bottom: 1rem;
        }

        .section-heading {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin: 1.25rem 0 0.7rem;
        }

        .section-title {
            color: var(--text);
            font-size: 1.18rem;
            font-weight: 760;
            margin: 0;
        }

        .section-copy {
            color: var(--muted);
            font-size: 0.84rem;
            margin: 0.15rem 0 0;
        }

        .chart-heading {
            color: var(--text);
            font-size: 0.98rem;
            font-weight: 720;
            margin: 0 0 0.12rem 0;
        }

        .chart-copy {
            color: var(--muted);
            font-size: 0.78rem;
            margin: 0 0 0.3rem 0;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(16, 20, 27, 0.98), rgba(10, 13, 18, 0.98));
            border: 1px solid var(--border);
            border-radius: 15px;
            padding: 1rem 1rem 0.9rem;
            min-height: 118px;
            box-shadow: 0 14px 32px rgba(0, 0, 0, 0.22);
            transition: transform 160ms ease, border-color 160ms ease;
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: var(--border-strong);
        }

        [data-testid="stMetricLabel"] {
            color: #8f9baa !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.70rem !important;
            font-weight: 720;
        }

        [data-testid="stMetricValue"] {
            color: #f8fbff !important;
            font-weight: 780;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(145deg, rgba(14, 18, 24, 0.98), rgba(9, 12, 17, 0.98));
            border: 1px solid var(--border) !important;
            border-radius: 16px !important;
            box-shadow: 0 15px 38px rgba(0, 0, 0, 0.20);
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            border: 1px solid rgba(42, 224, 199, 0.54);
            border-radius: 10px;
            background: linear-gradient(90deg, #128d88, #16a6b8);
            color: #ffffff !important;
            font-weight: 760;
            min-height: 2.7rem;
            box-shadow: 0 8px 20px rgba(34, 197, 229, 0.12);
        }

        .stButton > button p,
        .stButton > button span,
        .stDownloadButton > button p,
        .stDownloadButton > button span,
        [data-testid="stFormSubmitButton"] > button p,
        [data-testid="stFormSubmitButton"] > button span {
            color: inherit !important;
            font-weight: inherit !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            border-color: #9ff9ec;
            background: linear-gradient(90deg, #20bcae, #22c5e5);
            color: #02100f !important;
        }

        section[data-testid="stSidebar"] .stButton > button {
            width: 100%;
            min-height: 2.85rem;
            justify-content: flex-start;
            padding: 0.65rem 0.85rem;
            margin: 0.12rem 0;
            border-radius: 9px;
            font-size: 0.92rem;
            letter-spacing: 0.005em;
            text-align: left;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            background: transparent;
            border: 1px solid transparent;
            color: #cbd5df !important;
            box-shadow: none;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
            background: rgba(42, 224, 199, 0.08);
            border-color: rgba(42, 224, 199, 0.20);
            color: #ffffff !important;
            transform: translateX(2px);
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, rgba(42, 224, 199, 0.20), rgba(34, 197, 229, 0.12));
            border: 1px solid rgba(42, 224, 199, 0.46);
            color: #dffff9 !important;
            box-shadow: inset 3px 0 0 var(--accent);
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: linear-gradient(90deg, rgba(42, 224, 199, 0.28), rgba(34, 197, 229, 0.18));
            color: #ffffff !important;
        }

        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {
            background: #0d1117 !important;
            border-color: rgba(148, 163, 184, 0.20) !important;
            color: #f5f8fb !important;
            border-radius: 9px !important;
        }

        div[data-baseweb="select"] > div:focus-within,
        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stTextArea textarea:focus {
            border-color: rgba(42, 224, 199, 0.68) !important;
            box-shadow: 0 0 0 1px rgba(42, 224, 199, 0.22) !important;
        }

        div[data-baseweb="select"] svg {
            fill: var(--accent);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 13px;
            overflow: hidden;
        }

        div[data-testid="stAlert"] {
            border: 1px solid var(--border);
            border-radius: 12px;
            background: rgba(14, 18, 24, 0.92);
        }

        [data-testid="stTabs"] button {
            color: var(--muted);
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }

        hr {
            border-color: rgba(148, 163, 184, 0.12);
        }

        @media (max-width: 720px) {
            .sc-banner {
                min-height: 190px;
            }

            .sc-banner-content {
                padding: 1.25rem;
            }

            .sc-banner-subtitle {
                font-size: 0.90rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@lru_cache(maxsize=16)
def image_data_uri(filename: str) -> str:
    """Return a local image as a cached data URI for a CSS background."""
    image_path = ASSETS_DIR / filename
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def page_banner(
    image_filename: str,
    title: str,
    subtitle: str,
    kicker: str,
) -> None:
    background = image_data_uri(image_filename)
    st.markdown(
        f"""
        <section
            class="sc-banner"
            style="background-image: url('{background}');"
            aria-label="{title}"
        >
            <div class="sc-banner-content">
                <div class="sc-kicker">{kicker}</div>
                <div class="sc-banner-title">{title}</div>
                <p class="sc-banner-subtitle">{subtitle}</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def style_plotly_figure(figure, *, height: int = 330) -> None:
    """Give Plotly charts the same dark dashboard appearance as the app."""
    figure.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,7,10,0.34)",
        font={"color": "#d9e1e8", "family": "Inter, sans-serif"},
        colorway=STAR_CITIZEN_COLORS,
        margin={"l": 18, "r": 18, "t": 18, "b": 18},
        legend_title_text="",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        hoverlabel={
            "bgcolor": "#10151c",
            "bordercolor": "#2ae0c7",
            "font_color": "#f7fafc",
        },
    )
    figure.update_xaxes(
        gridcolor="rgba(148,163,184,0.09)",
        zerolinecolor="rgba(148,163,184,0.14)",
        linecolor="rgba(148,163,184,0.12)",
        tickfont={"color": "#8e9aaa"},
        title_font={"color": "#8e9aaa"},
    )
    figure.update_yaxes(
        gridcolor="rgba(148,163,184,0.09)",
        zerolinecolor="rgba(148,163,184,0.14)",
        linecolor="rgba(148,163,184,0.12)",
        tickfont={"color": "#8e9aaa"},
        title_font={"color": "#8e9aaa"},
    )


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
            line={"color": "rgba(148,163,184,0.16)", "width": 18},
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
        text=f"<b>No data yet</b><br><span style='color:#8e9aaa'>{message}</span>",
        showarrow=False,
        align="center",
        font={"size": 14, "color": "#d9e1e8"},
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
            use_container_width=True,
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


def clear_login_state() -> None:
    for key in ("user_id", "user_email", "supabase_client"):
        st.session_state.pop(key, None)


def login_screen(client: Client) -> None:
    page_banner(
        "hero_banner.jpg",
        "Star Citizen Tracker",
        "A private operations ledger for contracts, mining, trading, and performance analysis across the verse.",
        "Operations Console",
    )

    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            try:
                response = client.auth.sign_in_with_password(
                    {"email": email.strip(), "password": password}
                )
                if response.user is None:
                    st.error("The sign-in response did not include a user.")
                else:
                    st.session_state.user_id = str(response.user.id)
                    st.session_state.user_email = response.user.email or email.strip()
                    st.rerun()
            except Exception as exc:
                st.error(f"Sign in failed: {exc}")

    with signup_tab:
        st.info(
            "Create one private account and use the same login on your "
            "computer, phone, and tablet."
        )
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
                help="Use at least 8 characters.",
            )
            submitted = st.form_submit_button(
                "Create account",
                use_container_width=True,
            )

        if submitted:
            try:
                response = client.auth.sign_up(
                    {"email": new_email.strip(), "password": new_password}
                )
                if response.user is None:
                    st.error("The account could not be created.")
                elif response.session is None:
                    st.success(
                        "Account created. Check your email if Supabase email "
                        "confirmation is enabled, then sign in."
                    )
                else:
                    st.session_state.user_id = str(response.user.id)
                    st.session_state.user_email = (
                        response.user.email or new_email.strip()
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
        use_container_width=True,
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
        use_container_width=True,
        hide_index=True,
        column_config={
            "Value": st.column_config.NumberColumn(format="%,.0f aUEC"),
        },
    )


def dashboard_page() -> None:
    page_banner(
        "dashboard_banner.jpg",
        "Operations Dashboard",
        "See contract income, mining activity, trade value, and recent records immediately from one command view.",
        "Live Command Overview",
    )

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

    metric_columns = st.columns(5)
    metric_columns[0].metric("Contracts", f"{len(contracts):,}")
    metric_columns[1].metric("Net payout", format_money(contract_net))
    metric_columns[2].metric("Personal shares", format_money(personal_share))
    metric_columns[3].metric("Mined value", format_money(mined_value))
    metric_columns[4].metric("Ore trade net", format_money(ore_sales - ore_purchases))

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
        contract_time_figure = px.area(
            contract_time_data,
            x="Day",
            y="net_payout",
            markers=True,
            hover_data=["contract_count"],
            labels={
                "net_payout": "Net payout in aUEC",
                "contract_count": "Contracts",
            },
        )
        contract_time_figure.update_traces(
            line={"width": 2.5},
            fillcolor="rgba(42,224,199,0.12)",
        )
        contract_time_figure.update_yaxes(rangemode="tozero")
        style_plotly_figure(contract_time_figure)

        contract_type_data = (
            contracts.groupby("contract_type", as_index=False)
            .agg(
                net_payout=("net_payout", "sum"),
                contract_count=("id", "count"),
            )
            .sort_values("net_payout", ascending=True)
            .tail(8)
        )
        contract_type_figure = px.bar(
            contract_type_data,
            x="net_payout",
            y="contract_type",
            orientation="h",
            hover_data=["contract_count"],
            labels={
                "net_payout": "Net payout in aUEC",
                "contract_type": "Contract type",
                "contract_count": "Contracts",
            },
        )
        contract_type_figure.update_traces(marker_color="#22c5e5")
        style_plotly_figure(contract_type_figure)

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
        ore_value_figure = px.bar(
            ore_value_data,
            x="ore_name",
            y="total_value",
            color="action",
            barmode="group",
            hover_data=["entry_count"],
            labels={
                "ore_name": "Ore or mineral",
                "total_value": "Value in aUEC",
                "action": "Entry type",
                "entry_count": "Entries",
            },
        )
        ore_value_figure.update_yaxes(rangemode="tozero")
        style_plotly_figure(ore_value_figure)

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
            textinfo="percent+label",
            marker={"line": {"color": "#0b0e13", "width": 3}},
        )
        style_plotly_figure(ore_mix_figure)

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
            use_container_width=True,
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
            use_container_width=True,
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


def records_page() -> None:
    page_banner(
        "records_banner.jpg",
        "Saved Records",
        "Search, review, and export your complete contract and resource transaction history.",
        "Records Archive",
    )

    contracts, ores = load_data()
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


def edit_records_page() -> None:
    page_banner(
        "edit_banner.jpg",
        "Edit or Delete Records",
        "Correct mistakes, revise saved values, or permanently remove duplicate entries.",
        "Data Maintenance",
    )

    contracts, ores = load_data()
    record_type = st.radio(
        "Record type",
        ["Contract", "Ore Entry"],
        horizontal=True,
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
                use_container_width=True,
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
            "I understand this permanently deletes the selected contract."
        )
        if st.button(
            "Delete Contract",
            type="primary",
            disabled=not confirm,
            use_container_width=True,
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
                use_container_width=True,
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
            "I understand this permanently deletes the selected ore entry."
        )
        if st.button(
            "Delete Ore Entry",
            type="primary",
            disabled=not confirm,
            use_container_width=True,
        ):
            try:
                delete_record("ore_transactions", selected_id)
                st.success("Ore entry deleted.")
                st.rerun()
            except Exception as exc:
                st.error(f"The ore entry could not be deleted: {exc}")


def main() -> None:
    apply_custom_theme()
    client = get_supabase()

    if "user_id" not in st.session_state:
        login_screen(client)
        return

    with st.sidebar:
        sidebar_art = ASSETS_DIR / "sidebar_art.jpg"
        if sidebar_art.exists():
            st.image(str(sidebar_art), use_container_width=True)
        st.title("Star Citizen Tracker")
        st.caption("Private operations console")
        st.caption(st.session_state.get("user_email", "Signed in"))

        st.markdown("#### Navigation")
        navigation_pages = [
            "Dashboard",
            "Contract Calculator",
            "Ore Ledger",
            "Saved Records",
            "Edit or Delete",
        ]

        if "nav_page" not in st.session_state:
            st.session_state.nav_page = "Dashboard"

        for navigation_page in navigation_pages:
            is_active = st.session_state.nav_page == navigation_page
            if st.button(
                navigation_page,
                key=f"nav_{navigation_page.lower().replace(' ', '_')}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.nav_page = navigation_page
                st.rerun()

        page = st.session_state.nav_page

        st.divider()
        if st.button("Sign out", use_container_width=True):
            try:
                client.auth.sign_out()
            finally:
                clear_login_state()
                st.rerun()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Contract Calculator":
        contract_page()
    elif page == "Ore Ledger":
        ore_page()
    elif page == "Saved Records":
        records_page()
    elif page == "Edit or Delete":
        edit_records_page()


if __name__ == "__main__":
    main()
