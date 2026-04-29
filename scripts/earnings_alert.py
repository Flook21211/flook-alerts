import os, json, requests
from datetime import datetime
import pytz

GROQ_API_KEY = os.environ['GROQ_API_KEY']
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
date_str = now.strftime('%d/%m/%Y')
month_year = now.strftime('%B %Y')

def search(q):
    try:
        r = requests.post('https://google.serper.dev/news',
            headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'},
            json={'q': q, 'num': 10}, timeout=10)
        return '\n'.join([f"- {x['title']}: {x.get('snippet','')}" for x in r.json().get('news',[])[:8]])
    except: return '(ไม่พบข้อมูล)'

s1 = ' '.join(all_stocks[:20])
s2 = ' '.join(all_stocks[20:])
ctx = '\n\n'.join([
    f"=== Search 1 ===\n{search(f'earnings announcement next 7 days {month_year} {s1}')}",
    f"=== Search 2 ===\n{search(f'earnings release date this week {s2}')}",
    f"=== Calendar ===\n{search(f'earnings calendar {month_year} S&P500 tech')}",
])

prompt = f"""คุณคือ AI ช่วยนักลงทุนไทย วันนี้คือ {date_str}
หุ้นในพอร์ต: {', '.join(all_stocks)}
ข่าว earnings:
{ctx}

สรุปหุ้นในพอร์ตที่จะประกาศ earnings ใน 7 วันข้างหน้า
ถ้าไม่มีให้บอกว่า "ไม่มี earnings สัปดาห์นี้"
ตอบแค่ข้อความส่ง LINE (ห้ามเกิน 800 ตัวอักษร):
📊 Earnings Alert — {date_str}
━━━━━━━━━━━━━━━
[ticker] — [วันที่] — [EPS ถ้ามี]
━━━━━━━━━━━━━━━
[สรุป 1-2 ประโยค]"""

resp = requests.post(
    'https://api.groq.com/openai/v1/chat/completions',
    headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
    json={'model': 'llama-3.3-70b-versatile', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 800},
    timeout=30)
msg = resp.json()['choices'][0]['message']['content'].strip()

r = requests.post('https://api.line.me/v2/bot/message/push',
    headers={'Content-Type':'application/json','Authorization':f'Bearer {LINE_TOKEN}'},
    json={'to': LINE_USER_ID, 'messages': [{'type':'text','text':msg}]}, timeout=10)
print(f"LINE: {r.status_code}")
print(msg)
