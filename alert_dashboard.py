import streamlit as st
import yfinance as yf
import ta
import gspread
import base64
import json
import re
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from datetime import datetime, date
from streamlit_option_menu import option_menu
import pandas as pd
import requests

# ----------------- Load Secrets -----------------
TWILIO_SID   = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
WA_FROM      = st.secrets["TWILIO_WHATSAPP_NUMBER"]
WA_TO        = st.secrets["MY_WHATSAPP_NUMBER"]

TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = st.secrets.get("TELEGRAM_CHAT_ID", "")

# Google Sheets URL (non-sensitive)
SHEET_URL = st.secrets.get("SHEET_URL")

# ----------------- Initialize Clients -----------------
# Twilio client
twilio = Client(TWILIO_SID, TWILIO_TOKEN)

# Telegram helper
def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg})

# ----------------- Google Sheets Setup -----------------
# Decode base64-encoded service account JSON robustly
raw_b64 = st.secrets.get("GCP_KEY_B64", "")
# Remove any non-base64 characters
clean_b64 = re.sub(r"[^A-Za-z0-9+/=]", "", raw_b64)
# Add proper padding if needed
missing_padding = len(clean_b64) % 4
if missing_padding:
    clean_b64 += '=' * (4 - missing_padding)
try:
    decoded = base64.b64decode(clean_b64)
    gcp_json = json.loads(decoded.decode("utf-8"))
except Exception as e:
    st.error(f"Failed to decode GCP credentials: {e}")
    st.stop()

# Authorize Google Sheets
auth_scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(gcp_json, scopes=auth_scopes)
gc    = gspread.authorize(creds)
sheet = gc.open_by_url(SHEET_URL).sheet1

# ----------------- App Configuration -----------------
today = date.today().weekday()  # 0=Mon,...6=Sun
is_weekend = today in [4, 5]    # Fri(4) & Sat(5)

st.set_page_config(page_title="Stock Alerts", layout="centered")
selected = option_menu(None, ["📊 Watchlist", "📈 Logs", "⚙️ Settings"], orientation="horizontal")

# Initialize state
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {"4250.SR": 21.5, "4161.SR": 23.0, "6001.SR": 34.0}
if "muted" not in st.session_state:
    st.session_state.muted = set()

# RSI threshold in sidebar
rsi_thr = st.sidebar.slider("RSI Alert Threshold", 10, 50, 30)

# ----------------- Watchlist Tab -----------------
if selected == "📊 Watchlist":
    st.title("Stock Watchlist")
    sym_input = st.text_input("Add symbol (e.g. 4250.SR)")
    thr_input = st.number_input("Alert price (SAR)", min_value=0.0, step=0.1)
    if st.button("Add") and sym_input:
        st.session_state.watchlist[sym_input.upper()] = thr_input

    for symbol, threshold in st.session_state.watchlist.items():
        st.markdown("---")
        data = yf.Ticker(symbol).history(period="7d")["Close"]
        price = data.iloc[-1] if not data.empty else 0.0
        rsi = ta.momentum.RSIIndicator(data, 14).rsi().iloc[-1] if not data.empty else 0.0
        st.line_chart(data, height=150)
        cols = st.columns(5)
        cols[0].metric("Symbol", symbol)
        cols[1].metric("Price (SAR)", f"{price:.2f}")
        cols[2].metric("RSI", f"{rsi:.1f}")
        cols[3].metric("Alert ≤", f"{threshold:.2f}")
        muted = symbol in st.session_state.muted
        if cols[4].button("Unmute" if muted else "Mute", key=f"mute_{symbol}"):
            if muted: st.session_state.muted.remove(symbol)
            else:    st.session_state.muted.add(symbol)
        # Auto alert logic
        if price <= threshold and rsi <= rsi_thr and not muted and not is_weekend:
            msg = f"{symbol}: SAR {price:.2f}, RSI {rsi:.1f}"
            twilio.messages.create(body=msg, from_=WA_FROM, to=WA_TO)
            send_telegram(msg)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([ts, symbol, f"{price:.2f}", WA_TO, "Auto"])
            st.success("Alert sent!")
        # Manual alert button
        if st.button(f"Alert Now ({symbol})", key=f"alert_{symbol}"):
            msg = f"{symbol}: SAR {price:.2f}, RSI {rsi:.1f}"
            twilio.messages.create(body=msg, from_=WA_FROM, to=WA_TO)
            send_telegram(msg)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([ts, symbol, f"{price:.2f}", WA_TO, "Manual"])
            st.info("Manual alert sent")

# ----------------- Logs Tab -----------------
elif selected == "📈 Logs":
    st.title("Alert Logs")
    df = pd.DataFrame(sheet.get_all_records())
    st.dataframe(df)

# ----------------- Settings Tab -----------------
elif selected == "⚙️ Settings":
    st.title("Settings")
    st.write("WhatsApp From:", WA_FROM)
    st.write("WhatsApp To:", WA_TO)
    st.write("Sheet URL:", SHEET_URL)
    st.write("Weekend Suppression:", is_weekend)
