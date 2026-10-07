from telethon import TelegramClient, events
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Web Server အတွက် (App မှ /books.json ကို လှမ်းခေါ်သည့်အခါ စာအုပ်စာရင်းများကို ပို့ပေးမည်)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/books.json' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            if os.path.exists('books.json'):
                with open('books.json', 'r', encoding='utf-8') as f:
                    content = f.read()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.wfile.write(b'[]')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Server is running!")
            
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    server_address = ('', 10000)
    httpd = HTTPServer(server_address, SimpleHandler)
    print("Starting HTTP server on port 10000...")
    httpd.serve_forever()

# Web Server ကို နောက်ကွယ်မှ အမြဲအလုပ်လုပ်နေစေရန် Thread ဖြင့် ဖွင့်ခြင်း
server_thread = threading.Thread(target=run_web_server)
server_thread.daemon = True
server_thread.start()

# Telegram Bot အချက်အလက်များ
api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
channel_username = '@HWP_Bookshelf'

client = TelegramClient('ebook_session', api_id, api_hash)

# Channel ထဲတွင် ရှိသမျှ စာအုပ်ဟောင်းများကို အစအဆုံး အရင်ဖတ်မည့် ဖန်ရှင်
async def scan_all_existing_books():
    books_list = []
    print("🔍 Channel ထဲရှိ စာအုပ်အားလုံးကို စတင်စကန်ဖတ်နေပါပြီ...")
    
    # limit မပါဘဲ (သို့မဟုတ် လိုသလောက် ချိန်၍) ရှိသမျှ မက်ဆေ့ခ်ျများကို အစအဆုံး ဖတ်မည်
    async for message in client.iter_messages(channel_username):
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
                download_link = f"https://t.me/HWP_Bookshelf/{message.id}"
                book_info = {
                    "file_name": message.file.name,
                    "message_id": message.id,
                    "file_size": message.file.size,
                    "download_link": download_link
                }
                # ထပ်နေတာ မရှိစေရန် စစ်ဆေးပြီး ထည့်မည်
                if not any(b['message_id'] == book_info['message_id'] for b in books_list):
                    books_list.append(book_info)
                    
    # message_id အကြီးအငယ်အလိုက် စီပေးခြင်း (အသစ်တွေက အပေါ်ဆုံးရောက်ရန်)
    books_list = sorted(books_list, key=lambda x: x['message_id'], reverse=True)
    
    with open('books.json', 'w', encoding='utf-8') as f:
        json.dump(books_list, f, ensure_ascii=False, indent=4)
    print(f"📚 စုစုပေါင်း စာအုပ် {len(books_list)} အုပ်ကို books.json သို့ အပြည့်အစုံ သိမ်းဆည်းပြီးပါပြီ။")

# ပြီးနောက် update တက်လာသမျှ (စာအုပ်အသစ်များကိုသာ) ဆက်ဖမ်းမည့် စနစ်
@client.on(events.NewMessage(chats=channel_username))
async def my_event_handler(event):
    message = event.message
    if message.file and message.file.name:
        if message.file.name.lower().endswith(('.pdf', '.epub')):
            download_link = f"https://t.me/HWP_Bookshelf/{message.id}"
            new_book = {
                "file_name": message.file.name,
                "message_id": message.id,
                "file_size": message.file.size,
                "download_link": download_link
            }
            
            if os.path.exists('books.json'):
                with open('books.json', 'r', encoding='utf-8') as f:
                    try:
                        books_list = json.load(f)
                    except json.JSONDecodeError:
                        books_list = []
            else:
                books_list = []
                
            if not any(b['message_id'] == new_book['message_id'] for b in books_list):
                # စာအုပ်အသစ်ကို စာရင်းရဲ့ အရှေ့ဆုံးသို့ ထည့်မည်
                books_list.insert(0, new_book)
                with open('books.json', 'w', encoding='utf-8') as f:
                    json.dump(books_list, f, ensure_ascii=False, indent=4)
                print(f"📚 စာအုပ်အသစ် ထပ်တိုးလာ၍ သိမ်းပြီးပါပြီ: {message.file.name}")

async def main():
    print("🔄 Telegram Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    # ပထမအကြိမ် စတင်သည်နှင့် ရှိသမျှ စာအုပ်ဟောင်းများကို အရင်စကန်ဖတ်မည်
    await scan_all_existing_books()

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
