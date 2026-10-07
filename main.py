from telethon import TelegramClient, events
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Web Server အတွက် Handler (Render က /books.json တောင်းဆိုသည့်အခါ ဖိုင်ထဲမှ ဒေတာများကို ပို့ပေးမည်)
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

# Web Server ကို နောက်ကွယ်မှ အမြဲအလုပ်လုပ်နေစေရန် Thread ဖြင့် Run ခြင်း
server_thread = threading.Thread(target=run_web_server)
server_thread.daemon = True
server_thread.start()

# Telegram Bot အချက်အလက်များ
api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
channel_username = '@HWP_Bookshelf'

client = TelegramClient('ebook_session', api_id, api_hash)

# ချန်နယ်ထဲသို့ စာအုပ်အသစ် ဝင်လာတိုင်း books.json ထဲသို့ အလိုအလျောက် ထည့်ပေးမည့် စနစ်
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
            
            # လက်ရှိ books.json ရှိပြီးသားများကို ဖတ်ရန်
            if os.path.exists('books.json'):
                with open('books.json', 'r', encoding='utf-8') as f:
                    try:
                        books_list = json.load(f)
                    except json.JSONDecodeError:
                        books_list = []
            else:
                books_list = []
                
            # စာအုပ်အသစ် မပါသေးမှသာ အသစ်ပေါင်းထည့်ရန်
            if not any(b['message_id'] == new_book['message_id'] for b in books_list):
                books_list.append(new_book)
                with open('books.json', 'w', encoding='utf-8') as f:
                    json.dump(books_list, f, ensure_ascii=False, indent=4)
                print(f"📚 စာအုပ်အသစ် တွေ့ရှိပြီး သိမ်းပြီးပါပြီ: {message.file.name}")

async def main():
    print("🔄 Telegram Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    # books.json မရှိသေးပါက အလွတ်စတင်ဖန်တီးရန်
    if not os.path.exists('books.json'):
        with open('books.json', 'w', encoding='utf-8') as f:
            json.dump([], f)

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
