import streamlit as st
import yfinance as yf
import ta
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from datetime import datetime, date
from streamlit_option_menu import option_menu
import requests
import pandas as pd

# ——————————————————————————————
# 1) Load all credentials from st.secrets
# ——————————————————————————————

# Twilio
TWILIO_SID    = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN  = st.secrets["TWILIO_AUTH_TOKEN"]
WA_FROM       = st.secrets["TWILIO_WHATSAPP_NUMBER"]
WA_TO         = st.secrets["MY_WHATSAPP_NUMBER"]

# Telegram (optional)
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = st.secrets.get("TELEGRAM_CHAT_ID", "")

# Google Service Account as a dict
gcp_info = st.secrets["gcp_service_account"]

# Google Sheets URL
SHEET_URL = st.secrets["SHEET_URL"]  # add this key in your secrets

# ——————————————————————————————
# 2) Initialize clients
# ——————————————————————————————

# Twilio
twilio = Client(TWILIO_SID, TWILIO_TOKEN)

# Telegram helper
def send_telegram(msg):
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT): return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg})

# Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds  = Credentials.from_service_account_info(gcp_info, scopes=SCOPES)
gc     = gspread.authorize(creds)
sheet  = gc.open_by_url(SHEET_URL).sheet1

# ——————————————————————————————
# 3) App layout & logic
# ——————————————————————————————

st.set_page_config("📈 Stock Alerts", layout="centered")
selected = option_menu(None, ["Watchlist","Logs","Settings"], orientation="horizontal")

# Sidebar controls
st.sidebar.title("Settings")
max_rsi = st.sidebar.slider("RSI Threshold", 10, 50, 30)

if selected == "Watchlist":
    st.title("Stock Watchlist")
    # (your watchlist UI, price+RSI charting, alerts...)

elif selected == "Logs":
    st.title("Alert Logs")
    df = pd.DataFrame(sheet.get_all_records())
    st.dataframe(df)

else:
    st.title("Settings")
    st.write("WhatsApp from:", WA_FROM)
    st.write("WhatsApp to:", WA_TO)
    st.write("[View Sheet]({})".format(SHEET_URL))
