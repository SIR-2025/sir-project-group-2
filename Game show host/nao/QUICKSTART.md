# Quick Start - NAO Quiz Host

## 🚀 Start Services (5 Terminals)

**Volgorde is belangrijk!**

```powershell
# Terminal 1: Redis Server
cd conf/redis
.\redis-server.exe redis.conf

# Terminal 2: Kahoot Server
cd "Game show host/Kahoot-server"
python app.py

# Terminal 3: Google STT Service
run-google-stt

# Terminal 4: NAO Robot
# → Zet NAO aan, check IP (standaard: 10.0.0.137)

# Terminal 5: Main Script
cd "Game show host/nao"
python main.py
```

---

## 📁 File Overview

| File | Wat zit erin |
|------|--------------|
| `main.py` | Hoofd script - quiz flow, phases, NAO controller |
| `server_connection.py` | KahootAPI class - HTTP calls naar Flask server |
| `nao_listener.py` | Google Speech-to-Text voor cohost input |
| `llm_integration_groq.py` | Groq LLM voor grappen genereren |
| `prompts.py` | Alle LLM prompts (jokes, roasts, etc.) |
| `nao_motions.py` | NAO animaties en bewegingen |
| `.env` | API keys (GROQ_API_KEY) |

---

## ⚙️ Configuratie

In `main.py` bovenaan:

```python
NAO_IP = "10.0.0.137"           # NAO IP adres
SERVER_URL = "http://localhost:5000"  # Kahoot server
MINIMUM_PLAYERS = 2             # Min spelers om te starten
```

---

## ✅ Checklist voor Start

- [ ] `.env` bevat `GROQ_API_KEY=...`
- [ ] `conf/google/google-key.json` bestaat
- [ ] NAO robot staat aan en is bereikbaar
- [ ] Alle 4 services draaien (Redis, Kahoot, STT, main.py)

---

## 🌐 URLs

- **Spelers joinen:** http://localhost:5000/join
- **Admin view:** http://localhost:5000/admin

---

## 🐛 Troubleshooting

| Probleem | Oplossing |
|----------|-----------|
| "Cannot connect to Redis" | Start `redis-server.exe` eerst |
| "Cannot connect to server" | Start `python app.py` in Kahoot-server |
| "No speech detected" | Check `run-google-stt` en google-key.json |
| "Cannot connect to NAO" | Check NAO IP en of robot aan staat |
| "GROQ error" | Check `.env` file met GROQ_API_KEY |
