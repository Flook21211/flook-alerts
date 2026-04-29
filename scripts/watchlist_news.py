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

# --- Config from GitHub Secrets ---
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

# --- Date in Thai ---
tz = pytz.timezone('Asia/Bangkok')
now = datetime.now(tz)
thai_months = {
    1: 'ม.ค.', 2: 'ก.พ.', 3: 'มี.ค.', 4: 'เม.ย.',
    5: 'พ.ค.', 6: 'มิ.ย.', 7: 'ก.ค.', 8: 'ส.ค.',
    9: 'ก.ย.', 10: 'ต.ค.', 11: 'พ.ย.', 12: 'ธ.ค.'
}
thai_year = now.year + 543
date_str = f"{now.day} {thai_months[now.month]} {thai_year}"


# --- Search news ---
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
        return f"(ค้นไม่ได้: {e})"


# --- Calculate RSI ---
def calc_rsi(prices, period=14):
    try:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 1)
    except:
        return None


# --- Fetch technical data ---
def get_tech_data(tickers):
    lines = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period='3mo')
            if hist.empty:
                continue
            price = round(hist['Close'].iloc[-1], 2)
            prev = round(hist['Close'].iloc[-2], 2)
            chg = round((price - prev) / prev * 100, 2)
            ma50 = round(hist['Close'].rolling(50).mean().iloc[-1], 2)
            ma200 = round(hist['Close'].rolling(200).mean().iloc[-1], 2) if len(hist) >= 200 else None
            rsi = calc_rsi(hist['Close'])

            ma50_status = '✅ เหนือ MA50' if price > ma50 else '❌ ต่ำกว่า MA50'
            ma200_status = ''
            if ma200:
                ma200_status = ' | ✅ เหนือ MA200' if price > ma200 else ' | ❌ ต่ำกว่า MA200'

            chg_str = f'+{chg}%' if chg >= 0 else f'{chg}%'
            rsi_str = f'RSI {rsi}' if rsi else 'RSI N/A'

            lines.append(f"{ticker}: ${price} ({chg_str}) | {rsi_str} | {ma50_status}{ma200_status}")
        except Exception as e:
            lines.append(f"{ticker}: (ดึงข้อมูลไม่ได้: {e})")
    return '\n'.join(lines)


month_year = now.strftime('%B %Y')
today = now.strftime('%Y-%m-%d')
top_stocks = ' '.join(all_stocks[:15])

    # แบ่งหุ้นเป็นกลุ่มย่อยสำหรับ search
growth1 = 'NVDA MSFT CRWD PLTR TSM ASML ARM AMD AVGO AAPL FICO TSLA'
growth2 = 'AMZN HIMS META GOOGL NFLX MRVL CSCO MU LRCX INTC'
growth3 = 'SNPS CDNS ONTO AMAT KLAC PANW SHOP APP ZETA UBER'
growth4 = 'EOSE ONDS ASTS BE NXT BA GE RTX ABBV OKLO'
defensive = 'COST LLY NVO ISRG UNH NEE PEP KO WMT PG BRK.B V MRK LMT WM DUK'
dividend = 'PFE CVX XOM O'
speculative = 'RKLB TEM NVTS NBIS SOFI ENPH FSLR'

# --- Run searches 
searches = {
    'Fed/FOMC': search_news(f'Fed FOMC interest rate decision policy {month_year}', 5),
    'BOT': search_news(f'Bank of Thailand interest rate monetary policy {month_year}', 3),
    'US Market': search_news(f'US stock market S&P500 Nasdaq today {today}', 5),
    'Gold': search_news(f'gold price XAU today {today}', 3),
    'DXY': search_news(f'DXY dollar index US dollar strength today {today}', 3),
    'USD/THB': search_news(f'USD THB dollar baht exchange rate today {today}', 3),
    'VIX': search_news(f'VIX volatility fear index market today {today}', 3),
    'Oil': search_news(f'crude oil WTI Brent price today {today}', 3),
    'Earnings': search_news(f'earnings report results this week {growth1}', 5),
    'Growth1': search_news(f'{growth1} stock news {today}', 10),
    'Growth2': search_news(f'{growth2} stock news {today}', 10),
    'Growth3': search_news(f'{growth3} stock news {today}', 10),
    'Growth4': search_news(f'{growth4} stock news {today}', 10),
    'Defensive': search_news(f'{defensive} stock news {today}', 10),
    'Dividend': search_news(f'{dividend} stock news {today}', 5),
    'Speculative': search_news(f'{speculative} stock news {today}', 10),
}

search_context = '\n\n'.join([f"=== {k} ===\n{v}" for k, v in searches.items()])

# --- Fetch technical data for key stocks ---
key_stocks = all_stocks
tech_data = ''
if HAS_YF:
    print("Fetching technical data...")
    tech_data = get_tech_data(key_stocks)
    print(tech_data)

# --- Groq summarize ---
prompt = f"""คุณคือ AI ช่วยนักลงทุนไทย สรุปข่าวเป็นภาษาไทย กระชับ อ่านง่าย
วันนี้คือ {date_str}

ข้อมูลข่าวล่าสุด:
{search_context}

ข้อมูล Technical (ราคา, % เปลี่ยน, RSI, MA50, MA200):
{tech_data if tech_data else '(ไม่มีข้อมูล technical)'}

หุ้นใน watchlist: {', '.join(all_stocks)}

สร้างข้อความตามรูปแบบนี้ (ตอบแค่ข้อความเท่านั้น ไม่ต้องอธิบายเพิ่ม ไม่เกิน 4000 ตัวอักษร):

📊 Watchlist News Alert
📅 {date_str}
━━━━━━━━━━━━━━━━━
[ถ้ามี earnings วันนี้/สัปดาห์นี้ ใส่:]
🚨 EARNINGS WEEK
[ticker — วันที่ — EPS ถ้ามี]
━━━━━━━━━━━━━━━━━
📌 ข่าว + ทิศทางหุ้น
(ใส่ 15-20 ตัว แต่ละตัว 2-3 ประโยค + ทิศทาง)

🟢📈 [ticker] $[ราคา] — [ข่าวดี + RSI + MA บอกทิศทาง]
🔴📉 [ticker] $[ราคา] — [ข่าวร้าย + RSI + MA บอกทิศทาง]
⚪➡️ [ticker] $[ราคา] — [ข่าวกลาง + RSI + MA บอกทิศทาง]

━━━━━━━━━━━━━━━━━
📊 สรุปทิศทาง (Bias วันนี้)

📈 Bullish: [ticker, ticker, ...]
📉 Bearish: [ticker, ticker, ...]
➡️ Neutral: [ticker, ticker, ...]

━━━━━━━━━━━━━━━━━
🌍 Macro

🏦 Fed/FOMC: [สรุปนโยบายดอกเบี้ย]
🏦 BOT: [สรุปธนาคารแห่งประเทศไทย]
📈 S&P500/Nasdaq: [ทิศทางตลาด]
💵 DXY: [ค่า Dollar Index + ทิศทาง]
💱 USD/THB: [อัตราแลกเปลี่ยน]
😱 VIX: [ระดับ VIX + ความหมาย]
🛢️ Oil: [ราคาน้ำมัน WTI/Brent]
🥇 Gold: [ราคาทอง]

💡 จับตา: [5 สิ่งสำคัญที่ต้องติดตามวันนี้]"""

groq_resp = requests.post(
    'https://api.groq.com/openai/v1/chat/completions',
    headers={
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        'model': 'llama-3.3-70b-versatile',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 4000,
        'temperature': 0.3
    },
    timeout=60
)

result = groq_resp.json()
print("Groq response:", result)
message = result['choices'][0]['message']['content'].strip()

# --- Send LINE ---
line_resp = requests.post(
    'https://api.line.me/v2/bot/message/push',
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_TOKEN}'
    },
    json={
        'to': LINE_USER_ID,
        'messages': [{'type': 'text', 'text': message}]
    },
    timeout=10
)

print(f"LINE status: {line_resp.status_code}")
print(message)
