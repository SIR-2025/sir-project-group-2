# NAO Quiz Host

NAO robot controller for the quiz show. Handles speech, jokes, and physical behaviors.

> 📖 For full project setup, see the [main README](../README.md).

---

## Quick Start

```bash
# 1. Ensure Kahoot server is running first (in Kahoot-server/ folder)

# 2. Start Redis (required for SIC framework)
# From sic_applications root folder:
cd conf/redis
.\redis-server.exe redis.conf      # Windows
# ./redis-server redis.conf        # Linux/Mac

# 3. Start Google STT service (from any folder)
run-google-stt

# 4. Configure and run
cd "Game show host/nao"
# Edit NAO_IP in main.py
python main.py
```

---

## Configuration

### 1. NAO Connection (`main.py`)

```python
NAO_IP = "10.0.0.239"           # Your NAO's IP address
SERVER_URL = "http://localhost:5000"
JOIN_WAIT_TIME = 60             # Seconds for players to join
```

### 2. API Key (`.env`)

Create `nao/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get free key at [console.groq.com](https://console.groq.com).

### 3. Google Credentials

Ensure `conf/google/google-key.json` exists with valid Google Cloud credentials.

---

## Architecture

```
nao/
├── main.py                 # NaoQuizMaster - main orchestrator
├── prompts.py              # LLM prompts for jokes
├── api/
│   └── kahoot_api.py       # HTTP client for Kahoot server
├── robot/
│   └── show_controller.py  # Physical control (mic, gaze, walk)
└── speech/
    ├── listener.py         # Google Speech-to-Text
    └── llm.py              # Groq LLM integration
```

### Components

| Component | Purpose |
|-----------|---------|
| `NaoQuizMaster` | Orchestrates quiz phases, coordinates all components |
| `NaoShowController` | Mic pose, pointing, face tracking, walking |
| `NaoListener` | Converts cohost speech to text |
| `KahootAPI` | Communicates with quiz server |
| `stream_llm_response_to_nao` | Generates and speaks jokes |

---

## Show Phases

| Phase | What NAO Does |
|-------|---------------|
| **Intro** | Introduces self, roasts cohost, listens to response |
| **Wait** | Tells players to join, jokes about usernames |
| **Quiz** | Reads questions, reveals answers, makes jokes |
| **Finale** | Announces winner/loser with personalized roasts |

---

## Joke System

Jokes are generated via Groq's fast LLM API in real-time.

### Joke Types

| Type | Trigger | Target |
|------|---------|--------|
| `wrong_answer` | After showing answers | Players who got it wrong |
| `cohost_roast` | During quiz | Direct jab at cohost |
| `cohost_react` | After cohost speaks | Sarcastic comeback |
| `audience` | Between questions | Whole group |
| `winner` | Finale | Backhanded compliment |
| `loser` | Finale | Gentle roast |

### Customize Personality

Edit `prompts.py`:

```python
BASE_PERSONA = """You are 'QuizBot 3000', a sarcastic stand-up comedian robot.
You have an edgy sense of humor. Think pub comedy, not family-friendly.
Keep responses SHORT: max 2 sentences, max 50 tokens."""
```

### Cohost Questions

```python
COHOST_QUESTIONS = [
    "Hey co-host, that was brutal right?",
    "Co-host, you agree that was tough?",
    # Add your own...
]
```

---

## Physical Behaviors

### Mic Pose

NAO holds a microphone pose throughout the show:
- Left arm holds imaginary mic
- Right arm free for pointing
- Arm swing disabled during walking

### Face Tracking

NAO tracks faces when talking to cohost:
- Head follows detected faces
- Stops tracking for audience moments

### Airborne Detection

If NAO is picked up:
- Stops all movement
- Eyes turn red
- Shouts "Put me down!"
- Countdown when placed back

---

## Testing

### Test NAO Connection

```bash
python -c "from sic_framework.devices import Nao; Nao(ip='10.0.0.239'); print('OK')"
```

### Test Server API

```bash
python api/kahoot_api.py
```

### Test Speech Recognition

```bash
python speech/listener.py
```

### Test LLM

Uncomment test code in `speech/llm.py`, then run it.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| NAO won't connect | Check IP, ensure same network, ping test |
| SIC services fail | Ensure `redis-server` is running first |
| STT not working | Run `run-google-stt` in separate terminal |
| No jokes | Check `.env` has `GROQ_API_KEY` |
| Server unreachable | Start Kahoot server first |
| NAO falls | Airborne detection kicks in - normal behavior |

### Debug Output

Watch console output for status:
- `[INIT]` - Initialization steps
- `[API]` - Server communication
- `[JOKE]` - LLM generation
- `[LISTEN]` - Speech recognition
- `[NAO]` - Physical actions

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `sic-framework` | NAO robot control |
| `requests` | HTTP calls to server |
| `groq` | LLM API for jokes |
| `python-dotenv` | Load `.env` file |

---

## Required Services

Before running, ensure these are active (in this order):

| Service | Folder | Command | Purpose |
|---------|--------|---------|---------|
| Kahoot server | `Kahoot-server/` | `python app.py` | Quiz state management |
| Redis | `conf/redis/` | `.\redis-server.exe redis.conf` | SIC framework message broker |
| Google STT | any | `run-google-stt` | Speech recognition |
