# Quick Start - Nao Kahoot Quiz

## 📁 Project Structuur

Dit is de **Nao module** van het Game Show Host project:

```
Game show host/
├── Kahoot-server/     ← Quiz server (Flask)
└── nao/              ← Deze folder (Nao code)
    ├── nao_kahoot.py
    └── QUICKSTART.md  ← Je bent hier
```

**Lees eerst**: `../README.md` (hoofd README) voor overzicht van hele project.

## 🎯 Wat Doet Deze Module?

De **Nao module** verbindt met de Kahoot server en presenteert de quiz:
- ✅ SIC framework application (echte Nao code)
- ✅ Modulair design (makkelijk uitbreiden)
- ✅ Test mode (geen Nao nodig voor leren)
- ✅ **Veel print statements** (zie wat er gebeurt)
- ✅ Direct werkend

## 🚀 Start in 3 Minuten

### 0. Install Dependencies (eenmalig)

```bash
# Installeer vanaf project root
cd "Game show host"
pip install -r requirements.txt
```

### 1. Start Quiz Server

```bash
# Terminal 1: Ga naar server folder
cd "Game show host/Kahoot-server"
python app.py
```

Je ziet:
```
🎮 Simple Kahoot Server Starting
Server: http://localhost:5000
```

### 2. Start Nao Application (Test Mode)

```bash
# Terminal 2: Ga naar nao folder
cd "Game show host/nao"
python nao_kahoot.py
```

Je ziet alle print statements:
```
[API] Initialized with server: http://localhost:5000
[NAO SAYS] Hello everyone! Welcome to the quiz!
[API] Getting status...
...
```

✅ **Gefeliciteerd!** De Nao module werkt!

## 📚 Meer Informatie

### Over het Hele Project
Lees `../README.md` voor:
- Architectuur overzicht
- Hoe beide modules samenwerken
- Gebruik scenario's
- Uitbreidingen

### Over de Quiz Server
Lees `../Kahoot-server/README.md` voor:
- API documentatie
- Hoe vragen aan te passen
- Server endpoints

## 🎨 Code Structuur - nao_kahoot.py

Het bestand `nao_kahoot.py` bestaat uit twee hoofdklassen:

### 1. KahootAPI Class
Communiceert met de server (API wrapper):

```python
class KahootAPI:
    def get_status(self):
        print("[API] Getting status...")  # Debug print!
        response = requests.get(f"{self.server_url}/api/status")
        data = response.json()
        print(f"[API] Status: {data}")    # Zie response!
        return data
```

**Doet**:
- Alle HTTP requests naar server
- Print debug info
- Return JSON data

### 2. NaoQuizMaster Class
Bestuurt Nao en quiz flow (SIC Application):

```python
class NaoQuizMaster(SICApplication):
    def say(self, text):
        print(f"[NAO SAYS] {text}")       # Debug print!
        self.nao.tts.request(NaoqiTextToSpeechRequest(text))
```

**Doet**:
- Maakt Nao praten
- Controleert quiz flow
- Wacht op antwoorden
- Kondigt resultaten aan

**Voordelen**:
- 🔍 **Zie alles**: Print bij elke stap
- 🧩 **Modulair**: Elke class doet 1 ding
- 🧪 **Testbaar**: Test zonder Nao
- 📈 **Uitbreidbaar**: Voeg functies toe zonder alles te breken

## 🔧 Configuration

In `nao_kahoot.py` bovenaan:

```python
SERVER_URL = "http://localhost:5000"  # Je server adres
NAO_IP = "192.168.1.XXX"              # Nao IP (later)
TEST_API_ONLY = True                   # True = geen Nao nodig
```

### Test Zonder Nao
```python
TEST_API_ONLY = True
```

### Gebruik Met Echte Nao
```python
TEST_API_ONLY = False
NAO_IP = "192.168.1.100"  # Jouw Nao IP
```

## 📊 Hoe Nao Module met Server Praat

```
Browser (Spelers)
       ↓
Flask Server (../Kahoot-server/app.py)
       ↓ REST API (JSON)
KahootAPI Class (nao_kahoot.py)
       ↓ gebruikt door
NaoQuizMaster Class (nao_kahoot.py)
       ↓ SIC Framework
NAO Robot
```

**Flow**:
1. Spelers joinen via browser → Server
2. Nao haalt status op → `KahootAPI.get_status()`
3. Nao leest vraag voor → `NaoQuizMaster.announce_question()`
4. Nao wacht op antwoorden → `NaoQuizMaster.wait_for_answers()`
5. Nao haalt resultaten op → `KahootAPI.get_results()`
6. Nao kondigt aan → `NaoQuizMaster.announce_results()`

## 💡 Best Practices (Zoals in Code)

### 1. Print Statements voor Debugging
```python
def get_status(self):
    print("[API] Getting status...")     # Wat ga je doen
    response = requests.get(...)
    print(f"[API] Status: {response}")   # Wat kreeg je terug
    return response
```

### 2. Kleine Functies (Single Responsibility)
```python
# ✅ GOED: 1 functie = 1 taak
def say(self, text):
    print(f"[NAO SAYS] {text}")
    self.nao.tts.request(NaoqiTextToSpeechRequest(text))

# ❌ FOUT: Te veel verantwoordelijkheden
def say_and_move_and_lights(self, text, gesture, color):
    # Te ingewikkeld!
```

### 3. Modules Scheiden
```python
# API communicatie = apart
class KahootAPI:
    pass

# Nao logica = apart  
class NaoQuizMaster:
    def __init__(self):
        self.api = KahootAPI()  # Gebruikt API class
```

## 🎓 Volgende Stappen

### 1. Begrijp de Code
- Open `nao_kahoot.py`
- Lees de comments
- Run in test mode
- Volg de print statements

### 2. Test met Spelers
```bash
# Browser: open http://localhost:5000/join
# Voeg jezelf toe als speler
# Run nao_kahoot.py
# Beantwoord vragen als speler
```

### 3. Verbind met Echte Nao
```python
# Edit nao_kahoot.py:
TEST_API_ONLY = False
NAO_IP = "10.0.0.137"  # Jouw Nao IP
```

### 4. Breid Uit
Ideeën:
- Voeg grappen toe tussen vragen
- Maak Nao gebaren bij juiste/foute antwoorden
- LED effecten (groen = goed, rood = fout)
- Nao reageert op snelheid van antwoorden

Veel plezier met leren! 🚀

---

## 🐛 Troubleshooting

### "Cannot connect to server"
```bash
# Check of server draait
# Terminal 1: cd ../Kahoot-server && python app.py
```

### "Print statements maar Nao praat niet"
```python
# Check configuratie in nao_kahoot.py:
TEST_API_ONLY = False  # Moet False zijn voor echte Nao
NAO_IP = "10.0.0.137"  # Check IP adres
```

### "Nao praat te snel"
```python
# Voeg time.sleep() toe in announce_question():
def announce_question(self, question_data):
    self.say(question_data['text'])
    time.sleep(2)  # Voeg pauze toe
    self.say("The options are:")
```

**Meer hulp?** Lees `../README.md` voor complete troubleshooting.


