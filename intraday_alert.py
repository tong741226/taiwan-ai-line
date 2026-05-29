import os
import requests
import yfinance as yf

LINE_TOKEN = os.getenv("LINE_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")


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

# 測試用：先保留這行，確認 LINE 能收到後再刪掉

if taiex <= -1:
    alert_message.append(f"⚠️ 台股加權跌幅 {taiex}%")

if tsmc <= -1.5:
    alert_message.append(f"⚠️ 台積電跌幅 {tsmc}%")

if otc <= -1:
    alert_message.append(f"⚠️ OTC櫃買跌幅 {otc}%")

if alert_message:
    message = "🚨 台股盤中風險警報\n\n" + "\n".join(alert_message)

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    res = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=payload
    )

    print("LINE status:", res.status_code)
    print("LINE response:", res.text)

    if res.status_code == 200:
        print("Alert sent!")
    else:
        print("Alert failed!")

else:
    print("No alert.")
