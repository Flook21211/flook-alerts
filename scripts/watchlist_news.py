import os
import json
import requests
from datetime import datetime
import pytz

try:
    import yfinance as yf
    import pandas as pd
    HAS_YF = True
except ImportError:
    HAS_YF = False

# --- Config ---
GROQ_API_KEY = os.environ['GROQ_API_KEY']
SERPER_API_KEY = os.environ['SERPER_API_KEY']
LINE_TOKEN = os.environ['LINE_TOKEN']
LINE_USER_ID = os.environ['LINE_USER_ID']

# --- Load watchlist ---
with open('data/watchlist.json', 'r') as f:
    data = json.load(f)

all_stocks = []
for category, tickers in data['watchlist']['stocks'].items():
    all_stocks.extend(tickers)

# --- Date ---
tz = pytz.timezone('Asia/Bangkok')
now = datetime.now(tz)
thai_months = {
    1: 'ม.ค.', 2: 'ก.พ.', 3: 'มี.ค.', 4: 'เม.ย.',
    5: 'พ.ค.', 6: 'มิ.ย.', 7: 'ก.ค.', 8: 'ส.ค.',
    9: 'ก.ย.', 10: 'ต.ค.', 11: 'พ.ย.', 12: 'ธ.ค.'
}
thai_year = now.year + 543
date_str = f"{now.day} {thai_months[now.month]} {thai_year}"
month_year = now.strftime('%B %Y')
today = now.strftime('%Y-%m-%d')


# --- Search ---
def search_news(query, num=10):
    try:
        resp = requests.post(
            'https://google.serper.dev/news',
            headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'},
            json={'q': query, 'num': num},
            timeout=10
        )
        results = resp.json().get('news', [])
        return '\n'.join([f"- {r['title']}: {r.get('snippet', '')}" for r in results[:num]])
    except Exception as e:
        return f"(error: {e})"


# --- RSI ---
def calc_rsi(prices, period=14):
    try:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 1)
    except Exception:
        return None


# --- Technical data ---
def get_tech_data(tickers):
    lines = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period='6mo')
            if hist.empty:
                continue
            price = round(hist['Close'].iloc[-1], 2)
            prev = round(hist['Close'].iloc[-2], 2)
            chg = round((price - prev) / prev * 100, 2)
            ma50 = round(hist['Close'].rolling(50).mean().iloc[-1], 2)
            rsi = calc_rsi(hist['Close'])
            ma50_status = 'above MA50' if price > ma50 else 'below MA50'
            chg_str = f'+{chg}%' if chg >= 0 else f'{chg}%'
            rsi_str = f'RSI {rsi}' if rsi else 'RSI N/A'
            if len(hist) >= 200:
                ma200 = round(hist['Close'].rolling(200).mean().iloc[-1], 2)
                ma200_label = 'above MA200' if price > ma200 else 'below MA200'
                ma200_status = f' | {ma200_label}'
            else:
                ma200_status = ''
            avg_vol = int(hist['Volume'].rolling(20).mean().iloc[-1])
            today_vol = int(hist['Volume'].iloc[-1])
            vol_ratio = round(today_vol / avg_vol, 1) if avg_vol > 0 else 0
            vol_str = f'Vol {vol_ratio}x avg'
            lines.append(f"{ticker}: ${price} ({chg_str}) | {rsi_str} | {ma50_status}{ma200_status} | {vol_str}")
        except Exception as e:
            lines.append(f"{ticker}: (error: {e})")
    return '\n'.join(lines)


# --- Stock groups ---
growth1 = 'NVDA MSFT AVGO AAPL GOOGL META AMZN TSM ASML LLY NVO FICO'
growth2 = 'CRWD PANW PLTR ARM AMD SNPS CDNS ANET VRT ETN ISRG NFLX'
growth3 = 'MRVL KLAC LRCX AMAT ONTO MU WDC COHR GLW LITE INTC'
growth4 = 'SHOP UBER APP ZETA HIMS TEM SOFI MXT ENPH FSLR TSLA BA'
defensive = 'COST WMT KO PEP PG BRK.B WM UNH MRK ABBV LMT RTX'
dividend = 'O CVX XOM PFE DUK NEE V GE CSCO'
speculative = 'ASTS RKLB OKLO EOSE ONDS NVTS NBIS BE'

# --- Searches ---
searches = {
    'Fed/FOMC': search_news(f'Fed FOMC interest rate decision policy {month_year}', 5),
    'BOT': search_news(f'Bank of Thailand interest rate monetary policy {month_year}', 5),
    'US Market': search_news(f'US stock market S&P500 Nasdaq today {today}', 5),
    'Gold': search_news(f'gold price XAU today {today}', 3),
    'DXY': search_news(f'DXY dollar index US dollar strength today {today}', 3),
    'USD/THB': search_news(f'USD THB dollar baht exchange rate today {today}', 3),
    'VIX': search_news(f'VIX volatility fear index market today {today}', 3),
    'Oil': search_news(f'crude oil WTI Brent price today {today}', 3),
    'Earnings1': search_news(f'earnings report results this week {growth1}', 5),
    'Earnings2': search_news(f'earnings report results this week {growth2}', 5),
    'Earnings3': search_news(f'earnings report results this week {growth3}', 5),
    'Earnings4': search_news(f'earnings report results this week {growth4}', 5),
    'EarningsDefensive': search_news(f'earnings report results this week {defensive}', 5),
    'EarningsDividend': search_news(f'earnings report results this week {dividend}', 5),
    'EarningsSpeculative': search_news(f'earnings report results this week {speculative}', 5),
    'Growth1': search_news(f'{growth1} stock news {today}', 5),
    'Growth2': search_news(f'{growth2} stock news {today}', 5),
    'Growth3': search_news(f'{growth3} stock news {today}', 5),
    'Growth4': search_news(f'{growth4} stock news {today}', 5),
    'Defensive': search_news(f'{defensive} stock news {today}', 3),
    'Dividend': search_news(f'{dividend} stock news {today}', 3),
    'Speculative': search_news(f'{speculative} stock news {today}', 3),
    'Treasury': search_news(f'US treasury yield 10 year bond rate today {today}', 5),
}

search_context = '\n\n'.join([f"=== {k} ===\n{v}" for k, v in searches.items()])

stock_context = '\n\n'.join([
    f"=== {k} ===\n{v}" for k, v in searches.items()
    if k not in ('Fed/FOMC', 'BOT', 'US Market', 'Gold', 'DXY', 'USD/THB', 'VIX', 'Oil')
])

# --- Technical ---
tech_data = ''
if HAS_YF:
    print("Fetching technical data...")
    tech_data = get_tech_data(all_stocks)
    print(tech_data)

# --- Groq call ---
def call_groq(prompt_text):
    resp = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': prompt_text}],
            'max_tokens': 3500,
            'temperature': 0.3
        },
        timeout=60
    )
    result = resp.json()
    print("Groq:", result)
    return result['choices'][0]['message']['content'].strip()


# --- Prompt หุ้น ---
prompt_stocks = f"""คุณคือ AI ช่วยนักลงทุนที่มีประสบการณ์มากกว่า20ปี ที่ช่วยวิเคราะห์หุ้นและข่าวเศรษฐกิจ วันนี้คือ {date_str}

ข้อมูลข่าว:
{stock_context}

ข้อมูล Technical:
{tech_data if tech_data else '(ไม่มีข้อมูล)'}

สร้างข้อความ (ตอบแค่ข้อความเท่านั้น ไม่เกิน 4000 ตัวอักษร):

📊 Watchlist News Alert
📅 {date_str}
━━━━━━━━━━━━━━━━━
ถ้ามีหุ้นที่จะประกาศ earnings ใน 7 วันข้างหน้าให้แสดง:
🚨 EARNINGS WEEK
[ticker — วันที่ — EPS ถ้ามี]
━━━━━━━━━━━━━━━━━
ถ้าไม่มี earnings ให้ข้ามส่วนนี้ไปเลย ไม่ต้องแสดงอะไร
━━━━━━━━━━━━━━━━━
📌 ข่าว + ทิศทางหุ้น
(ใส่ให้ครบ 15 ตัวจากทุก category แต่ละตัว 1-2 ประโยค)

🟢📈 [ticker] $[ราคา] ([%]) RSI[xx] — [ข่าว + ทิศทาง]
🔴📉 [ticker] $[ราคา] ([%]) RSI[xx] — [ข่าว + ทิศทาง]
⚪➡️ [ticker] $[ราคา] ([%]) RSI[xx] — [ข่าว + ทิศทาง]

━━━━━━━━━━━━━━━━━
📊 Bias วันนี้
📈 Bullish: [ticker, ...]
📉 Bearish: [ticker, ...]
➡️ Neutral: [ticker, ...]"""

# --- Prompt Macro ---
prompt_macro = f"""คุณคือ AI ช่วยนักลงทุนไทย วันนี้คือ {date_str}

ข้อมูลข่าว Macro:
=== Fed/FOMC ===
{searches.get('Fed/FOMC', '')}

=== BOT ===
{searches.get('BOT', '')}

=== US Market ===
{searches.get('US Market', '')}

=== DXY ===
{searches.get('DXY', '')}

=== USD/THB ===
{searches.get('USD/THB', '')}

=== VIX ===
{searches.get('VIX', '')}

=== Oil ===
{searches.get('Oil', '')}

=== Gold ===
{searches.get('Gold', '')}

=== Treasury ===
{searches.get('Treasury', '')}

สร้างข้อความ (ตอบแค่ข้อความเท่านั้น ไม่เกิน 4000 ตัวอักษร):

🌍 Macro Report
📅 {date_str}
━━━━━━━━━━━━━━━━━
🏦 Fed/FOMC: [สรุปนโยบายดอกเบี้ย]
🏦 BOT: [สรุปธนาคารแห่งประเทศไทย]
📈 S&P500/Nasdaq: [ทิศทางตลาด]
💵 DXY: [ค่า + ทิศทาง]
💱 USD/THB: [อัตรา]
😱 VIX: [ระดับ + ความหมาย]
🛢️ Oil: [ราคา WTI/Brent]
🥇 Gold: [ราคา]
📉 10Y Treasury: [yield + ทิศทาง + ผลต่อหุ้น growth]
━━━━━━━━━━━━━━━━━
💡 จับตา: [5 สิ่งสำคัญวันนี้]"""

# --- Generate messages ---
msg_stocks = call_groq(prompt_stocks)
msg_macro = call_groq(prompt_macro)

# --- LINE ส่ง 2 ข้อความ ---
line_resp = requests.post(
    'https://api.line.me/v2/bot/message/push',
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_TOKEN}'
    },
    json={
        'to': LINE_USER_ID,
        'messages': [
            {'type': 'text', 'text': msg_stocks},
            {'type': 'text', 'text': msg_macro}
        ]
    },
    timeout=10
)

print(f"LINE status: {line_resp.status_code}")
print(msg_stocks)
print(msg_macro)
