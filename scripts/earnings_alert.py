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
date_str = now.strftime('%d/%m/%Y')
month_year = now.strftime('%B %Y')
today = now.strftime('%Y-%m-%d')

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
ถ้าไม่มีให้บอกว่า "ไม่มี earnings สั
