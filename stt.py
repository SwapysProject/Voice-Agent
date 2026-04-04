"""
stt.py — Speech-to-Text using Deepgram
Sends audio bytes to Deepgram REST API and returns the transcript string.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# Deepgram query params: nova-2 model, punctuation, english
PARAMS = {
    "model": "nova-2",
    "punctuate": "true",
    "language": "en-US",
    "smart_format": "true",
}


async def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Takes raw audio bytes (webm/opus from browser MediaRecorder),
    sends to Deepgram, returns transcript text.
    Returns empty string if transcription fails or audio is silent.
    """
    if not audio_bytes or len(audio_bytes) < 1000:
        # Too small to be real speech
        return ""

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/webm",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                DEEPGRAM_URL,
                params=PARAMS,
                headers=headers,
                content=audio_bytes,
            )
            response.raise_for_status()
            data = response.json()

        # Navigate Deepgram's response structure
        transcript = (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )
        return transcript.strip()

    except httpx.HTTPStatusError as e:
        print(f"[STT] Deepgram HTTP error: {e.response.status_code} — {e.response.text}")
        return ""
    except Exception as e:
        print(f"[STT] Transcription error: {e}")
        return ""
