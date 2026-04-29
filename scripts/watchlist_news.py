import os, json, requests
from datetime import datetime
import pytz

GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
SERPER_API_KEY = os.environ['SERPER_API_KEY']
LINE_TOKEN = os.environ['LINE_TOKEN']
LINE_USER_ID = os.environ['LINE_USER_ID']

with open('data/watchlist.json') as f:
    data = json.load(f)
all_stocks = []
for tickers in data['watchlist']['stocks'].values():
    all_stocks.extend(tickers)

tz = pytz.timezone('Asia/Bangkok')
now = datetime.now(tz)
thai_months = {1:'ม.ค.',2:'ก.พ.',3:'มี.ค.',4:'เม.ย.',5:'พ.ค.',6:'มิ.ย.',
               7:'ก.ค.',8:'ส.ค.',9:'ก.ย.',10:'ต.ค.',11:'พ.ย.',12:'ธ.ค.'}
date_str = f"{now.day} {thai_months[now.month]} {now.year+543}"

def search(q):
    try:
        r = requests.post('https://google.serper.dev/news',
            headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'},
            json={'q': q, 'num': 5}, timeout=10)
        return '\n'.join([f"- {x['title']}: {x.get('snippet','')}" for x in r.json().get('news',[])[:5]])
    except: return '(ไม่พบข้อมูล)'

today = now.strftime('%Y-%m-%d')
month_year = now.strftime('%B %Y')
ctx = '\n\n'.join([
    f"=== Fed/FOMC ===\n{search(f'Fed FOMC interest rate {month_year}')}",
    f"=== BOT ===\n{search(f'Bank of Thailand interest rate {month_year}')}",
    f"=== US Market ===\n{search(f'US stock market news {today}')}",
    f"=== Gold ===\n{search(f'gold price today {today}')}",
    f"=== Earnings ===\n{search(f'earnings this week {today} NVDA MSFT META GOOGL AAPL TSLA')}",
    f"=== Watchlist ===\n{search(f'NVDA MSFT META GOOGL AAPL TSLA AVGO TSM ASML stock news {today}')}",
])

prompt = f"""คุณคือ AI ช่วยนักลงทุนไทย วันนี้คือ {date_str}
ข้อมูลข่าว:
{ctx}

watchlist: {', '.join(all_stocks)}

สร้างข้อความส่ง LINE ตามรูปแบบนี้ (ห้ามเกิน 1000 ตัวอักษร ตอบแค่ข้อความ):
📊 Watchlist News Alert
📅 {date_str}
━━━━━━━━━━━━━━━━━
🚨 EARNINGS WEEK (ถ้ามี)
[หุ้น + วัน]
━━━━━━━━━━━━━━━━━
📌 ข่าวหุ้นใน Watchlist
🟢 [ticker] — [ข่าวดี]
🔴 [ticker] — [ข่าวร้าย]
⚪ [ticker] — [ข่าวกลาง]
━━━━━━━━━━━━━━━━━
🌍 Macro
- [2-3 ข้อ]
💡 จับตา: [...]"""

resp = requests.post(
    f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}',
    json={'contents': [{'parts': [{'text': prompt}]}]}, timeout=30)
gemini_json = resp.json()
print("Gemini response:", gemini_json)
if 'candidates' not in gemini_json:
    raise Exception(f"Gemini error: {gemini_json}")
msg = gemini_json['candidates'][0]['content']['parts'][0]['text'].strip()

r = requests.post('https://api.line.me/v2/bot/message/push',
    headers={'Content-Type':'application/json','Authorization':f'Bearer {LINE_TOKEN}'},
    json={'to': LINE_USER_ID, 'messages': [{'type':'text','text':msg}]}, timeout=10)
print(f"LINE: {r.status_code}")
print(msg)
