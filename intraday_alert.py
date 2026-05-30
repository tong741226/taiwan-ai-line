import os
import requests
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


WATCHLIST = {
    "加權指數": "^TWII",
    "OTC櫃買": "^TWOII",
    "台積電": "2330.TW",
}


def get_change(symbol, name):
    try:
        data = yf.Ticker(symbol)
        hist = data.history(period="2d").dropna()

        if len(hist) < 2:
            return {
                "name": name,
                "percent": 0,
                "text": f"{name}: 無資料"
            }

        prev = hist["Close"].iloc[-2]
        now = hist["Close"].iloc[-1]
        pct = round((now - prev) / prev * 100, 2)

        return {
            "name": name,
            "percent": pct,
            "text": f"{name}: {pct}%"
        }

    except Exception as e:
        return {
            "name": name,
            "percent": 0,
            "text": f"{name}: 抓取失敗"
        }


def judge_market(taiex, otc, tsmc):
    score = 0
    signals = []

    if taiex > 0:
        score += 1
        signals.append("加權偏多")
    else:
        score -= 1
        signals.append("加權偏弱")

    if otc > 0:
        score += 1
        signals.append("OTC偏多")
    else:
        score -= 1
        signals.append("OTC偏弱")

    if tsmc > 0:
        score += 1
        signals.append("台積電偏多")
    else:
        score -= 1
        signals.append("台積電偏弱")

    if taiex > 0 and otc > 0 and tsmc > 0:
        view = "🟢 三方同步偏多"
        action = "可觀察多方機會，但仍需等量價確認。"
    elif taiex < 0 and otc < 0 and tsmc < 0:
        view = "🔴 三方同步偏弱"
        action = "盤勢風險升高，降低出手次數。"
    elif taiex > 0 and otc < 0:
        view = "🟠 指數強、中小型股弱"
        action = "避免追中小型股，留意開高走低。"
    elif taiex < 0 and otc > 0:
        view = "🟡 中小型股較強"
        action = "可觀察題材股，但嚴控部位。"
    else:
        view = "⚪ 盤勢震盪"
        action = "多空不明，先觀察。"

    return score, signals, view, action


items = {name: get_change(symbol, name) for name, symbol in WATCHLIST.items()}

taiex = items["加權指數"]["percent"]
otc = items["OTC櫃買"]["percent"]
tsmc = items["台積電"]["percent"]

score, signals, view, action = judge_market(taiex, otc, tsmc)

now = datetime.now().strftime("%Y-%m-%d %H:%M")

message = f"""
📡 台股AI盤中監控｜正確版

時間：{now}

====================
🎖️ 一、總指揮結論
====================

盤勢狀態：
{view}

盤中分數：
{score}

操作建議：
{action}

====================
📈 二、技術官｜三核心觀察
====================

{items["加權指數"]["text"]}
{items["OTC櫃買"]["text"]}
{items["台積電"]["text"]}

====================
🛡️ 三、風控官提醒
====================

- 不追高
- 不攤平
- 不摸頭
- 不抄底
- 等加權、OTC、台積電同步確認
- 若OTC轉弱，中小型股當沖風險升高
- 若台積電轉弱，大盤容易受壓

====================
⏰ 四、盤中節奏
====================

09:00～09:15：
觀察開盤氣勢，不急著進場

09:15～09:30：
確認量價是否延續

10:30後：
若主流族群不明，降低出手

13:00後：
避免尾盤追價

⚠️ 本訊息僅供觀察，不是投資建議。
"""

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

payload = {
    "chat_id": TELEGRAM_CHAT_ID,
    "text": message
}

res = requests.post(url, json=payload)

print("Telegram status:", res.status_code)
print("Telegram response:", res.text)
print(message)
