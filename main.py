from telethon import TelegramClient, events
import json
import os

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
    print("🔄 Cloud Server ပေါ်တွင် Telegram Channel ကို စောင့်ဆိုင်းနေပါပြီ...")

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
