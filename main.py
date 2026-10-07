from telethon import TelegramClient, events
from telethon.sessions import StringSession
import json
import os
import asyncio
import urllib.parse
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI()

api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
channel_username = '@HWP_Bookshelf'

session_string = os.getenv('SESSION_STRING', '')
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Channel ထဲရှိ စာအုပ်များကို စကန်ဖတ်ပြီး Render ဆာဗာ Download Link ဖြင့် books.json ထဲ သိမ်းမည့် ဖန်ရှင်
async def scan_all_existing_books():
    books_list = []
    print("🔍 Channel ထဲရှိ စာအုပ်များကို စတင်စကန်ဖတ်နေပါပြီ...")
    
    async for message in client.iter_messages(channel_username):
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
                # Render ဆာဗာကနေ တိုက်ရိုက်ဆွဲမည့် Download Endpoint လင့်ခ်
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
    print(f"📚 စုစုပေါင်း စာအုပ် {len(books_list)} အုပ်၏ လင့်ခ်များကို books.json သို့ သိမ်းပြီးပါပြီ။")

@app.on_event("startup")
async def startup_event():
    await client.start()
    await scan_all_existing_books()
    
    @client.on(events.NewMessage(chats=channel_username))
    async def my_event_handler(event):
        message = event.message
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
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
                    print(f"📚 စာအုပ်အသစ် ထပ်တိုးပြီးပါပြီ: {message.file.name}")

    asyncio.create_task(client.run_until_disconnected())

# အသုံးပြုသူက Download နှိပ်တဲ့အခါ Telegram ကနေ ဖိုင်ကို တိုက်ရိုက် Stream လုပ်ပေးမည့် Endpoint
@app.get("/download/{message_id}")
async def download_book(message_id: int):
    try:
        message = await client.get_messages(channel_username, ids=message_id)
        if not message or not message.file:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_stream = await client.download_file(message, bytes)
        file_name = message.file.name or f"book_{message_id}.pdf"
        
        return StreamingResponse(
            iter([file_stream]),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(file_name)}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/books.json")
async def get_books():
    if os.path.exists('books.json'):
        with open('books.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@app.get("/")
async def root():
    return {"status": "Server is running smoothly without Bot!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
