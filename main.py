from telethon import TelegramClient, events
from telethon.sessions import StringSession
import json
import os
import asyncio
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI()

api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
bot_token = os.getenv('BOT_TOKEN', '8867916581:AAFTY5JeBbxgCINReGfWh7MsSyFetgTv9tg')
channel_username = '@HWP_Bookshelf'

session_string = os.getenv('SESSION_STRING', '')
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Telegram Bot API ကိုသုံးပြီး Direct Link ရယူမည့် Helper Function
async def get_telegram_direct_link(message):
    try:
        if not message.media or not hasattr(message.media, 'document'):
            return None
        
        # Telegram Bot API getFile ကို httpx ဖြင့် လှမ်းခေါ်ခြင်း
        api_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={message.file.id}"
        
        async with httpx.AsyncClient() as httpx_client:
            response = await httpx_client.get(api_url)
            res_data = response.json()
            if res_data.get("ok"):
                file_path = res_data["result"]["file_path"]
                return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    except Exception as e:
        print(f"Error fetching direct link for message {message.id}: {e}")
    return None

# Channel ထဲရှိ စာအုပ်များကို စကန်ဖတ်မည့် ဖန်ရှင်
async def scan_all_existing_books():
    books_list = []
    print("🔍 Channel ထဲရှိ စာအုပ်များကို Telegram Bot API Direct Link ဖြင့် စတင်စကန်ဖတ်နေပါပြီ...")
    
    async for message in client.iter_messages(channel_username):
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
                download_link = await get_telegram_direct_link(message)
                
                # အကယ်၍ Direct Link မရခဲ့ပါက Fallback အနေဖြင့် Render Download Link ကို သုံးမည်
                if not download_link:
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
                download_link = await get_telegram_direct_link(message)
                if not download_link:
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
    return {"status": "Server is running with Telegram Bot API Direct Links!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
