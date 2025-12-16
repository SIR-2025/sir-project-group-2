# 🎮 NAO Game Show Host

An interactive quiz system where a NAO robot hosts a Kahoot-style quiz with AI-generated comedy.

## Overview

This project combines a **Flask quiz server** with a **NAO robot controller** to create an entertaining, interactive quiz show experience.

```
                         ┌─────────────────────────────────────┐
                         │         📺 Host Display             │
                         │      (Projector / TV Screen)        │
                         └──────────────────┬──────────────────┘
                                            │ Updates
                                            ▼
┌──────────────────┐                ┌───────────────────────────────────┐
│   📱 Players     │                │       🖥️  Kahoot-server           │
│                  │    HTTP        │                                   │
│  Phone 1  ───────┼───────────────►│   Flask Web App                   │
│  Phone 2  ───────┼───────────────►│   • Quiz State                    │
│  Phone 3  ───────┼───────────────►│   • Player Management             │
│  ...             │                │   • Scoring                       │
└──────────────────┘                │   • REST API                      │
                                    └──────────────────┬────────────────┘
                                                       │
                                                       │ REST API (JSON)
                                                       ▼
                                    ┌───────────────────────────────────┐
                                    │         🤖 NAO Robot              │
                                    │                                   │
                                    │   • Quiz Master (main.py)         │
                                    │   • Groq LLM (jokes)              │
                                    │   • Google STT (listening)        │
                                    │   • Physical Control              │
                                    └───────────────────────────────────┘
```

## 📦 Project Structure

```
Game show host/
├── README.md              ← You are here (umbrella documentation)
├── requirements.txt       ← All dependencies (install once)
├── Kahoot-server/         ← Quiz server module
│   ├── README.md          ← Server-specific docs
│   ├── app.py             ← Flask entry point
│   ├── routes/            ← API endpoints
│   ├── core/              ← Business logic
│   ├── data/              ← Quiz questions
│   ├── templates/         ← HTML pages
│   └── static/            ← CSS styling
└── nao/                   ← NAO robot module
    ├── README.md          ← Robot-specific docs
    ├── main.py            ← Robot entry point
    ├── prompts.py         ← LLM joke prompts
    ├── api/               ← Server communication
    ├── robot/             ← Physical control
    └── speech/            ← STT & LLM integration
```

## 🚀 Quick Start (for TAs)

### Step 1: Install Dependencies

```bash
cd "Game show host"
pip install -r requirements.txt
pip install "social-interaction-cloud[google-stt]"
```

### Step 2: Set Up API Keys

Create `nao/.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
```

Ensure Google credentials exist at `conf/google/google-key.json`.

### Step 3: Start Everything (4 terminals)

```bash
# Terminal 1: Quiz Server
cd "Game show host/Kahoot-server"
python app.py

# Terminal 2: Redis (required for SIC framework)
# From sic_applications root folder:
cd conf/redis
.\redis-server.exe redis.conf      # Windows
# ./redis-server redis.conf        # Linux/Mac

# Terminal 3: Google STT Service
# From any folder (uses PATH):
run-google-stt

# Terminal 4: NAO Robot
cd "Game show host/nao"
# Edit NAO_IP in main.py first!
python main.py
```

### Step 4: Open Browser

| URL | Purpose |
|-----|---------|
| http://localhost:5000/admin | Control quiz manually |
| http://localhost:5000/quiz | Project on screen for audience |
| http://localhost:5000/join | Players scan QR / join here |

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              INPUT                                       │
├─────────────────────────────────┬───────────────────────────────────────┤
│        🎤 NAO Microphone        │           📱 Player Phones            │
│         (cohost voice)          │            (answers)                  │
└────────────────┬────────────────┴───────────────────┬───────────────────┘
                 │                                    │
                 ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            PROCESSING                                    │
├─────────────────────┬─────────────────────┬─────────────────────────────┤
│    Google STT       │     Groq LLM        │      Flask Server           │
│  (speech to text)   │   (joke generation) │    (quiz logic)             │
└─────────┬───────────┴──────────┬──────────┴──────────────┬──────────────┘
          │                      │                         │
          ▼                      ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                      │
├─────────────────────┬─────────────────────┬─────────────────────────────┤
│    NAO Speech       │     NAO LEDs        │      📺 Display             │
│  (questions/jokes)  │   (red when angry)  │   (quiz interface)          │
└─────────────────────┴─────────────────────┴─────────────────────────────┘
```

### Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| **Kahoot-server** | Quiz state, player management, scoring, web interface |
| **nao** | Robot control, joke generation, speech recognition, show flow |

### Communication Flow

```
┌─────────────┐          ┌─────────────────┐          ┌─────────────┐
│   PLAYERS   │          │  KAHOOT SERVER  │          │  NAO ROBOT  │
└──────┬──────┘          └────────┬────────┘          └──────┬──────┘
       │                          │                          │
       │  ══════════════ PHASE 1: SETUP ══════════════════  │
       │                          │                          │
       │─── POST /join (name) ───►│                          │
       │◄── player_id ────────────│                          │
       │                          │                          │
       │  ══════════════ PHASE 2: QUIZ START ═════════════  │
       │                          │                          │
       │                          │◄─── POST /api/start ─────│
       │                          │◄─── GET /api/status ─────│
       │                          │──── question data ──────►│
       │                          │                          │
       │  ══════════════ PHASE 3: PER QUESTION ═══════════  │
       │                          │                          │
       │                          │              NAO speaks question
       │                          │◄── POST /api/reveal ─────│
       │─── POST /answer ────────►│                          │
       │                          │◄── POST /api/show_ans ───│
       │                          │─── correct/wrong list ──►│
       │                          │                          │
       │                          │         ┌────────────────┴───┐
       │                          │         │ Generate joke      │
       │                          │         │ via Groq LLM       │
       │                          │         └────────────────┬───┘
       │                          │                          │
       │                          │              NAO speaks joke
       │                          │                          │
       │  ══════════════ PHASE 4: FINALE ═════════════════  │
       │                          │                          │
       │                          │◄─ GET /api/leaderboard ──│
       │                          │─── final standings ─────►│
       │                          │                          │
       │                          │         NAO announces winner/loser
       │                          │              with roasts
       │                          │                          │
       ▼                          ▼                          ▼
```

---

## 🔧 Configuration

### Server Configuration

Edit `Kahoot-server/data/quiz_data.py`:

```python
QUIZ_TITLE = "Your Quiz Title"
QUESTIONS = [
    {
        "id": 0,
        "text": "What is the capital of France?",
        "options": ["Paris", "London", "Berlin", "Madrid"],
        "correct_answer": 0
    },
    # Add more...
]
```

### NAO Configuration

Edit `nao/main.py`:

```python
NAO_IP = "10.0.0.239"           # Your NAO's IP
SERVER_URL = "http://localhost:5000"
JOIN_WAIT_TIME = 60             # Wait time for players
```

### LLM Personality

Edit `nao/prompts.py` to customize NAO's humor style.

---

## 📋 Prerequisites

| Requirement | Purpose |
|-------------|---------|
| Python 3.8+ | Runtime |
| NAO robot | Quiz host hardware |
| Same WiFi network | All devices connected |
| Redis | SIC framework message broker |
| Google Cloud credentials | Speech-to-text |
| Groq API key | LLM joke generation |

---

## 🎬 Quiz Show Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           QUIZ SHOW FLOW                                 │
└─────────────────────────────────────────────────────────────────────────┘

    ┌───────────┐
    │   START   │
    └─────┬─────┘
          │
          ▼
    ┌───────────────────────────────────────────────────────────┐
    │  PHASE 1: INTRO                                           │
    │  • NAO wakes up and stands                                │
    │  • Introduces himself with wave gesture                   │
    │  • Roasts the cohost                                      │
    │  • Listens to cohost response, makes comeback             │
    └─────────────────────────┬─────────────────────────────────┘
                              │
                              ▼
    ┌───────────────────────────────────────────────────────────┐
    │  PHASE 2: WAIT FOR PLAYERS (60 seconds)                   │
    │  • Points to screen, tells players to join                │
    │  • Makes jokes about player usernames as they join        │
    │  • Interacts with cohost at halfway point                 │
    │  • Time announcements at 30s and 10s                      │
    └─────────────────────────┬─────────────────────────────────┘
                              │
                              ▼
    ┌───────────────────────────────────────────────────────────┐
    │  PHASE 3: QUIZ LOOP (per question)                        │
    │                                                           │
    │    ┌──────────────┐                                       │
    │    │ Read Question│◄──────────────────────────────┐       │
    │    └──────┬───────┘                               │       │
    │           ▼                                       │       │
    │    ┌──────────────┐                               │       │
    │    │Reveal Options│ (starts 20s timer)            │       │
    │    └──────┬───────┘                               │       │
    │           ▼                                       │       │
    │    ┌──────────────┐                               │       │
    │    │Wait Answers  │ (poll until timeout)          │       │
    │    └──────┬───────┘                               │       │
    │           ▼                                       │       │
    │    ┌──────────────┐                               │       │
    │    │Show Correct  │ + distribution                │       │
    │    └──────┬───────┘                               │       │
    │           ▼                                       │       │
    │    ┌──────────────┐                               │       │
    │    │ Make Joke    │ (LLM generates)               │       │
    │    └──────┬───────┘                               │       │
    │           ▼                                       │       │
    │    ┌──────────────┐     More questions?           │       │
    │    │ Leaderboard  │────────────────────YES────────┘       │
    │    └──────┬───────┘                                       │
    │           │ NO                                            │
    └───────────┼───────────────────────────────────────────────┘
                │
                ▼
    ┌───────────────────────────────────────────────────────────┐
    │  PHASE 4: FINALE                                          │
    │  • Build tension                                          │
    │  • Announce WINNER + backhanded compliment joke           │
    │  • Announce LOSER + gentle roast                          │
    │  • Ask cohost for closing words                           │
    │  • NAO bows and closes the show                           │
    └─────────────────────────┬─────────────────────────────────┘
                              │
                              ▼
                        ┌───────────┐
                        │    END    │
                        └───────────┘
```

### Phase Details

| Phase | NAO Actions | Server Actions |
|-------|-------------|----------------|
| **Intro** | Introduces self, roasts cohost | - |
| **Wait** | Jokes about player names | Accepts joins |
| **Quiz** | Reads questions, makes jokes | Tracks answers, scores |
| **Finale** | Announces winner/loser with roasts | Provides final standings |

---

## 🧪 Testing

### Test Server Only

```bash
cd "Game show host/Kahoot-server"
python app.py
# Open http://localhost:5000/admin
```

### Test NAO API Connection

```bash
cd "Game show host/nao"
python api/kahoot_api.py
```

### Test Full System

1. Start server (`Kahoot-server/`) → Terminal 1
2. Start Redis (`conf/redis/`) → Terminal 2
3. Start `run-google-stt` → Terminal 3
4. Start NAO script (`nao/`) → Terminal 4
5. Open `/admin` and `/quiz` in browser
6. Join as player via `/join`
7. Watch the show!

---

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| Server won't start | Check port 5000 is free |
| NAO won't connect | Verify IP, check same network |
| SIC services fail | Ensure `redis-server` is running first |
| STT not working | Ensure `run-google-stt` is running |
| No jokes generated | Check `.env` has valid `GROQ_API_KEY` |
| Players can't join | Use network IP, not localhost |

See module-specific READMEs for detailed troubleshooting.

---

## 📚 Module Documentation

| Module | README | Focus |
|--------|--------|-------|
| **Kahoot-server** | [Kahoot-server/README.md](Kahoot-server/README.md) | API reference, quiz configuration, web interface |
| **nao** | [nao/README.md](nao/README.md) | Robot setup, LLM prompts, speech recognition |

---

## 🎓 For Developers

### Adding New Features

1. **New quiz questions** → Edit `Kahoot-server/data/quiz_data.py`
2. **New joke types** → Edit `nao/prompts.py`
3. **New API endpoints** → Edit `Kahoot-server/routes/`
4. **New robot behaviors** → Edit `nao/robot/show_controller.py`

### Code Style

- Functions < 20 lines
- Lots of comments
- Print statements for debugging
- Test incrementally

---

## 📦 Dependencies

Install from project root:

```bash
pip install -r requirements.txt
pip install "social-interaction-cloud[google-stt]"
```

---

**Good luck with your NAO Quiz Show!** 🤖🎮
