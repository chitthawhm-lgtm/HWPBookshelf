from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from telethon import TelegramClient
import json
import os
import asyncio
import uvicorn

app = FastAPI()

api_id = 38901632
api_hash = 'efbda4d3465299fa86eebba3abcbd70f'
channel_username = '@HWP_Bookshelf'

client = TelegramClient('ebook_session', api_id, api_hash)

# Bot စတင်ချိန်တွင် စာအုပ်ဟောင်းများကို စကန်ဖတ်၍ books.json ဖန်တီးခြင်း
async def scan_all_existing_books():
    books_list = []
    print("🔍 Channel ထဲရှိ စာအုပ်အားလုံးကို စတင်စကန်ဖတ်နေပါပြီ...")
    
    async for message in client.iter_messages(channel_username):
        if message.file and message.file.name:
            if message.file.name.lower().endswith(('.pdf', '.epub')):
                # proxy download link အဖြစ် ပြောင်းလဲပေးခြင်း
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
    print(f"📚 စုစုပေါင်း စာအုပ် {len(books_list)} အုပ်ကို books.json သို့ သိမ်းဆည်းပြီးပါပြီ။")

@app.on_event("startup")
async def startup_event():
    await client.start()
    await scan_all_existing_books()
    
    # စာအုပ်အသစ်များ အလိုအလျောက် ဖမ်းယူရန် Background Task ဖြင့် ချိတ်ဆက်ခြင်း
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
                    print(f"📚 စာအုပ်အသစ် ထပ်တိုးလာ၍ သိမ်းပြီးပါပြီ: {message.file.name}")

    asyncio.create_task(client.run_until_disconnected())

# ၁။ စာအုပ်စာရင်း JSON ထုတ်ပေးမည့် Endpoint
@app.get("/books.json")
async def get_books():
    if os.path.exists('books.json'):
        with open('books.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@app.get("/")
async def root():
    return {"status": "Server is running!"}

# ၂။ ဖိုင်များကို Telegram မှ တိုက်ရိုက် Streaming ဖြင့် ဒေါင်းလုဒ်လုပ်ပေးမည့် Proxy Endpoint
@app.get("/download/{message_id}")
async def download_file(message_id: int):
    try:
        message = await client.get_messages(channel_username, ids=message_id)
        if not message or not message.file:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_name = message.file.name or f"book_{message_id}.pdf"
        
        # Telethon မှတဆင့် ဖိုင်ကို Chunk များအဖြစ် stream လုပ်ထုတ်ပေးခြင်း
        async def file_streamer():
            async for chunk in client.iter_download(message.media):
                yield chunk

        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': message.file.mime_type or 'application/octet-stream'
        }
        
        return StreamingResponse(file_streamer(), headers=headers)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
