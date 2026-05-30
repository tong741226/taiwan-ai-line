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
    "鴻海": "2317.TW",
    "廣達": "2382.TW",
    "緯創": "3231.TW",
    "緯穎": "6669.TW",
    "技嘉": "2376.TW",
    "華碩": "2357.TW",
    "奇鋐": "3017.TW",
    "雙鴻": "3324.TW",
    "台達電": "2308.TW",
    "智邦": "2345.TW",
    "南亞科": "2408.TW",
    "華邦電": "2344.TW",
}


def get_data(name, symbol):
    try:
        data = yf.Ticker(symbol)
        hist = data.history(period="5d").dropna()

        if len(hist) < 2:
            return {
                "name": name,
                "symbol": symbol,
                "price": 0,
                "change_pct": 0,
                "volume_ratio": 0,
                "status": "無資料"
            }

        today = hist.iloc[-1]
        yesterday = hist.iloc[-2]

        price = round(today["Close"], 2)
        prev_close = yesterday["Close"]
        change_pct = round((price - prev_close) / prev_close * 100, 2)

        avg_volume = hist["Volume"].iloc[:-1].mean()
        volume_ratio = round(today["Volume"] / avg_volume, 2) if avg_volume > 0 else 0

        return {
            "name": name,
            "symbol": symbol,
            "price": price,
            "change_pct": change_pct,
            "volume_ratio": volume_ratio,
            "status": "OK"
        }

    except Exception as e:
        return {
            "name": name,
            "symbol": symbol,
            "price": 0,
            "change_pct": 0,
            "volume_ratio": 0,
            "status": f"錯誤：{e}"
        }


def classify_stock(item):
    name = item["name"]
    pct = item["change_pct"]
    vol = item["volume_ratio"]

    alerts = []
    score = 0

    if pct >= 3:
        alerts.append(f"🔥 {name} 強攻 +{pct}%")
        score += 3
    elif pct >= 1.5:
        alerts.append(f"🟢 {name} 轉強 +{pct}%")
        score += 2
    elif pct >= 0.5:
        alerts.append(f"🟡 {name} 小漲 +{pct}%")
        score += 1

    if pct <= -3:
        alerts.append(f"🚨 {name} 重挫 {pct}%")
        score -= 3
    elif pct <= -1.5:
        alerts.append(f"⚠️ {name} 明顯轉弱 {pct}%")
        score -= 2
    elif pct <= -0.5:
        alerts.append(f"🟠 {name} 小跌 {pct}%")
        score -= 1

    if vol >= 2 and pct > 0:
        alerts.append(f"📈 {name} 放量上攻，量能 {vol} 倍")
        score += 2

    if vol >= 2 and pct < 0:
        alerts.append(f"📉 {name} 放量下殺，量能 {vol} 倍")
        score -= 2

    if vol >= 3:
        alerts.append(f"⚡ {name} 爆量，量能 {vol} 倍")

    return alerts, score


def market_review(results):
    score = 0
    strong = []
    weak = []
    explosive = []

    for item in results:
        alerts, s = classify_stock(item)
        score += s

        if item["change_pct"] >= 1.5:
            strong.append(item["name"])

        if item["change_pct"] <= -1.5:
            weak.append(item["name"])

        if item["volume_ratio"] >= 2:
            explosive.append(item["name"])

    if score >= 10:
        view = "🟢 強多盤，資金風險偏好明顯升溫"
        strategy = "可觀察主流族群續強，但禁止無腦追高。"
    elif score >= 5:
        view = "🟡 中性偏多，強勢股有輪動機會"
        strategy = "可小部位觀察強勢族群，等回測不破再進。"
    elif score >= -4:
        view = "⚪ 震盪盤，多空尚未明確"
        strategy = "以觀察為主，避免追價，等方向確認。"
    elif score >= -9:
        view = "🟠 中性偏弱，盤中風險升高"
        strategy = "降低出手次數，避免追高與攤平。"
    else:
        view = "🔴 空方風險盤，資金明顯退潮"
        strategy = "以防守為主，嚴控部位，不搶反彈。"

    return score, view, strategy, strong, weak, explosive


results = [get_data(name, symbol) for name, symbol in WATCHLIST.items()]

all_alerts = []
total_score = 0

for item in results:
    alerts, score = classify_stock(item)
    all_alerts.extend(alerts)
    total_score += score

market_score, market_view, strategy, strong, weak, explosive = market_review(results)

now = datetime.now().strftime("%Y-%m-%d %H:%M")

if all_alerts:
    message = f"""
📡 台股AI盤中警報 V3｜總指揮審查版

時間：{now}

一、總指揮結論
{market_view}

二、盤中分數
{market_score}

三、今日策略
{strategy}

四、強勢觀察
{", ".join(strong) if strong else "目前無明顯強勢股"}

五、弱勢警戒
{", ".join(weak) if weak else "目前無明顯弱勢股"}

六、爆量名單
{", ".join(explosive) if explosive else "目前無明顯爆量股"}

七、盤中異動明細
{chr(10).join(all_alerts)}

八、紀律官提醒
- 不追高
- 不攤平
- 不摸頭
- 等量價確認
- OTC轉弱時，中小型股風險升高
- 台積電轉弱時，大盤容易受壓
- 爆量長黑視為高風險訊號

⚠️ 本訊息僅供觀察，不是投資建議。
"""
else:
    message = f"""
📡 台股AI盤中監控 V3

時間：{now}

目前無重大異動。

盤勢狀態：
⚪ 觀察盤

紀律提醒：
- 不急著出手
- 等主流族群明確
- 等加權、OTC、台積電同步確認
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
