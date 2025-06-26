
# 📈 WhatsApp Stock Alert Bot + Dashboard

A complete solution to monitor Saudi stocks (TASI) and receive WhatsApp alerts when they hit target entry prices. Includes a Streamlit dashboard and a Python alert script.

## 🔧 Features
- Monitor any TASI or Yahoo Finance-supported stock
- Set price alerts and receive WhatsApp messages via Twilio
- Add stocks dynamically via the Streamlit dashboard
- Background Python script for scheduled alerting

## 📁 Folder Structure
```
whatsapp_stock_alert/
├── alert_dashboard.py     # Streamlit web app
├── price_alert.py         # Background WhatsApp alert bot
├── .env                   # Twilio credentials (DO NOT COMMIT)
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## 🚀 Setup Instructions

1. Clone the repo:
```bash
git clone https://github.com/yourusername/whatsapp-stock-alert.git
cd whatsapp-stock-alert
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+1XXXXXXXXXX
MY_WHATSAPP_NUMBER=whatsapp:+966XXXXXXXXX
```

4. Run Streamlit dashboard:
```bash
streamlit run alert_dashboard.py
```

5. Run background alert bot manually:
```bash
python price_alert.py
```

6. (Optional) Schedule price_alert.py using cron or a cloud task runner.

## ☁️ Deployment
- Host dashboard using [Streamlit Cloud](https://streamlit.io/cloud)
- Use PythonAnywhere, Replit, or a VPS to run `price_alert.py` every few hours

## ✅ License
MIT — feel free to fork, extend, or white-label for your use.
