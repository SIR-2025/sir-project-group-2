# Kahoot Server Module

Quiz server voor het Game Show Host project. Pure Flask, simpel en uitbreidbaar.

## 📁 Project Structuur

Dit is de **Server module** van het Game Show Host project:

```
Game show host/
├── Kahoot-server/     ← Deze folder (Quiz server)
│   ├── app.py
│   ├── quiz_data.py
│   └── ...
└── nao/              ← Nao robot code
```

**Lees eerst**: `../README.md` (hoofd README) voor overzicht van hele project.

## 🎯 Wat Doet Deze Module?

De **Server module** beheert de quiz:
- Houdt vragen en spelers bij (in-memory)
- Biedt web interface voor spelers
- Biedt REST API voor Nao robot
- Simpel: geen database nodig

## Quick Start

### 1. Install Dependencies
```bash
# Installeer vanaf project root
cd "Game show host"
pip install -r requirements.txt
```

### 2. Run Server
```bash
# Start server
cd "Game show host/Kahoot-server"
python app.py
```

Je ziet:
```
🎮 Simple Kahoot Server Starting
Server: http://localhost:5000
```

### 3. Test
- **Admin**: `http://localhost:5000/admin` (overzicht + QR code)
- **Join**: `http://localhost:5000/join` (voor spelers)

## 📂 File Structure

```
Kahoot-server/
├── app.py              # Flask server met alle routes
│                       # - Web routes (/, /admin, /join, /play)
│                       # - API routes (/api/...)
│                       # - Quiz state (in-memory dict)
│
├── quiz_data.py        # Vragen (EDIT DEZE!)
│                       # - QUIZ_TITLE
│                       # - QUESTIONS lijst
│
├── templates/          # HTML paginas voor spelers
│   ├── admin.html      # Admin dashboard (+ QR code)
│   ├── join.html       # Speler join pagina
│   └── play.html       # Quiz interface
│
└── static/             # CSS en JS
    └── css/
        └── style.css   # Styling
```

**Note**: Dependencies zitten in `../requirements.txt` (project root)

## 🔌 API voor Nao

De Nao robot gebruikt deze endpoints om de quiz te besturen.

### Status Ophalen
```
GET /api/status

Wat je krijgt:
{
    "is_active": true,              # Quiz actief?
    "current_question": 1,           # Huidige vraag nummer
    "total_questions": 3,            # Totaal aantal vragen
    "player_count": 5,               # Aantal spelers
    "answered_count": 3,             # Aantal antwoorden
    "current_question_data": {       # Huidige vraag
        "text": "Vraag tekst",
        "options": ["A", "B", "C", "D"],
        "correct_answer": 2
    }
}
```

**Nao gebruikt dit om**:
- Te checken hoeveel spelers er zijn
- Te zien hoeveel mensen hebben geantwoord
- Huidige vraag te krijgen

### Quiz Besturen
```
POST /api/start       # Start de quiz
POST /api/next        # Ga naar volgende vraag
POST /api/previous    # Ga naar vorige vraag (optioneel)
POST /api/reset       # Reset alles
```

### Resultaten Ophalen
```
GET /api/results

Wat je krijgt:
{
    "total_players": 5,                          # Totaal spelers
    "answered_count": 3,                         # Aantal antwoorden
    "answer_distribution": {0: 1, 1: 2, 2: 0},  # Verdeling per optie
    "correct_answer": 1,                         # Juiste antwoord index
    "player_answers": [...]                      # Wie antwoordde wat
}
```

**Nao gebruikt dit om**:
- Juiste antwoord te zeggen
- Statistieken te vertellen
- Grappen te maken ("Niemand koos A!")

## ✏️ Vragen Aanpassen

Edit `quiz_data.py`:

```python
# Quiz titel (verschijnt in interface)
QUIZ_TITLE = "Jouw Quiz Naam"

# Lijst met vragen
QUESTIONS = [
    {
        "id": 0,                              # Uniek ID
        "text": "Wat is de hoofdstad?",      # De vraag
        "options": ["A", "B", "C", "D"],     # 4 opties
        "correct_answer": 0                   # Index van juiste (0 = eerste)
    },
    {
        "id": 1,
        "text": "Volgende vraag?",
        "options": ["Optie 1", "Optie 2", "Optie 3", "Optie 4"],
        "correct_answer": 2  # 2 = derde optie
    }
]
```

**Tips**:
- Index begint bij 0 (0 = eerste optie, 1 = tweede, etc.)
- Altijd 4 opties gebruiken
- Elk vraag moet uniek `id` hebben
- Test na elke wijziging!

## 🤖 Voorbeeld: API Gebruiken vanuit Nao

Zie hoe de Nao module deze API gebruikt in `../nao/nao_kahoot.py`:

```python
# Voorbeeld uit de Nao module
import requests

SERVER = "http://localhost:5000"

# Haal status op
status = requests.get(f"{SERVER}/api/status").json()
print(f"Spelers: {status['player_count']}")
print(f"Geantwoord: {status['answered_count']}")

# Nao kan hier grappen maken
if status['answered_count'] < status['player_count']:
    nao.say("Kom op mensen, denk sneller!")

# Ga naar volgende vraag
requests.post(f"{SERVER}/api/next")
```

Voor volledige implementatie: zie `../nao/nao_kahoot.py`

## 🔨 Hoe Het Werkt

### Data Flow
1. **Vragen** → Hardcoded in `quiz_data.py`
2. **State** → In-memory dictionary in `app.py`
3. **Spelers** → Join via `/join`, antwoorden via `/api/player/answer`
4. **Nao** → Bestuurt via `/api/start`, `/api/next`, etc.
5. **Updates** → HTML polls elke 2 seconden

### Voordelen van Deze Aanpak
- ✅ Geen database nodig
- ✅ Geen WebSockets / SocketIO
- ✅ Simpel te begrijpen
- ✅ Makkelijk uit te breiden
- ✅ Werkt direct

### Limitaties
- ❌ Data gaat verloren bij restart (in-memory)
- ❌ Polling (geen real-time push)
- ❌ Single instance (geen load balancing)

Voor basis demo's: perfect. Voor productie: voeg database toe.

## 🚀 Uitbreiden

Wil je features toevoegen? Dit zijn de plekken:

### Meer Vragen
→ Edit `quiz_data.py`

### Timer Toevoegen
→ Voeg timestamp toe in `quiz_state` dict
→ Check tijd in `wait_for_answers()`

### Scoring Systeem
→ Bereken punten in `get_results()` functie
→ Voeg score toe aan player dict

### Database
→ Vervang `quiz_state` dict met SQLite
→ Gebruik SQLAlchemy voor easy ORM

### Nieuwe Endpoints
→ Voeg routes toe in `app.py`
→ Update `../nao/nao_kahoot.py` om ze te gebruiken

**Regel**: Houd het simpel. Test na elke wijziging.

## 📚 Meer Informatie

- **Over hele project**: Lees `../README.md`
- **Over Nao module**: Lees `../nao/QUICKSTART.md`
- **Troubleshooting**: Zie `../README.md` sectie "Veelvoorkomende Problemen"



