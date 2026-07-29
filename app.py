from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote
import base64
import html
import json
import re
import time
import zipfile

import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client
from streamlit_cookies_manager_ext import EncryptedCookieManager
from PIL import Image, ImageOps


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
DEFAULT_PUBLIC_APP_URL = "https://sccalculator.streamlit.app/"
SC_CRAFT_TOOLS_URL = "https://sc-craft.tools/"
AVATAR_BUCKET = "avatars"
AVATAR_SIZE = (512, 512)
MAX_AVATAR_BYTES = 2 * 1024 * 1024

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
UEX_API_BASE = "https://api.uexcorp.uk/2.0"
UEX_CACHE_SECONDS = 840
SC_TRADE_TOOLS_API_BASE = "https://sc-trade.tools/api"
SC_TRADE_TOOLS_CACHE_SECONDS = 840
SC_TRADE_TOOLS_URL = "https://sc-trade.tools/"

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

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button,
        .stLinkButton > a {
            border: 1px solid #0a6d89;
            border-radius: 10px;
            background: linear-gradient(135deg, #0d7694 0%, #075f79 100%);
            color: #ffffff !important;
            font-size: .92rem !important;
            font-weight: 750 !important;
            line-height: 1.2 !important;
            letter-spacing: .005em;
            min-height: 2.75rem;
            box-shadow: 0 7px 16px rgba(7,95,121,.18);
            transition:
                background .16s ease,
                border-color .16s ease,
                color .16s ease,
                box-shadow .16s ease,
                transform .16s ease;
        }

        .stButton > button *,
        .stDownloadButton > button *,
        [data-testid="stFormSubmitButton"] > button *,
        .stLinkButton > a * {
            color: inherit !important;
            font-size: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover,
        .stLinkButton > a:hover {
            border-color: #043f53;
            background: linear-gradient(135deg, #075a73 0%, #043f53 100%);
            color: #ffffff !important;
            box-shadow: 0 10px 22px rgba(4,63,83,.28);
            transform: translateY(-1px);
        }

        .stButton > button:disabled,
        .stDownloadButton > button:disabled,
        [data-testid="stFormSubmitButton"] > button:disabled {
            background: #cbd7df !important;
            border-color: #c1ccd4 !important;
            color: #6e7e8b !important;
            box-shadow: none !important;
            transform: none !important;
        }

        section[data-testid="stSidebar"] .stButton > button {
            width:100%;
            height:3.35rem;
            min-height:3.35rem;
            justify-content:flex-start;
            padding:.72rem .9rem;
            margin:.14rem 0;
            border-radius:11px;
            font-size:.92rem !important;
            text-align:left;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            background: #edf6f9;
            border: 1px solid #b7d5df;
            color: #1d5366 !important;
            box-shadow: none;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"] * {
            color: #1d5366 !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
            background: #cfe8ef;
            border-color: #68a9bb;
            color: #0b4357 !important;
            box-shadow: 0 7px 16px rgba(30,104,126,.12);
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover * {
            color: #0b4357 !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0d7694 0%, #075f79 100%);
            border: 1px solid #075f79;
            color: #ffffff !important;
            box-shadow:
                inset 4px 0 0 #55d7f1,
                0 8px 18px rgba(7,95,121,.22);
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"] * {
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #095f79 0%, #044c62 100%);
            border-color: #044c62;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover * {
            color: #ffffff !important;
        }

        div[data-baseweb="tab-list"] {
            display: flex;
            flex-wrap: wrap;
            gap: .55rem;
            padding: .55rem;
            margin: .45rem 0 1rem;
            border: 1px solid #c5dce6;
            border-radius: 14px;
            background: #eaf4f7;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.82);
        }

        button[data-baseweb="tab"] {
            flex: 1 1 150px;
            min-height: 3.15rem;
            padding: .68rem .9rem !important;
            border: 1px solid #a9ccd9 !important;
            border-radius: 10px !important;
            background: #ffffff !important;
            color: #18546a !important;
            font-size: .88rem !important;
            font-weight: 790 !important;
            line-height: 1.2 !important;
            box-shadow: 0 4px 10px rgba(27,88,108,.07);
            transition:
                background .15s ease,
                border-color .15s ease,
                color .15s ease,
                transform .15s ease,
                box-shadow .15s ease;
        }

        button[data-baseweb="tab"] * {
            color: inherit !important;
            font-size: inherit !important;
            font-weight: inherit !important;
        }

        button[data-baseweb="tab"]:hover {
            background: #d9edf3 !important;
            border-color: #6aafc1 !important;
            color: #0a4357 !important;
            transform: translateY(-1px);
            box-shadow: 0 7px 16px rgba(27,88,108,.13);
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(
                135deg,
                #0d7694 0%,
                #075f79 100%
            ) !important;
            border-color: #075f79 !important;
            color: #ffffff !important;
            box-shadow:
                inset 4px 0 0 #55d7f1,
                0 8px 18px rgba(7,95,121,.22);
        }

        button[data-baseweb="tab"][aria-selected="true"] * {
            color: #ffffff !important;
        }

        .dashboard-metric-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin: .7rem 0 1rem;
        }

        .dashboard-metric-card {
            min-width: 0;
            min-height: 118px;
            padding: .95rem 1rem;
            border: 1px solid #c7dce6;
            border-radius: 15px;
            background:
                linear-gradient(145deg, #ffffff 0%, #f1f8fb 100%);
            box-shadow: 0 9px 22px rgba(18,74,99,.08);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .dashboard-metric-label {
            color: #526c80;
            font-size: .71rem;
            font-weight: 790;
            line-height: 1.25;
            letter-spacing: .055em;
            text-transform: uppercase;
            margin-bottom: .45rem;
        }

        .dashboard-metric-value {
            color: #0b526b;
            font-size: clamp(1.3rem, 2vw, 2rem);
            font-weight: 850;
            line-height: 1.08;
            overflow-wrap: anywhere;
        }

        .dashboard-metric-value.positive {
            color: #16825a;
        }

        .dashboard-metric-value.negative {
            color: #d43f48;
        }

        .dashboard-metric-detail {
            margin-top: .32rem;
            color: #718295;
            font-size: .72rem;
            line-height: 1.35;
        }

        @media (max-width: 900px) {
            .dashboard-metric-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 600px) {
            .dashboard-metric-grid {
                grid-template-columns: 1fr;
            }
        }

        .sidebar-profile-card {
            margin: .5rem 0 .7rem;
            padding: .85rem;
            border: 1px solid #c9dce6;
            border-radius: 15px;
            background:
                radial-gradient(circle at top left, rgba(13,118,148,.13), transparent 10rem),
                linear-gradient(145deg, #ffffff 0%, #eef7fa 100%);
            box-shadow: 0 9px 22px rgba(18,74,99,.08);
        }

        .sidebar-profile-row {
            display: flex;
            align-items: center;
            gap: .75rem;
            min-width: 0;
        }

        .sidebar-profile-avatar,
        .sidebar-profile-initials {
            width: 52px;
            height: 52px;
            flex: 0 0 52px;
            border-radius: 50%;
            border: 2px solid #8bc6d6;
            box-shadow: 0 6px 16px rgba(10,85,107,.17);
            object-fit: cover;
            background: #0d7694;
        }

        .sidebar-profile-initials {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 1.02rem;
            font-weight: 850;
            letter-spacing: .02em;
        }

        .sidebar-profile-copy {
            min-width: 0;
        }

        .sidebar-profile-name {
            color: #102f43;
            font-size: .95rem;
            font-weight: 820;
            line-height: 1.2;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .sidebar-profile-email {
            color: #60778a;
            font-size: .71rem;
            line-height: 1.35;
            margin-top: .18rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .profile-hero {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            gap: 1.3rem;
            align-items: center;
            margin-bottom: 1rem;
            padding: 1.35rem 1.5rem;
            border: 1px solid #c8dce6;
            border-radius: 20px;
            background:
                radial-gradient(circle at 10% 10%, rgba(13,118,148,.17), transparent 17rem),
                linear-gradient(135deg, #ffffff 0%, #edf7fa 100%);
            box-shadow: 0 16px 36px rgba(18,74,99,.11);
        }

        .profile-avatar-large,
        .profile-avatar-large-initials {
            width: 124px;
            height: 124px;
            border-radius: 50%;
            border: 4px solid #ffffff;
            box-shadow:
                0 0 0 2px #79bdd0,
                0 12px 28px rgba(8,70,91,.18);
            object-fit: cover;
            background: linear-gradient(135deg, #0d7694 0%, #064f66 100%);
        }

        .profile-avatar-large-initials {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 2.2rem;
            font-weight: 880;
            letter-spacing: .03em;
        }

        .profile-hero-kicker {
            color: #0d7694;
            font-size: .72rem;
            font-weight: 820;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: .35rem;
        }

        .profile-hero-name {
            color: #10233f;
            font-size: clamp(1.65rem, 3vw, 2.45rem);
            font-weight: 850;
            line-height: 1.05;
            letter-spacing: -.025em;
        }

        .profile-hero-email {
            color: #607087;
            font-size: .9rem;
            margin-top: .38rem;
        }

        .profile-hero-bio {
            color: #536b7e;
            font-size: .86rem;
            line-height: 1.55;
            margin-top: .65rem;
            max-width: 800px;
        }

        .profile-summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: .6rem 0 1rem;
        }

        .profile-summary-card {
            min-width: 0;
            min-height: 108px;
            padding: .95rem 1rem;
            border: 1px solid #ccdee6;
            border-radius: 15px;
            background: #ffffff;
            box-shadow: 0 8px 20px rgba(18,74,99,.07);
        }

        .profile-summary-label {
            color: #637b8d;
            font-size: .69rem;
            font-weight: 790;
            letter-spacing: .06em;
            text-transform: uppercase;
        }

        .profile-summary-value {
            color: #10374d;
            font-size: 1.1rem;
            font-weight: 830;
            margin-top: .42rem;
            overflow-wrap: anywhere;
        }

        .profile-summary-detail {
            color: #7b8b9b;
            font-size: .7rem;
            line-height: 1.35;
            margin-top: .25rem;
        }

        .profile-section-card {
            padding: 1.05rem 1.1rem;
            border: 1px solid #cfdee7;
            border-radius: 16px;
            background: #ffffff;
            box-shadow: 0 9px 22px rgba(18,74,99,.07);
        }

        .profile-security-note {
            margin: .55rem 0 .8rem;
            padding: .75rem .85rem;
            border-left: 4px solid #0d7694;
            border-radius: 9px;
            background: #edf8fb;
            color: #436477;
            font-size: .78rem;
            line-height: 1.5;
        }

        @media (max-width: 900px) {
            .profile-summary-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 620px) {
            .profile-hero {
                grid-template-columns: 1fr;
                text-align: center;
                justify-items: center;
            }

            .profile-summary-grid {
                grid-template-columns: 1fr;
            }
        }

        .rights-notice {
            margin-top: 1rem;
            padding: .9rem 1rem;
            border: 1px solid #cbdde5;
            border-radius: 12px;
            background: #f5fafc;
            color: #52677a;
            font-size: .76rem;
            line-height: 1.55;
        }

        .rights-notice strong {
            color: #123850;
        }

        .commodity-source-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
            margin: .35rem 0 1rem;
        }

        .commodity-source-card {
            padding: .9rem 1rem;
            border: 1px solid #cbdde5;
            border-radius: 13px;
            background: #ffffff;
            box-shadow: 0 9px 22px rgba(24,62,103,.06);
        }

        .commodity-source-name {
            color: #10233f;
            font-size: .95rem;
            font-weight: 780;
            margin-bottom: .2rem;
        }

        .commodity-source-copy {
            color: #607087;
            font-size: .78rem;
            line-height: 1.5;
        }

        .commodity-source-status {
            display: inline-block;
            margin-top: .55rem;
            padding: .22rem .52rem;
            border-radius: 999px;
            background: #e7f7f1;
            color: #16724d;
            font-size: .7rem;
            font-weight: 780;
        }

        .commodity-metric-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 12px;
            margin: .75rem 0 1rem;
        }

        .commodity-metric-card {
            min-width: 0;
            min-height: 126px;
            padding: 1rem 1.05rem;
            border: 1px solid #c7dce6;
            border-radius: 16px;
            background:
                linear-gradient(145deg, #ffffff 0%, #f1f8fb 100%);
            box-shadow: 0 10px 24px rgba(18,74,99,.09);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .commodity-metric-label {
            color: #49647a;
            font-size: .72rem;
            font-weight: 790;
            line-height: 1.25;
            letter-spacing: .065em;
            text-transform: uppercase;
            margin-bottom: .55rem;
        }

        .commodity-metric-value {
            color: #0b526b;
            font-size: clamp(1.35rem, 2.25vw, 2.2rem);
            font-weight: 850;
            line-height: 1.08;
            letter-spacing: -.025em;
            white-space: normal;
            overflow-wrap: anywhere;
        }

        .commodity-metric-value.positive {
            color: #16825a;
        }

        .commodity-metric-value.negative {
            color: #d43f48;
        }

        .commodity-metric-detail {
            margin-top: .35rem;
            color: #6d8092;
            font-size: .72rem;
            line-height: 1.3;
        }

        @media (max-width: 1180px) {
            .commodity-metric-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }
        }

        @media (max-width: 720px) {
            .commodity-metric-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 820px) {
            .commodity-source-grid {
                grid-template-columns: 1fr;
            }
        }

        div[data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stDateInput"] input,
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stDateInput input,
        input[type="text"],
        input[type="email"],
        input[type="password"] {
            background: #ffffff !important;
            border-color: #b9c9d8 !important;
            color: #10233f !important;
            -webkit-text-fill-color: #10233f !important;
            caret-color: #0d7694 !important;
            border-radius: 9px !important;
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder,
        input[type="text"]::placeholder,
        input[type="email"]::placeholder,
        input[type="password"]::placeholder {
            color: #7b8ba0 !important;
            -webkit-text-fill-color: #7b8ba0 !important;
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] label,
        [data-testid="stNumberInput"] label,
        [data-testid="stTextArea"] label,
        [data-testid="stDateInput"] label {
            color: #344b65 !important;
            font-weight: 650 !important;
        }

        div[data-baseweb="select"] > div:focus-within,
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stDateInput"] input:focus,
        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stTextArea textarea:focus {
            border-color: #0d7694 !important;
            box-shadow: 0 0 0 2px rgba(13,118,148,.16) !important;
            outline: none !important;
        }

        [data-baseweb="input"] {
            background: #ffffff !important;
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

        /* Premium application-wide design system */
        :root {
            --premium-navy: #0d2d49;
            --premium-teal: #087892;
            --premium-teal-dark: #055a70;
            --premium-blue: #176fc1;
            --premium-green: #22a66f;
            --premium-red: #e54950;
            --premium-orange: #f28a2a;
            --premium-purple: #7b55d9;
            --premium-surface: #ffffff;
            --premium-surface-soft: #f4f9fc;
            --premium-border: #bdd2df;
            --premium-border-strong: #8fb4c7;
            --premium-shadow: 0 12px 28px rgba(16, 61, 88, .09);
        }

        .stApp {
            background:
                radial-gradient(circle at 15% 0%, rgba(54,157,190,.08), transparent 26rem),
                linear-gradient(180deg, #f8fbfd 0%, #f1f6fa 100%);
        }

        .block-container {
            max-width: 1780px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3, h4 {
            color: var(--premium-navy) !important;
            letter-spacing: -.015em;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--premium-border) !important;
            border-radius: 17px !important;
            background: linear-gradient(145deg, #ffffff 0%, #f8fbfd 100%) !important;
            box-shadow: var(--premium-shadow);
        }

        [data-testid="stForm"] {
            border: 1.5px solid var(--premium-border) !important;
            border-radius: 16px !important;
            background: #ffffff !important;
            padding: 1rem !important;
            box-shadow: 0 9px 22px rgba(16,61,88,.07);
        }

        [data-testid="stExpander"] {
            border: 1.5px solid var(--premium-border) !important;
            border-radius: 13px !important;
            overflow: hidden;
            background: #ffffff !important;
            box-shadow: 0 6px 16px rgba(16,61,88,.06);
        }

        [data-testid="stExpander"] summary {
            background: #eef7fa;
            color: var(--premium-navy) !important;
            font-weight: 760 !important;
        }

        div[data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stDateInput"] input,
        [data-testid="stFileUploaderDropzone"] {
            min-height: 3rem;
            background: #ffffff !important;
            border: 1.5px solid var(--premium-border-strong) !important;
            border-radius: 11px !important;
            color: #112e46 !important;
            box-shadow: inset 0 1px 2px rgba(8,48,72,.04);
        }

        [data-testid="stTextArea"] textarea {
            min-height: 8.5rem;
        }

        div[data-baseweb="select"] > div:hover,
        [data-testid="stTextInput"] input:hover,
        [data-testid="stNumberInput"] input:hover,
        [data-testid="stTextArea"] textarea:hover,
        [data-testid="stDateInput"] input:hover {
            border-color: #4d9eb8 !important;
        }

        div[data-baseweb="select"] > div:focus-within,
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stDateInput"] input:focus {
            border-color: var(--premium-teal) !important;
            box-shadow: 0 0 0 3px rgba(8,120,146,.16) !important;
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stTextInput"] label,
        [data-testid="stNumberInput"] label,
        [data-testid="stTextArea"] label,
        [data-testid="stDateInput"] label,
        [data-testid="stSelectbox"] label,
        [data-testid="stMultiSelect"] label {
            color: #173b53 !important;
            font-weight: 760 !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button,
        .stLinkButton > a {
            min-height: 3rem;
            border: 1px solid var(--premium-teal-dark) !important;
            border-radius: 11px !important;
            background: linear-gradient(135deg, #0b89a4 0%, #05647b 100%) !important;
            color: #ffffff !important;
            font-size: .91rem !important;
            font-weight: 800 !important;
            box-shadow: 0 8px 18px rgba(5,100,123,.20);
        }

        .stButton > button *,
        .stDownloadButton > button *,
        [data-testid="stFormSubmitButton"] > button *,
        .stLinkButton > a * {
            color: inherit !important;
            font-weight: inherit !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover,
        .stLinkButton > a:hover {
            background: linear-gradient(135deg, #08758e 0%, #044e61 100%) !important;
            border-color: #044e61 !important;
            transform: translateY(-1px);
            box-shadow: 0 11px 22px rgba(4,78,97,.25);
        }

        .stButton > button[kind="secondary"] {
            background: #f3f9fc !important;
            color: #154d66 !important;
            border: 1.5px solid #7eb3c6 !important;
            box-shadow: 0 5px 13px rgba(16,61,88,.07);
        }

        .stButton > button[kind="secondary"]:hover {
            background: #dceff5 !important;
            color: #083f55 !important;
            border-color: #3c92ad !important;
        }

        div[data-baseweb="tab-list"] {
            gap: .55rem !important;
            padding: .55rem !important;
            border: 1.5px solid var(--premium-border) !important;
            border-radius: 14px !important;
            background: #eaf4f8 !important;
        }

        button[data-baseweb="tab"] {
            min-height: 3.15rem !important;
            border: 1.5px solid #9fc5d4 !important;
            border-radius: 10px !important;
            background: #ffffff !important;
            color: #154d66 !important;
            font-weight: 800 !important;
            box-shadow: 0 4px 10px rgba(16,61,88,.06);
        }

        button[data-baseweb="tab"]:hover {
            background: #d9edf3 !important;
            border-color: #5ca4bb !important;
            color: #073f55 !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0b89a4 0%, #05647b 100%) !important;
            border-color: #05647b !important;
            color: #ffffff !important;
            box-shadow: inset 4px 0 0 #67d9ee, 0 8px 18px rgba(5,100,123,.20);
        }

        button[data-baseweb="tab"][aria-selected="true"] * {
            color: #ffffff !important;
        }

        [data-testid="stDataFrame"] {
            border: 1.5px solid var(--premium-border) !important;
            border-radius: 14px !important;
            overflow: hidden;
            background: #ffffff;
            box-shadow: 0 8px 20px rgba(16,61,88,.07);
        }

        [data-testid="stMetric"] {
            padding: .85rem .9rem;
            border: 1px solid var(--premium-border);
            border-radius: 13px;
            background: #ffffff;
            box-shadow: 0 7px 17px rgba(16,61,88,.06);
        }

        [data-testid="stMetricValue"] {
            color: #0d526b !important;
            font-weight: 840 !important;
        }

        div[data-testid="stAlert"] {
            border-width: 1.5px !important;
            border-radius: 13px !important;
            box-shadow: 0 6px 16px rgba(16,61,88,.06);
        }

        .section-heading {
            margin-top: 1.2rem;
            padding: .3rem .1rem .65rem;
            border-bottom: 1px solid #cfdee7;
        }

        .section-title {
            color: var(--premium-navy);
            font-size: 1.18rem;
            font-weight: 850;
        }

        .section-copy {
            color: #6b8092;
            font-size: .8rem;
            margin-top: .18rem;
        }

        .analytics-heading {
            margin-bottom: .7rem;
        }

        .analytics-kicker {
            color: var(--premium-teal);
            font-size: .67rem;
            font-weight: 850;
            letter-spacing: .1em;
            text-transform: uppercase;
        }

        .analytics-title {
            color: var(--premium-navy);
            font-size: 1.02rem;
            font-weight: 840;
            margin-top: .12rem;
        }

        .analytics-copy {
            color: #657c8f;
            font-size: .76rem;
            line-height: 1.45;
            margin-top: .2rem;
        }

        .dashboard-summary-grid {
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            gap: 10px;
            margin: .7rem 0 1rem;
        }

        .dashboard-summary-card {
            min-width: 0;
            padding: .9rem .8rem;
            border: 1.5px solid var(--premium-border);
            border-radius: 14px;
            background: #ffffff;
            box-shadow: 0 8px 20px rgba(16,61,88,.07);
            text-align: center;
        }

        .dashboard-summary-icon {
            width: 38px;
            height: 38px;
            margin: 0 auto .45rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 11px;
            background: #e8f5f8;
            color: var(--premium-teal);
            font-size: 1.1rem;
            font-weight: 850;
        }

        .dashboard-summary-label {
            color: #526b7e;
            font-size: .68rem;
            font-weight: 800;
            line-height: 1.25;
            text-transform: uppercase;
            letter-spacing: .04em;
        }

        .dashboard-summary-value {
            color: var(--premium-navy);
            font-size: clamp(.95rem, 1.35vw, 1.3rem);
            font-weight: 860;
            line-height: 1.12;
            margin-top: .35rem;
            overflow-wrap: anywhere;
        }

        .dashboard-summary-detail {
            color: #718598;
            font-size: .66rem;
            line-height: 1.3;
            margin-top: .28rem;
        }

        .dashboard-summary-card.green { border-color: #a8dbc7; }
        .dashboard-summary-card.blue { border-color: #a9cce9; }
        .dashboard-summary-card.orange { border-color: #f4c691; }
        .dashboard-summary-card.purple { border-color: #cbb9ee; }
        .dashboard-summary-card.red { border-color: #edb0b4; }

        .st-key-sidebar_manage_profile {
            position: relative;
            z-index: 10;
            width: 2.35rem;
            margin-left: auto;
            margin-top: -4.55rem;
            margin-right: .65rem;
            margin-bottom: 2.35rem;
        }

        .st-key-sidebar_manage_profile button {
            width: 2.35rem !important;
            min-height: 2.35rem !important;
            height: 2.35rem !important;
            padding: 0 !important;
            border-radius: 50% !important;
            background: #ffffff !important;
            color: var(--premium-teal) !important;
            border: 1.5px solid #7fb8c9 !important;
            box-shadow: 0 6px 14px rgba(16,61,88,.16);
            font-size: 1.1rem !important;
        }

        .st-key-sidebar_manage_profile button:hover {
            background: var(--premium-teal) !important;
            color: #ffffff !important;
            border-color: var(--premium-teal) !important;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid #cbdce5;
            box-shadow: 7px 0 26px rgba(16,61,88,.05);
        }

        @media (max-width: 1320px) {
            .dashboard-summary-grid {
                grid-template-columns: repeat(4, minmax(0, 1fr));
            }
        }

        @media (max-width: 850px) {
            .dashboard-summary-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 560px) {
            .dashboard-summary-grid {
                grid-template-columns: 1fr;
            }
        }

        /* ================================================================
           Streamlit 1.4x+ control visibility overrides
           These role/test-id selectors cover the current Streamlit DOM.
           ================================================================ */

        /* Clearly boxed text, number, password, email, date, and search inputs */
        [data-testid="stTextInput"] div[data-baseweb="input"],
        [data-testid="stNumberInput"] div[data-baseweb="input"],
        [data-testid="stDateInput"] div[data-baseweb="input"],
        [data-testid="stTimeInput"] div[data-baseweb="input"],
        [data-testid="stSearchbox"] div[data-baseweb="input"] {
            min-height: 3.15rem !important;
            background: #ffffff !important;
            border: 2px solid #76aeca !important;
            border-radius: 11px !important;
            box-shadow:
                0 3px 9px rgba(24, 83, 108, .08),
                inset 0 1px 2px rgba(15, 62, 84, .035) !important;
            overflow: hidden !important;
            transition:
                border-color .15s ease,
                box-shadow .15s ease,
                background .15s ease !important;
        }

        [data-testid="stTextInput"] div[data-baseweb="input"]:hover,
        [data-testid="stNumberInput"] div[data-baseweb="input"]:hover,
        [data-testid="stDateInput"] div[data-baseweb="input"]:hover,
        [data-testid="stTimeInput"] div[data-baseweb="input"]:hover,
        [data-testid="stSearchbox"] div[data-baseweb="input"]:hover {
            border-color: #2987a5 !important;
            box-shadow: 0 5px 13px rgba(24, 83, 108, .13) !important;
        }

        [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stDateInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stTimeInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stSearchbox"] div[data-baseweb="input"]:focus-within {
            border-color: #057c99 !important;
            background: #fbfeff !important;
            box-shadow:
                0 0 0 4px rgba(5, 124, 153, .16),
                0 6px 15px rgba(24, 83, 108, .12) !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stSearchbox"] input {
            min-height: 3rem !important;
            padding: .68rem .78rem !important;
            border: 0 !important;
            outline: 0 !important;
            box-shadow: none !important;
            background: transparent !important;
            color: #102e47 !important;
            -webkit-text-fill-color: #102e47 !important;
            font-size: .9rem !important;
            font-weight: 560 !important;
        }

        /* Text areas need a full visible perimeter */
        [data-testid="stTextArea"] textarea {
            min-height: 9rem !important;
            padding: .82rem .86rem !important;
            background: #ffffff !important;
            border: 2px solid #76aeca !important;
            border-radius: 11px !important;
            color: #102e47 !important;
            -webkit-text-fill-color: #102e47 !important;
            box-shadow:
                0 3px 9px rgba(24, 83, 108, .08),
                inset 0 1px 2px rgba(15, 62, 84, .035) !important;
            font-size: .9rem !important;
            line-height: 1.48 !important;
            transition:
                border-color .15s ease,
                box-shadow .15s ease !important;
        }

        [data-testid="stTextArea"] textarea:hover {
            border-color: #2987a5 !important;
        }

        [data-testid="stTextArea"] textarea:focus {
            border-color: #057c99 !important;
            box-shadow:
                0 0 0 4px rgba(5, 124, 153, .16),
                0 6px 15px rgba(24, 83, 108, .12) !important;
            outline: none !important;
        }

        /* Selectboxes and multiselects */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
        [data-testid="stSelectbox"] [role="combobox"],
        [data-testid="stMultiSelect"] [role="combobox"] {
            min-height: 3.15rem !important;
            background: #ffffff !important;
            border: 2px solid #76aeca !important;
            border-radius: 11px !important;
            color: #102e47 !important;
            box-shadow: 0 3px 9px rgba(24, 83, 108, .08) !important;
            transition:
                border-color .15s ease,
                box-shadow .15s ease !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:hover {
            border-color: #2987a5 !important;
            box-shadow: 0 5px 13px rgba(24, 83, 108, .13) !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:focus-within {
            border-color: #057c99 !important;
            box-shadow:
                0 0 0 4px rgba(5, 124, 153, .16),
                0 6px 15px rgba(24, 83, 108, .12) !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] *,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] * {
            color: #102e47 !important;
            -webkit-text-fill-color: #102e47 !important;
        }

        /* Visible placeholders */
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stDateInput"] input::placeholder,
        [data-testid="stSearchbox"] input::placeholder {
            color: #73889a !important;
            -webkit-text-fill-color: #73889a !important;
            opacity: 1 !important;
            font-weight: 500 !important;
        }

        /* Input labels */
        [data-testid="stWidgetLabel"] p,
        [data-testid="stTextInput"] label p,
        [data-testid="stNumberInput"] label p,
        [data-testid="stTextArea"] label p,
        [data-testid="stSelectbox"] label p,
        [data-testid="stMultiSelect"] label p,
        [data-testid="stDateInput"] label p {
            color: #0e3650 !important;
            font-size: .82rem !important;
            font-weight: 800 !important;
        }

        /* Number-input +/- controls */
        [data-testid="stNumberInput"] button {
            min-width: 2.55rem !important;
            min-height: 3rem !important;
            border: 0 !important;
            border-left: 1px solid #bdd3de !important;
            border-radius: 0 !important;
            background: #edf6f9 !important;
            color: #0b5069 !important;
            box-shadow: none !important;
        }

        [data-testid="stNumberInput"] button:hover {
            background: #d8edf3 !important;
            color: #063d50 !important;
        }

        /* File upload area */
        [data-testid="stFileUploaderDropzone"] {
            border: 2px dashed #76aeca !important;
            background: #f6fbfd !important;
            padding: 1.15rem !important;
        }

        [data-testid="stFileUploaderDropzone"]:hover {
            border-color: #057c99 !important;
            background: #edf8fb !important;
        }

        /* Current Streamlit tabs: prominent segmented navigation */
        [data-testid="stTabs"] [role="tablist"] {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: .58rem !important;
            padding: .58rem !important;
            margin: .45rem 0 1rem !important;
            border: 1.5px solid #abcbd8 !important;
            border-radius: 14px !important;
            background: #e7f2f6 !important;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,.9),
                0 5px 14px rgba(24,83,108,.07) !important;
        }

        [data-testid="stTabs"] [role="tab"] {
            flex: 1 1 145px !important;
            min-width: 120px !important;
            min-height: 3.05rem !important;
            padding: .65rem .9rem !important;
            border: 1.5px solid #8fb9c9 !important;
            border-radius: 10px !important;
            background: #ffffff !important;
            color: #174e65 !important;
            font-size: .84rem !important;
            font-weight: 800 !important;
            line-height: 1.2 !important;
            box-shadow: 0 4px 10px rgba(24,83,108,.07) !important;
            transition:
                background .15s ease,
                border-color .15s ease,
                color .15s ease,
                transform .15s ease,
                box-shadow .15s ease !important;
        }

        [data-testid="stTabs"] [role="tab"] * {
            color: inherit !important;
            font-size: inherit !important;
            font-weight: inherit !important;
        }

        [data-testid="stTabs"] [role="tab"]:hover {
            background: #cfe9f0 !important;
            border-color: #4093ad !important;
            color: #073f54 !important;
            transform: translateY(-1px);
            box-shadow: 0 7px 15px rgba(24,83,108,.14) !important;
        }

        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background:
                linear-gradient(135deg, #0b8da8 0%, #05627a 100%) !important;
            border-color: #055b70 !important;
            color: #ffffff !important;
            box-shadow:
                inset 4px 0 0 #63d9ee,
                0 8px 18px rgba(5,98,122,.23) !important;
        }

        [data-testid="stTabs"] [role="tab"][aria-selected="true"] * {
            color: #ffffff !important;
        }

        /* Hide the old thin underline indicator; the filled tab is the indicator */
        [data-testid="stTabs"] [role="tab"] [data-baseweb="tab-highlight"],
        [data-testid="stTabs"] [role="tablist"] > div:last-child {
            display: none !important;
        }

        /* Radio options used as record-type selectors */
        [data-testid="stRadio"] [role="radiogroup"] {
            gap: .55rem !important;
            padding: .48rem !important;
            border: 1.5px solid #abcbd8 !important;
            border-radius: 12px !important;
            background: #edf6f9 !important;
        }

        [data-testid="stRadio"] label {
            padding: .45rem .7rem !important;
            border: 1px solid #b8d2dc !important;
            border-radius: 9px !important;
            background: #ffffff !important;
        }

        /* Checkbox outline */
        [data-testid="stCheckbox"] label {
            padding: .52rem .65rem !important;
            border: 1px solid #bdd3de !important;
            border-radius: 9px !important;
            background: #f8fbfd !important;
        }

        /* Form/card padding and separation */
        [data-testid="stForm"] {
            padding: 1.15rem !important;
            border: 1.5px solid #aac8d6 !important;
            border-radius: 16px !important;
            background: #ffffff !important;
            box-shadow: 0 10px 24px rgba(24,83,108,.09) !important;
        }

        @media (max-width: 760px) {
            [data-testid="stTabs"] [role="tab"] {
                flex: 1 1 100% !important;
            }
        }

        /* ================================================================
           Final control sizing and visibility repair
           Applied last so it overrides earlier Streamlit/BaseWeb rules.
           ================================================================ */

        /* Keep normal widgets compact and prevent full-row stretching. */
        [data-testid="stTextInput"],
        [data-testid="stNumberInput"],
        [data-testid="stSelectbox"],
        [data-testid="stMultiSelect"],
        [data-testid="stDateInput"],
        [data-testid="stTimeInput"],
        [data-testid="stSearchbox"] {
            width: 100% !important;
            min-width: 0 !important;
        }

        /* Text, search, date and time input shells. */
        [data-testid="stTextInput"] div[data-baseweb="input"],
        [data-testid="stDateInput"] div[data-baseweb="input"],
        [data-testid="stTimeInput"] div[data-baseweb="input"],
        [data-testid="stSearchbox"] div[data-baseweb="input"] {
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
            min-width: 0 !important;
            min-height: 3.15rem !important;
            height: 3.15rem !important;
            padding: 0 !important;
            overflow: hidden !important;
            background: #f8fcfe !important;
            border: 2px solid #6aa7c4 !important;
            border-radius: 11px !important;
            box-sizing: border-box !important;
            box-shadow:
                0 2px 7px rgba(21, 76, 101, .08),
                inset 0 1px 0 rgba(255,255,255,.9) !important;
        }

        [data-testid="stTextInput"] div[data-baseweb="input"]:hover,
        [data-testid="stDateInput"] div[data-baseweb="input"]:hover,
        [data-testid="stTimeInput"] div[data-baseweb="input"]:hover,
        [data-testid="stSearchbox"] div[data-baseweb="input"]:hover {
            background: #ffffff !important;
            border-color: #237f9f !important;
        }

        [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stDateInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stTimeInput"] div[data-baseweb="input"]:focus-within,
        [data-testid="stSearchbox"] div[data-baseweb="input"]:focus-within {
            background: #ffffff !important;
            border-color: #047894 !important;
            box-shadow:
                0 0 0 3px rgba(4,120,148,.17),
                0 5px 13px rgba(21,76,101,.11) !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stSearchbox"] input {
            flex: 1 1 auto !important;
            width: 100% !important;
            min-width: 0 !important;
            height: 100% !important;
            min-height: 0 !important;
            padding: .65rem .78rem !important;
            margin: 0 !important;
            border: 0 !important;
            outline: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            color: #102f49 !important;
            -webkit-text-fill-color: #102f49 !important;
            box-sizing: border-box !important;
        }

        /* Number inputs: compact value field with attached +/- controls. */
        [data-testid="stNumberInput"] div[data-baseweb="input"] {
            display: flex !important;
            align-items: stretch !important;
            width: 100% !important;
            min-width: 0 !important;
            min-height: 3.15rem !important;
            height: 3.15rem !important;
            padding: 0 !important;
            overflow: hidden !important;
            background: #f8fcfe !important;
            border: 2px solid #6aa7c4 !important;
            border-radius: 11px !important;
            box-sizing: border-box !important;
            box-shadow:
                0 2px 7px rgba(21,76,101,.08),
                inset 0 1px 0 rgba(255,255,255,.9) !important;
        }

        [data-testid="stNumberInput"] div[data-baseweb="input"]:hover {
            background: #ffffff !important;
            border-color: #237f9f !important;
        }

        [data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within {
            background: #ffffff !important;
            border-color: #047894 !important;
            box-shadow:
                0 0 0 3px rgba(4,120,148,.17),
                0 5px 13px rgba(21,76,101,.11) !important;
        }

        [data-testid="stNumberInput"] input {
            flex: 1 1 auto !important;
            width: auto !important;
            min-width: 0 !important;
            height: 100% !important;
            min-height: 0 !important;
            padding: .62rem .72rem !important;
            margin: 0 !important;
            border: 0 !important;
            outline: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            color: #102f49 !important;
            -webkit-text-fill-color: #102f49 !important;
            box-sizing: border-box !important;
        }

        [data-testid="stNumberInput"] button {
            flex: 0 0 2.45rem !important;
            width: 2.45rem !important;
            min-width: 2.45rem !important;
            max-width: 2.45rem !important;
            height: 100% !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            border-left: 1px solid #bfd6e1 !important;
            border-radius: 0 !important;
            background: #e9f4f8 !important;
            color: #07536c !important;
            box-shadow: none !important;
            transform: none !important;
        }

        [data-testid="stNumberInput"] button:hover {
            background: #d2e9f0 !important;
            color: #043d50 !important;
            transform: none !important;
        }

        /* Select and multiselect shells. */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
            min-width: 0 !important;
            min-height: 3.15rem !important;
            height: auto !important;
            padding: .18rem .38rem !important;
            background: #f8fcfe !important;
            border: 2px solid #6aa7c4 !important;
            border-radius: 11px !important;
            box-sizing: border-box !important;
            box-shadow:
                0 2px 7px rgba(21,76,101,.08),
                inset 0 1px 0 rgba(255,255,255,.9) !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:hover {
            background: #ffffff !important;
            border-color: #237f9f !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:focus-within {
            background: #ffffff !important;
            border-color: #047894 !important;
            box-shadow:
                0 0 0 3px rgba(4,120,148,.17),
                0 5px 13px rgba(21,76,101,.11) !important;
        }

        [data-testid="stSelectbox"] [role="combobox"],
        [data-testid="stMultiSelect"] [role="combobox"] {
            width: 100% !important;
            min-width: 0 !important;
            min-height: 2.65rem !important;
            border: 0 !important;
            outline: 0 !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        [data-testid="stSelectbox"] div[data-baseweb="select"] *,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] * {
            color: #102f49 !important;
            -webkit-text-fill-color: #102f49 !important;
        }

        /* Text areas remain larger, but no longer overflow their cards. */
        [data-testid="stTextArea"] textarea {
            display: block !important;
            width: 100% !important;
            min-width: 0 !important;
            min-height: 8rem !important;
            max-width: 100% !important;
            padding: .78rem .82rem !important;
            margin: 0 !important;
            background: #f8fcfe !important;
            border: 2px solid #6aa7c4 !important;
            border-radius: 11px !important;
            box-sizing: border-box !important;
            color: #102f49 !important;
            -webkit-text-fill-color: #102f49 !important;
            box-shadow:
                0 2px 7px rgba(21,76,101,.08),
                inset 0 1px 0 rgba(255,255,255,.9) !important;
            resize: vertical !important;
        }

        [data-testid="stTextArea"] textarea:hover {
            background: #ffffff !important;
            border-color: #237f9f !important;
        }

        [data-testid="stTextArea"] textarea:focus {
            background: #ffffff !important;
            border-color: #047894 !important;
            outline: 0 !important;
            box-shadow:
                0 0 0 3px rgba(4,120,148,.17),
                0 5px 13px rgba(21,76,101,.11) !important;
        }

        /* Keep placeholders visible against the lightly tinted field fill. */
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stDateInput"] input::placeholder,
        [data-testid="stSearchbox"] input::placeholder {
            color: #687f92 !important;
            -webkit-text-fill-color: #687f92 !important;
            opacity: 1 !important;
        }

        /* Avoid wide desktop forms looking excessively stretched. */
        [data-testid="stForm"] {
            width: 100% !important;
            max-width: 100% !important;
            padding: 1.15rem 1.2rem !important;
            box-sizing: border-box !important;
        }

        [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
            gap: 1rem !important;
            align-items: flex-start !important;
        }

        /* Smaller profile edit pen. */
        .st-key-sidebar_manage_profile {
            width: 1.8rem !important;
            margin-top: -4.15rem !important;
            margin-right: .7rem !important;
            margin-bottom: 2.35rem !important;
        }

        .st-key-sidebar_manage_profile button {
            width: 1.8rem !important;
            min-width: 1.8rem !important;
            max-width: 1.8rem !important;
            height: 1.8rem !important;
            min-height: 1.8rem !important;
            max-height: 1.8rem !important;
            padding: 0 !important;
            border-width: 1px !important;
            font-size: .72rem !important;
            line-height: 1 !important;
            box-shadow: 0 4px 10px rgba(16,61,88,.14) !important;
        }

        .st-key-sidebar_manage_profile button * {
            font-size: .72rem !important;
            line-height: 1 !important;
        }

        /* Responsive breathing room without major layout changes. */
        @media (max-width: 1100px) {
            [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
                gap: .75rem !important;
            }
        }

        @media (max-width: 760px) {
            [data-testid="stForm"] {
                padding: .9rem !important;
            }

            [data-testid="stTextInput"] div[data-baseweb="input"],
            [data-testid="stNumberInput"] div[data-baseweb="input"],
            [data-testid="stDateInput"] div[data-baseweb="input"],
            [data-testid="stTimeInput"] div[data-baseweb="input"],
            [data-testid="stSearchbox"] div[data-baseweb="input"],
            [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
            [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
                min-height: 3.3rem !important;
                height: auto !important;
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
                <div style="
                    margin-top:.85rem;
                    display:inline-flex;
                    align-items:center;
                    gap:.42rem;
                    width:max-content;
                    padding:.34rem .62rem;
                    border:1px solid #b9d8e4;
                    border-radius:999px;
                    background:#edf8fb;
                    color:#0d6b84;
                    font-size:.68rem;
                    font-weight:800;
                    letter-spacing:.045em;
                    text-transform:uppercase;">
                    ● Live operational workspace
                </div>
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


def render_rights_notice() -> None:
    """Display a prominent fan-project and third-party rights notice."""
    st.markdown(
        """
        <div class="rights-notice">
            <strong>Unofficial fan-made project.</strong>
            This application is not affiliated with, sponsored by, or endorsed by
            Cloud Imperium Games, Roberts Space Industries, or any third-party data
            provider. Star Citizen, Squadron 42, related names, logos, game content,
            and assets remain the property of their respective rights holders.
            Third-party websites and data remain subject to their owners' terms,
            privacy policies, copyrights, and availability. Embedded content and
            external links are provided for convenience and informational use only.
            No ownership of third-party content is claimed, and accuracy or continued
            availability is not guaranteed.
        </div>
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
    """Load encrypted browser cookies before authentication is evaluated."""
    try:
        cookie_password = st.secrets["COOKIE_PASSWORD"]
    except KeyError:
        return None

    if not cookie_password or st.session_state.get("skip_cookie_restore"):
        return None

    try:
        if "cookie_manager" not in st.session_state:
            st.session_state.cookie_manager = EncryptedCookieManager(
                prefix=COOKIE_PREFIX,
                password=str(cookie_password),
            )

        cookies = st.session_state.cookie_manager
        if cookies.ready():
            return cookies

        # The cookie component is asynchronous. Stop before rendering the
        # login page so a refresh is not mistaken for a signed-out session.
        st.markdown("### Restoring your secure session")
        st.caption(
            "The app is loading the encrypted browser cookie used to keep "
            "you signed in after a refresh."
        )
        st.info("This normally completes automatically in a moment.")
        if st.button("Continue to sign in instead", width="stretch"):
            st.session_state.skip_cookie_restore = True
            st.rerun()
        st.stop()
    except Exception as exc:
        st.session_state.pop("cookie_manager", None)
        st.warning(
            "Persistent login is temporarily unavailable, but normal sign-in "
            f"can still be used. Details: {exc}"
        )
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


def user_metadata_dict(user: Any) -> dict[str, Any]:
    """Return a mutable Supabase user-metadata dictionary."""
    metadata = (
        getattr(user, "user_metadata", None)
        or getattr(user, "raw_user_meta_data", None)
        or {}
    )
    return dict(metadata) if isinstance(metadata, dict) else {}


def set_authenticated_user(user: Any, fallback_email: str = "") -> None:
    """Store the signed-in user's account and profile information."""
    user_email = getattr(user, "email", None) or fallback_email or ""
    metadata = user_metadata_dict(user)

    st.session_state.user_id = str(user.id)
    st.session_state.user_email = user_email or "Signed in"
    st.session_state.user_display_name = resolve_user_display_name(
        user,
        user_email,
    )
    st.session_state.user_callsign = str(
        metadata.get("callsign", "") or ""
    ).strip()
    st.session_state.user_bio = str(
        metadata.get("bio", "") or ""
    ).strip()
    st.session_state.user_avatar_url = str(
        metadata.get("avatar_url", "") or ""
    ).strip()
    st.session_state.user_avatar_path = str(
        metadata.get("avatar_path", "") or ""
    ).strip()

    metadata_timezone = str(
        metadata.get("timezone", "") or ""
    ).strip()
    if metadata_timezone in available_timezones():
        st.session_state.selected_timezone = metadata_timezone

    created_at = getattr(user, "created_at", None)
    if created_at:
        st.session_state.user_created_at = str(created_at)


def profile_initials(name: str, email: str = "") -> str:
    """Return one or two initials for the avatar fallback."""
    source = name.strip() or email.split("@", 1)[0]
    pieces = [
        piece
        for piece in re.split(r"[\s._\-+]+", source)
        if piece
    ]
    if not pieces:
        return "SC"
    if len(pieces) == 1:
        return pieces[0][:2].upper()
    return (pieces[0][0] + pieces[-1][0]).upper()


def avatar_markup(
    *,
    avatar_url: str,
    display_name: str,
    email: str,
    large: bool = False,
) -> str:
    """Return avatar image or initials HTML."""
    safe_name = html.escape(display_name or "Citizen")
    if avatar_url:
        css_class = (
            "profile-avatar-large"
            if large
            else "sidebar-profile-avatar"
        )
        return (
            f'<img class="{css_class}" '
            f'src="{html.escape(avatar_url, quote=True)}" '
            f'alt="{safe_name} profile picture" />'
        )

    initials = html.escape(profile_initials(display_name, email))
    css_class = (
        "profile-avatar-large-initials"
        if large
        else "sidebar-profile-initials"
    )
    return f'<div class="{css_class}">{initials}</div>'


def public_storage_url(value: Any) -> str:
    """Extract a public URL from supabase-py return shapes."""
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        for key in ("publicUrl", "public_url", "url"):
            candidate = value.get(key)
            if candidate:
                return str(candidate)
        data = value.get("data")
        if isinstance(data, dict):
            for key in ("publicUrl", "public_url", "url"):
                candidate = data.get(key)
                if candidate:
                    return str(candidate)

    candidate = getattr(value, "public_url", None)
    if candidate:
        return str(candidate)

    return ""


def prepare_avatar_bytes(uploaded_file: Any) -> bytes:
    """Center-crop an uploaded image and return a web-friendly JPEG."""
    raw_bytes = uploaded_file.getvalue()
    if len(raw_bytes) > MAX_AVATAR_BYTES:
        raise ValueError("Profile pictures must be 2 MB or smaller.")

    image = Image.open(BytesIO(raw_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    avatar = ImageOps.fit(
        image,
        AVATAR_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    output = BytesIO()
    avatar.save(
        output,
        format="JPEG",
        quality=90,
        optimize=True,
        progressive=True,
    )
    return output.getvalue()


def save_profile_metadata(
    client: Client,
    updates: dict[str, Any],
) -> None:
    """Merge profile updates into Supabase user metadata."""
    response = client.auth.get_user()
    current_user = getattr(response, "user", None)
    current_metadata = (
        user_metadata_dict(current_user)
        if current_user is not None
        else {}
    )
    merged_metadata = {**current_metadata, **updates}

    updated_response = client.auth.update_user(
        {"data": merged_metadata}
    )
    updated_user = getattr(updated_response, "user", None)
    if updated_user is not None:
        set_authenticated_user(
            updated_user,
            st.session_state.get("user_email", ""),
        )
    else:
        for key, value in updates.items():
            session_key = {
                "display_name": "user_display_name",
                "callsign": "user_callsign",
                "bio": "user_bio",
                "avatar_url": "user_avatar_url",
                "avatar_path": "user_avatar_path",
                "timezone": "selected_timezone",
            }.get(key)
            if session_key:
                st.session_state[session_key] = value


def upload_profile_avatar(
    client: Client,
    uploaded_file: Any,
) -> None:
    """Upload a normalized avatar and save its URL in user metadata."""
    avatar_bytes = prepare_avatar_bytes(uploaded_file)
    avatar_path = f"{st.session_state.user_id}/avatar.jpg"

    storage = client.storage.from_(AVATAR_BUCKET)
    storage.upload(
        path=avatar_path,
        file=avatar_bytes,
        file_options={
            "content-type": "image/jpeg",
            "cache-control": "3600",
            "upsert": "true",
        },
    )

    public_url = public_storage_url(
        storage.get_public_url(avatar_path)
    )
    if not public_url:
        raise RuntimeError(
            "Supabase uploaded the avatar but did not return a public URL."
        )

    cache_busted_url = (
        public_url.split("?", 1)[0] + f"?v={int(time.time())}"
    )
    save_profile_metadata(
        client,
        {
            "avatar_url": cache_busted_url,
            "avatar_path": avatar_path,
        },
    )


def remove_profile_avatar(client: Client) -> None:
    """Remove the current avatar and restore initials."""
    avatar_path = st.session_state.get("user_avatar_path", "")
    if avatar_path:
        try:
            client.storage.from_(AVATAR_BUCKET).remove([avatar_path])
        except Exception:
            pass

    save_profile_metadata(
        client,
        {
            "avatar_url": "",
            "avatar_path": "",
        },
    )


def parse_account_date(value: str) -> str:
    """Format Supabase account timestamps for display."""
    if not value:
        return "Not available"
    try:
        parsed = pd.to_datetime(value, utc=True)
        return parsed.tz_convert(
            ZoneInfo(selected_timezone())
        ).strftime("%b %d, %Y")
    except Exception:
        return str(value)[:10]


def refresh_profile_user(client: Client) -> Any | None:
    """Refresh profile details from the authenticated Supabase user."""
    try:
        response = client.auth.get_user()
        user = getattr(response, "user", None)
        if user is not None:
            set_authenticated_user(
                user,
                st.session_state.get("user_email", ""),
            )
        return user
    except Exception:
        return None


def profile_page(
    client: Client,
    cookies: EncryptedCookieManager | None,
) -> None:
    """Render a full account and profile experience."""
    current_user = refresh_profile_user(client)

    display_name = st.session_state.get(
        "user_display_name",
        "Citizen",
    )
    email = st.session_state.get("user_email", "Signed in")
    callsign = st.session_state.get("user_callsign", "")
    bio = st.session_state.get("user_bio", "")
    avatar_url = st.session_state.get("user_avatar_url", "")
    created_at = (
        getattr(current_user, "created_at", None)
        if current_user is not None
        else st.session_state.get("user_created_at", "")
    )

    hero_bio = (
        bio
        or "Manage your identity, security, profile picture, and "
        "personal app preferences."
    )
    callsign_text = (
        f"Callsign: {html.escape(callsign)}"
        if callsign
        else "Star Citizen operations account"
    )

    st.markdown(
        f"""
        <section class="profile-hero">
            {avatar_markup(
                avatar_url=avatar_url,
                display_name=display_name,
                email=email,
                large=True,
            )}
            <div>
                <div class="profile-hero-kicker">Account Command Center</div>
                <div class="profile-hero-name">
                    {html.escape(display_name)}
                </div>
                <div class="profile-hero-email">
                    {html.escape(email)} · {callsign_text}
                </div>
                <div class="profile-hero-bio">
                    {html.escape(hero_bio)}
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    summary_cards = [
        {
            "label": "Member Since",
            "value": parse_account_date(str(created_at or "")),
            "detail": "Supabase account creation date",
        },
        {
            "label": "Display Timezone",
            "value": selected_timezone(),
            "detail": "Used throughout dashboards and exports",
        },
        {
            "label": "Profile Picture",
            "value": "Uploaded" if avatar_url else "Initials",
            "detail": "Stored in your Supabase avatar folder",
        },
        {
            "label": "Account Email",
            "value": email,
            "detail": "Used as the account username",
        },
    ]

    st.markdown(
        '<div class="profile-summary-grid">'
        + "".join(
            (
                '<div class="profile-summary-card">'
                f'<div class="profile-summary-label">{html.escape(card["label"])}</div>'
                f'<div class="profile-summary-value">{html.escape(card["value"])}</div>'
                f'<div class="profile-summary-detail">{html.escape(card["detail"])}</div>'
                "</div>"
            )
            for card in summary_cards
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    profile_tab, security_tab, preferences_tab = st.tabs(
        ["Profile & Picture", "Security & Login", "Preferences"]
    )

    with profile_tab:
        picture_col, details_col = st.columns([1, 1.55])

        with picture_col:
            st.markdown("### Profile Picture")
            with st.container(border=True):
                st.markdown(
                    avatar_markup(
                        avatar_url=avatar_url,
                        display_name=display_name,
                        email=email,
                        large=True,
                    ),
                    unsafe_allow_html=True,
                )
                avatar_file = st.file_uploader(
                    "Upload a new profile picture",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=False,
                    help=(
                        "The image is center-cropped to a square and resized "
                        "to 512 × 512. Maximum file size: 2 MB."
                    ),
                    key="profile_avatar_upload",
                )

                if st.button(
                    "Upload Profile Picture",
                    key="upload_profile_avatar_button",
                    disabled=avatar_file is None,
                    width="stretch",
                ):
                    try:
                        upload_profile_avatar(client, avatar_file)
                        st.success("Profile picture updated.")
                        st.rerun()
                    except Exception as exc:
                        st.error(
                            "The profile picture could not be uploaded. "
                            "Run `schema_migration_v5_profile_avatars.sql` "
                            f"in Supabase first. Details: {exc}"
                        )

                if st.button(
                    "Remove Profile Picture",
                    key="remove_profile_avatar_button",
                    disabled=not bool(avatar_url),
                    width="stretch",
                ):
                    try:
                        remove_profile_avatar(client)
                        st.success("Profile picture removed.")
                        st.rerun()
                    except Exception as exc:
                        st.error(
                            f"The profile picture could not be removed: {exc}"
                        )

        with details_col:
            st.markdown("### Public Profile Details")
            with st.form("comprehensive_profile_form"):
                new_display_name = st.text_input(
                    "Display name",
                    value=display_name,
                    help="Shown in the dashboard greeting and sidebar.",
                )
                new_callsign = st.text_input(
                    "Callsign or handle",
                    value=callsign,
                    placeholder="Optional Star Citizen callsign",
                )
                new_bio = st.text_area(
                    "Profile description",
                    value=bio,
                    placeholder=(
                        "Add a short description of your play style, "
                        "organization role, or preferred activities."
                    ),
                    max_chars=500,
                    height=150,
                )
                save_profile = st.form_submit_button(
                    "Save Profile Changes",
                    width="stretch",
                )

            if save_profile:
                cleaned_name = new_display_name.strip()
                if not cleaned_name:
                    st.error("Enter a display name.")
                else:
                    try:
                        save_profile_metadata(
                            client,
                            {
                                "display_name": cleaned_name,
                                "callsign": new_callsign.strip(),
                                "bio": new_bio.strip(),
                            },
                        )
                        st.success("Profile details updated.")
                        st.rerun()
                    except Exception as exc:
                        st.error(
                            f"The profile could not be updated: {exc}"
                        )

    with security_tab:
        security_col1, security_col2 = st.columns(2)

        with security_col1:
            st.markdown("### Email Address")
            with st.container(border=True):
                st.text_input(
                    "Current account email",
                    value=email,
                    disabled=True,
                    key="current_profile_email",
                )
                with st.form("change_email_form"):
                    new_email = st.text_input(
                        "New email address",
                        placeholder="new-address@example.com",
                    )
                    change_email = st.form_submit_button(
                        "Request Email Change",
                        width="stretch",
                    )

                if change_email:
                    if "@" not in new_email:
                        st.error("Enter a valid email address.")
                    elif new_email.strip().lower() == email.lower():
                        st.info("That is already your account email.")
                    else:
                        try:
                            client.auth.update_user(
                                {"email": new_email.strip()}
                            )
                            st.success(
                                "Email-change request submitted. Check the "
                                "confirmation messages sent by Supabase."
                            )
                        except Exception as exc:
                            st.error(
                                f"The email could not be changed: {exc}"
                            )

        with security_col2:
            st.markdown("### Password")
            with st.container(border=True):
                st.markdown(
                    """
                    <div class="profile-security-note">
                        Use at least 8 characters. Supabase may require a
                        security code for sensitive password changes,
                        depending on the project's authentication settings.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    "Send Password Security Code",
                    key="send_password_security_code",
                    width="stretch",
                ):
                    try:
                        client.auth.reauthenticate()
                        st.success(
                            "Security code sent to your account email."
                        )
                    except Exception as exc:
                        st.error(
                            f"The security code could not be sent: {exc}"
                        )

                with st.form("profile_password_change_form"):
                    new_password = st.text_input(
                        "New password",
                        type="password",
                    )
                    confirm_password = st.text_input(
                        "Confirm new password",
                        type="password",
                    )
                    password_nonce = st.text_input(
                        "Security code",
                        placeholder=(
                            "Optional unless Supabase requires reauthentication"
                        ),
                    )
                    update_password = st.form_submit_button(
                        "Change Password",
                        width="stretch",
                    )

                if update_password:
                    if len(new_password) < 8:
                        st.error(
                            "Use a password with at least 8 characters."
                        )
                    elif new_password != confirm_password:
                        st.error("The passwords do not match.")
                    else:
                        attributes: dict[str, Any] = {
                            "password": new_password
                        }
                        if password_nonce.strip():
                            attributes["nonce"] = password_nonce.strip()
                        try:
                            client.auth.update_user(attributes)
                            st.success(
                                "Password updated successfully. Your current "
                                "session remains active."
                            )
                        except Exception as exc:
                            st.error(
                                "The password could not be changed. Send a "
                                f"security code and try again. Details: {exc}"
                            )

        st.markdown("### Session Controls")
        with st.container(border=True):
            st.caption(
                "Signing out removes this browser's saved Supabase refresh "
                "token. Your account and saved records remain unchanged."
            )
            if st.button(
                "Sign Out of This Device",
                key="profile_sign_out",
                width="stretch",
            ):
                try:
                    client.auth.sign_out()
                finally:
                    remove_cookie_value(
                        cookies,
                        COOKIE_REFRESH_TOKEN,
                    )
                    clear_login_state()
                    st.rerun()

    with preferences_tab:
        st.markdown("### Timezone & Display Preferences")
        with st.container(border=True):
            mode = st.radio(
                "Timezone list",
                ["U.S. timezones", "All timezones"],
                horizontal=True,
                key="profile_timezone_mode",
            )
            options = (
                list(US_TIMEZONES.values())
                if mode == "U.S. timezones"
                else sorted(available_timezones())
            )
            current_timezone = selected_timezone()
            if current_timezone not in options:
                options = [current_timezone, *options]

            profile_timezone = st.selectbox(
                "Display timezone",
                options,
                index=options.index(current_timezone),
                key="profile_timezone_selector",
            )
            st.caption(
                "This timezone is used for dashboard dates, account dates, "
                "saved records, and exports."
            )

            if st.button(
                "Save Timezone Preference",
                key="save_profile_timezone",
                width="stretch",
            ):
                try:
                    save_profile_metadata(
                        client,
                        {"timezone": profile_timezone},
                    )
                    st.session_state.selected_timezone = profile_timezone
                    st.success("Timezone preference saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        f"The timezone could not be saved: {exc}"
                    )


def profile_settings(client: Client) -> None:
    """Backward-compatible compact link to the full profile page."""
    st.caption(
        "Profile, password, picture, email, and timezone settings are "
        "available on the My Profile page."
    )
    if st.button(
        "Open My Profile",
        key="open_profile_from_settings",
        width="stretch",
    ):
        st.session_state.nav_page = "My Profile"
        st.rerun()


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
        st.session_state.pop("skip_cookie_restore", None)
    else:
        cookies.pop(COOKIE_REFRESH_TOKEN, None)
    cookies.save()
    # Give the browser component a moment to persist the encrypted value
    # before the Streamlit rerun begins.
    time.sleep(0.20)


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
        "password_recovery_active",
        "recovery_error",
        "skip_cookie_restore",
    ):
        st.session_state.pop(key, None)


def get_public_app_url() -> str:
    """Return the deployed app URL used by Supabase recovery emails."""
    try:
        configured = str(st.secrets["APP_PUBLIC_URL"]).strip()
    except KeyError:
        configured = ""
    return configured or DEFAULT_PUBLIC_APP_URL


def query_value(name: str) -> str:
    """Read one query parameter as a simple string."""
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def handle_auth_redirect(
    client: Client,
    cookies: EncryptedCookieManager | None,
) -> None:
    """Handle Supabase recovery callbacks before showing the login page."""
    code = query_value("code")
    token_hash = query_value("token_hash")
    recovery_flag = query_value("recovery")
    auth_type = query_value("type")

    if not any((code, token_hash, recovery_flag, auth_type == "recovery")):
        return

    if "user_id" not in st.session_state:
        try:
            if code:
                response = client.auth.exchange_code_for_session(
                    {"auth_code": code}
                )
            elif token_hash:
                response = client.auth.verify_otp(
                    {
                        "token_hash": token_hash,
                        "type": "recovery",
                    }
                )
            else:
                return

            user = getattr(response, "user", None)
            session = getattr(response, "session", None)
            if user is None and session is not None:
                user = getattr(session, "user", None)
            if user is None:
                raise RuntimeError("The recovery link did not include a user.")

            user_email = getattr(user, "email", "") or ""
            set_authenticated_user(user, user_email)
            remember_authenticated_session(
                response,
                user_email,
                True,
                cookies,
            )
        except Exception as exc:
            st.session_state.recovery_error = str(exc)
            return

    st.session_state.password_recovery_active = True
    st.query_params.clear()


def password_update_screen(
    client: Client,
    cookies: EncryptedCookieManager | None,
) -> None:
    """Let an authenticated recovery-session user choose a new password."""
    page_banner(
        "hero_banner.jpg",
        "Choose a New Password",
        "Your recovery link was accepted. Set a new password for this account.",
        "Account Recovery",
    )

    with st.form("password_update_form"):
        new_password = st.text_input(
            "New password",
            type="password",
            help="Use at least 8 characters.",
        )
        confirm_password = st.text_input(
            "Confirm new password",
            type="password",
        )
        submitted = st.form_submit_button(
            "Update Password",
            width="stretch",
        )

    if submitted:
        if len(new_password) < 8:
            st.error("Use a password with at least 8 characters.")
        elif new_password != confirm_password:
            st.error("The passwords do not match.")
        else:
            try:
                client.auth.update_user({"password": new_password})
                st.session_state.pop("password_recovery_active", None)
                st.session_state.pop("recovery_error", None)
                st.success("Password updated. You are signed in.")
                time.sleep(0.5)
                st.rerun()
            except Exception as exc:
                st.error(f"The password could not be updated: {exc}")

    if st.button("Cancel and sign out", width="stretch"):
        try:
            client.auth.sign_out()
        except Exception:
            pass
        remove_cookie_value(cookies, COOKIE_REFRESH_TOKEN)
        clear_login_state()
        st.session_state.pop("password_recovery_active", None)
        st.rerun()


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

    login_tab, signup_tab, recovery_tab = st.tabs(["Sign in", "Create account", "Recover account"])

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

    with recovery_tab:
        st.info(
            "Your username is the email address used to create the account. "
            "Enter that email below to receive a Supabase password-recovery link."
        )
        recovery_error = st.session_state.pop("recovery_error", "")
        if recovery_error:
            st.error(f"The recovery link could not be completed: {recovery_error}")

        with st.form("password_recovery_request_form"):
            recovery_email = st.text_input(
                "Account email",
                key="recovery_email",
            )
            recovery_submitted = st.form_submit_button(
                "Send Password Reset Email",
                width="stretch",
            )

        if recovery_submitted:
            if "@" not in recovery_email:
                st.error("Enter the email address used for the account.")
            else:
                try:
                    redirect_url = (
                        get_public_app_url().rstrip("/")
                        + "/?recovery=1"
                    )
                    client.auth.reset_password_for_email(
                        recovery_email.strip(),
                        {"redirect_to": redirect_url},
                    )
                    st.success(
                        "Recovery email sent. Open the link in that email, "
                        "then return here to choose a new password."
                    )
                except Exception as exc:
                    st.error(f"The recovery email could not be sent: {exc}")

        st.caption(
            "The app cannot reveal an unknown email address. If you no longer "
            "remember which email you used, contact the app owner."
        )

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

    # Existing deployments may not have the inventory quantity migration yet.
    # Keep the app readable until the supplied SQL migration is run.
    if "quantity_scu" not in ores.columns:
        ores["quantity_scu"] = 0.0
    ores["quantity_scu"] = pd.to_numeric(
        ores["quantity_scu"],
        errors="coerce",
    ).fillna(0.0)

    return contracts, ores


def empty_commodity_transaction_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "id",
            "user_id",
            "date_saved",
            "commodity_name",
            "action",
            "quantity_scu",
            "unit_price",
            "fees",
            "total_value",
            "origin",
            "destination",
            "shipment_reference",
            "notes",
            "cash_effect",
        ]
    )


def normalize_commodity_action(value: Any) -> str:
    """Map records created by older app versions to current action names."""
    normalized = re.sub(
        r"[^a-z]+",
        " ",
        str(value or "").strip().casefold(),
    ).strip()

    buy_aliases = {
        "buy",
        "bought",
        "purchase",
        "purchased",
        "player buy",
    }
    sell_aliases = {
        "sell",
        "sold",
        "sale",
        "player sell",
    }
    loss_aliases = {
        "lost",
        "destroyed",
        "lost destroyed",
        "destroyed lost",
        "shipment lost",
        "shipment destroyed",
        "loss",
    }

    if normalized in buy_aliases:
        return "Bought"
    if normalized in sell_aliases:
        return "Sold"
    if normalized in loss_aliases:
        return "Lost / Destroyed"

    if "destroy" in normalized or "lost" in normalized:
        return "Lost / Destroyed"
    if "sell" in normalized or "sold" in normalized or "sale" in normalized:
        return "Sold"
    if "buy" in normalized or "bought" in normalized or "purchas" in normalized:
        return "Bought"

    return str(value or "Unknown").strip() or "Unknown"


def normalize_commodity_transactions(
    trades: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize legacy rows and derive reliable totals for every app section."""
    expected_columns = [
        "id",
        "user_id",
        "date_saved",
        "commodity_name",
        "action",
        "quantity_scu",
        "unit_price",
        "fees",
        "total_value",
        "origin",
        "destination",
        "shipment_reference",
        "notes",
    ]

    if trades is None or trades.empty:
        return empty_commodity_transaction_frame()

    normalized = trades.copy()
    for column in expected_columns:
        if column not in normalized.columns:
            normalized[column] = (
                0.0
                if column
                in {
                    "quantity_scu",
                    "unit_price",
                    "fees",
                    "total_value",
                }
                else ""
            )

    normalized["commodity_name"] = (
        normalized["commodity_name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "Unknown Commodity")
    )
    normalized["action"] = normalized["action"].map(
        normalize_commodity_action
    )

    for column in (
        "quantity_scu",
        "unit_price",
        "fees",
        "total_value",
    ):
        normalized[column] = pd.to_numeric(
            normalized[column],
            errors="coerce",
        ).fillna(0.0)
        normalized[column] = normalized[column].clip(lower=0.0)

    calculated_value = (
        normalized["quantity_scu"]
        * normalized["unit_price"]
    )
    needs_calculated_value = (
        normalized["total_value"] <= 0
    ) & (calculated_value > 0)
    normalized.loc[
        needs_calculated_value,
        "total_value",
    ] = calculated_value.loc[needs_calculated_value]

    if "date_saved" in normalized.columns:
        normalized["date_saved"] = pd.to_datetime(
            normalized["date_saved"],
            errors="coerce",
            utc=True,
        )
        try:
            normalized["date_saved"] = normalized[
                "date_saved"
            ].dt.tz_convert(APP_TIMEZONE)
        except (TypeError, AttributeError):
            pass

    for column in (
        "origin",
        "destination",
        "shipment_reference",
        "notes",
    ):
        normalized[column] = (
            normalized[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    normalized["cash_effect"] = 0.0
    bought_mask = normalized["action"] == "Bought"
    sold_mask = normalized["action"] == "Sold"
    loss_mask = normalized["action"] == "Lost / Destroyed"

    normalized.loc[bought_mask, "cash_effect"] = -(
        normalized.loc[bought_mask, "total_value"]
        + normalized.loc[bought_mask, "fees"]
    )
    normalized.loc[sold_mask, "cash_effect"] = (
        normalized.loc[sold_mask, "total_value"]
        - normalized.loc[sold_mask, "fees"]
    )
    normalized.loc[loss_mask, "cash_effect"] = -(
        normalized.loc[loss_mask, "total_value"]
        + normalized.loc[loss_mask, "fees"]
    )

    ordered_columns = [
        *expected_columns,
        "cash_effect",
    ]
    return normalized[ordered_columns]


def load_commodity_transactions() -> pd.DataFrame:
    """Load and normalize the signed-in user's commodity records."""
    try:
        raw_trades = fetch_table("commodity_transactions")
        trades = normalize_commodity_transactions(raw_trades)
        st.session_state.commodity_tracker_ready = True
        st.session_state.pop("commodity_tracker_error", None)
        st.session_state.commodity_tracker_row_count = len(trades)
    except Exception as exc:
        st.session_state.commodity_tracker_ready = False
        st.session_state.commodity_tracker_error = str(exc)
        st.session_state.commodity_tracker_row_count = 0
        return empty_commodity_transaction_frame()

    return trades


def insert_commodity_transaction(payload: dict[str, Any]) -> None:
    """Insert one validated commodity activity record."""
    action = normalize_commodity_action(payload.get("action"))
    quantity = max(safe_float(payload.get("quantity_scu")), 0.0)
    unit_price = max(safe_float(payload.get("unit_price")), 0.0)
    fees = max(safe_float(payload.get("fees")), 0.0)
    total_value = max(
        safe_float(payload.get("total_value")),
        quantity * unit_price,
    )

    cleaned_payload = {
        **payload,
        "commodity_name": str(
            payload.get("commodity_name", "")
        ).strip(),
        "action": action,
        "quantity_scu": quantity,
        "unit_price": unit_price,
        "fees": fees,
        "total_value": total_value,
    }
    get_supabase().table("commodity_transactions").insert(
        cleaned_payload
    ).execute()


def commodity_summary_values(
    trades: pd.DataFrame,
) -> dict[str, float]:
    """Calculate consistent commodity totals used by every page and export."""
    normalized = normalize_commodity_transactions(trades)

    if normalized.empty:
        return {
            "records": 0.0,
            "bought_records": 0.0,
            "sold_records": 0.0,
            "loss_records": 0.0,
            "bought_scu": 0.0,
            "sold_scu": 0.0,
            "lost_scu": 0.0,
            "on_hand_scu": 0.0,
            "purchase_cost": 0.0,
            "sales_revenue": 0.0,
            "loss_value": 0.0,
            "net_cash_flow": 0.0,
        }

    bought = normalized[normalized["action"] == "Bought"]
    sold = normalized[normalized["action"] == "Sold"]
    lost = normalized[
        normalized["action"] == "Lost / Destroyed"
    ]

    purchase_cost = -float(bought["cash_effect"].sum())
    sales_revenue = float(sold["cash_effect"].sum())
    loss_value = -float(lost["cash_effect"].sum())

    bought_scu = float(bought["quantity_scu"].sum())
    sold_scu = float(sold["quantity_scu"].sum())
    lost_scu = float(lost["quantity_scu"].sum())

    return {
        "records": float(len(normalized)),
        "bought_records": float(len(bought)),
        "sold_records": float(len(sold)),
        "loss_records": float(len(lost)),
        "bought_scu": bought_scu,
        "sold_scu": sold_scu,
        "lost_scu": lost_scu,
        "on_hand_scu": bought_scu - sold_scu - lost_scu,
        "purchase_cost": purchase_cost,
        "sales_revenue": sales_revenue,
        "loss_value": loss_value,
        "net_cash_flow": float(normalized["cash_effect"].sum()),
    }


def build_commodity_inventory(
    trades: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate commodity inventory and money movement by commodity."""
    columns = [
        "Commodity",
        "Bought (SCU)",
        "Sold (SCU)",
        "Lost / Destroyed (SCU)",
        "On Hand (SCU)",
        "Purchase Cost (aUEC)",
        "Sales Revenue (aUEC)",
        "Recorded Loss Value (aUEC)",
        "Net Cash Flow (aUEC)",
    ]
    normalized = normalize_commodity_transactions(trades)
    if normalized.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []
    for commodity, group in normalized.groupby(
        "commodity_name",
        dropna=False,
    ):
        totals = commodity_summary_values(group)
        rows.append(
            {
                "Commodity": commodity,
                "Bought (SCU)": totals["bought_scu"],
                "Sold (SCU)": totals["sold_scu"],
                "Lost / Destroyed (SCU)": totals["lost_scu"],
                "On Hand (SCU)": totals["on_hand_scu"],
                "Purchase Cost (aUEC)": totals["purchase_cost"],
                "Sales Revenue (aUEC)": totals["sales_revenue"],
                "Recorded Loss Value (aUEC)": totals["loss_value"],
                "Net Cash Flow (aUEC)": totals["net_cash_flow"],
            }
        )

    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("Commodity")
        .reset_index(drop=True)
    )


def commodity_trade_tracker(
    commodity_names: list[str],
    selected_commodity: str,
    uex_prices: pd.DataFrame,
    default_quantity_scu: float,
) -> None:
    """Render the user's commodity buy, sell, inventory, and loss tracker."""
    st.markdown("### Commodity Buy, Sell, and Loss Tracker")
    st.caption(
        "Record purchases, sales, and destroyed or lost shipments. "
        "Every commodity page, dashboard graph, saved-record table, and "
        "export uses this same normalized ledger."
    )

    prefill_notice = st.session_state.pop(
        "commodity_prefill_notice",
        None,
    )
    if prefill_notice:
        st.success(prefill_notice)

    trades = load_commodity_transactions()
    totals = commodity_summary_values(trades)

    if not st.session_state.get("commodity_tracker_ready", False):
        st.warning(
            "The Commodity Tracker database connection is not ready. "
            "Run `schema_migration_v4_commodity_tracker.sql` in Supabase, "
            "then reload the app."
        )
        tracker_error = st.session_state.get(
            "commodity_tracker_error",
            "",
        )
        if tracker_error:
            with st.expander("Show database error details"):
                st.code(tracker_error)

    record_tab, inventory_tab, history_tab = st.tabs(
        ["Record Activity", "On-Hand Inventory", "Trade History"]
    )

    with record_tab:
        available_names = list(
            dict.fromkeys(
                [
                    name
                    for name in commodity_names
                    if str(name).strip()
                ]
            )
        )
        if not available_names:
            available_names = [selected_commodity or "Unknown Commodity"]

        if (
            "tracked_commodity_name" not in st.session_state
            or st.session_state["tracked_commodity_name"]
            not in available_names
        ):
            st.session_state["tracked_commodity_name"] = (
                selected_commodity
                if selected_commodity in available_names
                else available_names[0]
            )
        if "commodity_transaction_type" not in st.session_state:
            st.session_state["commodity_transaction_type"] = "Bought"
        if "commodity_shipment_lost" not in st.session_state:
            st.session_state["commodity_shipment_lost"] = False
        if "commodity_transaction_quantity" not in st.session_state:
            st.session_state["commodity_transaction_quantity"] = max(
                float(default_quantity_scu),
                0.01,
            )
        if "commodity_transaction_fees" not in st.session_state:
            st.session_state["commodity_transaction_fees"] = 0.0

        default_buy_price = 0.0
        default_sell_price = 0.0
        if not uex_prices.empty:
            buy_rows = uex_prices[
                pd.to_numeric(
                    uex_prices["Terminal Sells at"],
                    errors="coerce",
                ).fillna(0.0)
                > 0
            ]
            sell_rows = uex_prices[
                pd.to_numeric(
                    uex_prices["Terminal Buys at"],
                    errors="coerce",
                ).fillna(0.0)
                > 0
            ]
            if not buy_rows.empty:
                default_buy_price = float(
                    buy_rows["Terminal Sells at"].min()
                )
            if not sell_rows.empty:
                default_sell_price = float(
                    sell_rows["Terminal Buys at"].max()
                )

        if "commodity_transaction_unit_price" not in st.session_state:
            st.session_state["commodity_transaction_unit_price"] = (
                default_buy_price
            )

        with st.form("commodity_transaction_form"):
            form_col1, form_col2, form_col3 = st.columns(3)
            with form_col1:
                tracked_commodity = st.selectbox(
                    "Commodity",
                    available_names,
                    key="tracked_commodity_name",
                )
            with form_col2:
                transaction_type = st.selectbox(
                    "Activity",
                    ["Bought", "Sold"],
                    key="commodity_transaction_type",
                )
            with form_col3:
                shipment_lost = st.checkbox(
                    "Shipment destroyed or lost",
                    key="commodity_shipment_lost",
                    help=(
                        "Records cargo as Lost / Destroyed and removes it "
                        "from on-hand inventory."
                    ),
                )

            value_col1, value_col2, value_col3 = st.columns(3)
            with value_col1:
                quantity_scu = st.number_input(
                    "Quantity (SCU)",
                    min_value=0.01,
                    step=1.0,
                    format="%.2f",
                    key="commodity_transaction_quantity",
                )
            with value_col2:
                unit_price = st.number_input(
                    (
                        "Estimated cargo value per SCU"
                        if shipment_lost
                        else "Unit price (aUEC/SCU)"
                    ),
                    min_value=0.0,
                    step=100.0,
                    key="commodity_transaction_unit_price",
                )
            with value_col3:
                fees = st.number_input(
                    "Fees and operating costs (aUEC)",
                    min_value=0.0,
                    step=100.0,
                    key="commodity_transaction_fees",
                )

            location_col1, location_col2 = st.columns(2)
            with location_col1:
                origin = st.text_input(
                    "Purchase or departure location",
                    placeholder="Area18, Lorville, Pyro...",
                    key="commodity_transaction_origin",
                )
            with location_col2:
                destination = st.text_input(
                    "Sale or intended destination",
                    placeholder="New Babbage, station, outpost...",
                    key="commodity_transaction_destination",
                )

            shipment_reference = st.text_input(
                "Shipment name or reference",
                placeholder="Optional run name, ship, or cargo reference",
                key="commodity_shipment_reference",
            )
            transaction_notes = st.text_area(
                "Notes",
                placeholder=(
                    "Route notes, stock limits, loss reason, escort costs, "
                    "or other details"
                ),
                key="commodity_transaction_notes",
            )

            final_action = (
                "Lost / Destroyed"
                if shipment_lost
                else transaction_type
            )
            total_value = float(quantity_scu) * float(unit_price)
            if final_action == "Sold":
                cash_effect = total_value - float(fees)
            else:
                cash_effect = -(total_value + float(fees))

            st.info(
                f"Record type: {final_action}. Cargo value: "
                f"{total_value:,.0f} aUEC. Net cash effect: "
                f"{cash_effect:+,.0f} aUEC."
            )

            submitted = st.form_submit_button(
                (
                    "Record Destroyed / Lost Shipment"
                    if shipment_lost
                    else (
                        "Record Commodity Purchase"
                        if transaction_type == "Bought"
                        else "Record Commodity Sale"
                    )
                ),
                width="stretch",
            )

        if submitted:
            if not tracked_commodity.strip():
                st.error("Choose a commodity.")
            elif quantity_scu <= 0:
                st.error("Enter a quantity greater than zero.")
            elif unit_price <= 0:
                st.error("Enter the price or estimated cargo value per SCU.")
            else:
                payload = {
                    "user_id": st.session_state.user_id,
                    "commodity_name": tracked_commodity,
                    "action": final_action,
                    "quantity_scu": float(quantity_scu),
                    "unit_price": float(unit_price),
                    "fees": float(fees),
                    "total_value": float(total_value),
                    "origin": origin.strip(),
                    "destination": destination.strip(),
                    "shipment_reference": shipment_reference.strip(),
                    "notes": transaction_notes.strip(),
                }
                try:
                    insert_commodity_transaction(payload)
                    st.success(f"{final_action} activity recorded.")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "The activity could not be saved. Confirm the "
                        "commodity migration and Supabase permissions. "
                        f"Details: {exc}"
                    )

    with inventory_tab:
        inventory = build_commodity_inventory(trades)
        if inventory.empty:
            st.info("No commodity activity has been recorded yet.")
        else:
            render_commodity_metric_cards(
                [
                    {
                        "label": "Commodities Tracked",
                        "value": f"{len(inventory):,}",
                    },
                    {
                        "label": "Total On Hand",
                        "value": f"{totals['on_hand_scu']:,.2f} SCU",
                        "tone": (
                            "positive"
                            if totals["on_hand_scu"] > 0
                            else "negative"
                            if totals["on_hand_scu"] < 0
                            else ""
                        ),
                    },
                    {
                        "label": "Sales Revenue",
                        "value": f"{totals['sales_revenue']:,.0f} aUEC",
                        "tone": (
                            "positive"
                            if totals["sales_revenue"] > 0
                            else ""
                        ),
                    },
                    {
                        "label": "Recorded Cargo Loss",
                        "value": f"{totals['loss_value']:,.0f} aUEC",
                        "tone": (
                            "negative"
                            if totals["loss_value"] > 0
                            else ""
                        ),
                    },
                    {
                        "label": "Net Cash Flow",
                        "value": f"{totals['net_cash_flow']:+,.0f} aUEC",
                        "tone": (
                            "positive"
                            if totals["net_cash_flow"] > 0
                            else "negative"
                            if totals["net_cash_flow"] < 0
                            else ""
                        ),
                    },
                ]
            )

            st.dataframe(
                inventory,
                width="stretch",
                hide_index=True,
                column_config={
                    "Bought (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "Sold (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "Lost / Destroyed (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "On Hand (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "Purchase Cost (aUEC)": st.column_config.NumberColumn(
                        format="%,.0f aUEC"
                    ),
                    "Sales Revenue (aUEC)": st.column_config.NumberColumn(
                        format="%,.0f aUEC"
                    ),
                    "Recorded Loss Value (aUEC)": (
                        st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        )
                    ),
                    "Net Cash Flow (aUEC)": st.column_config.NumberColumn(
                        format="%,.0f aUEC"
                    ),
                },
            )
            st.download_button(
                "Download Commodity Inventory CSV",
                data=dataframe_csv_bytes(inventory),
                file_name="star_citizen_commodity_inventory.csv",
                mime="text/csv",
                width="stretch",
            )

    with history_tab:
        if trades.empty:
            st.info("No commodity activity has been recorded yet.")
        else:
            history = trades.rename(
                columns={
                    "date_saved": "Date",
                    "commodity_name": "Commodity",
                    "action": "Activity",
                    "quantity_scu": "Quantity (SCU)",
                    "unit_price": "Unit Price (aUEC/SCU)",
                    "fees": "Fees (aUEC)",
                    "total_value": "Cargo Value (aUEC)",
                    "cash_effect": "Net Cash Effect (aUEC)",
                    "origin": "Origin",
                    "destination": "Destination",
                    "shipment_reference": "Shipment Reference",
                    "notes": "Notes",
                }
            ).copy()
            display_columns = [
                "Date",
                "Commodity",
                "Activity",
                "Quantity (SCU)",
                "Unit Price (aUEC/SCU)",
                "Cargo Value (aUEC)",
                "Fees (aUEC)",
                "Net Cash Effect (aUEC)",
                "Origin",
                "Destination",
                "Shipment Reference",
                "Notes",
            ]
            st.dataframe(
                history[display_columns],
                width="stretch",
                hide_index=True,
                column_config={
                    "Quantity (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "Unit Price (aUEC/SCU)": (
                        st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        )
                    ),
                    "Cargo Value (aUEC)": st.column_config.NumberColumn(
                        format="%,.0f aUEC"
                    ),
                    "Fees (aUEC)": st.column_config.NumberColumn(
                        format="%,.0f aUEC"
                    ),
                    "Net Cash Effect (aUEC)": (
                        st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        )
                    ),
                },
            )

            download_col, delete_col = st.columns([2, 1])
            with download_col:
                st.download_button(
                    "Download Commodity Trade History CSV",
                    data=dataframe_csv_bytes(history[display_columns]),
                    file_name="star_citizen_commodity_trade_history.csv",
                    mime="text/csv",
                    width="stretch",
                )
            with delete_col:
                trade_options = {
                    int(row["id"]): (
                        f'ID {int(row["id"])} | '
                        f'{row["commodity_name"]} | {row["action"]} | '
                        f'{float(row["quantity_scu"]):,.2f} SCU'
                    )
                    for _, row in trades.iterrows()
                }
                selected_trade_id = st.selectbox(
                    "Select record",
                    options=list(trade_options),
                    format_func=lambda value: trade_options[value],
                    key="delete_commodity_trade_select",
                    label_visibility="collapsed",
                )
                confirm_delete = st.checkbox(
                    "Confirm deletion",
                    key="delete_commodity_trade_confirm",
                )
                if st.button(
                    "Delete Selected Record",
                    disabled=not confirm_delete,
                    type="primary",
                    key="delete_commodity_trade_button",
                    width="stretch",
                ):
                    try:
                        delete_record(
                            "commodity_transactions",
                            selected_trade_id,
                        )
                        st.success("Commodity record deleted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(
                            "The commodity record could not be deleted: "
                            f"{exc}"
                        )

    with st.expander("Commodity data health", expanded=False):
        action_counts = (
            trades["action"].value_counts().to_dict()
            if not trades.empty
            else {}
        )
        health_rows = pd.DataFrame(
            [
                ["Database connection", "Ready" if st.session_state.get(
                    "commodity_tracker_ready", False
                ) else "Not ready"],
                ["Loaded records", int(totals["records"])],
                ["Bought records", int(totals["bought_records"])],
                ["Sold records", int(totals["sold_records"])],
                ["Lost / destroyed records", int(totals["loss_records"])],
                ["Normalized actions", ", ".join(
                    f"{key}: {value}"
                    for key, value in action_counts.items()
                ) or "None"],
                ["Net cash flow", f"{totals['net_cash_flow']:+,.0f} aUEC"],
            ],
            columns=["Check", "Result"],
        )
        st.dataframe(
            health_rows,
            width="stretch",
            hide_index=True,
        )

def empty_blueprint_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "id",
            "user_id",
            "date_saved",
            "blueprint_name",
            "blueprint_category",
            "blueprint_status",
            "source_location",
            "copies_owned",
            "target_builds",
            "materials",
            "notes",
        ]
    )


def load_blueprints() -> pd.DataFrame:
    """Load the signed-in user's blueprint tracker records."""
    try:
        blueprints = fetch_table("blueprint_tracker")
        st.session_state.blueprint_tracker_ready = True
        st.session_state.pop("blueprint_tracker_error", None)
    except Exception as exc:
        st.session_state.blueprint_tracker_ready = False
        st.session_state.blueprint_tracker_error = str(exc)
        return empty_blueprint_frame()

    if not blueprints.empty and "date_saved" in blueprints.columns:
        blueprints["date_saved"] = pd.to_datetime(
            blueprints["date_saved"],
            errors="coerce",
            utc=True,
        ).dt.tz_convert(APP_TIMEZONE)

    return blueprints


def normalize_blueprint_materials(value: Any) -> dict[str, float]:
    """Return a clean resource-to-required-SCU mapping."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}

    if not isinstance(value, dict):
        return {}

    cleaned: dict[str, float] = {}
    for resource, quantity in value.items():
        resource_name = str(resource).strip()
        if not resource_name:
            continue
        try:
            numeric_quantity = float(quantity)
        except (TypeError, ValueError):
            continue
        if numeric_quantity > 0:
            cleaned[resource_name] = numeric_quantity
    return cleaned


def insert_blueprint(payload: dict[str, Any]) -> None:
    get_supabase().table("blueprint_tracker").insert(payload).execute()


def build_blueprint_readiness(
    blueprints: pd.DataFrame,
    ore_inventory: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare tracked blueprint requirements with current on-hand ore."""
    blueprint_columns = [
        "Blueprint",
        "Category",
        "Status",
        "Copies Owned",
        "Planned Builds",
        "Required Materials",
        "Readiness",
        "Missing Materials",
    ]
    material_columns = [
        "Material",
        "Required (SCU)",
        "On Hand (SCU)",
        "Shortage (SCU)",
        "Surplus (SCU)",
        "Coverage",
    ]

    if blueprints.empty:
        return (
            pd.DataFrame(columns=blueprint_columns),
            pd.DataFrame(columns=material_columns),
        )

    inventory_map: dict[str, float] = {}
    if not ore_inventory.empty:
        inventory_map = {
            str(row["Ore / Mineral"]): float(row["On Hand (SCU)"])
            for _, row in ore_inventory.iterrows()
        }

    combined_required: dict[str, float] = {}
    readiness_rows: list[dict[str, Any]] = []

    for _, row in blueprints.iterrows():
        materials = normalize_blueprint_materials(row.get("materials", {}))
        try:
            target_builds = max(1, int(row.get("target_builds", 1) or 1))
        except (TypeError, ValueError):
            target_builds = 1

        total_requirements = {
            material: quantity * target_builds
            for material, quantity in materials.items()
        }

        for material, quantity in total_requirements.items():
            combined_required[material] = (
                combined_required.get(material, 0.0) + quantity
            )

        missing: list[str] = []
        coverage_values: list[float] = []
        for material, required in total_requirements.items():
            on_hand = inventory_map.get(material, 0.0)
            shortage = max(required - on_hand, 0.0)
            if shortage > 0:
                missing.append(f"{material}: {shortage:,.2f} SCU")
            coverage_values.append(
                min(on_hand / required, 1.0) if required > 0 else 1.0
            )

        readiness_percent = (
            min(coverage_values) * 100 if coverage_values else 100.0
        )
        requirements_text = ", ".join(
            f"{material}: {quantity:,.2f} SCU"
            for material, quantity in total_requirements.items()
        ) or "No materials entered"

        readiness_rows.append(
            {
                "Blueprint": row.get("blueprint_name", ""),
                "Category": row.get("blueprint_category", ""),
                "Status": row.get("blueprint_status", "Owned"),
                "Copies Owned": int(row.get("copies_owned", 1) or 1),
                "Planned Builds": target_builds,
                "Required Materials": requirements_text,
                "Readiness": readiness_percent,
                "Missing Materials": "; ".join(missing) or "Ready",
            }
        )

    material_rows: list[dict[str, Any]] = []
    for material, required in sorted(combined_required.items()):
        on_hand = inventory_map.get(material, 0.0)
        shortage = max(required - on_hand, 0.0)
        surplus = max(on_hand - required, 0.0)
        coverage = min(on_hand / required, 1.0) * 100 if required > 0 else 100.0
        material_rows.append(
            {
                "Material": material,
                "Required (SCU)": required,
                "On Hand (SCU)": on_hand,
                "Shortage (SCU)": shortage,
                "Surplus (SCU)": surplus,
                "Coverage": coverage,
            }
        )

    return (
        pd.DataFrame(readiness_rows, columns=blueprint_columns),
        pd.DataFrame(material_rows, columns=material_columns),
    )


def format_money(value: float | int) -> str:
    return f"{float(value):,.0f} aUEC"


def build_ore_inventory(ores: pd.DataFrame) -> pd.DataFrame:
    """Calculate mined, bought, sold, and on-hand SCU by resource."""
    columns = [
        "Ore / Mineral",
        "Mined (SCU)",
        "Bought (SCU)",
        "Sold (SCU)",
        "On Hand (SCU)",
        "Sales Value",
        "Purchase Value",
    ]
    if ores.empty:
        return pd.DataFrame(columns=columns)

    working = ores.copy()
    working["quantity_scu"] = pd.to_numeric(
        working.get("quantity_scu", 0),
        errors="coerce",
    ).fillna(0.0)
    working["total_value"] = pd.to_numeric(
        working.get("total_value", 0),
        errors="coerce",
    ).fillna(0.0)

    quantity_pivot = working.pivot_table(
        index="ore_name",
        columns="action",
        values="quantity_scu",
        aggfunc="sum",
        fill_value=0.0,
    )

    for action in ("Mined", "Bought", "Sold"):
        if action not in quantity_pivot.columns:
            quantity_pivot[action] = 0.0

    inventory = quantity_pivot[["Mined", "Bought", "Sold"]].copy()
    inventory["On Hand"] = (
        inventory["Mined"] + inventory["Bought"] - inventory["Sold"]
    )

    value_pivot = working.pivot_table(
        index="ore_name",
        columns="action",
        values="total_value",
        aggfunc="sum",
        fill_value=0.0,
    )
    for action in ("Bought", "Sold"):
        if action not in value_pivot.columns:
            value_pivot[action] = 0.0

    inventory["Sales Value"] = value_pivot["Sold"]
    inventory["Purchase Value"] = value_pivot["Bought"]
    inventory = inventory.reset_index().rename(
        columns={
            "ore_name": "Ore / Mineral",
            "Mined": "Mined (SCU)",
            "Bought": "Bought (SCU)",
            "Sold": "Sold (SCU)",
            "On Hand": "On Hand (SCU)",
        }
    )
    return inventory[columns].sort_values("Ore / Mineral")


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
            "quantity_scu": "Quantity (SCU)",
            "total_value": "Value",
            "location": "Location",
            "notes": "Notes",
        }
    ).copy()

    quantity = pd.to_numeric(
        table.get("Quantity (SCU)", 0),
        errors="coerce",
    ).fillna(0.0)
    value = pd.to_numeric(table.get("Value", 0), errors="coerce").fillna(0.0)
    table["Unit Value"] = value.where(quantity <= 0, value / quantity)

    ordered_columns = [
        "ID",
        "Date",
        "Action",
        "Ore",
        "Quantity (SCU)",
        "Value",
        "Unit Value",
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
            "Quantity (SCU)": st.column_config.NumberColumn(format="%,.2f SCU"),
            "Value": st.column_config.NumberColumn(format="%,.0f aUEC"),
            "Unit Value": st.column_config.NumberColumn(format="%,.0f aUEC/SCU"),
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
                <div class="time-settings">⚙ Change timezone in My Profile → Preferences</div>
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

def analytics_heading(
    title: str,
    copy: str,
    kicker: str = "Performance Analytics",
) -> None:
    """Render a consistent analytics-card heading."""
    st.markdown(
        f"""
        <div class="analytics-heading">
            <div class="analytics-kicker">{html.escape(kicker)}</div>
            <div class="analytics-title">{html.escape(title)}</div>
            <div class="analytics-copy">{html.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_summary(
    cards: list[dict[str, str]],
) -> None:
    """Render the dashboard's responsive earnings summary strip."""
    rendered_cards: list[str] = []
    for card in cards:
        rendered_cards.append(
            '<div class="dashboard-summary-card '
            + html.escape(card.get("class", ""))
            + '">'
            + '<div class="dashboard-summary-icon">'
            + html.escape(card.get("icon", "•"))
            + "</div>"
            + '<div class="dashboard-summary-label">'
            + html.escape(card["label"])
            + "</div>"
            + '<div class="dashboard-summary-value">'
            + html.escape(card["value"])
            + "</div>"
            + '<div class="dashboard-summary-detail">'
            + html.escape(card.get("detail", ""))
            + "</div>"
            + "</div>"
        )

    st.markdown(
        '<div class="dashboard-summary-grid">'
        + "".join(rendered_cards)
        + "</div>",
        unsafe_allow_html=True,
    )


def dashboard_page() -> None:
    dashboard_hero()

    contracts, ores = load_data()
    commodity_trades = load_commodity_transactions()

    with st.container(border=True):
        filter_col1, filter_col2 = st.columns([1, 2])
        with filter_col1:
            date_range = st.selectbox(
                "Dashboard date range",
                ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
                key="dashboard_date_range",
            )
        with filter_col2:
            search_text = st.text_input(
                "Search dashboard records",
                placeholder="Contract, ore, commodity, type, location, or notes",
                key="dashboard_search",
            )

    contracts = filter_data(contracts, date_range, search_text)
    ores = filter_data(ores, date_range, search_text)
    commodity_trades = filter_data(
        commodity_trades,
        date_range,
        search_text,
    )

    contract_net = (
        float(contracts["net_payout"].sum())
        if not contracts.empty
        else 0.0
    )
    contract_take_home = (
        float(contracts["individual_share"].sum())
        if not contracts.empty
        else 0.0
    )

    ore_sales_rows = ores[ores["action"] == "Sold"] if not ores.empty else ores
    ore_purchase_rows = ores[ores["action"] == "Bought"] if not ores.empty else ores
    ore_sales = (
        float(ore_sales_rows["total_value"].sum())
        if not ore_sales_rows.empty
        else 0.0
    )
    ore_purchases = (
        float(ore_purchase_rows["total_value"].sum())
        if not ore_purchase_rows.empty
        else 0.0
    )
    ore_inventory = build_ore_inventory(ores)
    ore_on_hand_scu = (
        float(ore_inventory["On Hand (SCU)"].sum())
        if not ore_inventory.empty
        else 0.0
    )

    commodity_trades = normalize_commodity_transactions(
        commodity_trades
    )
    commodity_totals = commodity_summary_values(
        commodity_trades
    )
    commodity_sales_rows = commodity_trades[
        commodity_trades["action"] == "Sold"
    ]
    commodity_purchase_rows = commodity_trades[
        commodity_trades["action"] == "Bought"
    ]
    commodity_loss_rows = commodity_trades[
        commodity_trades["action"] == "Lost / Destroyed"
    ]

    commodity_sales = commodity_totals["sales_revenue"]
    commodity_spend = commodity_totals["purchase_cost"]
    commodity_losses = commodity_totals["loss_value"]
    commodity_net = commodity_totals["net_cash_flow"]
    commodity_on_hand_scu = commodity_totals["on_hand_scu"]

    total_recorded_earnings = (
        contract_take_home + ore_sales + commodity_sales
    )
    total_recorded_spend = ore_purchases + commodity_spend + commodity_losses
    overall_net_profit = total_recorded_earnings - total_recorded_spend

    st.markdown(
        """
        <div class="section-heading">
            <div class="section-title">Command overview</div>
            <div class="section-copy">
                Key operational totals from contracts, mining, and commodity trading.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_dashboard_metric_cards(
        [
            {
                "label": "Contracts Completed",
                "value": f"{len(contracts):,}",
                "detail": f"Contract net: {format_money(contract_net)}",
            },
            {
                "label": "Commodity Sales",
                "value": f"{len(commodity_sales_rows):,}",
                "detail": f"Lost shipments: {len(commodity_loss_rows):,}",
            },
            {
                "label": "Ore On Hand",
                "value": f"{ore_on_hand_scu:,.2f} SCU",
                "tone": "positive" if ore_on_hand_scu > 0 else "",
                "detail": "Mined + bought − sold",
            },
            {
                "label": "Commodity On Hand",
                "value": f"{commodity_on_hand_scu:,.2f} SCU",
                "tone": (
                    "positive"
                    if commodity_on_hand_scu > 0
                    else "negative"
                    if commodity_on_hand_scu < 0
                    else ""
                ),
                "detail": "Bought − sold − lost",
            },
            {
                "label": "Total Recorded Earnings",
                "value": format_money(total_recorded_earnings),
                "tone": "positive" if total_recorded_earnings > 0 else "",
                "detail": "Contracts + ore sales + commodity sales",
            },
            {
                "label": "Overall Net Profit",
                "value": format_money(overall_net_profit),
                "tone": (
                    "positive"
                    if overall_net_profit > 0
                    else "negative"
                    if overall_net_profit < 0
                    else ""
                ),
                "detail": "Recorded earnings minus recorded spend",
            },
        ]
    )

    feature_dashboard_cards()

    st.markdown(
        """
        <div class="section-heading">
            <div class="section-title">Integrated analytics</div>
            <div class="section-copy">
                Contracts, ore activity, and commodity trading in one operational picture.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Combined earnings over time
    earnings_parts: list[pd.DataFrame] = []

    if not contracts.empty:
        contract_events = contracts.dropna(subset=["date_saved"]).copy()
        if not contract_events.empty:
            contract_events["Day"] = contract_events["date_saved"].dt.floor("D")
            contract_events["Contract Earnings"] = pd.to_numeric(
                contract_events.get("individual_share", 0),
                errors="coerce",
            ).fillna(0.0)
            earnings_parts.append(
                contract_events[["Day", "Contract Earnings"]]
                .groupby("Day", as_index=False)
                .sum()
            )

    if not ore_sales_rows.empty:
        ore_events = ore_sales_rows.dropna(subset=["date_saved"]).copy()
        if not ore_events.empty:
            ore_events["Day"] = ore_events["date_saved"].dt.floor("D")
            ore_events["Ore Sales"] = pd.to_numeric(
                ore_events.get("total_value", 0),
                errors="coerce",
            ).fillna(0.0)
            earnings_parts.append(
                ore_events[["Day", "Ore Sales"]]
                .groupby("Day", as_index=False)
                .sum()
            )

    if not commodity_sales_rows.empty:
        commodity_events = commodity_sales_rows.dropna(
            subset=["date_saved"]
        ).copy()
        if not commodity_events.empty:
            commodity_events["Day"] = commodity_events["date_saved"].dt.floor("D")
            commodity_events["Commodity Sales"] = (
                pd.to_numeric(
                    commodity_events.get("total_value", 0),
                    errors="coerce",
                ).fillna(0.0)
                - pd.to_numeric(
                    commodity_events.get("fees", 0),
                    errors="coerce",
                ).fillna(0.0)
            )
            earnings_parts.append(
                commodity_events[["Day", "Commodity Sales"]]
                .groupby("Day", as_index=False)
                .sum()
            )

    if earnings_parts:
        earnings_daily = earnings_parts[0]
        for part in earnings_parts[1:]:
            earnings_daily = earnings_daily.merge(part, on="Day", how="outer")

        earning_columns = [
            "Contract Earnings",
            "Ore Sales",
            "Commodity Sales",
        ]
        for column in earning_columns:
            if column not in earnings_daily.columns:
                earnings_daily[column] = 0.0
        earnings_daily[earning_columns] = earnings_daily[
            earning_columns
        ].fillna(0.0)
        earnings_daily["Total Earnings"] = earnings_daily[
            earning_columns
        ].sum(axis=1)
        earnings_daily = earnings_daily.sort_values("Day").reset_index(drop=True)
        earnings_daily["Day Label"] = earnings_daily["Day"].dt.strftime(
            "%b %d, %Y"
        )
        earnings_daily["Position"] = list(range(len(earnings_daily)))
        earnings_daily["Plot Value"] = earnings_daily["Total Earnings"].abs()
        earnings_daily["Label"] = earnings_daily["Total Earnings"].map(
            lambda value: f"{value:,.0f} aUEC"
        )

        total_earnings_figure = go.Figure(
            go.Bar(
                x=earnings_daily["Position"],
                y=earnings_daily["Plot Value"],
                marker_color=[
                    "#22A66F" if value >= 0 else "#E54950"
                    for value in earnings_daily["Total Earnings"]
                ],
                text=earnings_daily["Label"],
                textposition="outside",
                cliponaxis=False,
                customdata=earnings_daily[
                    [
                        "Contract Earnings",
                        "Ore Sales",
                        "Commodity Sales",
                        "Total Earnings",
                    ]
                ].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[3]:,.0f} aUEC total</b><br>"
                    "Contracts: %{customdata[0]:,.0f} aUEC<br>"
                    "Ore sales: %{customdata[1]:,.0f} aUEC<br>"
                    "Commodity sales: %{customdata[2]:,.0f} aUEC"
                    "<extra></extra>"
                ),
            )
        )
        positions = earnings_daily["Position"].tolist()
        total_earnings_figure.update_xaxes(
            tickmode="array",
            tickvals=positions,
            ticktext=earnings_daily["Day Label"].tolist(),
            range=[-0.6, max(positions[-1] + 0.6, 0.6)],
            title_text="Day",
        )
        total_earnings_figure.update_yaxes(
            title_text="Earnings in aUEC",
            rangemode="tozero",
        )
        style_plotly_figure(total_earnings_figure, height=390)
        total_earnings_figure.update_layout(
            showlegend=False,
            margin={"l": 48, "r": 24, "t": 38, "b": 52},
        )
    else:
        total_earnings_figure = empty_dashboard_figure(
            "Save a contract, ore sale, or commodity sale to begin tracking combined earnings."
        )

    # Earnings and net contribution by source
    source_data = pd.DataFrame(
        {
            "Source": [
                "Contracts",
                "Ore / Mining",
                "Commodities",
            ],
            "Net Contribution": [
                contract_take_home,
                ore_sales - ore_purchases,
                commodity_net,
            ],
        }
    )
    source_data["Plot Value"] = source_data[
        "Net Contribution"
    ].abs()
    source_data["Label"] = source_data[
        "Net Contribution"
    ].map(lambda value: f"{value:+,.0f} aUEC")

    source_figure = px.bar(
        source_data,
        x="Plot Value",
        y="Source",
        orientation="h",
        text="Label",
        custom_data=["Net Contribution"],
        labels={
            "Plot Value": "Contribution magnitude in aUEC",
            "Source": "Source",
        },
    )
    source_figure.update_traces(
        marker_color=[
            "#22A66F" if value >= 0 else "#E54950"
            for value in source_data["Net Contribution"]
        ],
        textposition="inside",
        insidetextanchor="middle",
        textfont={"color": "#ffffff"},
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Net contribution: %{customdata[0]:+,.0f} aUEC"
            "<extra></extra>"
        ),
    )
    style_plotly_figure(source_figure, height=390)
    source_figure.update_layout(
        showlegend=False,
        margin={"l": 32, "r": 20, "t": 26, "b": 52},
    )
    # Ore value by mineral
    if not ores.empty:
        ore_value_data = (
            ores.groupby(["ore_name", "action"], as_index=False)
            .agg(
                total_value=("total_value", "sum"),
                entry_count=("id", "count"),
            )
        )
        top_ores = (
            ore_value_data.groupby("ore_name")["total_value"]
            .sum()
            .nlargest(6)
            .index
        )
        ore_value_data = ore_value_data[
            ore_value_data["ore_name"].isin(top_ores)
        ].copy()
        ore_value_data["Plot Value"] = ore_value_data["total_value"].abs()
        ore_value_data["Label"] = ore_value_data["total_value"].map(
            lambda value: f"{value:,.0f}"
        )

        ore_value_figure = px.bar(
            ore_value_data,
            x="ore_name",
            y="Plot Value",
            color="action",
            barmode="group",
            text="Label",
            custom_data=["total_value", "entry_count"],
            color_discrete_map={
                "Bought": "#176FC1",
                "Mined": "#70B7EC",
                "Sold": "#E54950",
            },
            labels={
                "ore_name": "Mineral",
                "Plot Value": "Value in aUEC",
                "action": "Activity",
            },
        )
        ore_value_figure.update_traces(
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "%{fullData.name}: %{customdata[0]:,.0f} aUEC<br>"
                "Records: %{customdata[1]}<extra></extra>"
            ),
        )
        style_plotly_figure(ore_value_figure, height=390)
        ore_value_figure.update_layout(
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "center",
                "x": .5,
                "title_text": "",
            },
            margin={"l": 48, "r": 20, "t": 58, "b": 52},
            uniformtext_minsize=9,
            uniformtext_mode="hide",
        )
    else:
        ore_value_figure = empty_dashboard_figure(
            "Mined, bought, and sold mineral values will appear here."
        )

    # Commodity profit by commodity
    if not commodity_trades.empty:
        commodity_rows: list[dict[str, object]] = []
        for commodity_name, group in commodity_trades.groupby(
            "commodity_name"
        ):
            bought = group[group["action"] == "Bought"]
            sold = group[group["action"] == "Sold"]
            lost = group[group["action"] == "Lost / Destroyed"]

            bought_cost = float((bought["total_value"] + bought["fees"]).sum())
            sold_revenue = float((sold["total_value"] - sold["fees"]).sum())
            lost_value = float((lost["total_value"] + lost["fees"]).sum())
            net_profit = sold_revenue - bought_cost - lost_value

            commodity_rows.append(
                {
                    "Commodity": commodity_name,
                    "Net Profit": net_profit,
                    "Sales": sold_revenue,
                    "Spend": bought_cost,
                    "Losses": lost_value,
                }
            )

        commodity_profit_data = (
            pd.DataFrame(commodity_rows)
            .sort_values("Net Profit", ascending=False)
            .head(8)
        )
        commodity_profit_data["Plot Value"] = commodity_profit_data[
            "Net Profit"
        ].abs()
        commodity_profit_data["Label"] = commodity_profit_data[
            "Net Profit"
        ].map(lambda value: f"{value:,.0f} aUEC")

        commodity_profit_figure = px.bar(
            commodity_profit_data,
            x="Commodity",
            y="Plot Value",
            text="Label",
            custom_data=["Net Profit", "Sales", "Spend", "Losses"],
        )
        commodity_profit_figure.update_traces(
            marker_color=[
                "#22A66F" if value >= 0 else "#E54950"
                for value in commodity_profit_data["Net Profit"]
            ],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Net profit: %{customdata[0]:,.0f} aUEC<br>"
                "Sales: %{customdata[1]:,.0f} aUEC<br>"
                "Spend: %{customdata[2]:,.0f} aUEC<br>"
                "Losses: %{customdata[3]:,.0f} aUEC<extra></extra>"
            ),
        )
        style_plotly_figure(commodity_profit_figure, height=390)
        commodity_profit_figure.update_layout(
            showlegend=False,
            margin={"l": 48, "r": 20, "t": 38, "b": 58},
        )
    else:
        commodity_profit_figure = empty_dashboard_figure(
            "Commodity profit will appear after purchases, sales, or losses are recorded."
        )

    # Contract earnings by type
    if not contracts.empty:
        contract_type_data = (
            contracts.groupby("contract_type", as_index=False)
            .agg(
                net_payout=("net_payout", "sum"),
                contract_count=("id", "count"),
            )
            .sort_values("net_payout", ascending=True)
            .tail(8)
        )
        contract_type_data["Plot Value"] = contract_type_data[
            "net_payout"
        ].abs()
        contract_type_data["Label"] = contract_type_data["net_payout"].map(
            lambda value: f"{value:,.0f} aUEC"
        )
        contract_type_figure = px.bar(
            contract_type_data,
            x="Plot Value",
            y="contract_type",
            orientation="h",
            text="Label",
            custom_data=["net_payout", "contract_count"],
            labels={
                "Plot Value": "Payout magnitude in aUEC",
                "contract_type": "Contract type",
            },
        )
        contract_type_figure.update_traces(
            marker_color=[
                "#22A66F" if value >= 0 else "#E54950"
                for value in contract_type_data["net_payout"]
            ],
            textposition="inside",
            insidetextanchor="middle",
            textfont={"color": "#ffffff"},
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Net payout: %{customdata[0]:,.0f} aUEC<br>"
                "Contracts: %{customdata[1]}<extra></extra>"
            ),
        )
        style_plotly_figure(contract_type_figure, height=390)
        contract_type_figure.update_layout(
            showlegend=False,
            margin={"l": 48, "r": 20, "t": 38, "b": 52},
        )
    else:
        contract_type_figure = empty_dashboard_figure(
            "Contract categories will appear after your first mission."
        )

    # Activity mix by record count
    activity_data = pd.DataFrame(
        {
            "Activity": ["Contracts", "Ore / Mining", "Commodities"],
            "Records": [len(contracts), len(ores), len(commodity_trades)],
        }
    )
    if activity_data["Records"].sum() > 0:
        activity_mix_figure = px.pie(
            activity_data,
            names="Activity",
            values="Records",
            hole=.55,
            color="Activity",
            color_discrete_map={
                "Contracts": "#22A66F",
                "Ore / Mining": "#347FD1",
                "Commodities": "#F28A2A",
            },
        )
        activity_mix_figure.update_traces(
            texttemplate="%{percent:.1%}",
            textposition="inside",
            marker={"line": {"color": "#ffffff", "width": 3}},
            sort=False,
            hovertemplate=(
                "<b>%{label}</b><br>"
                "%{value:,.0f} records<br>%{percent}<extra></extra>"
            ),
        )
        activity_mix_figure.add_annotation(
            text=(
                f"<b>{int(activity_data['Records'].sum()):,}</b><br>"
                "<span style='font-size:10px'>Total Records</span>"
            ),
            x=.5,
            y=.5,
            showarrow=False,
            font={"size": 14, "color": "#0D2D49"},
        )
        style_plotly_figure(activity_mix_figure, height=390)
        activity_mix_figure.update_layout(
            legend={
                "orientation": "v",
                "yanchor": "middle",
                "y": .5,
                "xanchor": "left",
                "x": 1.02,
                "title_text": "",
            },
            margin={"l": 10, "r": 135, "t": 20, "b": 20},
        )
    else:
        activity_mix_figure = empty_dashboard_figure(
            "Activity distribution will appear after records are saved.",
            donut=True,
        )

    top_col1, top_col2, top_col3 = st.columns(3, gap="medium")
    with top_col1:
        with st.container(border=True):
            analytics_heading(
                "Total earnings over time",
                "Combined earnings from contracts, ore sales, and commodity sales.",
                "Combined Performance",
            )
            st.plotly_chart(
                total_earnings_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

    with top_col2:
        with st.container(border=True):
            analytics_heading(
                "Net contribution by source",
                "Contracts, ore trading, and commodities remain visible even when a source is negative.",
                "Income & Cost Mix",
            )
            st.plotly_chart(
                source_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

    with top_col3:
        with st.container(border=True):
            analytics_heading(
                "Ore value by mineral",
                "Compare mined, purchased, and sold mineral value.",
                "Mining Performance",
            )
            st.plotly_chart(
                ore_value_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

    bottom_col1, bottom_col2, bottom_col3 = st.columns(3, gap="medium")
    with bottom_col1:
        with st.container(border=True):
            analytics_heading(
                "Commodity trade profit",
                "Net commodity profit after purchases, fees, and shipment losses.",
                "Trade Performance",
            )
            st.plotly_chart(
                commodity_profit_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

    with bottom_col2:
        with st.container(border=True):
            analytics_heading(
                "Contract earnings by type",
                "Contract categories ranked by total net payout.",
                "Mission Performance",
            )
            st.plotly_chart(
                contract_type_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

    with bottom_col3:
        with st.container(border=True):
            analytics_heading(
                "Activity mix",
                "Share of saved records across contracts, ore, and commodities.",
                "Operational Mix",
            )
            st.plotly_chart(
                activity_mix_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

    st.markdown(
        """
        <div class="section-heading">
            <div class="section-title">Earnings summary</div>
            <div class="section-copy">
                Income, spending, inventory, and profitability totals for the selected period.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_dashboard_summary(
        [
            {
                "icon": "◉",
                "label": "Total Earnings",
                "value": format_money(total_recorded_earnings),
                "detail": "All recorded income",
                "class": "green",
            },
            {
                "icon": "▤",
                "label": "Contract Take-Home",
                "value": format_money(contract_take_home),
                "detail": f"{len(contracts):,} contracts",
                "class": "blue",
            },
            {
                "icon": "◆",
                "label": "Ore Sales",
                "value": format_money(ore_sales),
                "detail": f"{ore_on_hand_scu:,.2f} SCU on hand",
                "class": "blue",
            },
            {
                "icon": "⬡",
                "label": "Commodity Sales",
                "value": format_money(commodity_sales),
                "detail": f"{commodity_on_hand_scu:,.2f} SCU on hand",
                "class": "orange",
            },
            {
                "icon": "↗",
                "label": "Commodity Net",
                "value": format_money(commodity_net),
                "detail": "Sales − purchases − losses",
                "class": "green" if commodity_net >= 0 else "red",
            },
            {
                "icon": "▣",
                "label": "Total Spend",
                "value": format_money(total_recorded_spend),
                "detail": "Ore and commodity purchases",
                "class": "purple",
            },
            {
                "icon": "⚖",
                "label": "Net Profit",
                "value": format_money(overall_net_profit),
                "detail": "Earnings after recorded spend",
                "class": "green" if overall_net_profit >= 0 else "red",
            },
        ]
    )

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

    st.markdown("### Add Ore or Gem Activity")
    with st.form("ore_form", clear_on_submit=True):
        action = st.selectbox("Entry type", ["Mined", "Bought", "Sold"])
        selected_ore = st.selectbox("Ore or mineral", ORE_TYPES)
        custom_ore = ""
        if selected_ore == "Other / Custom":
            custom_ore = st.text_input("Custom ore or mineral")

        amount_col1, amount_col2 = st.columns(2)
        with amount_col1:
            quantity_scu = st.number_input(
                "Quantity (SCU)",
                min_value=0.0,
                step=0.1,
                format="%.2f",
                help=(
                    "Enter the amount mined, bought, or sold. On-hand inventory "
                    "is calculated as mined plus bought minus sold."
                ),
            )
        with amount_col2:
            total_value = st.number_input(
                "Total value (aUEC)",
                min_value=0.0,
                step=1000.0,
                help=(
                    "For Sold entries, enter the sale proceeds. For Bought entries, "
                    "enter the purchase cost. Mined entries may use an estimated value."
                ),
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
        elif quantity_scu <= 0 and total_value <= 0:
            st.error("Enter a quantity, a value, or both.")
        else:
            payload = {
                "user_id": st.session_state.user_id,
                "action": action,
                "ore_name": ore_name,
                "quantity_scu": quantity_scu,
                "total_value": total_value,
                "location": location.strip(),
                "notes": notes.strip(),
            }

            try:
                insert_ore(payload)
                st.success(
                    f"{action} entry saved: {ore_name} | "
                    f"{quantity_scu:,.2f} SCU | {format_money(total_value)}"
                )
                st.rerun()
            except Exception as exc:
                error_text = str(exc)
                if "quantity_scu" in error_text:
                    st.error(
                        "The quantity column is not installed yet. Run "
                        "schema_migration_v2.sql in Supabase, then try again."
                    )
                else:
                    st.error(f"The ore entry could not be saved: {exc}")

    _, ores = load_data()
    inventory = build_ore_inventory(ores)

    st.markdown("### On-Hand Ore and Gem Inventory")
    if inventory.empty:
        st.info("Add mined, bought, or sold quantities to begin tracking on-hand inventory.")
    else:
        total_on_hand = float(inventory["On Hand (SCU)"].sum())
        total_sales = float(inventory["Sales Value"].sum())
        total_purchases = float(inventory["Purchase Value"].sum())
        inv_col1, inv_col2, inv_col3 = st.columns(3)
        inv_col1.metric("Total On Hand", f"{total_on_hand:,.2f} SCU")
        inv_col2.metric("Recorded Sales", format_money(total_sales))
        inv_col3.metric("Trade Net", format_money(total_sales - total_purchases))

        st.dataframe(
            inventory,
            width="stretch",
            hide_index=True,
            column_config={
                "Mined (SCU)": st.column_config.NumberColumn(format="%,.2f SCU"),
                "Bought (SCU)": st.column_config.NumberColumn(format="%,.2f SCU"),
                "Sold (SCU)": st.column_config.NumberColumn(format="%,.2f SCU"),
                "On Hand (SCU)": st.column_config.NumberColumn(format="%,.2f SCU"),
                "Sales Value": st.column_config.NumberColumn(format="%,.0f aUEC"),
                "Purchase Value": st.column_config.NumberColumn(format="%,.0f aUEC"),
            },
        )

    st.markdown("### Recent Ore Activity")
    display_ore_table(ores)


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
        "quantity_scu": "Quantity (SCU)",
        "total_value": "Total Value (aUEC)",
        "location": "Location",
        "notes": "Notes",
    }
    export = ores.rename(columns=columns).copy()
    ordered = [
        "Date",
        "Action",
        "Ore / Mineral",
        "Quantity (SCU)",
        "Total Value (aUEC)",
        "Location",
        "Notes",
    ]
    export = export[[column for column in ordered if column in export.columns]]
    if "Date" in export.columns:
        export["Date"] = pd.to_datetime(export["Date"], errors="coerce")
        if getattr(export["Date"].dt, "tz", None) is not None:
            export["Date"] = export["Date"].dt.tz_localize(None)
    return export


def prepare_commodity_export(
    commodity_trades: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare normalized commodity records for Excel, CSV, and Sheets."""
    trades = normalize_commodity_transactions(
        commodity_trades
    )
    columns = {
        "date_saved": "Date",
        "commodity_name": "Commodity",
        "action": "Activity",
        "quantity_scu": "Quantity (SCU)",
        "unit_price": "Unit Price (aUEC/SCU)",
        "total_value": "Cargo Value (aUEC)",
        "fees": "Fees (aUEC)",
        "cash_effect": "Net Cash Effect (aUEC)",
        "origin": "Origin",
        "destination": "Destination",
        "shipment_reference": "Shipment Reference",
        "notes": "Notes",
    }
    export = trades.rename(columns=columns).copy()
    ordered = [
        "Date",
        "Commodity",
        "Activity",
        "Quantity (SCU)",
        "Unit Price (aUEC/SCU)",
        "Cargo Value (aUEC)",
        "Fees (aUEC)",
        "Net Cash Effect (aUEC)",
        "Origin",
        "Destination",
        "Shipment Reference",
        "Notes",
    ]
    export = export[
        [column for column in ordered if column in export.columns]
    ]
    if "Date" in export.columns:
        export["Date"] = pd.to_datetime(
            export["Date"],
            errors="coerce",
        )
        if getattr(export["Date"].dt, "tz", None) is not None:
            export["Date"] = export["Date"].dt.tz_localize(None)
    return export


def set_export_column_widths(worksheet: Any, frame: pd.DataFrame) -> None:
    for column_index, column_name in enumerate(frame.columns):
        values = frame[column_name].fillna("").astype(str)
        maximum = max([len(str(column_name)), *values.map(len).tolist()])
        worksheet.set_column(column_index, column_index, min(maximum + 2, 42))


def export_summary_values(
    contracts: pd.DataFrame,
    ores: pd.DataFrame,
    commodity_trades: pd.DataFrame,
) -> list[list[Any]]:
    """Return export-summary rows shared by Excel, CSV, and Google Sheets."""
    gross_payout = (
        float(contracts["total_payout"].sum())
        if not contracts.empty and "total_payout" in contracts.columns
        else 0.0
    )
    contract_take_home = (
        float(contracts["individual_share"].sum())
        if not contracts.empty and "individual_share" in contracts.columns
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
    inventory = build_ore_inventory(ores)
    on_hand = (
        float(inventory["On Hand (SCU)"].sum())
        if not inventory.empty
        else 0.0
    )
    commodity_totals = commodity_summary_values(
        commodity_trades
    )
    total_earnings = (
        contract_take_home
        + ore_sales
        + commodity_totals["sales_revenue"]
    )

    return [
        ["Metric", "Value"],
        ["Account", st.session_state.get("user_email", "")],
        ["Generated", datetime.now().strftime("%Y-%m-%d %I:%M %p")],
        ["Contract Records", len(contracts)],
        ["Gross Contract Payout", gross_payout],
        ["Contract Take-Home", contract_take_home],
        ["Ore Ledger Entries", len(ores)],
        ["Ore Sales", ore_sales],
        ["Ore Purchases", ore_purchases],
        ["Ore Trade Net", ore_sales - ore_purchases],
        ["Ore On Hand (SCU)", on_hand],
        ["Commodity Records", int(commodity_totals["records"])],
        ["Commodity Purchases", commodity_totals["purchase_cost"]],
        ["Commodity Sales", commodity_totals["sales_revenue"]],
        ["Commodity Losses", commodity_totals["loss_value"]],
        ["Commodity Net Cash Flow", commodity_totals["net_cash_flow"]],
        ["Commodity On Hand (SCU)", commodity_totals["on_hand_scu"]],
        ["Total Earnings", total_earnings],
    ]


def build_excel_export(
    contracts: pd.DataFrame,
    ores: pd.DataFrame,
    commodity_trades: pd.DataFrame,
) -> bytes:
    """Create a verified multi-sheet workbook for Excel and Google Sheets."""
    contract_export = prepare_contract_export(contracts)
    ore_export = prepare_ore_export(ores)
    inventory_export = build_ore_inventory(ores)
    commodity_export = prepare_commodity_export(
        commodity_trades
    )
    commodity_inventory_export = build_commodity_inventory(
        commodity_trades
    )
    summary_rows = export_summary_values(
        contracts,
        ores,
        commodity_trades,
    )

    output = BytesIO()
    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
        datetime_format="yyyy-mm-dd hh:mm AM/PM",
    ) as writer:
        workbook = writer.book
        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 20,
                "font_color": "#FFFFFF",
                "bg_color": "#10233F",
                "align": "left",
                "valign": "vcenter",
            }
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#1378E5",
                "border": 1,
                "border_color": "#8FC7FF",
                "align": "center",
                "valign": "vcenter",
            }
        )
        label_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#243A55",
                "bg_color": "#EAF4FF",
                "border": 1,
                "border_color": "#D1E3F5",
            }
        )
        value_format = workbook.add_format(
            {
                "font_color": "#10233F",
                "bg_color": "#FFFFFF",
                "border": 1,
                "border_color": "#D1E3F5",
            }
        )
        money_format = workbook.add_format({"num_format": '#,##0 "aUEC"'})
        quantity_format = workbook.add_format({"num_format": '0.00 "SCU"'})
        date_format = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm AM/PM"})

        summary = workbook.add_worksheet("Summary")
        writer.sheets["Summary"] = summary
        summary.set_tab_color("#1378E5")
        summary.set_column("A:A", 28)
        summary.set_column("B:B", 26)
        summary.set_row(0, 34)
        summary.merge_range("A1:F1", "STAR CITIZEN TRACKER EXPORT", title_format)
        summary.write_row("A3", summary_rows[0], header_format)
        for row_index, row in enumerate(summary_rows[1:], start=3):
            summary.write(row_index, 0, row[0], label_format)
            value = row[1]
            if row[0] in {
                "Gross Contract Payout",
                "Contract Take-Home",
                "Ore Sales",
                "Ore Purchases",
                "Ore Trade Net",
                "Commodity Purchases",
                "Commodity Sales",
                "Commodity Losses",
                "Commodity Net Cash Flow",
                "Total Earnings",
            }:
                summary.write_number(row_index, 1, float(value), money_format)
            elif row[0] in {
                "Ore On Hand (SCU)",
                "Commodity On Hand (SCU)",
            }:
                summary.write_number(row_index, 1, float(value), quantity_format)
            elif isinstance(value, (int, float)):
                summary.write_number(row_index, 1, float(value), value_format)
            else:
                summary.write(row_index, 1, value, value_format)

        sheet_specs = [
            ("Contracts", contract_export, {
                "Date": date_format,
                "Total Payout": money_format,
                "Expenses": money_format,
                "Net Payout": money_format,
                "Individual Share": money_format,
            }),
            ("Ore Ledger", ore_export, {
                "Date": date_format,
                "Quantity (SCU)": quantity_format,
                "Total Value (aUEC)": money_format,
            }),
            ("Ore Inventory", inventory_export, {
                "Mined (SCU)": quantity_format,
                "Bought (SCU)": quantity_format,
                "Sold (SCU)": quantity_format,
                "On Hand (SCU)": quantity_format,
                "Sales Value": money_format,
                "Purchase Value": money_format,
            }),
            ("Commodity Ledger", commodity_export, {
                "Date": date_format,
                "Quantity (SCU)": quantity_format,
                "Unit Price (aUEC/SCU)": money_format,
                "Cargo Value (aUEC)": money_format,
                "Fees (aUEC)": money_format,
                "Net Cash Effect (aUEC)": money_format,
            }),
            ("Commodity Inventory", commodity_inventory_export, {
                "Bought (SCU)": quantity_format,
                "Sold (SCU)": quantity_format,
                "Lost / Destroyed (SCU)": quantity_format,
                "On Hand (SCU)": quantity_format,
                "Purchase Cost (aUEC)": money_format,
                "Sales Revenue (aUEC)": money_format,
                "Recorded Loss Value (aUEC)": money_format,
                "Net Cash Flow (aUEC)": money_format,
            }),
        ]

        table_names = {
            "Contracts": "ContractsTable",
            "Ore Ledger": "OreLedgerTable",
            "Ore Inventory": "OreInventoryTable",
            "Commodity Ledger": "CommodityLedgerTable",
            "Commodity Inventory": "CommodityInventoryTable",
        }

        for sheet_name, frame, formats in sheet_specs:
            frame.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            worksheet.set_row(0, 24)
            set_export_column_widths(worksheet, frame)
            for column_index, column_name in enumerate(frame.columns):
                worksheet.write(0, column_index, column_name, header_format)
                if column_name in formats:
                    width = 22 if column_name == "Date" else 18
                    worksheet.set_column(
                        column_index,
                        column_index,
                        width,
                        formats[column_name],
                    )
            if len(frame) and len(frame.columns):
                worksheet.add_table(
                    0,
                    0,
                    len(frame),
                    len(frame.columns) - 1,
                    {
                        "name": table_names[sheet_name],
                        "style": "Table Style Medium 2",
                        "columns": [
                            {"header": column} for column in frame.columns
                        ],
                    },
                )
            elif len(frame.columns):
                worksheet.autofilter(0, 0, 0, len(frame.columns) - 1)

    return output.getvalue()


def dataframe_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Return an Excel-friendly UTF-8 CSV."""
    export = frame.copy()
    for column in export.columns:
        if pd.api.types.is_datetime64_any_dtype(export[column]):
            export[column] = export[column].astype(str)
    return export.to_csv(index=False).encode("utf-8-sig")


def build_csv_export_zip(
    contracts: pd.DataFrame,
    ores: pd.DataFrame,
    commodity_trades: pd.DataFrame,
) -> bytes:
    """Create a ZIP with every export table as a separate CSV."""
    contract_export = prepare_contract_export(contracts)
    ore_export = prepare_ore_export(ores)
    inventory_export = build_ore_inventory(ores)
    commodity_export = prepare_commodity_export(
        commodity_trades
    )
    commodity_inventory_export = build_commodity_inventory(
        commodity_trades
    )
    summary_export = pd.DataFrame(
        export_summary_values(
            contracts,
            ores,
            commodity_trades,
        )[1:],
        columns=["Metric", "Value"],
    )

    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Summary.csv", dataframe_csv_bytes(summary_export))
        archive.writestr("Contracts.csv", dataframe_csv_bytes(contract_export))
        archive.writestr("Ore Ledger.csv", dataframe_csv_bytes(ore_export))
        archive.writestr(
            "Ore Inventory.csv",
            dataframe_csv_bytes(inventory_export),
        )
        archive.writestr(
            "Commodity Ledger.csv",
            dataframe_csv_bytes(commodity_export),
        )
        archive.writestr(
            "Commodity Inventory.csv",
            dataframe_csv_bytes(commodity_inventory_export),
        )
    return output.getvalue()


def google_service_account_config() -> dict[str, Any] | None:
    """Read optional Google service-account JSON from Streamlit Secrets."""
    try:
        raw = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    except KeyError:
        return None

    if isinstance(raw, dict):
        return dict(raw)
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return None


def create_filled_google_sheet(
    contracts: pd.DataFrame,
    ores: pd.DataFrame,
    commodity_trades: pd.DataFrame,
) -> str:
    """Create and share a populated Google Sheet when credentials are configured."""
    credentials = google_service_account_config()
    if not credentials:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not configured in Streamlit Secrets."
        )

    import gspread

    client = gspread.service_account_from_dict(credentials)
    title = f"Star Citizen Tracker {datetime.now().strftime('%Y-%m-%d %H%M')}"
    spreadsheet = client.create(title)

    summary_frame = pd.DataFrame(
        export_summary_values(
            contracts,
            ores,
            commodity_trades,
        )[1:],
        columns=["Metric", "Value"],
    )
    frames = {
        "Summary": summary_frame,
        "Contracts": prepare_contract_export(contracts),
        "Ore Ledger": prepare_ore_export(ores),
        "Ore Inventory": build_ore_inventory(ores),
        "Commodity Ledger": prepare_commodity_export(
            commodity_trades
        ),
        "Commodity Inventory": build_commodity_inventory(
            commodity_trades
        ),
    }

    first_sheet = spreadsheet.sheet1
    first_sheet.update_title("Summary")

    for index, (sheet_name, frame) in enumerate(frames.items()):
        worksheet = (
            first_sheet
            if index == 0
            else spreadsheet.add_worksheet(
                title=sheet_name,
                rows=max(len(frame) + 20, 100),
                cols=max(len(frame.columns) + 5, 20),
            )
        )
        safe_frame = frame.copy().fillna("")
        for column in safe_frame.columns:
            safe_frame[column] = safe_frame[column].map(
                lambda value: (
                    value.isoformat(sep=" ")
                    if isinstance(value, (datetime, pd.Timestamp))
                    else value
                )
            )
        values = [safe_frame.columns.tolist(), *safe_frame.values.tolist()]
        worksheet.update(range_name="A1", values=values)
        worksheet.freeze(rows=1)
        worksheet.format(
            "1:1",
            {
                "backgroundColor": {"red": 0.075, "green": 0.47, "blue": 0.90},
                "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
            },
        )

    user_email = st.session_state.get("user_email", "")
    if user_email and "@" in user_email:
        spreadsheet.share(
            user_email,
            perm_type="user",
            role="writer",
            notify=False,
        )

    return spreadsheet.url


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


def display_commodity_table(
    commodity_trades: pd.DataFrame,
) -> None:
    """Display normalized commodity records and their signed cash effect."""
    commodity_trades = normalize_commodity_transactions(
        commodity_trades
    )
    if commodity_trades.empty:
        st.info(
            "No commodity records have been saved yet. Add one under "
            "Commodities → My Trade Tracker."
        )
        return

    display = commodity_trades.rename(
        columns={
            "id": "ID",
            "date_saved": "Date",
            "commodity_name": "Commodity",
            "action": "Activity",
            "quantity_scu": "Quantity (SCU)",
            "unit_price": "Unit Price",
            "fees": "Fees",
            "total_value": "Cargo Value",
            "cash_effect": "Net Cash Effect",
            "origin": "Origin",
            "destination": "Destination",
            "shipment_reference": "Shipment Reference",
            "notes": "Notes",
        }
    ).copy()

    display_columns = [
        "ID",
        "Date",
        "Commodity",
        "Activity",
        "Quantity (SCU)",
        "Unit Price",
        "Cargo Value",
        "Fees",
        "Net Cash Effect",
        "Origin",
        "Destination",
        "Shipment Reference",
        "Notes",
    ]

    st.dataframe(
        display[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(
                format="%d",
                width="small",
            ),
            "Date": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD hh:mm A",
                width="medium",
            ),
            "Commodity": st.column_config.TextColumn(
                width="medium",
            ),
            "Activity": st.column_config.TextColumn(
                width="medium",
            ),
            "Quantity (SCU)": st.column_config.NumberColumn(
                format="%,.2f SCU",
                width="small",
            ),
            "Unit Price": st.column_config.NumberColumn(
                format="%,.0f aUEC/SCU",
                width="small",
            ),
            "Cargo Value": st.column_config.NumberColumn(
                format="%,.0f aUEC",
                width="small",
            ),
            "Fees": st.column_config.NumberColumn(
                format="%,.0f aUEC",
                width="small",
            ),
            "Net Cash Effect": st.column_config.NumberColumn(
                format="%,.0f aUEC",
                width="small",
            ),
            "Origin": st.column_config.TextColumn(width="large"),
            "Destination": st.column_config.TextColumn(width="large"),
            "Shipment Reference": st.column_config.TextColumn(
                width="medium",
            ),
            "Notes": st.column_config.TextColumn(width="large"),
        },
    )

    st.download_button(
        "Download Commodity Records CSV",
        data=dataframe_csv_bytes(display[display_columns]),
        file_name="star_citizen_commodity_records.csv",
        mime="text/csv",
        width="stretch",
    )

def saved_records_page() -> None:
    page_banner(
        "records_banner.jpg",
        "Saved Records",
        (
            "Search, review, edit, and delete your complete contract, ore, "
            "and commodity transaction history from one command page."
        ),
        "Records Archive",
    )

    contracts, ores = load_data()
    commodity_trades = load_commodity_transactions()

    view_tab, manage_tab = st.tabs(
        ["View Records", "Manage Records"]
    )

    with view_tab:
        contract_tab, ore_tab, commodity_tab = st.tabs(
            ["Contracts", "Ore Ledger", "Commodities"]
        )

        with contract_tab:
            display_contract_table(contracts)

        with ore_tab:
            display_ore_table(ores)

        with commodity_tab:
            display_commodity_table(commodity_trades)

    with manage_tab:
        st.markdown("### Edit or Delete Records")
        st.caption(
            "Select a saved contract, ore entry, or commodity transaction. "
            "Update the values you need or permanently remove duplicate and "
            "outdated entries."
        )
        manage_records_section(
            contracts,
            ores,
            commodity_trades,
        )


def manage_records_section(
    contracts: pd.DataFrame,
    ores: pd.DataFrame,
    commodity_trades: pd.DataFrame,
) -> None:
    record_type = st.radio(
        "Record type",
        ["Contract", "Ore Entry", "Commodity Entry"],
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
        record = contracts.loc[
            contracts["id"] == selected_id
        ].iloc[0]

        with st.form("edit_contract_form"):
            name = st.text_input(
                "Contract name",
                value=record["contract_name"],
            )
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
            if (
                not name.strip()
                or not type_value.strip()
                or payout <= 0
            ):
                st.error(
                    "Contract name, contract type, and a positive payout "
                    "are required."
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
                    update_record(
                        "contracts",
                        selected_id,
                        payload,
                    )
                    st.success("Contract updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        f"The contract could not be updated: {exc}"
                    )

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
                st.error(
                    f"The contract could not be deleted: {exc}"
                )

    elif record_type == "Ore Entry":
        if ores.empty:
            st.info("No ore entries are available to edit.")
            return

        ore_options = {
            int(row["id"]): (
                f'ID {int(row["id"])} | {row["action"]} | '
                f'{row["ore_name"]} | '
                f'{float(row.get("quantity_scu", 0) or 0):,.2f} SCU | '
                f'{format_money(row["total_value"])}'
            )
            for _, row in ores.iterrows()
        }
        selected_id = st.selectbox(
            "Select ore entry",
            options=list(ore_options),
            format_func=lambda value: ore_options[value],
            key="manage_ore_select",
        )
        record = ores.loc[
            ores["id"] == selected_id
        ].iloc[0]

        with st.form("edit_ore_form"):
            actions = ["Mined", "Bought", "Sold"]
            current_action = str(record["action"])
            if current_action not in actions:
                actions.append(current_action)

            action = st.selectbox(
                "Entry type",
                actions,
                index=actions.index(current_action),
            )
            ore_name = st.text_input(
                "Ore or mineral",
                value=record["ore_name"],
            )
            edit_amount_col1, edit_amount_col2 = st.columns(2)
            with edit_amount_col1:
                quantity_scu = st.number_input(
                    "Quantity (SCU)",
                    min_value=0.0,
                    value=float(
                        record.get("quantity_scu", 0) or 0
                    ),
                    step=0.1,
                    format="%.2f",
                )
            with edit_amount_col2:
                value = st.number_input(
                    "Total value (aUEC)",
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
            if not ore_name.strip():
                st.error("Ore name is required.")
            elif quantity_scu <= 0 and value <= 0:
                st.error("Enter a quantity, a value, or both.")
            else:
                payload = {
                    "action": action,
                    "ore_name": ore_name.strip(),
                    "quantity_scu": quantity_scu,
                    "total_value": value,
                    "location": location.strip(),
                    "notes": notes.strip(),
                }
                try:
                    update_record(
                        "ore_transactions",
                        selected_id,
                        payload,
                    )
                    st.success("Ore entry updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        f"The ore entry could not be updated: {exc}"
                    )

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
                delete_record(
                    "ore_transactions",
                    selected_id,
                )
                st.success("Ore entry deleted.")
                st.rerun()
            except Exception as exc:
                st.error(
                    f"The ore entry could not be deleted: {exc}"
                )

    else:
        if commodity_trades.empty:
            st.info(
                "No commodity entries are available to edit."
            )
            return

        commodity_options = {
            int(row["id"]): (
                f'ID {int(row["id"])} | '
                f'{row["action"]} | '
                f'{row["commodity_name"]} | '
                f'{float(row.get("quantity_scu", 0) or 0):,.2f} SCU | '
                f'{format_money(row.get("total_value", 0))}'
            )
            for _, row in commodity_trades.iterrows()
        }

        selected_id = st.selectbox(
            "Select commodity entry",
            options=list(commodity_options),
            format_func=lambda value: commodity_options[value],
            key="manage_commodity_select",
        )
        record = commodity_trades.loc[
            commodity_trades["id"] == selected_id
        ].iloc[0]

        with st.form("edit_commodity_form"):
            actions = [
                "Bought",
                "Sold",
                "Lost / Destroyed",
            ]
            current_action = str(
                record.get("action", "Bought")
            )
            if current_action not in actions:
                actions.append(current_action)

            activity = st.selectbox(
                "Activity",
                actions,
                index=actions.index(current_action),
            )
            commodity_name = st.text_input(
                "Commodity",
                value=str(
                    record.get("commodity_name", "") or ""
                ),
            )

            amount_col1, amount_col2, amount_col3 = (
                st.columns(3)
            )
            with amount_col1:
                quantity_scu = st.number_input(
                    "Quantity (SCU)",
                    min_value=0.01,
                    value=max(
                        float(
                            record.get("quantity_scu", 0)
                            or 0
                        ),
                        0.01,
                    ),
                    step=1.0,
                    format="%.2f",
                )
            with amount_col2:
                unit_price = st.number_input(
                    "Unit price (aUEC/SCU)",
                    min_value=0.0,
                    value=float(
                        record.get("unit_price", 0) or 0
                    ),
                    step=100.0,
                )
            with amount_col3:
                fees = st.number_input(
                    "Fees and operating costs",
                    min_value=0.0,
                    value=float(
                        record.get("fees", 0) or 0
                    ),
                    step=100.0,
                )

            location_col1, location_col2 = st.columns(2)
            with location_col1:
                origin = st.text_input(
                    "Origin",
                    value=str(
                        record.get("origin", "") or ""
                    ),
                )
            with location_col2:
                destination = st.text_input(
                    "Destination",
                    value=str(
                        record.get("destination", "") or ""
                    ),
                )

            shipment_reference = st.text_input(
                "Shipment reference",
                value=str(
                    record.get(
                        "shipment_reference",
                        "",
                    )
                    or ""
                ),
            )
            notes = st.text_area(
                "Notes",
                value=str(record.get("notes", "") or ""),
            )
            update_submitted = st.form_submit_button(
                "Update Commodity Entry",
                width="stretch",
            )

        if update_submitted:
            if not commodity_name.strip():
                st.error("Commodity name is required.")
            else:
                total_value = (
                    float(quantity_scu)
                    * float(unit_price)
                )
                payload = {
                    "commodity_name": commodity_name.strip(),
                    "action": activity,
                    "quantity_scu": float(quantity_scu),
                    "unit_price": float(unit_price),
                    "fees": float(fees),
                    "total_value": float(total_value),
                    "origin": origin.strip(),
                    "destination": destination.strip(),
                    "shipment_reference": (
                        shipment_reference.strip()
                    ),
                    "notes": notes.strip(),
                }
                try:
                    update_record(
                        "commodity_transactions",
                        selected_id,
                        payload,
                    )
                    st.success(
                        "Commodity entry updated."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "The commodity entry could not be "
                        f"updated: {exc}"
                    )

        confirm = st.checkbox(
            (
                "I understand this permanently deletes "
                "the selected commodity entry."
            ),
            key="delete_commodity_record_confirm",
        )
        if st.button(
            "Delete Commodity Entry",
            type="primary",
            disabled=not confirm,
            width="stretch",
            key="delete_commodity_record_button",
        ):
            try:
                delete_record(
                    "commodity_transactions",
                    selected_id,
                )
                st.success(
                    "Commodity entry deleted."
                )
                st.rerun()
            except Exception as exc:
                st.error(
                    "The commodity entry could not be "
                    f"deleted: {exc}"
                )

def render_dashboard_metric_cards(
    cards: list[dict[str, str]],
) -> None:
    """Render responsive dashboard metrics without truncating values."""
    card_html: list[str] = []

    for card in cards:
        tone = card.get("tone", "")
        tone_class = (
            tone if tone in {"positive", "negative"} else ""
        )
        detail = card.get("detail", "")
        detail_html = (
            '<div class="dashboard-metric-detail">'
            + html.escape(detail)
            + "</div>"
            if detail
            else ""
        )
        card_html.append(
            '<div class="dashboard-metric-card">'
            '<div class="dashboard-metric-label">'
            + html.escape(card["label"])
            + "</div>"
            '<div class="dashboard-metric-value '
            + tone_class
            + '">'
            + html.escape(card["value"])
            + "</div>"
            + detail_html
            + "</div>"
        )

    st.markdown(
        '<div class="dashboard-metric-grid">'
        + "".join(card_html)
        + "</div>",
        unsafe_allow_html=True,
    )


def prefill_commodity_tracker_from_terminal(
    *,
    signature: str,
    commodity_name: str,
    action: str,
    quantity_scu: float,
    unit_price: float,
    origin: str = "",
    destination: str = "",
) -> None:
    """Copy a selected market terminal into the private trade tracker form."""
    if st.session_state.get("_commodity_terminal_prefill_signature") == signature:
        return

    st.session_state["_commodity_terminal_prefill_signature"] = signature
    st.session_state["tracked_commodity_name"] = commodity_name
    st.session_state["commodity_transaction_type"] = action
    st.session_state["commodity_shipment_lost"] = False
    st.session_state["commodity_transaction_quantity"] = max(
        float(quantity_scu),
        0.01,
    )
    st.session_state["commodity_transaction_unit_price"] = max(
        float(unit_price),
        0.0,
    )

    if origin:
        st.session_state["commodity_transaction_origin"] = origin
    if destination:
        st.session_state["commodity_transaction_destination"] = destination

    terminal = origin or destination or "the selected terminal"
    st.session_state["commodity_prefill_notice"] = (
        f"{commodity_name} {action.lower()} entry prefilled from {terminal}. "
        "Open My Trade Tracker, review the quantity and costs, then save it."
    )


def render_commodity_metric_cards(
    cards: list[dict[str, str]],
) -> None:
    """Render readable commodity metrics without Markdown code-block parsing."""
    card_html: list[str] = []

    for card in cards:
        tone = card.get("tone", "")
        tone_class = (
            tone if tone in {"positive", "negative"} else ""
        )
        detail = card.get("detail", "")
        detail_html = (
            '<div class="commodity-metric-detail">'
            + html.escape(detail)
            + "</div>"
            if detail
            else ""
        )

        card_html.append(
            '<div class="commodity-metric-card">'
            '<div class="commodity-metric-label">'
            + html.escape(card["label"])
            + "</div>"
            '<div class="commodity-metric-value '
            + tone_class
            + '">'
            + html.escape(card["value"])
            + "</div>"
            + detail_html
            + "</div>"
        )

    metric_markup = (
        '<div class="commodity-metric-grid">'
        + "".join(card_html)
        + "</div>"
    )
    st.markdown(metric_markup, unsafe_allow_html=True)


def optional_secret(name: str) -> str:
    """Read an optional Streamlit secret without interrupting the app."""
    try:
        return str(st.secrets[name]).strip()
    except (KeyError, FileNotFoundError):
        return ""


def parse_uex_ids(value: Any) -> list[int]:
    """Convert UEX comma-separated ID fields into integer lists."""
    if value is None or value == "":
        return []

    if isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = str(value).split(",")

    parsed: list[int] = []
    for raw_value in raw_values:
        try:
            parsed.append(int(str(raw_value).strip()))
        except (TypeError, ValueError):
            continue
    return parsed


def uex_flag(value: Any) -> bool:
    """Interpret UEX integer and string flag fields."""
    return str(value).strip().lower() in {"1", "true", "yes"}


def unix_timestamp_label(value: Any) -> str:
    """Format a UEX Unix timestamp for display."""
    try:
        return datetime.fromtimestamp(
            int(value),
            tz=ZoneInfo("UTC"),
        ).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


@st.cache_data(ttl=UEX_CACHE_SECONDS, show_spinner=False)
def fetch_uex_resource(resource: str) -> list[dict[str, Any]]:
    """Fetch one UEX API resource and return its data array."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "Star-Citizen-Tracker/1.0",
    }

    token = optional_secret("UEX_API_TOKEN")
    client_version = optional_secret("UEX_CLIENT_VERSION")

    if token:
        # UEX documents Bearer authentication globally and a secret-key
        # header for some user endpoints. Sending both keeps this compatible
        # with either configuration while public endpoints remain usable.
        headers["Authorization"] = f"Bearer {token}"
        headers["secret-key"] = token

    if client_version:
        headers["X-Client-Version"] = client_version

    url = f"{UEX_API_BASE}/{resource}"
    response = requests.get(url, headers=headers, timeout=25)

    # Public location endpoints do not require authorization. If a rotated or
    # restricted token is rejected, retry the public request without it.
    if response.status_code in {401, 403} and token:
        public_headers = {
            "Accept": "application/json",
            "User-Agent": "Star-Citizen-Tracker/1.0",
        }
        response = requests.get(url, headers=public_headers, timeout=25)

    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected UEX response for {resource}.")

    status = payload.get("status")
    if status not in {None, "ok"}:
        message = payload.get("message") or status
        raise RuntimeError(f"UEX returned {message} for {resource}.")

    data = payload.get("data", [])
    if isinstance(data, dict):
        return list(data.values())
    if not isinstance(data, list):
        raise RuntimeError(f"UEX returned an invalid data array for {resource}.")
    return data


def indexed_uex_rows(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Index UEX records by integer ID."""
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        try:
            indexed[int(row["id"])] = row
        except (KeyError, TypeError, ValueError):
            continue
    return indexed


def enrich_uex_spawn_rates(
    live_rows: pd.DataFrame,
    local_rows: pd.DataFrame,
) -> pd.DataFrame:
    """Add locally maintained spawn-rate notes to matching live UEX rows."""
    if live_rows.empty or local_rows.empty:
        return live_rows

    local = local_rows.copy()
    local["_resource"] = local["Resource"].astype(str).str.casefold()
    local["_system"] = local["System"].astype(str).str.casefold()
    local["_location"] = local["Location"].astype(str).str.casefold()

    def find_spawn_rate(row: pd.Series) -> str:
        resource = str(row["Resource"]).casefold()
        system = str(row["System"]).casefold()
        location = str(row["Location"]).casefold()

        matches = local[
            (local["_resource"] == resource)
            & (local["_system"] == system)
        ]

        exact = matches[
            matches["_location"].apply(
                lambda candidate: candidate in location or location in candidate
            )
        ]
        if not exact.empty:
            return str(exact.iloc[0]["Spawn Rate"])

        system_rates = (
            matches["Spawn Rate"]
            .dropna()
            .astype(str)
            .loc[lambda values: values.str.strip().ne("")]
        )
        if not system_rates.empty:
            return f"{system_rates.mode().iloc[0]} (community estimate)"

        resource_rates = (
            local.loc[local["_resource"] == resource, "Spawn Rate"]
            .dropna()
            .astype(str)
            .loc[lambda values: values.str.strip().ne("")]
        )
        if not resource_rates.empty:
            return f"{resource_rates.mode().iloc[0]} (resource estimate)"

        return "UEX location confirmed; exact rate unavailable"

    live_rows["Spawn Rate"] = live_rows.apply(find_spawn_rate, axis=1)
    return live_rows


@st.cache_data(ttl=UEX_CACHE_SECONDS, show_spinner=False)
def fetch_live_uex_mining_locations() -> tuple[pd.DataFrame, str]:
    """Build a live mining-location table from UEX commodity relationships."""
    commodities = fetch_uex_resource("commodities")
    star_systems = indexed_uex_rows(fetch_uex_resource("star_systems"))
    planets = indexed_uex_rows(fetch_uex_resource("planets"))
    moons = indexed_uex_rows(fetch_uex_resource("moons"))
    orbits = indexed_uex_rows(fetch_uex_resource("orbits"))
    points_of_interest = indexed_uex_rows(fetch_uex_resource("poi"))

    local_reference = load_mining_locations_local()
    output_rows: list[dict[str, Any]] = []

    def append_location(
        commodity: dict[str, Any],
        category: str,
        location_record: dict[str, Any],
        site_type: str,
    ) -> None:
        name = (
            location_record.get("name")
            or location_record.get("nickname")
            or "Unknown location"
        )
        system_name = (
            location_record.get("star_system_name")
            or star_systems.get(
                int(location_record.get("id_star_system") or 0),
                {},
            ).get("name")
            or "Unknown"
        )
        method = "Hand / ROC" if category == "Gem" else "Ship"
        price_sell = commodity.get("price_sell")
        price_note = ""
        try:
            if float(price_sell) > 0:
                price_note = f" UEX average sell value: {float(price_sell):,.0f} aUEC/SCU."
        except (TypeError, ValueError):
            pass

        output_rows.append(
            {
                "Resource": commodity.get("name", "Unknown"),
                "Category": category,
                "System": system_name,
                "Location": name,
                "Site Type": site_type,
                "Spawn Rate": "Not published by UEX",
                "Mining Method": method,
                "Notes": (
                    "Live UEX resource-to-location mapping."
                    f"{price_note}"
                ).strip(),
                "Source": "UEX API",
                "UEX Updated": unix_timestamp_label(
                    commodity.get("date_modified")
                ),
            }
        )

    for commodity in commodities:
        if not any(
            uex_flag(commodity.get(flag))
            for flag in ("is_extractable", "is_mineral", "is_harvestable")
        ):
            continue

        if commodity.get("is_available_live") is not None and not uex_flag(
            commodity.get("is_available_live")
        ):
            continue

        if commodity.get("is_visible") is not None and not uex_flag(
            commodity.get("is_visible")
        ):
            continue

        category = (
            "Gem"
            if uex_flag(commodity.get("is_harvestable"))
            else "Ore"
        )

        before_count = len(output_rows)

        for location_id in parse_uex_ids(commodity.get("ids_planets")):
            if location_id in planets:
                append_location(
                    commodity,
                    category,
                    planets[location_id],
                    "Planet",
                )

        for location_id in parse_uex_ids(commodity.get("ids_moons")):
            if location_id in moons:
                append_location(
                    commodity,
                    category,
                    moons[location_id],
                    "Moon",
                )

        for location_id in parse_uex_ids(commodity.get("ids_orbits")):
            if location_id in orbits:
                orbit = orbits[location_id]
                site_type = (
                    "Lagrange / Asteroid"
                    if uex_flag(orbit.get("is_lagrange"))
                    or uex_flag(orbit.get("is_asteroid"))
                    else "Orbit"
                )
                append_location(
                    commodity,
                    category,
                    orbit,
                    site_type,
                )

        for location_id in parse_uex_ids(commodity.get("ids_poi")):
            if location_id in points_of_interest:
                poi = points_of_interest[location_id]
                site_type = (
                    "Mining POI"
                    if uex_flag(poi.get("is_mining_related"))
                    else "Point of Interest"
                )
                append_location(
                    commodity,
                    category,
                    poi,
                    site_type,
                )

        # Use system-only rows when UEX does not provide a more precise body.
        if len(output_rows) == before_count:
            for location_id in parse_uex_ids(
                commodity.get("ids_star_systems")
            ):
                if location_id in star_systems:
                    append_location(
                        commodity,
                        category,
                        star_systems[location_id],
                        "System",
                    )

    live = pd.DataFrame(output_rows)
    if live.empty:
        raise RuntimeError("UEX returned no extractable mineral locations.")

    live = live.drop_duplicates(
        subset=["Resource", "Category", "System", "Location", "Site Type"]
    )
    live = enrich_uex_spawn_rates(live, local_reference)

    fetched_at = datetime.now(ZoneInfo("UTC")).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    return live, fetched_at


def load_mining_locations_local() -> pd.DataFrame:
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
                "Source",
                "UEX Updated",
            ]
        )

    local = pd.read_csv(MINING_LOCATIONS_FILE)
    local["Source"] = "Packaged reference"
    local["UEX Updated"] = ""
    return local


def load_mining_locations() -> pd.DataFrame:
    """Load live UEX mining locations with a packaged fallback."""
    try:
        live, fetched_at = fetch_live_uex_mining_locations()
        st.session_state.uex_mining_status = {
            "is_live": True,
            "message": f"Live UEX data loaded at {fetched_at}.",
        }
        return live
    except Exception as exc:
        st.session_state.uex_mining_status = {
            "is_live": False,
            "message": (
                "UEX could not be reached, so the packaged reference is "
                f"being used. Details: {exc}"
            ),
        }
        return load_mining_locations_local()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a mixed API value into a finite float."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if pd.isna(numeric):
        return default
    return numeric


def unix_datetime_label(value: Any) -> str:
    """Format an API Unix timestamp with date and time."""
    try:
        return datetime.fromtimestamp(
            int(value),
            tz=ZoneInfo("UTC"),
        ).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OSError):
        return ""


def uex_trade_location(row: dict[str, Any] | pd.Series) -> str:
    """Build a readable UEX terminal location path."""
    parts = [
        row.get("star_system_name"),
        row.get("planet_name"),
        row.get("orbit_name"),
        row.get("moon_name"),
        row.get("space_station_name"),
        row.get("city_name"),
        row.get("outpost_name"),
        row.get("terminal_name"),
    ]
    cleaned: list[str] = []
    for part in parts:
        value = str(part or "").strip()
        if value and value not in cleaned:
            cleaned.append(value)
    return " > ".join(cleaned) or "Unknown terminal"


def uex_trade_environment(row: dict[str, Any] | pd.Series) -> str:
    """Classify a trade terminal as ground or space based."""
    if row.get("space_station_name") or row.get("orbit_name"):
        return "Space"
    if row.get("planet_name") or row.get("moon_name"):
        return "Ground"
    return "Other"


@st.cache_data(ttl=SC_TRADE_TOOLS_CACHE_SECONDS, show_spinner=False)
def fetch_sc_trade_tools_resource(
    path: str,
    *,
    token_required: bool = False,
) -> Any:
    """Fetch one SC Trade Tools API resource."""
    token = optional_secret("SC_TRADE_TOOLS_TOKEN")
    if token_required and not token:
        raise RuntimeError(
            "SC_TRADE_TOOLS_TOKEN is not configured in Streamlit Secrets."
        )

    headers = {
        "Accept": "application/json",
        "User-Agent": "Star-Citizen-Tracker/1.0",
    }
    if token:
        headers["token"] = token

    url = f"{SC_TRADE_TOOLS_API_BASE}/{path.lstrip('/')}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=UEX_CACHE_SECONDS, show_spinner=False)
def fetch_uex_commodity_prices(commodity_id: int) -> list[dict[str, Any]]:
    return fetch_uex_resource(
        f"commodities_prices?id_commodity={int(commodity_id)}"
    )


@st.cache_data(ttl=UEX_CACHE_SECONDS, show_spinner=False)
def fetch_uex_commodity_routes(
    commodity_id: int,
    investment: int,
) -> list[dict[str, Any]]:
    resource = f"commodities_routes?id_commodity={int(commodity_id)}"
    if investment > 0:
        resource += f"&investment={int(investment)}"
    return fetch_uex_resource(resource)


@st.cache_data(ttl=SC_TRADE_TOOLS_CACHE_SECONDS, show_spinner=False)
def fetch_sc_trade_tools_transactions(
    commodity_name: str,
) -> list[dict[str, Any]]:
    encoded_name = quote(commodity_name, safe="")
    payload = fetch_sc_trade_tools_resource(
        f"commodity/items/{encoded_name}/transactions",
        token_required=True,
    )
    return payload if isinstance(payload, list) else []


@st.cache_data(ttl=SC_TRADE_TOOLS_CACHE_SECONDS, show_spinner=False)
def fetch_sc_trade_tools_reports() -> list[dict[str, Any]]:
    payload = fetch_sc_trade_tools_resource(
        "commodity/reports",
        token_required=True,
    )
    return payload if isinstance(payload, list) else []


def normalize_uex_prices(rows: list[dict[str, Any]]) -> pd.DataFrame:
    output: list[dict[str, Any]] = []
    for row in rows:
        terminal_buys = safe_float(row.get("price_buy"))
        terminal_sells = safe_float(row.get("price_sell"))

        area_parts = [
            row.get("planet_name"),
            row.get("moon_name"),
            row.get("orbit_name"),
            row.get("space_station_name"),
            row.get("city_name"),
            row.get("outpost_name"),
        ]
        area_values: list[str] = []
        for part in area_parts:
            value = str(part or "").strip()
            if value and value not in area_values:
                area_values.append(value)
        area = " > ".join(area_values) or "System location"

        output.append(
            {
                "System": row.get("star_system_name") or "Unknown",
                "Environment": uex_trade_environment(row),
                "Area": area,
                "Location": uex_trade_location(row),
                "Terminal": row.get("terminal_name") or "Unknown",
                "Terminal Buys at": terminal_buys,
                "Terminal Sells at": terminal_sells,
                "Demand (SCU)": safe_float(row.get("scu_buy")),
                "Stock (SCU)": safe_float(row.get("scu_sell_stock")),
                "Forecast Demand (SCU)": safe_float(row.get("scu_sell")),
                "User Buy Avg": safe_float(row.get("price_buy_users")),
                "User Sell Avg": safe_float(row.get("price_sell_users")),
                "Weekly Buy Avg": safe_float(row.get("price_buy_avg_week")),
                "Weekly Sell Avg": safe_float(row.get("price_sell_avg_week")),
                "Monthly Buy Avg": safe_float(row.get("price_buy_avg_month")),
                "Monthly Sell Avg": safe_float(row.get("price_sell_avg_month")),
                "Buy Volatility": safe_float(row.get("volatility_price_buy")),
                "Sell Volatility": safe_float(row.get("volatility_price_sell")),
                "Quality": safe_float(row.get("quality")),
                "Container Sizes": str(row.get("container_sizes") or ""),
                "Game Version": str(row.get("game_version") or ""),
                "Last Updated": unix_datetime_label(row.get("date_modified")),
                "Terminal ID": int(row.get("id_terminal") or 0),
                "Commodity ID": int(row.get("id_commodity") or 0),
            }
        )
    return pd.DataFrame(output)


def normalize_uex_routes(rows: list[dict[str, Any]]) -> pd.DataFrame:
    output: list[dict[str, Any]] = []
    for row in rows:
        origin_parts = [
            row.get("origin_star_system_name"),
            row.get("origin_planet_name"),
            row.get("origin_orbit_name"),
            row.get("origin_terminal_name"),
        ]
        destination_parts = [
            row.get("destination_star_system_name"),
            row.get("destination_planet_name"),
            row.get("destination_orbit_name"),
            row.get("destination_terminal_name"),
        ]
        origin = " > ".join(
            dict.fromkeys(
                str(value).strip()
                for value in origin_parts
                if str(value or "").strip()
            )
        )
        destination = " > ".join(
            dict.fromkeys(
                str(value).strip()
                for value in destination_parts
                if str(value or "").strip()
            )
        )
        output.append(
            {
                "Commodity": row.get("commodity_name") or "Unknown",
                "Origin": origin or "Unknown",
                "Destination": destination or "Unknown",
                "Buy Price / SCU": safe_float(row.get("price_origin")),
                "Sell Price / SCU": safe_float(row.get("price_destination")),
                "Margin / SCU": safe_float(row.get("price_margin")),
                "ROI": safe_float(row.get("price_roi")),
                "Investment": safe_float(row.get("investment")),
                "Expected Profit": safe_float(row.get("profit")),
                "Distance (GM)": safe_float(row.get("distance")),
                "Score": safe_float(row.get("score")),
                "Origin Stock (SCU)": safe_float(row.get("scu_origin")),
                "Destination Demand (SCU)": safe_float(
                    row.get("scu_destination")
                ),
                "Origin Volatility": safe_float(
                    row.get("volatility_origin")
                ),
                "Destination Volatility": safe_float(
                    row.get("volatility_destination")
                ),
                "Origin Containers": str(
                    row.get("container_sizes_origin") or ""
                ),
                "Destination Containers": str(
                    row.get("container_sizes_destination") or ""
                ),
                "Origin Environment": (
                    "Space"
                    if uex_flag(row.get("is_space_station_origin"))
                    else "Ground"
                    if uex_flag(row.get("is_on_ground_origin"))
                    else "Other"
                ),
                "Destination Environment": (
                    "Space"
                    if uex_flag(row.get("is_space_station_destination"))
                    else "Ground"
                    if uex_flag(row.get("is_on_ground_destination"))
                    else "Other"
                ),
                "Origin Monitored": bool(
                    uex_flag(row.get("is_monitored_origin"))
                ),
                "Destination Monitored": bool(
                    uex_flag(row.get("is_monitored_destination"))
                ),
                "Origin Freight Elevator": bool(
                    uex_flag(row.get("has_freight_elevator_origin"))
                ),
                "Destination Freight Elevator": bool(
                    uex_flag(row.get("has_freight_elevator_destination"))
                ),
                "Origin Loading Dock": bool(
                    uex_flag(row.get("has_loading_dock_origin"))
                ),
                "Destination Loading Dock": bool(
                    uex_flag(row.get("has_loading_dock_destination"))
                ),
                "Origin Refuel": bool(
                    uex_flag(row.get("has_refuel_origin"))
                ),
                "Destination Refuel": bool(
                    uex_flag(row.get("has_refuel_destination"))
                ),
                "UEX Route Code": str(row.get("code") or ""),
            }
        )
    return pd.DataFrame(output)


def normalize_sc_transactions(rows: list[dict[str, Any]]) -> pd.DataFrame:
    output: list[dict[str, Any]] = []
    for row in rows:
        output.append(
            {
                "Location": row.get("location") or "Unknown",
                "Shop": row.get("shop") or "Unknown",
                "Action": str(row.get("action") or "").upper(),
                "Commodity": row.get("itemName") or "",
                "Price / SCU": safe_float(row.get("price")),
                "Fees": safe_float(row.get("fees")),
                "Quantity (SCU)": safe_float(row.get("quantityInScu")),
                "Max Quantity (SCU)": safe_float(
                    row.get("maxQuantityInScu")
                ),
                "Requested Quantity (SCU)": safe_float(
                    row.get("itemQuantityInScu")
                ),
                "Security Level": row.get("securityLevel"),
                "Faction": row.get("faction") or "",
                "Box Sizes": ", ".join(
                    str(value) for value in row.get("boxSizesInScu", [])
                ),
                "Hidden Location": bool(row.get("isHidden")),
            }
        )
    return pd.DataFrame(output)


def normalize_sc_reports(rows: list[dict[str, Any]]) -> pd.DataFrame:
    report_rows: dict[str, dict[str, Any]] = {}
    for series in rows:
        metric = str(series.get("name") or "Metric").strip()
        for point in series.get("series", []) or []:
            commodity = str(point.get("name") or "").strip()
            if not commodity:
                continue
            report_rows.setdefault(
                commodity,
                {"Commodity": commodity},
            )[metric] = safe_float(point.get("value"))
    return pd.DataFrame(report_rows.values())


def commodity_catalog() -> tuple[list[str], dict[str, dict[str, Any]], dict[str, Any]]:
    """Build a union commodity catalog from UEX and SC Trade Tools."""
    uex_rows: list[dict[str, Any]] = []
    sc_rows: list[dict[str, Any]] = []
    errors: dict[str, Any] = {}

    try:
        uex_rows = fetch_uex_resource("commodities")
    except Exception as exc:
        errors["UEX"] = str(exc)

    try:
        payload = fetch_sc_trade_tools_resource("commodity/items")
        sc_rows = payload if isinstance(payload, list) else []
    except Exception as exc:
        errors["SC Trade Tools"] = str(exc)

    uex_map: dict[str, dict[str, Any]] = {}
    for row in uex_rows:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        if row.get("is_visible") is not None and not uex_flag(
            row.get("is_visible")
        ):
            continue
        if row.get("is_available_live") is not None and not uex_flag(
            row.get("is_available_live")
        ):
            continue
        uex_map[name.casefold()] = row

    names = {
        str(row.get("name") or "").strip()
        for row in uex_rows
        if str(row.get("name") or "").strip()
    }
    names.update(
        str(row.get("name") or "").strip()
        for row in sc_rows
        if str(row.get("name") or "").strip()
    )

    return sorted(names, key=str.casefold), uex_map, errors


def selected_sc_report(
    reports: pd.DataFrame,
    commodity_name: str,
) -> pd.DataFrame:
    if reports.empty or "Commodity" not in reports.columns:
        return pd.DataFrame()
    return reports[
        reports["Commodity"].astype(str).str.casefold()
        == commodity_name.casefold()
    ]


@st.fragment(run_every="15m")
def commodities_page() -> None:
    page_banner(
        "records_banner.jpg",
        "Commodity Trading",
        "Compare market prices, cargo availability, demand, route profitability, risk, and cross-source trade intelligence.",
        "Trade Operations",
    )

    checked_at = datetime.now(ZoneInfo(selected_timezone())).strftime(
        "%b %d, %Y at %I:%M %p %Z"
    )
    status_col, link_col1, link_col2 = st.columns([1.5, 1, 1])
    with status_col:
        st.info(
            "Auto-refresh: every 15 minutes while this page remains open. "
            f"Last checked {checked_at}."
        )
    with link_col1:
        st.link_button(
            "Open UEX Trade Routes",
            "https://uexcorp.space/trade/routes",
            width="stretch",
        )
    with link_col2:
        st.link_button(
            "Open SC Trade Tools",
            "https://sc-trade.tools/trade-routes",
            width="stretch",
        )

    names, uex_map, catalog_errors = commodity_catalog()
    sc_token_available = bool(optional_secret("SC_TRADE_TOOLS_TOKEN"))

    st.markdown(
        f"""
        <div class="commodity-source-grid">
            <div class="commodity-source-card">
                <div class="commodity-source-name">UEX Live Market Data</div>
                <div class="commodity-source-copy">Prices, stock, demand, quality, volatility, terminal history, and calculated commodity routes.</div>
                <span class="commodity-source-status">{'Connected' if 'UEX' not in catalog_errors else 'Unavailable'}</span>
            </div>
            <div class="commodity-source-card">
                <div class="commodity-source-name">SC Trade Tools Market Intelligence</div>
                <div class="commodity-source-copy">Commodity directory, shops, locations, market analytics, and selected-commodity shop transactions.</div>
                <span class="commodity-source-status">{'Licensed API connected' if sc_token_available else 'Public data connected; analytics token optional'}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if catalog_errors:
        with st.expander("Show data-source connection details"):
            for source, message in catalog_errors.items():
                st.write(f"**{source}:** {message}")

    if not names:
        st.error("No commodity catalog could be loaded from either provider.")
        render_rights_notice()
        return

    default_name = "Agricium" if "Agricium" in names else names[0]
    control_col1, control_col2, control_col3 = st.columns([2, 1, 1])
    with control_col1:
        selected_commodity = st.selectbox(
            "Commodity",
            names,
            index=names.index(default_name),
            key="commodity_selected_name",
        )
    with control_col2:
        cargo_scu = st.number_input(
            "Cargo amount (SCU)",
            min_value=1.0,
            max_value=1000000.0,
            value=100.0,
            step=10.0,
            key="commodity_cargo_scu",
        )
    with control_col3:
        investment_limit = st.number_input(
            "Investment limit (aUEC)",
            min_value=0.0,
            max_value=1000000000.0,
            value=1000000.0,
            step=100000.0,
            key="commodity_investment_limit",
        )

    selected_uex = uex_map.get(selected_commodity.casefold())
    uex_prices = pd.DataFrame()
    uex_routes = pd.DataFrame()
    uex_error = ""

    if selected_uex:
        try:
            commodity_id = int(selected_uex.get("id") or 0)
            uex_prices = normalize_uex_prices(
                fetch_uex_commodity_prices(commodity_id)
            )
            uex_routes = normalize_uex_routes(
                fetch_uex_commodity_routes(
                    commodity_id,
                    int(investment_limit),
                )
            )
        except Exception as exc:
            uex_error = str(exc)
    else:
        uex_error = "This commodity name was not matched to a UEX commodity ID."

    st.markdown("### Choose a Commodity Tool")
    st.caption(
        "Use the highlighted navigation below for market prices, routes, "
        "personal trade records, source data, and profit calculations."
    )

    (
        market_tab,
        routes_tab,
        planner_tab,
        tracker_tab,
        sc_tab,
        calculator_tab,
    ) = st.tabs(
        [
            "Market Snapshot",
            "Trade Routes",
            "Route Planner",
            "My Trade Tracker",
            "SC Trade Tools",
            "Cargo Calculator",
        ]
    )

    with market_tab:
        if uex_error:
            st.warning(f"UEX market data could not be loaded: {uex_error}")

        if uex_prices.empty:
            st.info("No UEX terminal listings were returned for this commodity.")
        else:
            filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
            with filter_col1:
                systems = sorted(
                    uex_prices["System"].dropna().astype(str).unique()
                )
                selected_systems = st.multiselect(
                    "System",
                    systems,
                    default=systems,
                    key="commodity_market_system_filter",
                )
            with filter_col2:
                selected_environments = st.multiselect(
                    "Environment",
                    ["Ground", "Space", "Other"],
                    default=["Ground", "Space", "Other"],
                    key="commodity_market_environment_filter",
                )
            with filter_col3:
                market_side = st.selectbox(
                    "Market side",
                    ["All listings", "Player can buy", "Player can sell"],
                    key="commodity_market_side_filter",
                )
            with filter_col4:
                market_search = st.text_input(
                    "Search locations",
                    placeholder="Lorville, Levski, Pyro...",
                    key="commodity_market_search",
                )

            filtered_prices = uex_prices.copy()
            if selected_systems:
                filtered_prices = filtered_prices[
                    filtered_prices["System"].isin(selected_systems)
                ]
            else:
                filtered_prices = filtered_prices.iloc[0:0]

            if selected_environments:
                filtered_prices = filtered_prices[
                    filtered_prices["Environment"].isin(
                        selected_environments
                    )
                ]
            else:
                filtered_prices = filtered_prices.iloc[0:0]

            if market_side == "Player can buy":
                filtered_prices = filtered_prices[
                    filtered_prices["Terminal Sells at"] > 0
                ]
            elif market_side == "Player can sell":
                filtered_prices = filtered_prices[
                    filtered_prices["Terminal Buys at"] > 0
                ]

            if market_search.strip():
                query = market_search.strip()
                search_mask = filtered_prices.astype(str).apply(
                    lambda column: column.str.contains(
                        query,
                        case=False,
                        na=False,
                        regex=False,
                    )
                ).any(axis=1)
                filtered_prices = filtered_prices[search_mask]

            player_buy_rows = filtered_prices[
                filtered_prices["Terminal Sells at"] > 0
            ]
            player_sell_rows = filtered_prices[
                filtered_prices["Terminal Buys at"] > 0
            ]
            best_purchase = (
                float(player_buy_rows["Terminal Sells at"].min())
                if not player_buy_rows.empty
                else 0.0
            )
            best_sale = (
                float(player_sell_rows["Terminal Buys at"].max())
                if not player_sell_rows.empty
                else 0.0
            )
            spread = max(best_sale - best_purchase, 0.0)
            estimated_profit = spread * float(cargo_scu)

            render_commodity_metric_cards(
                [
                    {
                        "label": "Best Player Buy",
                        "value": f"{best_purchase:,.0f} aUEC/SCU",
                        "detail": "Lowest terminal purchase price",
                    },
                    {
                        "label": "Best Player Sale",
                        "value": f"{best_sale:,.0f} aUEC/SCU",
                        "detail": "Highest terminal sale price",
                    },
                    {
                        "label": "Maximum Spread",
                        "value": f"{spread:,.0f} aUEC/SCU",
                        "tone": "positive" if spread > 0 else "",
                        "detail": "Best sale minus best purchase",
                    },
                    {
                        "label": f"Gross Profit at {cargo_scu:,.0f} SCU",
                        "value": f"{estimated_profit:,.0f} aUEC",
                        "tone": "positive" if estimated_profit > 0 else "",
                        "detail": "Before fuel, fees, risk, and losses",
                    },
                    {
                        "label": "Matching Terminals",
                        "value": f"{len(filtered_prices):,}",
                        "detail": "After current filters",
                    },
                ]
            )

            st.markdown("### Best Trading Terminals")
            st.caption(
                "Player buys show where you purchase the commodity. Player sells "
                "show where you deliver it. System, area, and terminal are separated "
                "to make the listings easier to read."
            )

            buy_table = (
                player_buy_rows.sort_values(
                    ["Terminal Sells at", "Stock (SCU)"],
                    ascending=[True, False],
                )
                .head(12)
                .rename(columns={"Terminal Sells at": "Player Pays"})
            )
            sell_table = (
                player_sell_rows.sort_values(
                    ["Terminal Buys at", "Demand (SCU)"],
                    ascending=[False, False],
                )
                .head(12)
                .rename(columns={"Terminal Buys at": "Player Receives"})
            )

            st.markdown("#### Best Places to Buy")
            st.caption(
                "Select one row to copy that terminal and price into "
                "My Trade Tracker automatically."
            )
            if buy_table.empty:
                st.info("No purchase terminals match the current filters.")
            else:
                buy_display = buy_table[
                    [
                        "System",
                        "Environment",
                        "Area",
                        "Terminal",
                        "Player Pays",
                        "Stock (SCU)",
                        "Last Updated",
                    ]
                ].reset_index(drop=True)

                buy_event = st.dataframe(
                    buy_display,
                    width="stretch",
                    hide_index=True,
                    key="commodity_best_buy_selection",
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config={
                        "Player Pays": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "Stock (SCU)": st.column_config.NumberColumn(
                            format="%,.0f SCU"
                        ),
                    },
                )

                selected_buy_rows = list(
                    buy_event.selection.rows
                )
                if selected_buy_rows:
                    selected_buy = buy_display.iloc[
                        selected_buy_rows[0]
                    ]
                    selected_buy_location = " > ".join(
                        value
                        for value in [
                            str(selected_buy["System"]).strip(),
                            str(selected_buy["Area"]).strip(),
                            str(selected_buy["Terminal"]).strip(),
                        ]
                        if value
                    )
                    prefill_commodity_tracker_from_terminal(
                        signature=(
                            f"buy|{selected_commodity}|"
                            f"{selected_buy_location}|"
                            f"{float(selected_buy['Player Pays'])}"
                        ),
                        commodity_name=selected_commodity,
                        action="Bought",
                        quantity_scu=float(cargo_scu),
                        unit_price=float(selected_buy["Player Pays"]),
                        origin=selected_buy_location,
                    )
                    st.success(
                        "Buy terminal copied to My Trade Tracker. "
                        "Open that tab to review and save the entry."
                    )

            st.markdown("#### Best Places to Sell")
            st.caption(
                "Select one row to copy that destination and sale price into "
                "My Trade Tracker automatically."
            )
            if sell_table.empty:
                st.info("No sale terminals match the current filters.")
            else:
                sell_display = sell_table[
                    [
                        "System",
                        "Environment",
                        "Area",
                        "Terminal",
                        "Player Receives",
                        "Demand (SCU)",
                        "Last Updated",
                    ]
                ].reset_index(drop=True)

                sell_event = st.dataframe(
                    sell_display,
                    width="stretch",
                    hide_index=True,
                    key="commodity_best_sell_selection",
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config={
                        "Player Receives": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "Demand (SCU)": st.column_config.NumberColumn(
                            format="%,.0f SCU"
                        ),
                    },
                )

                selected_sell_rows = list(
                    sell_event.selection.rows
                )
                if selected_sell_rows:
                    selected_sell = sell_display.iloc[
                        selected_sell_rows[0]
                    ]
                    selected_sell_location = " > ".join(
                        value
                        for value in [
                            str(selected_sell["System"]).strip(),
                            str(selected_sell["Area"]).strip(),
                            str(selected_sell["Terminal"]).strip(),
                        ]
                        if value
                    )
                    prefill_commodity_tracker_from_terminal(
                        signature=(
                            f"sell|{selected_commodity}|"
                            f"{selected_sell_location}|"
                            f"{float(selected_sell['Player Receives'])}"
                        ),
                        commodity_name=selected_commodity,
                        action="Sold",
                        quantity_scu=float(cargo_scu),
                        unit_price=float(
                            selected_sell["Player Receives"]
                        ),
                        destination=selected_sell_location,
                    )
                    st.success(
                        "Sale terminal copied to My Trade Tracker. "
                        "Open that tab to review and save the entry."
                    )

            st.markdown("#### All Matching Terminal Listings")
            market_columns = [
                "System",
                "Environment",
                "Area",
                "Terminal",
                "Location",
                "Terminal Buys at",
                "Terminal Sells at",
                "Demand (SCU)",
                "Stock (SCU)",
                "Forecast Demand (SCU)",
                "User Buy Avg",
                "User Sell Avg",
                "Weekly Buy Avg",
                "Weekly Sell Avg",
                "Monthly Buy Avg",
                "Monthly Sell Avg",
                "Buy Volatility",
                "Sell Volatility",
                "Quality",
                "Container Sizes",
                "Game Version",
                "Last Updated",
            ]
            st.dataframe(
                filtered_prices[market_columns],
                width="stretch",
                hide_index=True,
                column_config={
                    "Terminal Buys at": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                    "Terminal Sells at": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                    "Demand (SCU)": st.column_config.NumberColumn(
                        format="%,.0f SCU"
                    ),
                    "Stock (SCU)": st.column_config.NumberColumn(
                        format="%,.0f SCU"
                    ),
                    "Forecast Demand (SCU)": st.column_config.NumberColumn(
                        format="%,.0f SCU"
                    ),
                    "User Buy Avg": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                    "User Sell Avg": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                    "Weekly Buy Avg": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                    "Weekly Sell Avg": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                    "Monthly Buy Avg": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                    "Monthly Sell Avg": st.column_config.NumberColumn(
                        format="%,.0f aUEC/SCU"
                    ),
                },
            )
            st.download_button(
                "Download Filtered Commodity Market CSV",
                data=dataframe_csv_bytes(filtered_prices[market_columns]),
                file_name=(
                    f"star_citizen_{re.sub(r'[^a-z0-9]+', '_', selected_commodity.lower()).strip('_')}_market.csv"
                ),
                mime="text/csv",
                width="stretch",
            )

    with routes_tab:
        if uex_routes.empty:
            st.info("No UEX routes were returned for this commodity and investment.")
        else:
            route_filter1, route_filter2, route_filter3, route_filter4 = st.columns(4)
            with route_filter1:
                min_profit = st.number_input(
                    "Minimum expected profit",
                    min_value=0.0,
                    value=0.0,
                    step=10000.0,
                    key="commodity_route_min_profit",
                )
            with route_filter2:
                min_roi = st.number_input(
                    "Minimum ROI",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key="commodity_route_min_roi",
                )
            with route_filter3:
                route_environment = st.multiselect(
                    "Origin environment",
                    ["Ground", "Space", "Other"],
                    default=["Ground", "Space", "Other"],
                    key="commodity_route_environment",
                )
            with route_filter4:
                route_search = st.text_input(
                    "Search route locations",
                    placeholder="Stanton, Pyro, Levski...",
                    key="commodity_route_search",
                )

            filtered_routes = uex_routes[
                (uex_routes["Expected Profit"] >= min_profit)
                & (uex_routes["ROI"] >= min_roi)
            ].copy()
            if route_environment:
                filtered_routes = filtered_routes[
                    filtered_routes["Origin Environment"].isin(
                        route_environment
                    )
                ]
            else:
                filtered_routes = filtered_routes.iloc[0:0]
            if route_search.strip():
                route_query = route_search.strip()
                route_mask = filtered_routes.astype(str).apply(
                    lambda column: column.str.contains(
                        route_query,
                        case=False,
                        na=False,
                        regex=False,
                    )
                ).any(axis=1)
                filtered_routes = filtered_routes[route_mask]

            if filtered_routes.empty:
                st.info("No routes match the selected filters.")
            else:
                top_profit = float(filtered_routes["Expected Profit"].max())
                top_roi = float(filtered_routes["ROI"].max())
                median_distance = float(
                    filtered_routes["Distance (GM)"].median()
                )
                route_metric1, route_metric2, route_metric3, route_metric4 = st.columns(4)
                route_metric1.metric("Matching Routes", f"{len(filtered_routes):,}")
                route_metric2.metric("Highest Profit", f"{top_profit:,.0f} aUEC")
                route_metric3.metric("Highest ROI", f"{top_roi:,.1f}%")
                route_metric4.metric("Median Distance", f"{median_distance:,.1f} GM")

                route_chart = filtered_routes.nlargest(
                    15,
                    "Expected Profit",
                ).copy()
                route_chart["Route"] = (
                    route_chart["Origin"]
                    + " → "
                    + route_chart["Destination"]
                )
                route_figure = px.bar(
                    route_chart,
                    x="Expected Profit",
                    y="Route",
                    color="ROI",
                    orientation="h",
                    text_auto=",.0f",
                    color_continuous_scale="Teal",
                )
                route_figure.update_traces(
                    textposition="inside",
                    textfont={"color": "#ffffff"},
                )
                route_figure.update_yaxes(categoryorder="total ascending")
                style_plotly_figure(route_figure, height=590)
                route_figure.update_layout(coloraxis_colorbar_title="ROI %")
                st.plotly_chart(
                    route_figure,
                    width="stretch",
                    config={"displayModeBar": False},
                )

                route_columns = [
                    "Commodity",
                    "Origin",
                    "Destination",
                    "Buy Price / SCU",
                    "Sell Price / SCU",
                    "Margin / SCU",
                    "ROI",
                    "Investment",
                    "Expected Profit",
                    "Distance (GM)",
                    "Score",
                    "Origin Stock (SCU)",
                    "Destination Demand (SCU)",
                    "Origin Volatility",
                    "Destination Volatility",
                    "Origin Containers",
                    "Destination Containers",
                    "Origin Environment",
                    "Destination Environment",
                    "Origin Monitored",
                    "Destination Monitored",
                    "Origin Freight Elevator",
                    "Destination Freight Elevator",
                    "Origin Loading Dock",
                    "Destination Loading Dock",
                    "Origin Refuel",
                    "Destination Refuel",
                    "UEX Route Code",
                ]
                st.dataframe(
                    filtered_routes[route_columns].sort_values(
                        "Expected Profit",
                        ascending=False,
                    ),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Buy Price / SCU": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "Sell Price / SCU": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "Margin / SCU": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "ROI": st.column_config.NumberColumn(format="%.1f%%"),
                        "Investment": st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        ),
                        "Expected Profit": st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        ),
                    },
                )
                st.download_button(
                    "Download Filtered Trade Routes CSV",
                    data=dataframe_csv_bytes(filtered_routes[route_columns]),
                    file_name=(
                        f"star_citizen_{re.sub(r'[^a-z0-9]+', '_', selected_commodity.lower()).strip('_')}_routes.csv"
                    ),
                    mime="text/csv",
                    width="stretch",
                )

    with planner_tab:
        st.markdown("### Commodity Route Planner")
        st.caption(
            "Plan a practical run using cargo capacity, available funds, reserve "
            "cash, system preferences, and terminal environment. The route load is "
            "limited by cargo space, funds, origin stock, and destination demand."
        )

        if uex_routes.empty:
            st.info(
                "No UEX route data is available for the selected commodity and "
                "investment limit."
            )
        else:
            planner_routes = uex_routes.copy()
            planner_routes["Origin System"] = planner_routes["Origin"].astype(
                str
            ).str.split(" > ").str[0]
            planner_routes["Destination System"] = planner_routes[
                "Destination"
            ].astype(str).str.split(" > ").str[0]

            system_options = sorted(
                set(planner_routes["Origin System"].dropna().astype(str))
                | set(
                    planner_routes["Destination System"].dropna().astype(str)
                )
            )

            planner_col1, planner_col2, planner_col3, planner_col4 = st.columns(4)
            with planner_col1:
                planner_cargo = st.number_input(
                    "Ship cargo capacity (SCU)",
                    min_value=1.0,
                    max_value=1000000.0,
                    value=float(cargo_scu),
                    step=10.0,
                    key="planner_cargo_capacity",
                )
            with planner_col2:
                planner_funds = st.number_input(
                    "Available trading funds",
                    min_value=0.0,
                    max_value=1000000000.0,
                    value=float(investment_limit),
                    step=100000.0,
                    key="planner_available_funds",
                )
            with planner_col3:
                reserve_funds = st.number_input(
                    "Funds to keep in reserve",
                    min_value=0.0,
                    max_value=1000000000.0,
                    value=0.0,
                    step=50000.0,
                    key="planner_reserve_funds",
                )
            with planner_col4:
                planner_priority = st.selectbox(
                    "Rank routes by",
                    [
                        "Highest Planned Profit",
                        "Highest Planned ROI",
                        "Shortest Distance",
                        "Lowest Investment",
                    ],
                    key="planner_priority",
                )

            pref_col1, pref_col2, pref_col3, pref_col4 = st.columns(4)
            with pref_col1:
                origin_systems = st.multiselect(
                    "Origin systems",
                    system_options,
                    default=system_options,
                    key="planner_origin_systems",
                )
            with pref_col2:
                destination_systems = st.multiselect(
                    "Destination systems",
                    system_options,
                    default=system_options,
                    key="planner_destination_systems",
                )
            with pref_col3:
                origin_environments = st.multiselect(
                    "Origin environment",
                    ["Ground", "Space", "Other"],
                    default=["Ground", "Space", "Other"],
                    key="planner_origin_environment",
                )
            with pref_col4:
                destination_environments = st.multiselect(
                    "Destination environment",
                    ["Ground", "Space", "Other"],
                    default=["Ground", "Space", "Other"],
                    key="planner_destination_environment",
                )

            usable_funds = max(
                float(planner_funds) - float(reserve_funds),
                0.0,
            )
            planned_rows: list[dict[str, Any]] = []

            for _, route in planner_routes.iterrows():
                if route["Origin System"] not in origin_systems:
                    continue
                if route["Destination System"] not in destination_systems:
                    continue
                if route["Origin Environment"] not in origin_environments:
                    continue
                if (
                    route["Destination Environment"]
                    not in destination_environments
                ):
                    continue

                buy_price = float(route["Buy Price / SCU"])
                sell_price = float(route["Sell Price / SCU"])
                if buy_price <= 0 or sell_price <= 0:
                    continue

                load_limits = [
                    float(planner_cargo),
                    usable_funds / buy_price,
                ]

                origin_stock = float(route["Origin Stock (SCU)"])
                destination_demand = float(
                    route["Destination Demand (SCU)"]
                )
                if origin_stock > 0:
                    load_limits.append(origin_stock)
                if destination_demand > 0:
                    load_limits.append(destination_demand)

                planned_scu = max(min(load_limits), 0.0)
                if planned_scu <= 0:
                    continue

                actual_investment = planned_scu * buy_price
                planned_revenue = planned_scu * sell_price
                planned_profit = planned_revenue - actual_investment
                planned_roi = (
                    planned_profit / actual_investment * 100
                    if actual_investment > 0
                    else 0.0
                )

                planned_rows.append(
                    {
                        "Origin": route["Origin"],
                        "Destination": route["Destination"],
                        "Load (SCU)": planned_scu,
                        "Buy Price / SCU": buy_price,
                        "Sell Price / SCU": sell_price,
                        "Investment": actual_investment,
                        "Planned Revenue": planned_revenue,
                        "Planned Profit": planned_profit,
                        "Planned ROI": planned_roi,
                        "Distance (GM)": float(route["Distance (GM)"]),
                        "Origin Stock (SCU)": origin_stock,
                        "Destination Demand (SCU)": destination_demand,
                        "Origin Freight Elevator": route[
                            "Origin Freight Elevator"
                        ],
                        "Destination Freight Elevator": route[
                            "Destination Freight Elevator"
                        ],
                        "Origin Loading Dock": route["Origin Loading Dock"],
                        "Destination Loading Dock": route[
                            "Destination Loading Dock"
                        ],
                        "Origin Refuel": route["Origin Refuel"],
                        "Destination Refuel": route["Destination Refuel"],
                    }
                )

            planned_routes = pd.DataFrame(planned_rows)

            if planned_routes.empty:
                st.info(
                    "No route can be funded and loaded with the current planner "
                    "settings."
                )
            else:
                sort_map = {
                    "Highest Planned Profit": ("Planned Profit", False),
                    "Highest Planned ROI": ("Planned ROI", False),
                    "Shortest Distance": ("Distance (GM)", True),
                    "Lowest Investment": ("Investment", True),
                }
                sort_column, sort_ascending = sort_map[planner_priority]
                planned_routes = planned_routes.sort_values(
                    sort_column,
                    ascending=sort_ascending,
                ).reset_index(drop=True)

                best_route = planned_routes.iloc[0]

                metric1, metric2, metric3, metric4, metric5 = st.columns(5)
                metric1.metric(
                    "Recommended Load",
                    f"{best_route['Load (SCU)']:,.1f} SCU",
                )
                metric2.metric(
                    "Investment",
                    f"{best_route['Investment']:,.0f} aUEC",
                )
                metric3.metric(
                    "Planned Profit",
                    f"{best_route['Planned Profit']:,.0f} aUEC",
                )
                metric4.metric(
                    "Planned ROI",
                    f"{best_route['Planned ROI']:,.1f}%",
                )
                metric5.metric(
                    "Distance",
                    f"{best_route['Distance (GM)']:,.1f} GM",
                )

                st.markdown("#### Recommended Run")
                origin_col, destination_col = st.columns(2)
                with origin_col:
                    st.markdown("**Purchase terminal**")
                    st.write(best_route["Origin"])
                    st.caption(
                        f"Load {best_route['Load (SCU)']:,.1f} SCU at "
                        f"{best_route['Buy Price / SCU']:,.0f} aUEC/SCU."
                    )
                    st.write(
                        "Freight elevator: "
                        + (
                            "Yes"
                            if best_route["Origin Freight Elevator"]
                            else "No"
                        )
                    )
                    st.write(
                        "Loading dock: "
                        + (
                            "Yes"
                            if best_route["Origin Loading Dock"]
                            else "No"
                        )
                    )

                with destination_col:
                    st.markdown("**Sale terminal**")
                    st.write(best_route["Destination"])
                    st.caption(
                        f"Sell at {best_route['Sell Price / SCU']:,.0f} "
                        f"aUEC/SCU for about "
                        f"{best_route['Planned Revenue']:,.0f} aUEC."
                    )
                    st.write(
                        "Freight elevator: "
                        + (
                            "Yes"
                            if best_route["Destination Freight Elevator"]
                            else "No"
                        )
                    )
                    st.write(
                        "Refueling available: "
                        + (
                            "Yes"
                            if best_route["Destination Refuel"]
                            else "No"
                        )
                    )

                st.markdown("#### Ranked Route Options")
                planner_columns = [
                    "Origin",
                    "Destination",
                    "Load (SCU)",
                    "Buy Price / SCU",
                    "Sell Price / SCU",
                    "Investment",
                    "Planned Revenue",
                    "Planned Profit",
                    "Planned ROI",
                    "Distance (GM)",
                    "Origin Stock (SCU)",
                    "Destination Demand (SCU)",
                ]
                st.dataframe(
                    planned_routes[planner_columns].head(50),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Load (SCU)": st.column_config.NumberColumn(
                            format="%,.1f SCU"
                        ),
                        "Buy Price / SCU": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "Sell Price / SCU": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "Investment": st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        ),
                        "Planned Revenue": st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        ),
                        "Planned Profit": st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        ),
                        "Planned ROI": st.column_config.NumberColumn(
                            format="%.1f%%"
                        ),
                        "Distance (GM)": st.column_config.NumberColumn(
                            format="%,.1f GM"
                        ),
                    },
                )
                st.download_button(
                    "Download Planned Routes CSV",
                    data=dataframe_csv_bytes(
                        planned_routes[planner_columns]
                    ),
                    file_name=(
                        "star_citizen_"
                        f"{re.sub(r'[^a-z0-9]+', '_', selected_commodity.lower()).strip('_')}"
                        "_route_plan.csv"
                    ),
                    mime="text/csv",
                    width="stretch",
                )


    with tracker_tab:
        commodity_trade_tracker(
            names,
            selected_commodity,
            uex_prices,
            float(cargo_scu),
        )


    with sc_tab:
        public_col1, public_col2, public_col3, public_col4 = st.columns(4)
        try:
            sc_items = fetch_sc_trade_tools_resource("commodity/items")
        except Exception:
            sc_items = []
        try:
            sc_shops = fetch_sc_trade_tools_resource("commodity/shops")
        except Exception:
            sc_shops = []
        try:
            sc_locations = fetch_sc_trade_tools_resource("locations")
        except Exception:
            sc_locations = []
        try:
            sc_ships = fetch_sc_trade_tools_resource("ships")
        except Exception:
            sc_ships = []

        public_col1.metric("SC Trade Commodities", f"{len(sc_items):,}")
        public_col2.metric("Commodity Shops", f"{len(sc_shops):,}")
        public_col3.metric("Trade Locations", f"{len(sc_locations):,}")
        public_col4.metric("Supported Ships", f"{len(sc_ships):,}")

        source_presence = pd.DataFrame(
            [
                {
                    "Commodity": selected_commodity,
                    "Available in UEX": selected_uex is not None,
                    "Available in SC Trade Tools": any(
                        str(row.get("name") or "").casefold()
                        == selected_commodity.casefold()
                        for row in sc_items
                    ),
                    "UEX Terminals": len(uex_prices),
                    "UEX Routes": len(uex_routes),
                }
            ]
        )
        st.markdown("#### Cross-Source Coverage")
        st.dataframe(source_presence, width="stretch", hide_index=True)

        if not sc_token_available:
            st.info(
                "SC Trade Tools public directory data is connected. Add a licensed "
                "SC_TRADE_TOOLS_TOKEN in Streamlit Secrets to unlock its selected-"
                "commodity transactions and aggregate market reports inside this app."
            )
            with st.expander("SC Trade Tools API token setup"):
                st.code(
                    'SC_TRADE_TOOLS_TOKEN = "your-sc-trade-tools-api-token"',
                    language="toml",
                )
                st.link_button(
                    "Open Official SC Trade Tools API Licence",
                    "https://www.patreon.com/cw/sc_trade_tools/membership",
                    width="stretch",
                )
                st.caption(
                    "Keep the token in Streamlit Secrets. Never commit it to GitHub."
                )
        else:
            try:
                sc_transactions = normalize_sc_transactions(
                    fetch_sc_trade_tools_transactions(selected_commodity)
                )
            except Exception as exc:
                sc_transactions = pd.DataFrame()
                st.warning(
                    f"SC Trade Tools commodity transactions could not be loaded: {exc}"
                )

            try:
                sc_reports = normalize_sc_reports(
                    fetch_sc_trade_tools_reports()
                )
            except Exception as exc:
                sc_reports = pd.DataFrame()
                st.warning(f"SC Trade Tools market reports could not be loaded: {exc}")

            selected_report = selected_sc_report(
                sc_reports,
                selected_commodity,
            )
            if not selected_report.empty:
                st.markdown("#### SC Trade Tools Aggregate Analytics")
                report_long = selected_report.melt(
                    id_vars=["Commodity"],
                    var_name="Metric",
                    value_name="Value",
                )
                st.dataframe(report_long, width="stretch", hide_index=True)

            st.markdown("#### SC Trade Tools Shop Transactions")
            if sc_transactions.empty:
                st.info("No SC Trade Tools transaction rows were returned.")
            else:
                sc_filter1, sc_filter2 = st.columns(2)
                with sc_filter1:
                    actions = sorted(
                        sc_transactions["Action"].dropna().astype(str).unique()
                    )
                    selected_actions = st.multiselect(
                        "Shop action",
                        actions,
                        default=actions,
                        key="sc_trade_action_filter",
                    )
                with sc_filter2:
                    sc_search = st.text_input(
                        "Search SC Trade Tools locations",
                        key="sc_trade_location_search",
                    )

                filtered_sc = sc_transactions.copy()
                if selected_actions:
                    filtered_sc = filtered_sc[
                        filtered_sc["Action"].isin(selected_actions)
                    ]
                else:
                    filtered_sc = filtered_sc.iloc[0:0]
                if sc_search.strip():
                    sc_query = sc_search.strip()
                    sc_mask = filtered_sc.astype(str).apply(
                        lambda column: column.str.contains(
                            sc_query,
                            case=False,
                            na=False,
                            regex=False,
                        )
                    ).any(axis=1)
                    filtered_sc = filtered_sc[sc_mask]

                st.dataframe(
                    filtered_sc.sort_values("Price / SCU", ascending=False),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Price / SCU": st.column_config.NumberColumn(
                            format="%,.0f aUEC/SCU"
                        ),
                        "Fees": st.column_config.NumberColumn(
                            format="%,.0f aUEC"
                        ),
                        "Quantity (SCU)": st.column_config.NumberColumn(
                            format="%,.0f SCU"
                        ),
                        "Max Quantity (SCU)": st.column_config.NumberColumn(
                            format="%,.0f SCU"
                        ),
                    },
                )

            if not sc_reports.empty:
                with st.expander("Browse all SC Trade Tools commodity analytics"):
                    report_search = st.text_input(
                        "Search analytics commodities",
                        key="sc_trade_report_search",
                    )
                    filtered_reports = sc_reports.copy()
                    if report_search.strip():
                        filtered_reports = filtered_reports[
                            filtered_reports["Commodity"].astype(str).str.contains(
                                report_search.strip(),
                                case=False,
                                na=False,
                                regex=False,
                            )
                        ]
                    st.dataframe(
                        filtered_reports,
                        width="stretch",
                        hide_index=True,
                    )

    with calculator_tab:
        st.markdown("### Cargo Run Calculator")
        st.caption(
            "Use UEX best-market prices as defaults, then adjust the numbers for the "
            "terminal and route you intend to run."
        )

        default_buy = 0.0
        default_sell = 0.0
        if not uex_prices.empty:
            purchase_rows = uex_prices[uex_prices["Terminal Sells at"] > 0]
            sale_rows = uex_prices[uex_prices["Terminal Buys at"] > 0]
            if not purchase_rows.empty:
                default_buy = float(purchase_rows["Terminal Sells at"].min())
            if not sale_rows.empty:
                default_sell = float(sale_rows["Terminal Buys at"].max())

        calc_col1, calc_col2, calc_col3 = st.columns(3)
        with calc_col1:
            planned_scu = st.number_input(
                "Planned cargo (SCU)",
                min_value=0.0,
                value=float(cargo_scu),
                step=10.0,
                key="commodity_calc_scu",
            )
            buy_price = st.number_input(
                "Purchase price per SCU",
                min_value=0.0,
                value=float(default_buy),
                step=100.0,
                key="commodity_calc_buy_price",
            )
        with calc_col2:
            sell_price = st.number_input(
                "Sale price per SCU",
                min_value=0.0,
                value=float(default_sell),
                step=100.0,
                key="commodity_calc_sell_price",
            )
            loading_fees = st.number_input(
                "Loading and unloading fees",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                key="commodity_calc_fees",
            )
        with calc_col3:
            operating_cost = st.number_input(
                "Fuel, repair, escort, and other costs",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                key="commodity_calc_operating_cost",
            )
            loss_reserve_percent = st.number_input(
                "Risk reserve",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0,
                key="commodity_calc_risk_reserve",
            )

        purchase_cost = planned_scu * buy_price
        gross_revenue = planned_scu * sell_price
        gross_profit = gross_revenue - purchase_cost
        risk_reserve = max(gross_profit, 0.0) * (
            loss_reserve_percent / 100.0
        )
        net_profit = (
            gross_profit
            - loading_fees
            - operating_cost
            - risk_reserve
        )
        roi = (net_profit / purchase_cost * 100.0) if purchase_cost > 0 else 0.0
        break_even_sale = (
            buy_price
            + (loading_fees + operating_cost) / planned_scu
            if planned_scu > 0
            else 0.0
        )

        calc_metric1, calc_metric2, calc_metric3, calc_metric4, calc_metric5 = st.columns(5)
        calc_metric1.metric("Purchase Cost", f"{purchase_cost:,.0f} aUEC")
        calc_metric2.metric("Gross Revenue", f"{gross_revenue:,.0f} aUEC")
        calc_metric3.metric("Gross Profit", f"{gross_profit:,.0f} aUEC")
        calc_metric4.metric("Net Profit", f"{net_profit:,.0f} aUEC")
        calc_metric5.metric("Net ROI", f"{roi:,.1f}%")

        st.info(
            f"Break-even sale price: {break_even_sale:,.0f} aUEC/SCU. "
            f"Risk reserve held back: {risk_reserve:,.0f} aUEC."
        )

        calculator_export = pd.DataFrame(
            [
                {
                    "Commodity": selected_commodity,
                    "Cargo (SCU)": planned_scu,
                    "Purchase Price / SCU": buy_price,
                    "Sale Price / SCU": sell_price,
                    "Purchase Cost": purchase_cost,
                    "Gross Revenue": gross_revenue,
                    "Loading Fees": loading_fees,
                    "Operating Cost": operating_cost,
                    "Risk Reserve": risk_reserve,
                    "Net Profit": net_profit,
                    "Net ROI (%)": roi,
                    "Break-even Sale Price / SCU": break_even_sale,
                }
            ]
        )
        st.download_button(
            "Download Cargo Run Plan CSV",
            data=dataframe_csv_bytes(calculator_export),
            file_name="star_citizen_commodity_run_plan.csv",
            mime="text/csv",
            width="stretch",
        )

    render_rights_notice()


def mining_environment_tags(row: pd.Series) -> str:
    """Classify a mining row into broad searchable environment groups."""
    site_type = str(row.get("Site Type", "") or "").casefold()
    location = str(row.get("Location", "") or "").casefold()
    combined = f"{site_type} {location}"

    tags: list[str] = []

    if any(
        token in combined
        for token in (
            "asteroid",
            "orbit",
            "lagrange",
            "halo",
            "belt",
            "ring",
            "cluster",
            "space",
        )
    ):
        tags.append("Space / Asteroid")

    if "planet" in combined:
        tags.append("Planet")

    if "moon" in combined:
        tags.append("Moon")

    if "cave" in combined:
        tags.append("Cave")

    if "surface" in combined:
        tags.append("Surface")

    if any(
        token in combined
        for token in (
            "point of interest",
            "mining poi",
            "outpost",
            "facility",
        )
    ):
        tags.append("Point of Interest")

    if "system" in combined:
        tags.append("System-wide")

    if not tags:
        tags.append("Other")

    # Preserve order while removing duplicates.
    return ", ".join(dict.fromkeys(tags))


def mining_locations_page() -> None:
    page_banner(
        "ore_banner.jpg",
        "Ore and Gem Locations",
        "Search reported mining locations, compare spawn rates, and filter resources by category and star system.",
        "Mining Intelligence",
    )

    control_col1, control_col2 = st.columns([1, 4])
    with control_col1:
        if st.button(
            "Refresh Live Data",
            key="refresh_uex_mining_data",
            width="stretch",
        ):
            fetch_uex_resource.clear()
            fetch_live_uex_mining_locations.clear()
            st.rerun()

    locations = load_mining_locations()
    if not locations.empty:
        locations = locations.copy()
        locations["Environment"] = locations.apply(
            mining_environment_tags,
            axis=1,
        )
    else:
        locations["Environment"] = pd.Series(dtype="object")

    uex_status = st.session_state.get("uex_mining_status", {})

    with control_col2:
        if uex_status.get("is_live"):
            st.success(uex_status.get("message", "Live UEX data loaded."))
        else:
            st.warning(
                uex_status.get(
                    "message",
                    "Using the packaged mining reference.",
                )
            )

    st.caption(
        "UEX location relationships are refreshed from its API and cached for one hour. "
        "UEX does not publish a probability for every resource, so packaged community "
        "spawn-rate notes are merged where a match is available."
    )

    search_text = st.text_input(
        "Search locations and resources",
        placeholder="Search for Gold, Aberdeen, Pyro, cave, asteroid, ROC...",
        key="mining_location_search",
    )

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

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
        environment_choices = [
            "Space / Asteroid",
            "Planet",
            "Moon",
            "Cave",
            "Surface",
            "Point of Interest",
            "System-wide",
            "Other",
        ]
        selected_environments = st.multiselect(
            "Environment",
            environment_choices,
            default=environment_choices,
            key="mining_environment_filter",
            help="Filter locations such as space, asteroid fields, planets, moons, caves, and surfaces.",
        )

    with filter_col4:
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

    if selected_environments:
        selected_environment_set = set(selected_environments)
        filtered = filtered[
            filtered["Environment"].apply(
                lambda value: bool(
                    selected_environment_set.intersection(
                        {
                            item.strip()
                            for item in str(value).split(",")
                            if item.strip()
                        }
                    )
                )
            )
        ]
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

    display_columns = [
        "Resource",
        "Category",
        "System",
        "Environment",
        "Location",
        "Site Type",
        "Spawn Rate",
        "Mining Method",
        "UEX Updated",
    ]

    if filtered.empty:
        st.info("No locations match the current search and filters.")
    else:
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
                "Environment": st.column_config.TextColumn("Environment", width="medium"),
                "Location": st.column_config.TextColumn("Location", width="large"),
                "Site Type": st.column_config.TextColumn("Spawn Area", width="medium"),
                "Spawn Rate": st.column_config.TextColumn("Spawn Rate", width="medium"),
                "Mining Method": st.column_config.TextColumn("Method", width="small"),
                "UEX Updated": st.column_config.TextColumn("UEX Updated", width="medium"),
            },
        )

    st.download_button(
        "Download Filtered Mining Locations CSV",
        data=dataframe_csv_bytes(filtered[display_columns]),
        file_name="star_citizen_mining_locations.csv",
        mime="text/csv",
        width="stretch",
    )

    with st.expander("How to use spawn-rate information"):
        st.markdown(
            """
            The resource and location relationships are loaded from the UEX API.
            UEX does not provide a numeric spawn probability for every mineral, so
            locally maintained rates such as **Common**, **Rare**, or a reported
            percentage are merged when the resource, system, and location match.
            The app automatically falls back to `data/mining_locations.csv` when
            UEX is unavailable.
            """
        )



def blueprints_page() -> None:
    page_banner(
        "contracts_banner.jpg",
        "Crafting Blueprints",
        "Browse the live community blueprint database and track the blueprints and required materials in your own collection.",
        "Crafting Intelligence",
    )

    st.info(
        "The live catalog below is supplied by SC Craft Tools. Use it to identify "
        "a blueprint and its recipe, then record the blueprint and material quantities "
        "in your personal tracker."
    )

    link_col1, link_col2 = st.columns([1, 1])
    with link_col1:
        st.link_button(
            "Open Full Blueprint Database",
            SC_CRAFT_TOOLS_URL,
            width="stretch",
        )
    with link_col2:
        st.link_button(
            "Open Blueprint Finder",
            "https://citizen-starter-guide.com/star-citizen-blueprint-finder/",
            width="stretch",
        )

    st.markdown("### Live Blueprint Database")
    st.caption(
        "Search the embedded database for blueprints, ingredients, missions, "
        "contractors, and systems. If embedded viewing is blocked by the provider, "
        "use the external database button above."
    )
    st.iframe(
        SC_CRAFT_TOOLS_URL,
        height=920,
        scrolling=True,
    )

    render_rights_notice()

    st.markdown("### My Blueprint Tracker")
    st.caption(
        "Record blueprints you own and their material requirements. The tracker "
        "compares combined requirements against the ore and gems currently on hand "
        "in your Ore Ledger."
    )

    blueprints = load_blueprints()
    _, ores = load_data()
    inventory = build_ore_inventory(ores)

    if not st.session_state.get("blueprint_tracker_ready", False):
        st.warning(
            "The Blueprint Tracker database connection is not ready. Run "
            "`schema_migration_v3_blueprints_repair.sql` in Supabase SQL Editor, "
            "wait about 10 seconds, then reload the app."
        )
        blueprint_error = st.session_state.get("blueprint_tracker_error", "")
        if blueprint_error:
            with st.expander("Show database error details"):
                st.code(blueprint_error)

    add_tab, readiness_tab, manage_tab = st.tabs(
        ["Add Blueprint", "Readiness & Materials", "Manage Blueprints"]
    )

    with add_tab:
        st.markdown("#### Add an Owned Blueprint")
        st.caption(
            "Enter the material requirement for one craft. Planned builds multiply "
            "those quantities in the combined readiness calculation."
        )

        resource_options = sorted(
            set(
                [
                    resource
                    for resource in ORE_TYPES
                    if resource != "Other / Custom"
                ]
                + (
                    inventory["Ore / Mineral"].dropna().astype(str).tolist()
                    if not inventory.empty
                    else []
                )
            )
        )

        blueprint_name = st.text_input(
            "Blueprint name",
            placeholder="Example: Purgatory Helmet",
            key="new_blueprint_name",
        )
        field_col1, field_col2, field_col3 = st.columns(3)
        with field_col1:
            blueprint_category = st.selectbox(
                "Category",
                [
                    "Armor",
                    "Weapon",
                    "Ship Component",
                    "Vehicle Component",
                    "Tool",
                    "Consumable",
                    "Other",
                ],
                key="new_blueprint_category",
            )
        with field_col2:
            copies_owned = st.number_input(
                "Copies owned",
                min_value=1,
                max_value=999,
                value=1,
                step=1,
                key="new_blueprint_copies",
            )
        with field_col3:
            target_builds = st.number_input(
                "Planned builds",
                min_value=1,
                max_value=999,
                value=1,
                step=1,
                key="new_blueprint_target_builds",
            )

        status_col, source_col = st.columns(2)
        with status_col:
            blueprint_status = st.selectbox(
                "Tracker status",
                ["Owned", "In Progress", "Ready to Craft", "Completed"],
                key="new_blueprint_status",
            )
        with source_col:
            source_location = st.text_input(
                "Where it was acquired",
                placeholder="Mission, contractor, location, or event",
                key="new_blueprint_source",
            )

        selected_materials = st.multiselect(
            "Required ores and gems",
            resource_options,
            key="new_blueprint_materials",
            placeholder="Choose each material required by the recipe",
        )

        material_requirements: dict[str, float] = {}
        if selected_materials:
            st.markdown("##### Required amount per craft")
            material_columns = st.columns(3)
            for index, material in enumerate(selected_materials):
                with material_columns[index % 3]:
                    material_requirements[material] = st.number_input(
                        material,
                        min_value=0.01,
                        value=1.0,
                        step=0.25,
                        format="%.2f",
                        key=f"new_blueprint_material_{re.sub(r'[^a-z0-9]+', '_', material.lower())}",
                        help="Enter the amount required for one planned craft.",
                    )

        blueprint_notes = st.text_area(
            "Notes",
            placeholder="Recipe notes, unlock details, or reminders",
            key="new_blueprint_notes",
        )

        if st.button(
            "Save Blueprint to Tracker",
            key="save_blueprint_tracker",
            width="stretch",
        ):
            if not blueprint_name.strip():
                st.error("Enter a blueprint name.")
            elif not material_requirements:
                st.error("Select at least one required material.")
            else:
                payload = {
                    "user_id": st.session_state.user_id,
                    "blueprint_name": blueprint_name.strip(),
                    "blueprint_category": blueprint_category,
                    "blueprint_status": blueprint_status,
                    "source_location": source_location.strip(),
                    "copies_owned": int(copies_owned),
                    "target_builds": int(target_builds),
                    "materials": material_requirements,
                    "notes": blueprint_notes.strip(),
                }
                try:
                    insert_blueprint(payload)
                    st.success("Blueprint saved to your tracker.")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "The blueprint could not be saved. Confirm that "
                        "`schema_migration_v3_blueprints_repair.sql` was run in "
                        f"Supabase. Details: {exc}"
                    )

    with readiness_tab:
        readiness, combined_materials = build_blueprint_readiness(
            blueprints,
            inventory,
        )

        if readiness.empty:
            st.info("Add a blueprint to begin tracking material readiness.")
        else:
            ready_count = int(
                (readiness["Readiness"] >= 100).sum()
            )
            required_total = (
                float(combined_materials["Required (SCU)"].sum())
                if not combined_materials.empty
                else 0.0
            )
            on_hand_for_requirements = (
                float(
                    combined_materials[
                        ["Required (SCU)", "On Hand (SCU)"]
                    ].min(axis=1).sum()
                )
                if not combined_materials.empty
                else 0.0
            )
            shortage_total = (
                float(combined_materials["Shortage (SCU)"].sum())
                if not combined_materials.empty
                else 0.0
            )

            metric_1, metric_2, metric_3, metric_4 = st.columns(4)
            metric_1.metric("Blueprints Tracked", f"{len(readiness):,}")
            metric_2.metric("Ready to Craft", f"{ready_count:,}")
            metric_3.metric(
                "Required Materials",
                f"{required_total:,.2f} SCU",
            )
            metric_4.metric(
                "Material Shortage",
                f"{shortage_total:,.2f} SCU",
            )

            st.markdown("#### Combined Material Readiness")
            st.caption(
                "This table combines the planned builds from every tracked blueprint "
                "and compares the total requirement with your current on-hand inventory."
            )
            st.dataframe(
                combined_materials,
                width="stretch",
                hide_index=True,
                column_config={
                    "Required (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "On Hand (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "Shortage (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "Surplus (SCU)": st.column_config.NumberColumn(
                        format="%,.2f SCU"
                    ),
                    "Coverage": st.column_config.ProgressColumn(
                        "Coverage",
                        min_value=0,
                        max_value=100,
                        format="%.0f%%",
                    ),
                },
            )

            st.markdown("#### Blueprint Readiness")
            st.caption(
                "Individual readiness compares each recipe with current inventory. "
                "Use the combined table above when multiple blueprints require the "
                "same material."
            )
            st.dataframe(
                readiness,
                width="stretch",
                hide_index=True,
                column_config={
                    "Readiness": st.column_config.ProgressColumn(
                        "Readiness",
                        min_value=0,
                        max_value=100,
                        format="%.0f%%",
                    ),
                },
            )

            export_col1, export_col2 = st.columns(2)
            with export_col1:
                st.download_button(
                    "Download Blueprint Readiness CSV",
                    data=dataframe_csv_bytes(readiness),
                    file_name="star_citizen_blueprint_readiness.csv",
                    mime="text/csv",
                    width="stretch",
                )
            with export_col2:
                st.download_button(
                    "Download Combined Materials CSV",
                    data=dataframe_csv_bytes(combined_materials),
                    file_name="star_citizen_blueprint_materials.csv",
                    mime="text/csv",
                    width="stretch",
                )

    with manage_tab:
        if blueprints.empty:
            st.info("No blueprints are available to manage.")
        else:
            blueprint_options = {
                int(row["id"]): (
                    f'ID {int(row["id"])} | {row["blueprint_name"]} | '
                    f'{int(row.get("target_builds", 1) or 1)} planned'
                )
                for _, row in blueprints.iterrows()
            }
            selected_blueprint_id = st.selectbox(
                "Select blueprint",
                options=list(blueprint_options),
                format_func=lambda value: blueprint_options[value],
                key="manage_blueprint_select",
            )
            selected_row = blueprints.loc[
                blueprints["id"] == selected_blueprint_id
            ].iloc[0]
            current_materials = normalize_blueprint_materials(
                selected_row.get("materials", {})
            )

            with st.form("manage_blueprint_form"):
                edit_name = st.text_input(
                    "Blueprint name",
                    value=str(selected_row.get("blueprint_name", "")),
                )
                edit_col1, edit_col2, edit_col3 = st.columns(3)
                with edit_col1:
                    categories = [
                        "Armor",
                        "Weapon",
                        "Ship Component",
                        "Vehicle Component",
                        "Tool",
                        "Consumable",
                        "Other",
                    ]
                    current_category = str(
                        selected_row.get("blueprint_category", "Other")
                    )
                    if current_category not in categories:
                        categories.append(current_category)
                    edit_category = st.selectbox(
                        "Category",
                        categories,
                        index=categories.index(current_category),
                    )
                with edit_col2:
                    edit_copies = st.number_input(
                        "Copies owned",
                        min_value=1,
                        max_value=999,
                        value=int(selected_row.get("copies_owned", 1) or 1),
                        step=1,
                    )
                with edit_col3:
                    edit_target = st.number_input(
                        "Planned builds",
                        min_value=1,
                        max_value=999,
                        value=int(selected_row.get("target_builds", 1) or 1),
                        step=1,
                    )

                statuses = [
                    "Owned",
                    "In Progress",
                    "Ready to Craft",
                    "Completed",
                ]
                current_status = str(
                    selected_row.get("blueprint_status", "Owned")
                )
                if current_status not in statuses:
                    statuses.append(current_status)
                edit_status = st.selectbox(
                    "Tracker status",
                    statuses,
                    index=statuses.index(current_status),
                )
                edit_source = st.text_input(
                    "Where it was acquired",
                    value=str(selected_row.get("source_location", "") or ""),
                )

                st.markdown("##### Required amount per craft")
                edited_materials: dict[str, float] = {}
                if current_materials:
                    material_columns = st.columns(3)
                    for index, (material, quantity) in enumerate(
                        sorted(current_materials.items())
                    ):
                        with material_columns[index % 3]:
                            edited_materials[material] = st.number_input(
                                material,
                                min_value=0.01,
                                value=float(quantity),
                                step=0.25,
                                format="%.2f",
                                key=f"edit_blueprint_material_{selected_blueprint_id}_{re.sub(r'[^a-z0-9]+', '_', material.lower())}",
                            )
                else:
                    st.caption(
                        "This blueprint has no stored materials. Delete and recreate "
                        "it to add a new material list."
                    )

                edit_notes = st.text_area(
                    "Notes",
                    value=str(selected_row.get("notes", "") or ""),
                )
                update_blueprint = st.form_submit_button(
                    "Update Blueprint",
                    width="stretch",
                )

            if update_blueprint:
                payload = {
                    "blueprint_name": edit_name.strip(),
                    "blueprint_category": edit_category,
                    "blueprint_status": edit_status,
                    "source_location": edit_source.strip(),
                    "copies_owned": int(edit_copies),
                    "target_builds": int(edit_target),
                    "materials": edited_materials,
                    "notes": edit_notes.strip(),
                }
                try:
                    update_record(
                        "blueprint_tracker",
                        selected_blueprint_id,
                        payload,
                    )
                    st.success("Blueprint updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"The blueprint could not be updated: {exc}")

            confirm_delete = st.checkbox(
                "I understand this permanently deletes the selected blueprint.",
                key="delete_blueprint_confirm",
            )
            if st.button(
                "Delete Blueprint",
                type="primary",
                disabled=not confirm_delete,
                key="delete_blueprint_button",
                width="stretch",
            ):
                try:
                    delete_record(
                        "blueprint_tracker",
                        selected_blueprint_id,
                    )
                    st.success("Blueprint deleted.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"The blueprint could not be deleted: {exc}")



def export_page() -> None:
    page_banner(
        "export_banner.jpg",
        "Export Data",
        "Download verified Excel and CSV exports or create a populated Google Sheet when Google credentials are configured.",
        "Data Portability",
    )
    contracts, ores = load_data()
    commodity_trades = load_commodity_transactions()
    workbook_bytes = build_excel_export(
        contracts,
        ores,
        commodity_trades,
    )
    csv_zip_bytes = build_csv_export_zip(
        contracts,
        ores,
        commodity_trades,
    )
    inventory = build_ore_inventory(ores)
    commodity_inventory = build_commodity_inventory(
        commodity_trades
    )

    st.markdown("### Verified Complete Export")
    st.caption(
        "The workbook contains Summary, Contracts, Ore Ledger, Ore Inventory, Commodity Ledger, and Commodity Inventory worksheets."
    )
    download_col1, download_col2 = st.columns(2)
    with download_col1:
        st.download_button(
            "Download Excel Workbook",
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
    with download_col2:
        st.download_button(
            "Download All CSV Files",
            data=csv_zip_bytes,
            file_name=(
                "star_citizen_tracker_csv_export_"
                f"{datetime.now().strftime('%Y-%m-%d')}.zip"
            ),
            mime="application/zip",
            width="stretch",
        )

    st.markdown("### Google Sheets")
    google_config = google_service_account_config()
    if google_config:
        if st.button("Create a Filled Google Sheet", width="stretch"):
            try:
                with st.spinner("Creating and filling your Google Sheet..."):
                    sheet_url = create_filled_google_sheet(
                        contracts,
                        ores,
                        commodity_trades,
                    )
                st.session_state.created_google_sheet_url = sheet_url
                st.success("Google Sheet created and filled with your current data.")
            except Exception as exc:
                st.error(f"The Google Sheet could not be created: {exc}")
        created_url = st.session_state.get("created_google_sheet_url")
        if created_url:
            st.link_button(
                "Open the Filled Google Sheet",
                created_url,
                width="stretch",
            )
    else:
        st.info(
            "The previous Google Sheets button only opened a blank spreadsheet. "
            "That misleading button has been removed. You can upload the downloaded "
            "Excel workbook into Google Sheets now, or configure the optional Google "
            "service account described below to create a filled sheet automatically."
        )
        with st.expander("Google Sheets automatic-export setup"):
            st.markdown(
                """
                1. Create a Google Cloud service account.
                2. Enable the Google Sheets API and Google Drive API.
                3. Create a JSON key for the service account.
                4. Add the entire JSON object to Streamlit Secrets as
                   `GOOGLE_SERVICE_ACCOUNT_JSON`.
                5. Reboot the app. The **Create a Filled Google Sheet** button will appear.
                """
            )

    st.markdown("### Individual Files")
    contract_export = prepare_contract_export(contracts)
    ore_export = prepare_ore_export(ores)
    commodity_export = prepare_commodity_export(
        commodity_trades
    )
    csv_col1, csv_col2, csv_col3, csv_col4 = st.columns(4)
    with csv_col1:
        st.download_button(
            "Contracts CSV",
            dataframe_csv_bytes(contract_export),
            "star_citizen_contracts.csv",
            "text/csv",
            width="stretch",
        )
    with csv_col2:
        st.download_button(
            "Ore Ledger CSV",
            dataframe_csv_bytes(ore_export),
            "star_citizen_ore_ledger.csv",
            "text/csv",
            width="stretch",
        )
    with csv_col3:
        st.download_button(
            "Ore Inventory CSV",
            dataframe_csv_bytes(inventory),
            "star_citizen_ore_inventory.csv",
            "text/csv",
            width="stretch",
        )
    with csv_col4:
        st.download_button(
            "Commodity Ledger CSV",
            dataframe_csv_bytes(commodity_export),
            "star_citizen_commodity_ledger.csv",
            "text/csv",
            width="stretch",
        )
        st.download_button(
            "Commodity Inventory CSV",
            dataframe_csv_bytes(commodity_inventory),
            "star_citizen_commodity_inventory.csv",
            "text/csv",
            width="stretch",
        )


def edit_records_page() -> None:
    """Backward-compatible wrapper kept in case a direct link still targets this page."""
    saved_records_page()


def main() -> None:
    apply_custom_theme()
    cookies = get_cookie_manager()
    client = get_supabase()
    handle_auth_redirect(client, cookies)
    restore_login_from_cookie(client, cookies)

    if st.session_state.get("password_recovery_active"):
        password_update_screen(client, cookies)
        return

    if "user_id" not in st.session_state:
        login_screen(client, cookies)
        return

    with st.sidebar:
        logo_path = ASSETS_DIR / "star_citizen_logo_black.png"
        if logo_path.exists():
            st.image(str(logo_path), width="stretch")
        st.markdown("### Star Citizen Tracker")
        st.caption("Private operations console")

        sidebar_display_name = st.session_state.get(
            "user_display_name",
            "Citizen",
        )
        sidebar_email = st.session_state.get(
            "user_email",
            "Signed in",
        )
        sidebar_avatar_url = st.session_state.get(
            "user_avatar_url",
            "",
        )
        st.markdown(
            f"""
            <div class="sidebar-profile-card">
                <div class="sidebar-profile-row">
                    {avatar_markup(
                        avatar_url=sidebar_avatar_url,
                        display_name=sidebar_display_name,
                        email=sidebar_email,
                        large=False,
                    )}
                    <div class="sidebar-profile-copy">
                        <div class="sidebar-profile-name">
                            {html.escape(sidebar_display_name)}
                        </div>
                        <div class="sidebar-profile-email">
                            {html.escape(sidebar_email)}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "✎",
            key="sidebar_manage_profile",
            help="Edit profile and account settings",
            type="secondary",
        ):
            st.session_state.nav_page = "My Profile"
            st.rerun()

        navigation_pages = [
            "Dashboard",
            "Contract Calculator",
            "Ore Ledger",
            "Commodities",
            "Mining Locations",
            "Blueprints",
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

        st.divider()
        st.caption("System status: All systems operational")
        st.caption(
            "Unofficial fan-made tool. Star Citizen and related content belong "
            "to their respective rights holders. Not affiliated with or endorsed "
            "by Cloud Imperium Games or Roberts Space Industries."
        )
        st.link_button(
            "Official Star Citizen Website",
            "https://robertsspaceindustries.com/",
            width="stretch",
        )
        if st.button("Sign out", width="stretch"):
            try:
                client.auth.sign_out()
            finally:
                remove_cookie_value(cookies, COOKIE_REFRESH_TOKEN)
                clear_login_state()
                st.rerun()

    page = st.session_state.nav_page
    if page == "My Profile":
        profile_page(client, cookies)
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Contract Calculator":
        contract_page()
    elif page == "Ore Ledger":
        ore_page()
    elif page == "Commodities":
        commodities_page()
    elif page == "Mining Locations":
        mining_locations_page()
    elif page == "Blueprints":
        blueprints_page()
    elif page == "Saved Records":
        saved_records_page()
    elif page == "Export Data":
        export_page()


if __name__ == "__main__":
    main()
