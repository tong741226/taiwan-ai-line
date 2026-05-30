import os
import requests
import yfinance as yf

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def get_change(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="2d")

        if len(hist) < 2:
            return 0

        prev_close = hist["Close"].iloc[-2]
        current = hist["Close"].iloc[-1]
        change = ((current - prev_close) / prev_close) * 100

        return round(change, 2)

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return 0


taiex = get_change("^TWII")
tsmc = get_change("2330.TW")
otc = get_change("^TWOII")

alert_message = []

# 測試用，確認 Telegram 可收到後再刪掉
alert_message.append("✅ Telegram 測試成功：盤中警報系統已連線")

if taiex <= -1:
    alert_message.append(f"⚠️ 台股加權跌幅 {taiex}%")

if tsmc <= -1.5:
    alert_message.append(f"⚠️ 台積電跌幅 {tsmc}%")

if otc <= -1:
    alert_message.append(f"⚠️ OTC櫃買跌幅 {otc}%")

if alert_message:
    message = "🚨 台股盤中風險警報\n\n" + "\n".join(alert_message)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    res = requests.post(url, json=payload)

    print("Telegram status:", res.status_code)
    print("Telegram response:", res.text)

    if res.status_code == 200:
        print("Telegram alert sent!")
    else:
        print("Telegram alert failed!")

else:
    print("No alert.")
