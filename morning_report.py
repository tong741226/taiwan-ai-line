import os
import requests
import yfinance as yf
import feedparser
import pandas as pd
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_price(symbol, name):
    try:
        data = yf.Ticker(symbol)
        hist = data.history(period="7d").dropna()

        if len(hist) < 2:
            return f"{name}: 無資料"

        close = round(hist["Close"].iloc[-1], 2)
        prev = round(hist["Close"].iloc[-2], 2)
        change = round(close - prev, 2)
        percent = round((change / prev) * 100, 2)

        return f"{name}: {close} ({change}, {percent}%)"

    except Exception as e:
        return f"{name}: 抓取失敗：{e}"


def get_taifex_night_market():
    try:
        url = "https://www.taifex.com.tw/cht/index"
        tables = pd.read_html(url)

        for table in tables:
            text = table.astype(str).to_string()

            if "夜盤商品行情表" in text or "臺股期貨" in text:
                return f"台指夜盤（TAIFEX）\n{table.head(5).to_string()}"

        return "台指夜盤：TAIFEX無資料"

    except Exception as e:
        return f"台指夜盤抓取失敗：{e}"


def get_percent(text):
    try:
        return float(text.split(",")[-1].replace("%)", "").strip())
    except Exception:
        return None


def rule_analysis(market_items, news_titles):
    score = 0
    reasons = []

    for item in market_items:
        pct = get_percent(item)
        if pct is None:
            continue

        if pct > 1:
            score += 2
        elif pct > 0:
            score += 1
        elif pct < -1:
            score -= 2
        elif pct < 0:
            score -= 1

    news_all = " ".join(news_titles)

    positive_words = ["降息", "反彈", "創新高", "法人買", "AI", "半導體", "科技股", "資金回流"]
    negative_words = ["升息", "油價飆升", "戰爭", "通膨", "衰退", "美股收黑", "承壓", "賣壓"]

    for word in positive_words:
        if word in news_all:
            score += 1
            reasons.append(f"正向訊號：{word}")

    for word in negative_words:
        if word in news_all:
            score -= 1
            reasons.append(f"風險訊號：{word}")

    if score >= 6:
        direction = "偏多"
        view = "美股與台股動能偏強，今日有機會延續多方氣氛。"
    elif score >= 3:
        direction = "中性偏多"
        view = "市場氣氛偏正向，但仍需留意開高後震盪。"
    elif score >= 0:
        direction = "震盪"
        view = "多空訊號不完全一致，今日較可能震盪整理。"
    else:
        direction = "偏空"
        view = "市場風險訊號較多，今日操作宜保守。"

    reason_text = "\n".join(reasons[:6]) if reasons else "依美股、台股漲跌與新聞標題綜合判斷。"

    return f"""
一、總指揮結論
{view}

二、多空判斷
今日盤勢：{direction}
盤前分數：{score}

三、台股操作提醒
- 09:00～09:15 不急著追價
- 先觀察加權、櫃買、台指期是否同步走強
- 若開高走低，避免追高
- 強勢股等回測不破再觀察
- 優先留意 AI、半導體、電子權值與強勢中小型股

四、風險提醒
- 若美股雖漲但台股開盤無法延續，代表追價意願不足
- 若櫃買轉弱，中小型股當沖風險升高
- 若台指期快速翻黑，應降低出手次數

判斷依據：
{reason_text}
"""


news_url = "https://news.google.com/rss/search?q=美股+台股+聯準會&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
feed = feedparser.parse(news_url)

news_titles = []
news_text = ""

for i, entry in enumerate(feed.entries[:5], start=1):
    news_titles.append(entry.title)
    news_text += f"{i}. {entry.title}\n"

night_market = get_taifex_night_market()

market_items = [
    get_price("^DJI", "道瓊"),
    get_price("^IXIC", "NASDAQ"),
    get_price("^GSPC", "S&P500"),
    get_price("^SOX", "費城半導體"),
    get_price("^TWII", "台灣加權指數"),
    get_price("^TWOII", "櫃買指數"),
    get_price("^TWII", "台指期夜盤參考"),
]

raw_market_text = f"""
📰 重大新聞
{news_text}

🇺🇸 美股四大指數
{market_items[0]}
{market_items[1]}
{market_items[2]}
{market_items[3]}

🇹🇼 台灣市場
{market_items[4]}
{market_items[5]}
{market_items[6]}

🌙 台指夜盤
{night_market}
"""

analysis_text = rule_analysis(market_items, news_titles)

message = f"""
📢 台股AI操盤總指揮｜Telegram晨報

🧠 盤前分析
{analysis_text}

{raw_market_text}

⚠️ 本報告僅供參考，非投資建議。
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
