from telethon import TelegramClient, events
from telethon.sessions import StringSession
import json
import os
import asyncio
import uvicorn
from fastapi import FastAPI

app = FastAPI()

api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
# ပေးထားသော Bot Token ကို တိုက်ရိုက်ထည့်သွင်းပေးထားပါသည်
bot_token = os.getenv('BOT_TOKEN', '8867916581:AAFTY5JeBbxgCINReGfWh7MsSyFetgTv9tg')
channel_username = '@HWP_Bookshelf'

session_string = os.getenv('SESSION_STRING', '')
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Channel ထဲရှိ စာအုပ်များကို Telegram Direct Link ဖြင့် စကန်ဖတ်မည့် ဖန်ရှင်
async def scan_all_existing_books():
    books_list = []
    print("🔍 Channel ထဲရှိ စာအုပ်များကို Telegram Direct Link ဖြင့် စတင်စကန်ဖတ်နေပါပြီ...")
    
    async for message in client.iter_messages(channel_username):
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
                try:
                    # Telegram Bot API ဖြင့် တိုက်ရိုက်ဒေါင်းနိုင်သော URL များကို ရယူခြင်း
                    file_info = await client.get_file(message.media)
                    download_link = f"https://api.telegram.org/file/bot{bot_token}/{file_info.file_path}"
                except Exception as e:
                    print(f"Error getting file path for {message.file.name}: {e}")
                    download_link = f"https://hwpbookshelf-1.onrender.com/download/{message.id}"

                book_info = {
                    "file_name": message.file.name,
                    "message_id": message.id,
                    "file_size": message.file.size,
                    "download_link": download_link
                }
                if not any(b['message_id'] == book_info['message_id'] for b in books_list):
                    books_list.append(book_info)
                    
    books_list = sorted(books_list, key=lambda x: x['message_id'], reverse=True)
    
    with open('books.json', 'w', encoding='utf-8') as f:
        json.dump(books_list, f, ensure_ascii=False, indent=4)
    print(f"📚 စုစုပေါင်း စာအုပ် {len(books_list)} အုပ်၏ Direct Link များကို books.json သို့ သိမ်းပြီးပါပြီ။")

@app.on_event("startup")
async def startup_event():
    await client.start()
    await scan_all_existing_books()
    
    @client.on(events.NewMessage(chats=channel_username))
    async def my_event_handler(event):
        message = event.message
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
                try:
                    file_info = await client.get_file(message.media)
                    download_link = f"https://api.telegram.org/file/bot{bot_token}/{file_info.file_path}"
                except:
                    download_link = f"https://hwpbookshelf-1.onrender.com/download/{message.id}"

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
                    books_list.insert(0, new_book)
                    with open('books.json', 'w', encoding='utf-8') as f:
                        json.dump(books_list, f, ensure_ascii=False, indent=4)
                    print(f"📚 စာအုပ်အသစ် Direct Link ဖြင့် ထပ်တိုးပြီးပါပြီ: {message.file.name}")

    asyncio.create_task(client.run_until_disconnected())

@app.get("/books.json")
async def get_books():
    if os.path.exists('books.json'):
        with open('books.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@app.get("/")
async def root():
    return {"status": "Server is running with Direct Telegram Links!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
