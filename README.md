# Voice Agent

A full-stack voice agent: mic → Deepgram STT → Groq LLM → ElevenLabs TTS → speaker.
Built with FastAPI + WebSockets. Fully free to run.

## Folder structure

```
voice-agent/
├── .env                  ← your API keys (copy from .env.example)
├── .env.example          ← template
├── .gitignore
├── requirements.txt
├── main.py               ← FastAPI server + WebSocket handler
├── stt.py                ← Deepgram speech-to-text
├── llm.py                ← Groq LLM (Llama 3)
├── tts.py                ← ElevenLabs TTS (Edge-TTS fallback)
└── static/
    └── index.html        ← browser UI (mic capture + audio playback)
```

## 1. Get free API keys

| Service | Free tier | Link |
|---|---|---|
| Deepgram | 200 hours/month | https://console.deepgram.com |
| Groq | Very generous free | https://console.groq.com |
| ElevenLabs | 10,000 chars/month | https://elevenlabs.io |

> If you skip ElevenLabs, the agent auto-falls back to Edge-TTS (Microsoft neural voices, free forever).

## 2. Setup

```bash
# Clone / navigate to folder
cd voice-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in your API keys
cp .env.example .env
# Edit .env with your keys
```

## 3. Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser: http://localhost:8000

Hold the mic button to speak. Release to send. The agent responds with voice.

## How it works

1. Browser captures mic audio (MediaRecorder API → webm/opus)
2. Audio blob sent to server via WebSocket binary frame
3. Server calls Deepgram REST API → gets transcript text
4. Transcript + conversation history sent to Groq (Llama 3) → gets reply text
5. Reply text sent to ElevenLabs (or Edge-TTS) → gets mp3 audio bytes
6. Audio bytes base64-encoded, sent back to browser via WebSocket JSON
7. Browser decodes + plays the audio via Web Audio API

## Typical latency

- Deepgram STT: ~250–400ms
- Groq LLM: ~300–500ms
- ElevenLabs TTS: ~300–500ms
- **Total: ~0.9–1.4 seconds** from stop speaking to hearing reply

## What to provide / configure in .env

```env
DEEPGRAM_API_KEY=...           # required
GROQ_API_KEY=...               # required
ELEVENLABS_API_KEY=...         # optional (falls back to Edge-TTS)
ELEVENLABS_VOICE_ID=...        # optional (default = Rachel)
GROQ_MODEL=llama-3.1-8b-instant  # optional
SYSTEM_PROMPT=...              # optional (default set in .env)
```

## Next features to add

- [ ] Interrupt handling (user can speak while agent talks)
- [ ] Tool calls (web search, calculator, calendar)
- [ ] RAG (answer from your documents)
- [ ] Real-time streaming TTS (chunk by chunk, lower latency)
- [ ] Wake word detection
