from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os

import yfinance as yf
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import MACD

app = FastAPI()

# =========================
# Request Model
# =========================
class StockRequest(BaseModel):
    message: str


# =========================
# 股票代碼轉換
# =========================
def normalize_symbol(text: str):
    code = "".join([c for c in text if c.isdigit()])

    if len(code) == 4:
        return code + ".TW"

    return code


# =========================
# AI 分數計算
# =========================
def calculate_score(
    latest_close,
    ma5,
    ma20,
    ma60,
    rsi,
    macd,
    macd_signal,
    volume_ratio
):
    score = 50
    reasons = []

    if latest_close > ma5:
        score += 5
        reasons.append("站上5日線")

    if latest_close > ma20:
        score += 10
        reasons.append("站上20日線")

    if latest_close > ma60:
        score += 15
        reasons.append("站上60日線")

    if rsi > 60:
        score += 10
        reasons.append("RSI強勢")
    elif rsi < 40:
        score -= 10
        reasons.append("RSI偏弱")

    if macd > macd_signal:
        score += 10
        reasons.append("MACD黃金交叉")
    else:
        score -= 10
        reasons.append("MACD偏空")

    if volume_ratio > 1.2:
        score += 10
        reasons.append("量能放大")
    elif volume_ratio < 0.8:
        score -= 5
        reasons.append("量能不足")

    score = max(0, min(100, score))

    return score, reasons


# =========================
# 個股分析 API
# =========================
@app.post("/analyze")
def analyze_stock(req: StockRequest):
    try:
        raw = req.message.strip()
        symbol = normalize_symbol(raw)

        data = yf.download(
            symbol,
            period="3mo",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if data.empty:
            return {"reply": f"查不到股票資料：{raw}"}

        close = data["Close"].squeeze()
        volume = data["Volume"].squeeze()

        latest_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        change_pct = ((latest_close - prev_close) / prev_close) * 100

        ma5 = float(close.tail(5).mean())
        ma20 = float(close.tail(20).mean())
        ma60 = float(close.tail(60).mean())

        rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])

        macd_obj = MACD(close)
        macd = float(macd_obj.macd().iloc[-1])
        macd_signal = float(macd_obj.macd_signal().iloc[-1])
        macd_hist = float(macd_obj.macd_diff().iloc[-1])

        avg_volume = float(volume.tail(20).mean())
        latest_volume = float(volume.iloc[-1])
        volume_ratio = latest_volume / avg_volume

        score, reasons = calculate_score(
            latest_close,
            ma5,
            ma20,
            ma60,
            rsi,
            macd,
            macd_signal,
            volume_ratio
        )

        if score >= 80:
            signal = "強多"
        elif score >= 65:
            signal = "偏多"
        elif score >= 45:
            signal = "震盪"
        elif score >= 30:
            signal = "偏空"
        else:
            signal = "強空"

        rule_reply = f"""
【台股 AI 分析】

股票：{raw}
Yahoo代碼：{symbol}

收盤價：{latest_close:.2f}
漲跌幅：{change_pct:.2f}%

5日線：{ma5:.2f}
20日線：{ma20:.2f}
60日線：{ma60:.2f}

RSI：{rsi:.2f}

MACD：{macd:.3f}
MACD Signal：{macd_signal:.3f}
MACD Hist：{macd_hist:.3f}

量能比：{volume_ratio:.2f}

AI分數：{score}/100
AI判斷：{signal}

分析理由：
{chr(10).join(["- " + r for r in reasons])}
"""

        prompt = f"""
你是專業台股 AI 分析師，擅長技術分析、短線交易、當沖判斷與風險控管。

請根據以下資料分析股票：

{rule_reply}

請輸出：
1. 技術面分析
2. 多空方向
3. 短線觀察重點
4. 風險提醒
5. 操作建議

請用台股交易員口吻，簡潔、實戰、清楚回答。
"""

        response = gemini_model.generate_content(prompt)
        gemini_text = response.text

        return {
            "reply": rule_reply + "\n\n【Gemini AI 分析】\n" + gemini_text
        }

    except Exception as e:
        return {
            "reply": f"系統錯誤：{str(e)}"
        }


# =========================
# 大盤分析 API
# =========================
@app.get("/market")
def market_analysis():
    try:
        twii = yf.download(
            "^TWII",
            period="1mo",
            progress=False
        )

        close = twii["Close"].squeeze()

        latest = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        change = ((latest - prev) / prev) * 100

        if change > 1:
            mood = "市場偏強"
        elif change < -1:
            mood = "市場偏弱"
        else:
            mood = "市場震盪"

        return {
            "market": "TAIEX",
            "close": round(latest, 2),
            "change_percent": round(change, 2),
            "mood": mood
        }

    except Exception as e:
        return {
            "error": str(e)
        }


# =========================
# AI Team API
# =========================
@app.get("/ai-team")
def ai_team():
    market = market_analysis()

    return {
        "總指揮": {
            "市場情緒": market.get("mood"),
            "大盤": market.get("close")
        },
        "情資官": {
            "狀態": "已啟動"
        },
        "技術官": {
            "狀態": "已啟動"
        },
        "風控官": {
            "狀態": "已啟動"
        }
    }
