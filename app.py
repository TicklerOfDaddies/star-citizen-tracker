from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
import base64

import pandas as pd
import plotly.express as px
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
    """Apply the Star Citizen-inspired visual theme."""
    st.markdown(
        """
        <style>
        :root {
            --sc-bg: #06111b;
            --sc-panel: #0c1b28;
            --sc-panel-2: #102536;
            --sc-border: rgba(88, 197, 235, 0.28);
            --sc-cyan: #00c8ff;
            --sc-cyan-soft: #7ce7ff;
            --sc-orange: #ff8a2a;
            --sc-text: #eaf8ff;
            --sc-muted: #93afbf;
        }

        .stApp {
            background:
                radial-gradient(circle at 85% 0%, rgba(0, 200, 255, 0.10), transparent 28rem),
                radial-gradient(circle at 0% 100%, rgba(255, 138, 42, 0.07), transparent 30rem),
                linear-gradient(180deg, #06111b 0%, #081521 48%, #06111b 100%);
            color: var(--sc-text);
        }

        [data-testid="stHeader"] {
            background: rgba(6, 17, 27, 0.78);
            backdrop-filter: blur(14px);
        }

        [data-testid="stAppViewContainer"] > .main {
            background: transparent;
        }

        .block-container {
            max-width: 1480px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(8, 25, 38, 0.98), rgba(5, 15, 24, 0.98));
            border-right: 1px solid var(--sc-border);
        }

        section[data-testid="stSidebar"] [data-testid="stImage"] img {
            border-radius: 16px;
            border: 1px solid var(--sc-border);
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.36);
        }

        h1, h2, h3 {
            color: var(--sc-text) !important;
            letter-spacing: 0.02em;
        }

        p, label, .stCaption {
            color: var(--sc-muted);
        }

        .sc-banner {
            position: relative;
            min-height: 255px;
            display: flex;
            align-items: flex-end;
            overflow: hidden;
            border-radius: 20px;
            border: 1px solid var(--sc-border);
            margin-bottom: 1.6rem;
            background-position: center;
            background-size: cover;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.38);
        }

        .sc-banner::after {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(90deg, rgba(2, 10, 17, 0.95) 0%, rgba(4, 15, 24, 0.74) 42%, rgba(4, 15, 24, 0.12) 78%),
                linear-gradient(0deg, rgba(2, 10, 17, 0.94) 0%, transparent 60%);
        }

        .sc-banner-content {
            position: relative;
            z-index: 2;
            max-width: 760px;
            padding: 2rem 2.2rem;
        }

        .sc-kicker {
            color: var(--sc-cyan-soft);
            text-transform: uppercase;
            letter-spacing: 0.17em;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }

        .sc-banner-title {
            color: #ffffff;
            font-size: clamp(2rem, 4vw, 3.35rem);
            line-height: 1.02;
            font-weight: 760;
            margin: 0 0 0.65rem 0;
            text-shadow: 0 4px 16px rgba(0, 0, 0, 0.48);
        }

        .sc-banner-subtitle {
            color: #c7dce8;
            font-size: 1.02rem;
            max-width: 680px;
            margin: 0;
        }

        div[data-testid="stMetric"] {
            background:
                linear-gradient(145deg, rgba(14, 36, 52, 0.96), rgba(8, 24, 37, 0.96));
            border: 1px solid var(--sc-border);
            border-radius: 15px;
            padding: 1rem 1rem 0.9rem;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.22);
        }

        [data-testid="stMetricLabel"] {
            color: #8eb2c4 !important;
        }

        [data-testid="stMetricValue"] {
            color: #f2fbff !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            border: 1px solid rgba(124, 231, 255, 0.50);
            border-radius: 10px;
            background: linear-gradient(90deg, #007da8, #00a8dc);
            color: #ffffff;
            font-weight: 700;
            box-shadow: 0 8px 18px rgba(0, 168, 220, 0.16);
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            border-color: #9af0ff;
            background: linear-gradient(90deg, #0098c8, #00c8ff);
            color: #021019;
        }

        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {
            background: rgba(13, 32, 47, 0.94) !important;
            border-color: rgba(103, 192, 224, 0.30) !important;
            color: #eefbff !important;
        }

        div[data-baseweb="select"] svg {
            fill: var(--sc-cyan-soft);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--sc-border);
            border-radius: 14px;
            overflow: hidden;
        }

        div[data-testid="stAlert"] {
            border: 1px solid rgba(103, 192, 224, 0.25);
            border-radius: 12px;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--sc-cyan-soft);
            border-bottom-color: var(--sc-cyan);
        }

        hr {
            border-color: rgba(103, 192, 224, 0.18);
        }

        @media (max-width: 720px) {
            .sc-banner {
                min-height: 205px;
            }

            .sc-banner-content {
                padding: 1.35rem;
            }

            .sc-banner-subtitle {
                font-size: 0.92rem;
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


def style_plotly_figure(figure) -> None:
    """Give Plotly charts the same dark sci-fi appearance as the app."""
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,20,31,0.72)",
        font={"color": "#dff6ff"},
        colorway=STAR_CITIZEN_COLORS,
        margin={"l": 20, "r": 20, "t": 35, "b": 20},
        legend_title_text="",
        hoverlabel={
            "bgcolor": "#0b1c29",
            "bordercolor": "#00c8ff",
            "font_color": "#f2fbff",
        },
    )
    figure.update_xaxes(
        gridcolor="rgba(124,231,255,0.10)",
        zerolinecolor="rgba(124,231,255,0.18)",
    )
    figure.update_yaxes(
        gridcolor="rgba(124,231,255,0.10)",
        zerolinecolor="rgba(124,231,255,0.18)",
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
        "Interactive Dashboard",
        "Review contract income, ore activity, trends, and mission performance from one command view.",
        "Command Analytics",
    )

    contracts, ores = load_data()

    filter_col1, filter_col2 = st.columns([1, 2])
    with filter_col1:
        date_range = st.selectbox(
            "Date range",
            ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
        )
    with filter_col2:
        search_text = st.text_input(
            "Search",
            placeholder="Contract, ore, type, location, or notes",
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
        float(
            ores.loc[ores["action"] == "Mined", "total_value"].sum()
        )
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
    metric_columns[1].metric("Net contract payout", format_money(contract_net))
    metric_columns[2].metric("Personal shares", format_money(personal_share))
    metric_columns[3].metric("Mined value", format_money(mined_value))
    metric_columns[4].metric(
        "Ore trade net",
        format_money(ore_sales - ore_purchases),
    )

    view = st.selectbox(
        "Dashboard view",
        [
            "Overview",
            "Contracts Table",
            "Ore Ledger Table",
            "Contract Earnings by Type",
            "Contract Earnings Over Time",
            "Ore Value by Mineral",
            "Ore Activity Over Time",
            "Ore Activity Mix",
        ],
    )

    if view == "Overview":
        st.subheader("Contracts")
        display_contract_table(contracts)
        st.subheader("Ore Ledger")
        display_ore_table(ores)

    elif view == "Contracts Table":
        display_contract_table(contracts)

    elif view == "Ore Ledger Table":
        display_ore_table(ores)

    elif view == "Contract Earnings by Type":
        if contracts.empty:
            st.info("No contract records match the current filters.")
        else:
            chart_data = (
                contracts.groupby("contract_type", as_index=False)
                .agg(
                    net_payout=("net_payout", "sum"),
                    contract_count=("id", "count"),
                )
                .sort_values("net_payout", ascending=True)
            )
            figure = px.bar(
                chart_data,
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
            style_plotly_figure(figure)
            st.plotly_chart(figure, use_container_width=True)

    elif view == "Contract Earnings Over Time":
        if contracts.empty:
            st.info("No contract records match the current filters.")
        else:
            chart_data = contracts.dropna(subset=["date_saved"]).copy()
            chart_data["Day"] = chart_data["date_saved"].dt.floor("D")
            chart_data = (
                chart_data.groupby("Day", as_index=False)
                .agg(
                    net_payout=("net_payout", "sum"),
                    contract_count=("id", "count"),
                )
                .sort_values("Day")
            )
            figure = px.line(
                chart_data,
                x="Day",
                y="net_payout",
                markers=True,
                hover_data=["contract_count"],
                labels={
                    "net_payout": "Net payout in aUEC",
                    "contract_count": "Contracts",
                },
            )
            figure.update_yaxes(rangemode="tozero")
            style_plotly_figure(figure)
            st.plotly_chart(figure, use_container_width=True)

    elif view == "Ore Value by Mineral":
        if ores.empty:
            st.info("No ore records match the current filters.")
        else:
            chart_data = (
                ores.groupby(["ore_name", "action"], as_index=False)
                .agg(
                    total_value=("total_value", "sum"),
                    entry_count=("id", "count"),
                )
            )
            figure = px.bar(
                chart_data,
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
            figure.update_yaxes(rangemode="tozero")
            style_plotly_figure(figure)
            st.plotly_chart(figure, use_container_width=True)

    elif view == "Ore Activity Over Time":
        if ores.empty:
            st.info("No ore records match the current filters.")
        else:
            chart_data = ores.dropna(subset=["date_saved"]).sort_values(
                "date_saved"
            )
            figure = px.line(
                chart_data,
                x="date_saved",
                y="total_value",
                color="action",
                markers=True,
                hover_data=["ore_name", "location", "notes"],
                labels={
                    "date_saved": "Date and time",
                    "total_value": "Value in aUEC",
                    "action": "Entry type",
                    "ore_name": "Ore",
                },
            )
            figure.update_yaxes(rangemode="tozero")
            style_plotly_figure(figure)
            st.plotly_chart(figure, use_container_width=True)

    elif view == "Ore Activity Mix":
        if ores.empty:
            st.info("No ore records match the current filters.")
        else:
            chart_data = (
                ores.groupby("action", as_index=False)
                .agg(
                    total_value=("total_value", "sum"),
                    entry_count=("id", "count"),
                )
            )
            figure = px.pie(
                chart_data,
                names="action",
                values="total_value",
                hole=0.45,
                hover_data=["entry_count"],
            )
            figure.update_traces(textinfo="percent+label")
            style_plotly_figure(figure)
            st.plotly_chart(figure, use_container_width=True)


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

        page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Contract Calculator",
                "Ore Ledger",
                "Saved Records",
                "Edit or Delete",
            ],
        )

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
