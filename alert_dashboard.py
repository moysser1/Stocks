
import streamlit as st
import os
import time
import yfinance as yf
import ta
import gspread
from twilio.rest import Client
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
from streamlit_option_menu import option_menu
import pandas as pd
import json
import requests

# Twilio credentials
account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
auth_token = st.secrets["TWILIO_AUTH_TOKEN"]
from_whatsapp_number = st.secrets["TWILIO_WHATSAPP_NUMBER"]
admin_whatsapp_number = st.secrets["MY_WHATSAPP_NUMBER"]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uLvKwximiHQTAdqvfG2YDB_wYeNH75OxN4_ms81zc2E/edit#gid=0"

# Telegram settings
TELEGRAM_ENABLED = st.sidebar.checkbox("📣 Send Telegram Alerts", value=True)
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "your-telegram-bot-token")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "your-chat-id")

def send_telegram_alert(message):
    if not TELEGRAM_ENABLED:
        return
    try:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(telegram_url, data=payload)
    except Exception as e:
        st.error(f"Telegram Error: {e}")

# Authenticate with Twilio
client = Client(account_sid, auth_token)

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = {
    "type": st.secrets["GCP_TYPE"],
    "project_id": st.secrets["GCP_PROJECT_ID"],
    "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
    "private_key": st.secrets["GCP_PRIVATE_KEY"],
    "client_email": st.secrets["GCP_CLIENT_EMAIL"],
    "client_id": st.secrets["GCP_CLIENT_ID"],
    "auth_uri": st.secrets["GCP_AUTH_URI"],
    "token_uri": st.secrets["GCP_TOKEN_URI"],
    "auth_provider_x509_cert_url": st.secrets["GCP_AUTH_PROVIDER_X509_CERT_URL"],
    "client_x509_cert_url": st.secrets["GCP_CLIENT_X509_CERT_URL"]
}
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
sheet_client = gspread.authorize(creds)
sheet = sheet_client.open_by_url(SHEET_URL).sheet1

# Weekend detection
today_is_weekend = date.today().weekday() in [4, 5]

# UI and auth
lang = st.sidebar.selectbox("🌐 Language", ["English", "Arabic"])
is_ar = lang == "Arabic"

PASSWORD = "masar2025"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.attempts = 0

if not st.session_state.authenticated:
    col1, col2 = st.columns([3, 1])
    with col1:
        pw = st.text_input("🔐 Enter password:", type="password")
    with col2:
        if st.button("Forgot Password?"):
            client.messages.create(
                body="🔐 A user clicked 'Forgot Password' on your Streamlit stock alert dashboard.",
                from_=from_whatsapp_number,
                to=admin_whatsapp_number
            )
            st.info("Password reset request sent.")
    if pw == PASSWORD:
        st.session_state.authenticated = True
    else:
        st.session_state.attempts += 1
        if st.session_state.attempts >= 3:
            client.messages.create(
                body="⚠️ 3 failed login attempts on your stock alert dashboard.",
                from_=from_whatsapp_number,
                to=admin_whatsapp_number
            )
            st.warning("Too many failed attempts. Admin alerted.")
        st.stop()

st.set_page_config(page_title="Stock Alerts", layout="centered")

st.sidebar.subheader("📉 RSI Settings")
default_rsi_threshold = st.sidebar.slider("RSI Alert Threshold", min_value=10, max_value=50, value=30, step=1)

selected = option_menu("Main Menu", ["📊 Watchlist", "📈 Logs", "⚙️ Settings"], orientation="horizontal")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = {"4250.SR": 21.5, "4161.SR": 23.0, "6001.SR": 34.0}
if "whatsapp_number" not in st.session_state:
    st.session_state.whatsapp_number = admin_whatsapp_number
if "muted" not in st.session_state:
    st.session_state.muted = {}

if selected == "📊 Watchlist":
    st.title("📈 مراقبة الأسهم" if is_ar else "📈 Stock Alert Dashboard")
    st.sidebar.header("➕ إضافة سهم" if is_ar else "➕ Add Stock to Watchlist")
    symbol_input = st.sidebar.text_input("رمز السهم" if is_ar else "Ticker Symbol", "")
    threshold_input = st.sidebar.number_input("سعر التنبيه" if is_ar else "Alert Price", min_value=0.0, step=0.1)
    if st.sidebar.button("إضافة" if is_ar else "Add to Watchlist") and symbol_input:
        st.session_state.watchlist[symbol_input.upper()] = threshold_input

    st.sidebar.subheader("📲 رقم واتساب" if is_ar else "📲 Alert Recipient")
    new_number = st.sidebar.text_input("أدخل الرقم" if is_ar else "Enter WhatsApp Number", value=st.session_state.whatsapp_number)
    if st.sidebar.button("تحديث الرقم" if is_ar else "Update Number"):
        st.session_state.whatsapp_number = new_number
        st.success("تم التحديث ✅" if is_ar else f"Updated to: {new_number}")

    for symbol, threshold in st.session_state.watchlist.items():
        st.markdown("---")
        st.subheader(f"{symbol}")
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="7d")
        price = hist["Close"].iloc[-1] if not hist.empty else 0.0
        hist["RSI"] = ta.momentum.RSIIndicator(hist["Close"], window=14).rsi()
        rsi_value = hist["RSI"].iloc[-1] if not hist["RSI"].isnull().all() else 50

        st.line_chart(hist["Close"])

        muted = st.session_state.muted.get(symbol, False)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🔔 Alert ≤", f"{threshold:.2f}")
        col2.metric("📉 Current", f"{price:.2f}")
        col3.metric("📊 RSI", f"{rsi_value:.1f}")
        if col4.button("🔕 Mute" if not muted else "🔔 Unmute", key=f"mute_{symbol}"):
            st.session_state.muted[symbol] = not muted

        if price <= threshold and rsi_value <= default_rsi_threshold and not muted and not today_is_weekend:
            message = f"📉 {symbol} dropped to SAR {price:.2f} (RSI {rsi_value:.1f})"
            client.messages.create(body=message, from_=from_whatsapp_number, to=st.session_state.whatsapp_number)
            send_telegram_alert(message)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([now, symbol, f"{price:.2f}", st.session_state.whatsapp_number, "Auto (RSI)"])
            st.success("✅ RSI alert sent")

elif selected == "📈 Logs":
    st.title("📄 Alert Log")
    records = sheet.get_all_records()
    st.dataframe(pd.DataFrame(records))

elif selected == "⚙️ Settings":
    st.title("⚙️ Settings")
    st.markdown(f"🔗 [Google Sheet Logs]({SHEET_URL})")
    st.markdown(f"📲 Current WhatsApp: `{st.session_state.whatsapp_number}`")
