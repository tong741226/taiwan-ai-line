import os
import requests
import yfinance as yf
import feedparser
import pandas as pd
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_price(symbol, name):
    try:
        data = yf.Ticker(symbol)
        hist = data.history(period="7d").dropna()

        if len(hist) < 2:
            return {
                "name": name,
                "price": "無資料",
                "change": 0,
                "percent": 0,
                "text": f"{name}: 無資料"
            }

        close = round(hist["Close"].iloc[-1], 2)
        prev = round(hist["Close"].iloc[-2], 2)
        change = round(close - prev, 2)
        percent = round((change / prev) * 100, 2)

        return {
            "name": name,
            "price": close,
            "change": change,
            "percent": percent,
            "text": f"{name}: {close} ({change}, {percent}%)"
        }

    except Exception as e:
        return {
            "name": name,
            "price": "抓取失敗",
            "change": 0,
            "percent": 0,
            "text": f"{name}: 抓取失敗"
        }


def get_news():
    news_url = "https://news.google.com/rss/search?q=美股+台股+聯準會+AI+半導體&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(news_url)

    titles = []
    text = ""

    for i, entry in enumerate(feed.entries[:6], start=1):
        titles.append(entry.title)
        text += f"{i}. {entry.title}\n"

    return titles, text


def get_taifex_night_market():
    try:
        url = "https://www.taifex.com.tw/cht/index"
        tables = pd.read_html(url)

        for table in tables:
            table_text = table.astype(str).to_string()
            if "臺股期貨" in table_text or "夜盤商品行情表" in table_text:
                return "台指夜盤：請以TAIFEX最新資料確認"

        return "台指夜盤：暫無資料"

    except Exception:
        return "台指夜盤：抓取失敗"


def score_market(us_items, tw_items, news_titles):
    score = 0
    reasons = []

    for item in us_items:
        pct = item["percent"]
        if pct >= 1:
            score += 2
        elif pct > 0:
            score += 1
        elif pct <= -1:
            score -= 2
        elif pct < 0:
            score -= 1

    for item in tw_items:
        pct = item["percent"]
        if pct >= 1:
            score += 2
        elif pct > 0:
            score += 1
        elif pct <= -1:
            score -= 2
        elif pct < 0:
            score -= 1

    news_all = " ".join(news_titles)

    positive_words = ["AI", "半導體", "降息", "創新高", "反彈", "科技股", "資金回流", "NVIDIA"]
    negative_words = ["通膨", "升息", "戰爭", "油價飆升", "衰退", "美股收黑", "賣壓", "承壓"]

    for word in positive_words:
        if word in news_all:
            score += 1
            reasons.append(f"正向：{word}")

    for word in negative_words:
        if word in news_all:
            score -= 1
            reasons.append(f"風險：{word}")

    return score, reasons[:6]


def commander_view(score):
    if score >= 8:
        return "🟢 偏多", "80%", "🟡 中", "今日可交易，但禁止開盤追價。"
    elif score >= 4:
        return "🟡 中性偏多", "65%", "🟡 中", "可觀察強勢族群，等9:15後確認。"
    elif score >= 0:
        return "⚪ 震盪", "45%", "🟠 中高", "多空不明，先觀察不急著出手。"
    else:
        return "🔴 偏空", "25%", "🔴 高", "今日防守優先，降低出手次數。"


def industry_view(score):
    if score >= 4:
        return """
AI Server：★★★★☆
散熱：★★★★☆
PCB / CPO：★★★☆☆
記憶體：★★★☆☆
金融：★★☆☆☆
航運：觀察
"""
    elif score >= 0:
        return """
AI Server：★★★☆☆
散熱：★★★☆☆
PCB / CPO：★★☆☆☆
記憶體：★★☆☆☆
金融：★★☆☆☆
航運：觀察
"""
    else:
        return """
AI Server：★★☆☆☆
散熱：★★☆☆☆
PCB / CPO：★☆☆☆☆
記憶體：★☆☆☆☆
金融：防守觀察
航運：觀察
"""


def sniper_view(score):
    if score >= 4:
        return """
今日觀察：
- 2330 台積電
- 2382 廣達
- 3231 緯創
- 6669 緯穎
- 3017 奇鋐

條件：
- 不追開高第一根
- 等9:15後量價確認
- 強勢股回測不破再觀察
"""
    else:
        return """
今日觀察：
- 台積電是否穩住大盤
- OTC是否轉弱
- AI族群是否續強

條件：
- 無量不追
- 開高走低不追
- 指數不同步不進場
"""


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    res = requests.post(url, json=payload)

    print("Telegram status:", res.status_code)
    print("Telegram response:", res.text)
    print(message)


now = datetime.now().strftime("%Y-%m-%d %H:%M")

news_titles, news_text = get_news()

us_items = [
    get_price("^DJI", "道瓊"),
    get_price("^IXIC", "NASDAQ"),
    get_price("^GSPC", "S&P500"),
    get_price("^SOX", "費城半導體"),
    get_price("NVDA", "NVIDIA"),
]

tw_items = [
    get_price("^TWII", "台灣加權"),
    get_price("^TWOII", "OTC櫃買"),
    get_price("2330.TW", "台積電"),
]

night_market = get_taifex_night_market()

score, reasons = score_market(us_items, tw_items, news_titles)
direction, tradable, risk, commander_note = commander_view(score)

message = f"""
📣 台股AI操盤總指揮｜Telegram晨報

時間：{now}

====================
🎖️ 一、總指揮結論
====================

今日盤勢：{direction}
可交易度：{tradable}
風險等級：{risk}

總指揮判斷：
{commander_note}

盤前分數：{score}

====================
🕵️ 二、情資官｜全球市場
====================

🇺🇸 美股四大指數
{us_items[0]["text"]}
{us_items[1]["text"]}
{us_items[2]["text"]}
{us_items[3]["text"]}

NVIDIA：
{us_items[4]["text"]}

🌙 台指夜盤
{night_market}

====================
📈 三、技術官｜台股結構
====================

{tw_items[0]["text"]}
{tw_items[1]["text"]}
{tw_items[2]["text"]}

技術官判斷：
- 加權、OTC、台積電三者同步走強，才視為多方確認
- 若加權漲但OTC弱，中小型股當沖風險升高
- 若台積電轉弱，大盤容易受壓

====================
🏭 四、產業官｜族群輪動
====================

{industry_view(score)}

今日主流判斷：
- 優先觀察 AI Server、散熱、半導體
- 若資金無法延續，避免追高題材股

====================
🎯 五、狙擊官｜今日觀察
====================

{sniper_view(score)}

====================
🛡️ 六、風控官｜紀律提醒
====================

09:00～09:15：
- 禁止追價
- 不搶第一根
- 等加權、OTC、台積電同步確認

09:15～09:30：
- 確認量價是否延續
- 若開高走低，降低出手
- 若OTC轉弱，避開中小型股追高

停損紀律：
- 不攤平
- 不摸頭
- 不抄底
- 不追無量突破

====================
📰 七、重大新聞
====================

{news_text}

====================
📌 八、總指揮操盤結論
====================

今日重點不是預測，而是確認。

只做三件事：
1. 看加權是否站穩
2. 看OTC是否同步
3. 看台積電是否撐盤

三者同步，才有短線交易價值。
若不同步，觀望比出手重要。

⚠️ 本報告僅供觀察，不是投資建議。
"""

send_telegram(message)
