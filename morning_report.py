import os
import requests
import yfinance as yf
import feedparser
import google.generativeai as genai

LINE_TOKEN = os.getenv("LINE_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_price(symbol, name):
    try:
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
    except Exception as e:
        return f"{name}: 抓取失敗"


news_url = "https://news.google.com/rss/search?q=美股+台股+聯準會&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
feed = feedparser.parse(news_url)

news_text = ""
for i, entry in enumerate(feed.entries[:5], start=1):
    news_text += f"{i}. {entry.title}\n"


raw_market_text = f"""
📰 重大新聞
{news_text}

🇺🇸 美股四大指數
{get_price("^DJI", "道瓊")}
{get_price("^IXIC", "NASDAQ")}
{get_price("^GSPC", "S&P500")}
{get_price("^SOX", "費城半導體")}

🇹🇼 台灣市場
{get_price("^TWII", "台灣加權指數")}
{get_price("^TWOII", "櫃買指數")}
{get_price("TXF=F", "台指夜盤")}
"""


def ai_analysis(raw_text):
    if not GEMINI_API_KEY:
        return "AI分析：未設定 GEMINI_API_KEY"

    try:
        genai.configure(api_key=GEMINI_API_KEY)

        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
你是一位台股盤前分析助理。
請根據以下資料，產出簡短盤前分析：

{raw_text}

請用繁體中文輸出：
1. 今日盤勢重點
2. 多空判斷：偏多 / 偏空 / 震盪
3. 台股操作提醒
4. 風險提醒

不要給明確買賣建議，不要保證漲跌。
"""

        genai.configure(api_key=GEMINI_API_KEY)

        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        return f"AI分析失敗：{e}"


ai_text = ai_analysis(raw_market_text)

message = f"""
🧠 AI盤前分析
{ai_text}

{raw_market_text}
"""


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
print(message)
# test
