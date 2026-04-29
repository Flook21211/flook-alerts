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
thai_months = {1:'ม.ค.',2:'ก.พ.',3:'มี.ค.',4:'เม.ย.',5:'พ.ค.',6:'มิ.ย.',
               7:'ก.ค.',8:'ส.ค.',9:'ก.ย.',10:'ต.ค.',11:'พ.ย.',12:'ธ.ค.'}
date_str = f"{now.day} {thai_months[now.month]} {now.year+543}"

def search(q):
    try:
        r = requests.post('https://google.serper.dev/news',
            headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'},
            json={'q': q, 'num': 10}, timeout=10)
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

prompt = f"""คุณคือ AI นักหาข่าวและวิเคราะห์ช่วยนักลงทุนไทย วันนี้คือ {date_str}
ข้อมูลข่าว:
{ctx}

watchlist: {', '.join(all_stocks)}

สร้างข้อความส่ง LINE ตามรูปแบบนี้ (ตอบแค่ข้อความเท่านั้น ห้ามเกิน 4000 ตัวอักษร):
📊 Watchlist News Alert
📅 {date_str}
━━━━━━━━━━━━━━━━━
🚨 EARNINGS WEEK (ถ้ามี ระบุวันที่ชัดเจน)
[หุ้น — วันที่จริง — consensus EPS ถ้ามี]
━━━━━━━━━━━━━━━━━
📌 ข่าวหุ้นใน Watchlist (อย่างน้อย 5-7 ตัว แต่ละตัวอธิบาย 2-3 ประโยค )

🟢 [ticker] — [อธิบาย 2-3 ประโยค พร้อมสาเหตุที่หุ้นขึ้น]
🔴 [ticker] — [อธิบาย 2-3 ประโยค พร้อมสาเหตุที่หุ้นลง]
⚪ [ticker] — [อธิบาย 2-3 ประโยค]

━━━━━━━━━━━━━━━━━
🌍 Macro (อธิบายแต่ละข้อ 5 ประโยค พร้อมตัวเลขจริง)

- Fed: [รายละเอียด + ตัวเลขดอกเบี้ย]
- BOT: [รายละเอียด + ตัวเลข]
- ทองคำ: [ราคา + แนวโน้ม]
- ตลาดสหรัฐฯ: [ภาพรวม + ตัวเลข index]

💡 จับตา: [5 ประเด็นที่ต้องติดตามวันนี้]"""

resp = requests.post(
    'https://api.groq.com/openai/v1/chat/completions',
    headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
    json={'model': 'llama-3.3-70b-versatile', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 2500},
    timeout=30)
msg = resp.json()['choices'][0]['message']['content'].strip()

r = requests.post('https://api.line.me/v2/bot/message/push',
    headers={'Content-Type':'application/json','Authorization':f'Bearer {LINE_TOKEN}'},
    json={'to': LINE_USER_ID, 'messages': [{'type':'text','text':msg}]}, timeout=10)
print(f"LINE: {r.status_code}")
print(msg)
