import streamlit as st
import yfinance as yf
import ta
import gspread
import base64
import json
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from datetime import datetime, date
from streamlit_option_menu import option_menu
import pandas as pd
import requests

# ----------------- Load Secrets -----------------
TWILIO_SID    = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN  = st.secrets["TWILIO_AUTH_TOKEN"]
WA_FROM       = st.secrets["TWILIO_WHATSAPP_NUMBER"]
WA_TO         = st.secrets["MY_WHATSAPP_NUMBER"]

TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = st.secrets.get("TELEGRAM_CHAT_ID", "")

# Base64‑encoded GCP JSON service account
GCP_KEY_B64 = st.secrets["GCP_KEY_B64"]
SHEET_URL   = st.secrets["SHEET_URL"]

# ----------------- Initialize Clients -----------------
# Twilio
twilio = Client(TWILIO_SID, TWILIO_TOKEN)

# Telegram helper
def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg})

# Google Sheets
gcp_json = json.loads(base64.b64decode(GCP_KEY_B64).decode())
creds = Credentials.from_service_account_info(gcp_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc    = gspread.authorize(creds)
sheet = gc.open_by_url(SHEET_URL).sheet1

# ----------------- App Config -----------------
today = date.today().weekday()  # 0=Mon, ..., 6=Sun
is_weekend = today in [4, 5]  # Fri/Sat

st.set_page_config("Stock Alerts", layout="centered")

# ----------------- UI Layout -----------------
selected = option_menu(
    None, ["📊 Watchlist", "📈 Logs", "⚙️ Settings"],
    orientation="horizontal"
)

# Initialize state
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {"4250.SR": 21.5, "4161.SR": 23.0, "6001.SR": 34.0}
if "muted" not in st.session_state:
    st.session_state.muted = set()

# RSI threshold
rsi_thr = st.sidebar.slider("RSI Alert Threshold", 10, 50, 30)

# ----------------- Watchlist Tab -----------------
if selected == "📊 Watchlist":
    st.title("Stock Watchlist")
    # Add new symbol
    sym = st.text_input("Add symbol (e.g. 4250.SR)")
    thr = st.number_input("Alert price (SAR)", min_value=0.0, value=0.0)
    if st.button("Add"): st.session_state.watchlist[sym.upper()] = thr

    # Display each
    for symbol, threshold in st.session_state.watchlist.items():
        st.markdown("---")
        cols = st.columns([1,1,1,1,1])
        price_data = yf.Ticker(symbol).history(period="7d")["Close"]
        price = price_data.iloc[-1]
        rsi = ta.momentum.RSIIndicator(price_data, 14).rsi().iloc[-1]
        # Chart
        st.line_chart(price_data)
        # Metrics
        cols[0].metric("Current (SAR)", f"{price:.2f}")
        cols[1].metric("Alert ≤", f"{threshold:.2f}")
        cols[2].metric("RSI", f"{rsi:.1f}")
        # Mute toggle
        mute_key = f"mute_{symbol}"
        muted = symbol in st.session_state.muted
        if cols[3].button("Mute" if not muted else "Unmute", key=mute_key):
            if muted: st.session_state.muted.remove(symbol)
            else:    st.session_state.muted.add(symbol)
        # Alert logic
        if (price <= threshold and rsi <= rsi_thr and not muted and not is_weekend):
            msg = f"{symbol}: SAR {price:.2f}, RSI {rsi:.1f}"  
            twilio.messages.create(body=msg, from_=WA_FROM, to=WA_TO)
            send_telegram(msg)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, symbol, f"{price:.2f}", WA_TO, "Auto"])
            cols[4].success("✅ Alert sent")
        else:
            if cols[4].button("Alert Now", key=f"alert_{symbol}"):
                msg = f"{symbol}: SAR {price:.2f}, RSI {rsi:.1f}"  
                twilio.messages.create(body=msg, from_=WA_FROM, to=WA_TO)
                send_telegram(msg)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([timestamp, symbol, f"{price:.2f}", WA_TO, "Manual"])
                st.success("✅ Manual alert sent")

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
    st.write("Telegram Enabled:", bool(TELEGRAM_TOKEN and TELEGRAM_CHAT))
    st.write("Google Sheet URL:", SHEET_URL)
