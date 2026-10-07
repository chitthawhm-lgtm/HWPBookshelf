from telethon import TelegramClient, events
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

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
            self.wfile.write(b"Bot is running 24/7!")
            
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    server_address = ('', 10000)
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

server_thread = threading.Thread(target=run_web_server)
server_thread.daemon = True
server_thread.start()

api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
channel_username = '@HWP_Bookshelf'

client = TelegramClient('ebook_session', api_id, api_hash)

async def scan_existing_books():
    books_list = []
    print("🔍 Channel ထဲရှိ စာအုပ်များကို စတင်စကန်ဖတ်နေပါပြီ...")
    async for message in client.iter_messages(channel_username):
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
                # Telegram post link ကို download_link အဖြစ် ထည့်သွင်းခြင်း
                download_link = f"https://t.me/HWP_Bookshelf/{message.id}"
                book_info = {
                    "file_name": message.file.name,
                    "message_id": message.id,
                    "file_size": message.file.size,
                    "download_link": download_link
                }
                if book_info not in books_list:
                    books_list.append(book_info)
                    
    with open('books.json', 'w', encoding='utf-8') as f:
        json.dump(books_list, f, ensure_ascii=False, indent=4)
    print(f"📚 စုစုပေါင်း စာအုပ် {len(books_list)} အုပ်ကို books.json သို့ သိမ်းဆည်းပြီးပါပြီ။")

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
                books_list.append(new_book)
                with open('books.json', 'w', encoding='utf-8') as f:
                    json.dump(books_list, f, ensure_ascii=False, indent=4)
                print(f"📚 စာအုပ်အသစ် တွေ့ရှိပြီး သိမ်းပြီးပါပြီ: {message.file.name}")

async def main():
    print("🔄 Render Free Web Service ပေါ်တွင် Telegram Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    await scan_existing_books()

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
