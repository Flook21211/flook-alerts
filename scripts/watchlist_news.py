import os
import json
import requests
from datetime import datetime
import pytz

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
        return f"(ค้นไม่ได้: {e})"


month_year = now.strftime('%B %Y')
today = now.strftime('%Y-%m-%d')
top_stocks = ' '.join(all_stocks[:15])

searches = {
    'Fed/FOMC': search_news(f'Fed FOMC interest rate decision policy {month_year}', 10),
    'BOT': search_news(f'Bank of Thailand interest rate monetary policy {month_year}', 10),
    'US Market': search_news(f'US stock market S&P500 Nasdaq today {today}', 10),
    'Gold': search_news(f'gold price XAU today {today}', 5),
    'DXY': search_news(f'DXY dollar index US dollar strength today {today}', 5),
    'USD/THB': search_news(f'USD THB dollar baht exchange rate today {today}', 5),
    'VIX': search_news(f'VIX volatility fear index market today {today}', 5),
    'Oil': search_news(f'crude oil WTI Brent price today {today}', 5),
    'Earnings': search_news(f'earnings report results this week {top_stocks}', 10),
    'Watchlist1': search_news(f'NVDA MSFT META GOOGL AAPL TSLA AVGO TSM stock news {today}', 15),
    'Watchlist2': search_news(f'AMZN CRWD PLTR ARM AMD ASML NFLX COST stock news {today}', 15),
}

search_context = '\n\n'.join([f"=== {k} ===\n{v}" for k, v in searches.items()])

# --- Groq summarize ---
prompt = f"""คุณคือ AI ช่วยนักลงทุนไทย สรุปข่าวเป็นภาษาไทย กระชับ อ่านง่าย
วันนี้คือ {date_str}

ข้อมูลข่าวล่าสุด:
{search_context}

หุ้นใน watchlist: {', '.join(all_stocks)}

สร้างข้อความตามรูปแบบนี้ (ตอบแค่ข้อความเท่านั้น ไม่ต้องอธิบายเพิ่ม ไม่เกิน 5000 ตัวอักษร):

📊 Watchlist News Alert
📅 {date_str}
━━━━━━━━━━━━━━━━━
[ถ้ามี earnings วันนี้/สัปดาห์นี้ ใส่:]
🚨 EARNINGS WEEK
[ticker — วันที่ — EPS ถ้ามี]
━━━━━━━━━━━━━━━━━
📌 ข่าวหุ้นใน Watchlist
(ใส่ให้ครบ 10-15 ตัว แต่ละตัว 2-3 ประโยค พร้อม % ถ้ามี)

🟢 [ticker] — [ข่าวดี รายละเอียด]
🔴 [ticker] — [ข่าวร้าย รายละเอียด]
⚪ [ticker] — [ข่าวกลาง รายละเอียด]

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
