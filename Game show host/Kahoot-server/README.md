# Kahoot Server

Interactive quiz application inspired by Kahoot, designed for NAO robot control.

## Features

- Real-time multiplayer quiz game
- Kahoot-style speed-based scoring (500-1000 points)
- QR code generation for easy player joining
- Admin dashboard for manual control
- Host display for projector/TV
- RESTful API for NAO robot integration
- Leaderboard with rank tracking

## Project Structure

```
Kahoot-server/
├── app.py                      # Application entry point
├── routes/                     # HTTP endpoints
│   ├── web.py                  # HTML pages (admin, join, play, quiz)
│   ├── api_player.py           # Player API (join, answer, status)
│   └── api_nao.py              # NAO robot API (quiz control)
├── core/                       # Business logic
│   ├── state.py                # Global state management
│   ├── scoring.py              # Score calculation
│   └── helpers.py              # Utilities (QR code, IP detection)
├── data/                       # Configuration
│   └── quiz_data.py            # Quiz questions and title
├── templates/                  # HTML templates
└── static/css/                 # Stylesheets
```

## Installation

```bash
pip install flask flask-cors qrcode pillow
```

## Usage

### Start Server

```bash
python app.py
```

Server runs on port 5000. Access points:
- **Admin**: `http://localhost:5000/admin`
- **Player Join**: `http://localhost:5000/join`
- **Host Display**: `http://localhost:5000/quiz`

### Quiz Flow

1. Players join via QR code or join page
2. NAO/Admin starts quiz: `POST /api/start`
3. For each question:
   - Show question: phase automatically set to `PHASE_QUESTION`
   - Reveal options: `POST /api/reveal_options` (starts 20s timer)
   - Players submit answers via mobile interface
   - Show results: `POST /api/show_answers` (calculates scores)
   - Show leaderboard: `POST /api/show_leaderboard`
   - Next question: `POST /api/next`
4. Quiz ends after last question

## API Endpoints

### Player API (`/api/player`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/join` | Join quiz, returns `player_id` |
| POST | `/answer` | Submit answer (requires `player_id`, `answer` 0-3) |
| GET | `/status?player_id=X` | Poll for quiz state updates |

### NAO Robot API (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | Complete quiz status |
| GET | `/players` | List of player names |
| POST | `/start` | Start quiz at question 0 |
| POST | `/reveal_options` | Show options and start timer |
| POST | `/show_answers` | Calculate scores, show distribution |
| POST | `/show_leaderboard` | Display top 10 with rank changes |
| GET | `/leaderboard` | Get leaderboard data |
| POST | `/next` | Move to next question or finish |
| GET | `/results` | Get answer distribution |
| POST | `/reset` | Reset entire quiz |

## Configuration

### Edit Quiz Questions

Edit [data/quiz_data.py](data/quiz_data.py):

```python
QUIZ_TITLE = "Your Quiz Title"

QUESTIONS = [
    {
        "id": 0,
        "text": "Your question?",
        "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
        "correct_answer": 0  # Index 0-3
    },
    # Add more questions...
]
```

### Scoring System

- **Correct answer**: 500-1000 points (faster = more points)
- **Incorrect answer**: 0 points
- **Max time**: 20 seconds

Formula: Faster answers get up to 1000 points, slower answers get minimum 500 points.

## Quiz Phases

1. `PHASE_WAITING` - Before quiz starts
2. `PHASE_QUESTION` - Question displayed (options hidden)
3. `PHASE_ANSWERING` - Options revealed, timer running
4. `PHASE_RESULTS` - Answer distribution shown
5. `PHASE_LEADERBOARD` - Top 10 players displayed

## State Management

All quiz state is in-memory (resets on server restart):
- Player data (names, answers, scores)
- Current question and phase
- Answer submissions with timestamps
- Rankings and rank changes

No database required.

## Network Access

Players join from mobile devices on the same network. Server displays local IP on startup.
