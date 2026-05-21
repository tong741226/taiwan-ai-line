import os
import requests
import yfinance as yf
import feedparser

# =========================
# LINE TOKEN
# =========================

LINE_TOKEN = os.environ.get("LINE_TOKEN")

# =========================
# 抓資料
# =========================

def get_price(symbol, name):

    data = yf.Ticker(symbol)
    hist = data.history(period="7d")
    hist = hist.dropna()

    if len(hist) < 2:
        return f"{name}: 無資料"

    close = round(hist["Close"].iloc[-1], 2)
    prev = round(hist["Close"].iloc[-2], 2)

    change = round(close - prev, 2)
    percent = round((change / prev) * 100, 2)

    return f"{name}: {close} ({change}, {percent}%)"

# =========================
# 重大新聞
# =========================

news_url = "https://news.google.com/rss/search?q=美股+台股+聯準會&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

feed = feedparser.parse(news_url)

news_text = ""

for i, entry in enumerate(feed.entries[:5], start=1):
    news_text += f"{i}. {entry.title}\n"

# =========================
# 訊息內容
# =========================

message = f"""
📰 重大總經新聞
{news_text}

🇺🇸 美股四大指數
{get_price("^DJI", "道瓊")}
{get_price("^IXIC", "NASDAQ")}
{get_price("^GSPC", "S&P500")}
{get_price("^SOX", "費城半導體")}

🇹🇼 台灣市場
{get_price("^TWII", "加權指數")}
{get_price("^TWOII", "櫃買指數")}
{get_price("TXF=F", "台指夜盤")}
"""

# =========================
# LINE 推播
# =========================

url = "https://api.line.me/v2/bot/message/broadcast"

headers = {
    "Authorization": f"Bearer {LINE_TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "messages": [
        {
            "type": "text",
            "text": message
        }
    ]
}

res = requests.post(url, headers=headers, json=payload)

print(res.status_code)
print(res.text)