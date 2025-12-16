# Kahoot Server

Flask web server for the NAO Quiz Show. Manages quiz state, players, and scoring.

> 📖 For full project setup, see the [main README](../README.md).

---

## Quick Start

```bash
cd "Game show host/Kahoot-server"
pip install flask flask-cors qrcode[pil]
python app.py
```

Open http://localhost:5000/admin in your browser.

---

## Web Pages

| URL | Purpose |
|-----|---------|
| `/admin` | Control quiz flow, see player count |
| `/quiz` | Host display for projector/TV |
| `/join` | QR code + player name entry |
| `/play` | Player answer interface (mobile) |

---

## Architecture

```
Kahoot-server/
├── app.py                 # Flask entry point
├── routes/
│   ├── web.py             # HTML pages
│   ├── api_player.py      # Player endpoints (/api/player/*)
│   └── api_nao.py         # NAO endpoints (/api/*)
├── core/
│   ├── state.py           # In-memory quiz state
│   ├── scoring.py         # Points calculation
│   └── helpers.py         # QR code, IP detection
├── data/
│   └── quiz_data.py       # Questions (EDIT HERE)
├── templates/             # HTML (Jinja2)
└── static/css/            # Styling
```

---

## API Reference

### NAO Robot API (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | Quiz state, current question, player count |
| GET | `/players` | List of player names |
| POST | `/start` | Start quiz at question 0 |
| POST | `/reveal_options` | Show options, start 20s timer |
| POST | `/show_answers` | Calculate scores, reveal correct answer |
| POST | `/show_leaderboard` | Show top 10 with rank changes |
| GET | `/leaderboard` | Get leaderboard (no phase change) |
| POST | `/next` | Move to next question |
| GET | `/results` | Answer distribution for current question |
| POST | `/reset` | Reset quiz to initial state |

### Player API (`/api/player`)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/join` | `{"name": "..."}` | Join quiz, returns `player_id` |
| POST | `/answer` | `{"player_id": "...", "answer": 0}` | Submit answer (0-3) |
| GET | `/status?player_id=X` | - | Poll for quiz state |

### Example Response: `/api/show_answers`

```json
{
  "success": true,
  "distribution": [5, 2, 8, 1],
  "correct_answer": 2,
  "correct_answer_letter": "C",
  "correct_answer_text": "Amsterdam",
  "correct_players": ["Alice", "Bob"],
  "wrong_players": ["Charlie"]
}
```

---

## Quiz Configuration

### Edit Questions

Edit `data/quiz_data.py`:

```python
QUIZ_TITLE = "Your Quiz Title"

QUESTIONS = [
    {
        "id": 0,
        "text": "What is the capital of the Netherlands?",
        "options": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht"],
        "correct_answer": 0  # A=0, B=1, C=2, D=3
    },
    # Add more questions...
]
```

**Rules**:
- Each question needs: `id`, `text`, `options` (exactly 4), `correct_answer`
- `correct_answer` must be 0, 1, 2, or 3
- Server validates on startup

### Scoring System

| Speed | Points |
|-------|--------|
| Fast (0-5s) | ~1000 |
| Medium (5-15s) | ~750 |
| Slow (15-20s) | ~500 |
| Wrong | 0 |

---

## Quiz Phases

| Phase | Description |
|-------|-------------|
| `waiting` | Players can join, quiz not started |
| `question` | Question displayed, options hidden |
| `answering` | Options visible, 20s timer running |
| `results` | Correct answer + distribution shown |
| `leaderboard` | Top 10 with rank changes |
| `finished` | Quiz complete |

---

## State Management

All state is **in-memory** (resets on server restart):

```python
quiz_state = {
    "players": {},           # player_id -> {name, answers}
    "player_scores": {},     # player_id -> total score
    "current_answers": {},   # player_id -> current answer
    "phase": "waiting",
    "current_question": 0,
    "is_active": False
}
```

---

## Testing

### Verify Server Running

```bash
curl http://localhost:5000/api/status
```

### Simulate Player Join

```bash
curl -X POST http://localhost:5000/api/player/join \
  -H "Content-Type: application/json" \
  -d '{"name": "TestPlayer"}'
```

### Manual Test Flow

1. Open `/admin` in browser
2. Open `/join` in second tab, enter name
3. Click "Start Quiz" in admin
4. Click "Reveal Options"
5. Answer in player tab
6. Click "Show Answers"
7. Verify score appears

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5000 in use | Change port in `app.py`: `app.run(port=5001)` |
| Players can't join | Use network IP, ensure same WiFi |
| QR code not working | Type URL manually |
| Answers not registering | Click "Reveal Options" first |
| Scores not updating | Click "Show Answers" to calculate |

---

## Network Access

Players join from mobile devices:

1. Server shows local IP on startup
2. QR code on `/join` encodes this URL
3. All devices must be on same WiFi

**Note**: `localhost` only works on the same machine.
