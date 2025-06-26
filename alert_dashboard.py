import streamlit as st
import yfinance as yf
import ta
import gspread
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

# Google service account JSON stored as a nested dict in secrets
GCP_INFO      = st.secrets["gcp_service_account"]

# Google Sheets URL (non-sensitive)
SHEET_URL     = st.secrets["SHEET_URL"]

# ----------------- Initialize Clients -----------------
# Twilio client
twilio = Client(TWILIO_SID, TWILIO_TOKEN)

# Telegram helper
def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT, "text": msg}
        )

# Google Sheets client
auth_scopes  = ["https://www.googleapis.com/auth/spreadsheets"]
creds        = Credentials.from_service_account_info(GCP_INFO, scopes=auth_scopes)
gc           = gspread.authorize(creds)
sheet        = gc.open_by_url(SHEET_URL).sheet1

# ----------------- App Configuration -----------------
today        = date.today().weekday()  # 0=Mon,...6=Sun
is_weekend   = today in [4, 5]         # Friday(4) & Saturday(5)

st.set_page_config(page_title="Stock Alerts", layout="centered")
selected     = option_menu(
    None,
    ["📊 Watchlist", "📈 Logs", "⚙️ Settings"],
    orientation="horizontal"
)

# Initialize state
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {
        "4250.SR": 21.5,
        "4161.SR": 23.0,
        "6001.SR": 34.0
    }
if "muted" not in st.session_state:
    st.session_state.muted = set()

# RSI threshold slider
rsi_thr = st.sidebar.slider("RSI Alert Threshold", min_value=10, max_value=50, value=30, step=1)

# ----------------- Watchlist Tab -----------------
if selected == "📊 Watchlist":
    st.title("📈 Stock Watchlist")
    # Add new symbol
    sym = st.text_input("Add symbol (e.g. 4250.SR)")
    thr = st.number_input("Alert price (SAR)", min_value=0.0, step=0.1)
    if st.button("Add") and sym:
        st.session_state.watchlist[sym.upper()] = thr

    for symbol, threshold in st.session_state.watchlist.items():
        st.markdown("---")
        data = yf.Ticker(symbol).history(period="7d")["Close"]
        price = data.iloc[-1] if not data.empty else 0.0
        rsi   = ta.momentum.RSIIndicator(data, window=14).rsi().iloc[-1] if not data.empty else 0.0
        st.line_chart(data, height=150)

        cols = st.columns(5)
        cols[0].metric("Symbol", symbol)
        cols[1].metric("Price (SAR)", f"{price:.2f}")
        cols[2].metric("RSI", f"{rsi:.1f}")
        cols[3].metric("Alert ≤", f"{threshold:.2f}")

        muted = symbol in st.session_state.muted
        if cols[4].button("Unmute" if muted else "Mute", key=f"mute_{symbol}"):
            if muted:
                st.session_state.muted.remove(symbol)
            else:
                st.session_state.muted.add(symbol)

        # Auto alert logic
        if (
            price <= threshold
            and rsi <= rsi_thr
            and not muted
            and not is_weekend
        ):
            msg = f"📉 {symbol}: SAR {price:.2f}, RSI {rsi:.1f}"
            twilio.messages.create(body=msg, from_=WA_FROM, to=WA_TO)
            send_telegram(msg)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([ts, symbol, f"{price:.2f}", WA_TO, "Auto"])
            st.success("✅ Alert sent")

        # Manual alert
        if cols[4].button("🚨 Alert Now", key=f"alert_{symbol}"):
            msg = f"📉 {symbol}: SAR {price:.2f}, RSI {rsi:.1f}"
            twilio.messages.create(body=msg, from_=WA_FROM, to=WA_TO)
            send_telegram(msg)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([ts, symbol, f"{price:.2f}", WA_TO, "Manual"])
            st.info("ℹ️ Manual alert sent")

# ----------------- Logs Tab -----------------
elif selected == "📈 Logs":
    st.title("📄 Alert Logs")
    df = pd.DataFrame(sheet.get_all_records())
    st.dataframe(df)

# ----------------- Settings Tab -----------------
elif selected == "⚙️ Settings":
    st.title("⚙️ Settings")
    st.write("WhatsApp From:", WA_FROM)
    st.write("WhatsApp To:", WA_TO)
    st.write("Telegram Enabled:", bool(TELEGRAM_TOKEN and TELEGRAM_CHAT))
    st.write("Sheet URL:", SHEET_URL)
    st.write("Weekend Suppression:", is_weekend)
