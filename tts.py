"""
tts.py — Text-to-Speech
Primary: ElevenLabs API (high quality, 10k chars/month free)
Fallback: edge-tts (Microsoft Edge neural voices, fully free, runs locally)
"""

import os
import io
import asyncio
import httpx
import edge_tts
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

# Edge-TTS voice (good free option)
EDGE_VOICE = "en-US-JennyNeural"


async def synthesize_speech(text: str) -> bytes:
    """
    Converts text to speech audio bytes (mp3).
    Tries ElevenLabs first; falls back to Edge-TTS if key is missing or fails.
    """
    if not text.strip():
        return b""

    # Try ElevenLabs if key is configured
    if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != "your_elevenlabs_key_here":
        audio = await _elevenlabs_tts(text)
        if audio:
            return audio

    # Fallback to Edge-TTS (free)
    return await _edge_tts(text)


async def _elevenlabs_tts(text: str) -> bytes:
    """Call ElevenLabs API, return mp3 bytes."""
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                ELEVENLABS_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            print("[TTS] Used ElevenLabs")
            return response.content
    except Exception as e:
        print(f"[TTS] ElevenLabs failed ({e}), falling back to Edge-TTS")
        return b""


async def _edge_tts(text: str) -> bytes:
    """Use edge-tts (free Microsoft neural voices), return mp3 bytes."""
    try:
        communicate = edge_tts.Communicate(text, EDGE_VOICE)
        audio_buffer = io.BytesIO()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        audio_bytes = audio_buffer.getvalue()
        print(f"[TTS] Used Edge-TTS, {len(audio_bytes)} bytes")
        return audio_bytes
    except Exception as e:
        print(f"[TTS] Edge-TTS error: {e}")
        return b""
