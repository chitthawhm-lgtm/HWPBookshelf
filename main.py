from telethon import TelegramClient, events
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# အခမဲ့ Web Service အတွက် Port နှင့် Request များကို ဖြေရှင်းပေးမည့် Code
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")
        
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    server_address = ('', 10000)
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

# Web Server ကို Background မှာ သီးသန့် အလုပ်လုပ်ခိုင်းရန်
server_thread = threading.Thread(target=run_web_server)
server_thread.daemon = True
server_thread.start()

# Telegram Bot Logic
api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
channel_username = '@HWP_Bookshelf'

client = TelegramClient('ebook_session', api_id, api_hash)

@client.on(events.NewMessage(chats=channel_username))
async def my_event_handler(event):
    message = event.message
    if message.file and message.file.name:
        if message.file.name.lower().endswith(('.pdf', '.epub')):
            new_book = {
                "file_name": message.file.name,
                "message_id": message.id,
                "file_size": message.file.size
            }
            
            if os.path.exists('books.json'):
                with open('books.json', 'r', encoding='utf-8') as f:
                    try:
                        books_list = json.load(f)
                    except json.JSONDecodeError:
                        books_list = []
            else:
                books_list = []
                
            books_list.append(new_book)
            
            with open('books.json', 'w', encoding='utf-8') as f:
                json.dump(books_list, f, ensure_ascii=False, indent=4)
                
            print(f"📚 စာအုပ်အသစ် တွေ့ရှိပြီး သိမ်းပြီးပါပြီ: {message.file.name}")

async def main():
    print("🔄 Render Free Web Service ပေါ်တွင် Telegram Bot စတင်အလုပ်လုပ်နေပါပြီ...")

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
