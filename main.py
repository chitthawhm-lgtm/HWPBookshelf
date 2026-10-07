import os
import json
from urllib.parse import quote
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient
from telethon.sessions import StringSession

# ═══════════════════════════════════════════
# Credentials
# ═══════════════════════════════════════════
API_ID = int(os.environ.get("API_ID", "38901632"))
API_HASH = os.environ.get("API_HASH", "efbda4d3465299fa86eebba3abcbd70f")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHANNEL = "HWP_Bookshelf"
BASE_URL = os.environ.get("BASE_URL", "https://hwpbookshelf-1.onrender.com")

# ═══════════════════════════════════════════
# FastAPI
# ═══════════════════════════════════════════
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = None

# ═══════════════════════════════════════════
# Startup / Shutdown
# ═══════════════════════════════════════════
@app.on_event("startup")
async def startup():
    global client
    if not SESSION_STRING:
        print("❌ SESSION_STRING not set — User API မရ")
        return
    try:
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        await client.start()
        me = await client.get_me()
        print(f"✅ Telethon ready: {me.username or me.id}")
        # Auto-generate books.json
        await refresh_books()
    except Exception as e:
        print(f"❌ Startup: {e}")

@app.on_event("shutdown")
async def shutdown():
    if client:
        try:
            await client.disconnect()
        except:
            pass

# ═══════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════
@app.get("/")
async def root():
    return {"status": "ok", "ready": client is not None}

@app.get("/health")
async def health():
    return {"ok": True, "ready": client is not None}

@app.get("/books.json")
async def books():
    """Return cached books.json or refresh"""
    try:
        with open("books.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if client:
            await refresh_books()
            try:
                with open("books.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []

@app.get("/refresh")
async def refresh():
    """Manual refresh books.json"""
    count = await refresh_books()
    return {"status": "ok", "books": count}

@app.get("/download/{msg_id}")
async def download(msg_id: int):
    """Stream file from Telegram channel"""
    if not client:
        raise HTTPException(500, "Telethon client not ready")
    
    try:
        msg = await client.get_messages(CHANNEL, ids=msg_id)
    except Exception as e:
        raise HTTPException(500, f"Fetch error: {e}")
    
    if not msg:
        raise HTTPException(404, "Message not found")
    if not msg.document:
        raise HTTPException(404, "No document")
    
    # File info
    name = f"book_{msg_id}.bin"
    for a in msg.document.attributes:
        if hasattr(a, "file_name") and a.file_name:
            name = a.file_name
            break
    
    size = msg.document.size
    mime = msg.document.mime_type or "application/octet-stream"
    
    print(f"📥 Downloading: {name} ({size} bytes)")
    
    async def stream():
        try:
            async for chunk in client.iter_download(msg.document):
                yield chunk
        except Exception as e:
            print(f"Stream error: {e}")
    
    return StreamingResponse(
        stream(),
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
            "Content-Length": str(size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        }
    )

# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════
async def refresh_books():
    """Scan channel and rebuild books.json"""
    if not client:
        return 0
    
    books = []
    try:
        async for msg in client.iter_messages(CHANNEL):
            if not msg.document:
                continue
            name = f"file_{msg.id}.bin"
            for a in msg.document.attributes:
                if hasattr(a, "file_name") and a.file_name:
                    name = a.file_name
                    break
            books.append({
                "file_name": name,
                "message_id": msg.id,
                "file_size": msg.document.size,
                "download_link": f"{BASE_URL}/download/{msg.id}"
            })
    except Exception as e:
        print(f"❌ Scan error: {e}")
        return 0
    
    # Sort by message_id desc
    books.sort(key=lambda x: x["message_id"], reverse=True)
    
    with open("books.json", "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)
    
    print(f"📚 Saved {len(books)} books")
    return len(books)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))