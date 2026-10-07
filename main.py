from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from telethon import TelegramClient
from telethon.sessions import StringSession
import os

app = FastAPI()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION_STRING"]  # Telethon user session
CHANNEL = "@HWP_Bookshelf"

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

@app.on_event("startup")
async def startup():
    await client.start()

# ═══════════════════════════════════════════
# JSON — file metadata
# ═══════════════════════════════════════════
@app.get("/books.json")
async def books():
    books = []
    async for msg in client.iter_messages(CHANNEL):
        if not msg.document: continue
        name = next((a.file_name for a in msg.document.attributes 
                     if hasattr(a, 'file_name')), f"file_{msg.id}.bin")
        books.append({
            "file_name": name,
            "message_id": msg.id,
            "file_size": msg.document.size,
            "download_link": f"https://hwpbookshelf-1.onrender.com/download/{msg.id}"
        })
    return books

# ═══════════════════════════════════════════
# /download/{id} — Stream file on-demand
# ═══════════════════════════════════════════
@app.get("/download/{msg_id}")
async def download(msg_id: int):
    try:
        msg = await client.get_messages(CHANNEL, ids=msg_id)
    except Exception as e:
        raise HTTPException(500, f"Fetch error: {e}")

    if not msg or not msg.document:
        raise HTTPException(404, "File not found")

    name = next((a.file_name for a in msg.document.attributes
                 if hasattr(a, 'file_name')), f"book_{msg_id}.bin")
    size = msg.document.size
    mime = msg.document.mime_type or "application/octet-stream"

    async def stream():
        async for chunk in client.iter_download(msg.document):
            yield chunk

    from urllib.parse import quote
    return StreamingResponse(
        stream(),
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
            "Content-Length": str(size),
        }
    )