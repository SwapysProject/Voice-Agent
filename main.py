"""
main.py — FastAPI Voice Agent Server
Handles WebSocket connections from the browser.
Each connection gets its own conversation history (per session).

Flow per turn:
  browser sends audio bytes  →  STT (Deepgram)  →  LLM (Groq)  →  TTS (ElevenLabs/Edge)  →  browser plays audio

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import json
import base64
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from stt import transcribe_audio
from llm import get_llm_reply, reset_history
from tts import synthesize_speech

app = FastAPI(title="Voice Agent")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Mount static files only when the directory exists.
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Redirect root to the frontend HTML."""
    html_path = STATIC_DIR / "index.html"
    if not html_path.exists():
        html_path = BASE_DIR / "index.html"

    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Voice agent is running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint — one connection per browser tab.
    Receives audio blobs, processes them, sends back audio + transcript.

    Message protocol:
    ─ Client → Server:
        Binary frames: raw audio bytes (webm/opus from MediaRecorder)
        Text frames (JSON): {"type": "reset"} to clear conversation history

    ─ Server → Client:
        {"type": "transcript", "text": "what the user said"}
        {"type": "reply_text",  "text": "what the assistant will say"}
        {"type": "audio",       "data": "<base64-encoded mp3>"}
        {"type": "error",       "message": "..."}
        {"type": "status",      "message": "Processing..."}
    """
    await websocket.accept()
    print("[WS] Client connected")

    # Each WebSocket connection has its own isolated conversation history
    conversation_history = reset_history()

    try:
        while True:
            # Wait for a message from the browser
            message = await websocket.receive()

            # ── Handle control messages (JSON text) ──────────────────────────
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "reset":
                        conversation_history = reset_history()
                        await websocket.send_json({"type": "status", "message": "Conversation reset"})
                        print("[WS] Conversation history cleared")
                except json.JSONDecodeError:
                    pass
                continue

            # ── Handle audio binary frames ────────────────────────────────────
            if "bytes" not in message:
                continue

            audio_bytes = message["bytes"]
            print(f"[WS] Received audio: {len(audio_bytes)} bytes")

            # ── Step 1: STT ───────────────────────────────────────────────────
            await websocket.send_json({"type": "status", "message": "Transcribing..."})
            transcript = await transcribe_audio(audio_bytes)

            if not transcript:
                await websocket.send_json({
                    "type": "status",
                    "message": "No speech detected, try again"
                })
                continue

            print(f"[STT] Transcript: {transcript}")
            await websocket.send_json({"type": "transcript", "text": transcript})

            # ── Step 2: LLM ───────────────────────────────────────────────────
            await websocket.send_json({"type": "status", "message": "Thinking..."})
            reply_text, conversation_history = await get_llm_reply(
                user_message=transcript,
                conversation_history=conversation_history,
            )

            print(f"[LLM] Reply: {reply_text[:80]}...")
            await websocket.send_json({"type": "reply_text", "text": reply_text})

            # ── Step 3: TTS ───────────────────────────────────────────────────
            await websocket.send_json({"type": "status", "message": "Generating speech..."})
            audio_out = await synthesize_speech(reply_text)

            if not audio_out:
                await websocket.send_json({
                    "type": "error",
                    "message": "TTS failed — check your API keys"
                })
                continue

            # Send audio as base64-encoded string inside JSON
            audio_b64 = base64.b64encode(audio_out).decode("utf-8")
            await websocket.send_json({"type": "audio", "data": audio_b64})
            print(f"[TTS] Sent {len(audio_out)} bytes of audio to browser")

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
