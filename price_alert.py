
import os
import time
import yfinance as yf
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio credentials
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
to_whatsapp_number = os.getenv("MY_WHATSAPP_NUMBER")

client = Client(account_sid, auth_token)

# Define your watchlist here
watchlist = {
    "4250.SR": 21.5,  # Jabal Omar
    "4161.SR": 23.0,  # BinDawood
    "6001.SR": 34.0   # Halwani Bros
}

def send_alert(stock, price, threshold):
    message = f"📉 Alert: {stock} has dropped to SAR {price:.2f} (target ≤ {threshold})"
    client.messages.create(
        body=message,
        from_=from_whatsapp_number,
        to=to_whatsapp_number
    )
    print("Sent:", message)

def check_prices():
    for symbol, threshold in watchlist.items():
        ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")["Close"].iloc[-1]
        print(f"{symbol} price: {price:.2f}")
        if price <= threshold:
            send_alert(symbol, price, threshold)

if __name__ == "__main__":
    print("📊 Running stock price alert bot...")
    check_prices()
