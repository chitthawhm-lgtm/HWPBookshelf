import os
import json
import asyncio
from urllib.parse import quote
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient
from telethon.sessions import StringSession

# ═══════════════════════════════════════════
# Config
# ═══════════════════════════════════════════
API_ID = int(os.environ.get("API_ID", "38901632"))
API_HASH = os.environ.get("API_HASH", "efbda4d3465299fa86eebba3abcbd70f")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHANNEL = "HWP_Bookshelf"
BASE_URL = os.environ.get("BASE_URL", "https://hwpbookshelf-1.onrender.com")
REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", "600"))  # 10 min

# ═══════════════════════════════════════════
# App
# ═══════════════════════════════════════════
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = None
refresh_task = None

# ═══════════════════════════════════════════
# Books cache
# ═══════════════════════════════════════════
_books_cache = {"books": [], "count": 0, "last_refresh": None}

# ═══════════════════════════════════════════
# Core: scan channel
# ═══════════════════════════════════════════
async def scan_channel():
    """Scan entire channel and build books.json"""
    global _books_cache
    if not client:
        return 0

    books = []
    try:
        async for msg in client.iter_messages(CHANNEL):
            if not msg.document:
                continue

            name = None
            for attr in msg.document.attributes:
                if hasattr(attr, "file_name") and attr.file_name:
                    name = attr.file_name
                    break
            if not name:
                name = f"file_{msg.id}.bin"

            books.append({
                "file_name": name,
                "message_id": msg.id,
                "file_size": msg.document.size,
                "download_link": f"{BASE_URL}/download/{msg.id}",
                "date": msg.date.isoformat() if msg.date else None,
            })

        # Sort newest first
        books.sort(key=lambda x: x["message_id"], reverse=True)

        # Save to file
        with open("books.json", "w", encoding="utf-8") as f:
            json.dump(books, f, ensure_ascii=False, indent=2)

        # Update cache
        _books_cache["books"] = books
        _books_cache["count"] = len(books)
        _books_cache["last_refresh"] = datetime.utcnow().isoformat()

        print(f"📚 Refreshed: {len(books)} books @ {_books_cache['last_refresh']}")
        return len(books)

    except Exception as e:
        print(f"❌ Scan error: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def auto_refresh_loop():
    """Background task — refresh every N seconds"""
    while True:
        try:
            await asyncio.sleep(REFRESH_INTERVAL)
            print(f"⏰ Auto refresh triggered")
            await scan_channel()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Auto refresh error: {e}")


# ═══════════════════════════════════════════
# Startup / Shutdown
# ═══════════════════════════════════════════
@app.on_event("startup")
async def startup():
    global client, refresh_task

    if not SESSION_STRING:
        print("❌ SESSION_STRING not set")
        return

    try:
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        await client.start()
        me = await client.get_me()
        print(f"✅ Telethon ready: {me.username or me.id}")

        # Initial scan
        await scan_channel()

        # Start background refresh
        refresh_task = asyncio.create_task(auto_refresh_loop())
        print(f"⏰ Auto refresh every {REFRESH_INTERVAL}s")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown():
    global refresh_task
    if refresh_task:
        refresh_task.cancel()
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
    return {
        "status": "ok",
        "ready": client is not None,
        "books": _books_cache["count"],
    }


@app.get("/health")
async def health():
    return {
        "ok": True,
        "ready": client is not None,
        "books": _books_cache["count"],
        "last_refresh": _books_cache["last_refresh"],
    }


@app.get("/books.json")
async def books():
    """Return current book list (from cache)"""
    if _books_cache["books"]:
        return _books_cache["books"]

    # Fallback — read from file
    try:
        with open("books.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


@app.get("/sync")
async def sync():
    """Force refresh + return list"""
    count = await scan_channel()
    return {
        "ok": True,
        "count": count,
        "books": _books_cache["books"],
    }


@app.get("/refresh")
async def refresh():
    """Force refresh (same as /sync)"""
    count = await scan_channel()
    return {
        "ok": True,
        "count": count,
        "last_refresh": _books_cache["last_refresh"],
    }


@app.get("/download/{msg_id}")
async def download(msg_id: int):
    if not client:
        raise HTTPException(500, "Telethon not ready")

    try:
        msg = await client.get_messages(CHANNEL, ids=msg_id)
    except Exception as e:
        raise HTTPException(500, f"Fetch error: {e}")

    if not msg or not msg.document:
        raise HTTPException(404, "File not found")

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
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))