# Nao Game Show Host

Een modulair quiz systeem waar de Nao robot als quiz master fungeert.

## 📦 Wat Is Dit?

Dit project bestaat uit **twee onafhankelijke modules** die samenwerken:

```
Game show host/
├── requirements.txt   ← Installeer hier (voor beide modules)
├── Kahoot-server/     ← Quiz server (Flask web app)
└── nao/              ← Nao robot code (SIC framework)
```

### Module 1: Kahoot-server
- **Wat**: Een simpele Flask web server voor quiz beheer
- **Doet**: Houdt quiz staat bij, stuurt vragen naar spelers
- **Voor wie**: Spelers (via browser) en Nao (via API)
- **Technologie**: Pure Python Flask, geen database

### Module 2: nao
- **Wat**: Nao robot applicatie die quiz presenteert
- **Doet**: Verbindt met server, leest vragen voor, geeft resultaten
- **Voor wie**: Nao robot
- **Technologie**: SIC framework

## 🎯 Hoe Werkt Het?

```
┌─────────────┐
│   Spelers   │  → Browser: http://localhost:5000/join
│  (Browser)  │
└──────┬──────┘
       │
       ↓ HTTP Requests
┌─────────────────────────────────────────┐
│         Kahoot-server/                  │
│         Flask Server (app.py)           │
│                                         │
│  • Houdt quiz staat bij                │
│  • Ontvangt antwoorden van spelers     │
│  • Biedt REST API voor Nao             │
└──────┬──────────────────────────────────┘
       │
       ↓ REST API (JSON)
┌──────────────────────────────────┐
│         nao/                     │
│         Nao Robot Application    │
│                                  │
│  • Haalt vragen op via API      │
│  • Leest vragen voor            │
│  • Kondigt resultaten aan       │
└──────────────────────────────────┘
```

## 🚀 Quick Start (3 minuten)

### Stap 1: Installeer Dependencies

```bash
# Installeer alle dependencies (eenmalig)
cd "Game show host"
pip install -r requirements.txt
```

**Wat wordt geïnstalleerd**:
- Flask + CORS (voor server)
- QR code generator (voor speler join)
- Requests (voor API communicatie)
- SIC framework (uitgecomment - alleen nodig voor echte Nao)

### Stap 2: Start de Quiz Server

```bash
# Terminal 1: Start server
cd "Game show host/Kahoot-server"
python app.py
```

Je ziet:
```
🎮 Simple Kahoot Server Starting
Server: http://localhost:5000
```

### Stap 3: Test de Nao Code (zonder robot)

```bash
# Terminal 2: Test Nao applicatie
cd "Game show host/nao"
python nao_kahoot.py
```

Je ziet alle debug output:
```
[API] Getting status...
[NAO SAYS] Hello everyone! Welcome to the quiz!
```

✅ **Klaar!** De modules werken samen.

### Stap 4: Voeg Spelers Toe (optioneel)

Open in je browser:
- `http://localhost:5000/join`

## 📚 Documentatie Per Module

### Kahoot-server Module

**Lees**: `Kahoot-server/README.md`

Bevat:
- Gedetailleerde API documentatie
- Hoe vragen aan te passen (`quiz_data.py`)
- Uitleg van alle endpoints
- Hoe uit te breiden

### Nao Module

**Lees**: `nao/QUICKSTART.md`

Bevat:
- Stap-voor-stap uitleg
- Test mode (geen Nao nodig)
- Hoe te verbinden met echte Nao
- Code voorbeelden

## 🔧 Configuration

### Server Configuratie
In `Kahoot-server/quiz_data.py`:
```python
QUIZ_TITLE = "Nao's Fun Quiz"
QUESTIONS = [...]  # Pas vragen hier aan
```

### Nao Configuratie
In `nao/nao_kahoot.py`:
```python
SERVER_URL = "http://localhost:5000"  # Server adres
NAO_IP = "10.0.0.137"                  # Nao IP adres
TEST_API_ONLY = True                   # True = test zonder Nao
```

### SIC Framework (Echte Nao)
Als je met een echte Nao wilt werken:
1. Edit `requirements.txt`
2. Uncomment de regel: `# social-interaction-cloud`
3. Run: `pip install -r requirements.txt`

## 💡 Waarom Modulair?

### ✅ Voordelen

1. **Onafhankelijk testen**
   - Test server zonder Nao
   - Test Nao code zonder echte robot

2. **Makkelijk uitbreiden**
   - Voeg server features toe zonder Nao code aan te passen
   - Voeg Nao gedrag toe zonder server te wijzigen

3. **Duidelijke verantwoordelijkheden**
   - Server: Quiz logica en data
   - Nao: Presentatie en interactie

4. **Leren en begrijpen**
   - Elke module is klein en overzichtelijk
   - Duidelijke API grenzen

## 📖 Code Structuur Details

### Project Root
```
Game show host/
├── requirements.txt    # Centrale dependencies (gebruik deze!)
├── README.md          # Dit bestand
├── Kahoot-server/     # Server module
└── nao/              # Nao module
```

### Kahoot-server Files
```
Kahoot-server/
├── app.py              # Flask server met alle routes
├── quiz_data.py        # Vragen (HIER EDIT JE)
├── templates/          # HTML voor spelers
│   ├── admin.html      # Admin dashboard
│   ├── join.html       # Speler join pagina
│   └── play.html       # Quiz interface
└── static/
    └── css/
        └── style.css   # Styling
```

### Nao Files
```
nao/
├── nao_kahoot.py       # Main Nao application
└── QUICKSTART.md       # Gedetailleerde uitleg
```

## 🎓 Gebruik Scenario's

### Scenario 1: Ontwikkelen en Testen
```bash
# Eenmalig: Installeer dependencies
cd "Game show host"
pip install -r requirements.txt

# Terminal 1: Start server
cd Kahoot-server
python app.py

# Terminal 2: Test Nao (zonder robot)
cd ../nao
python nao_kahoot.py
```

### Scenario 2: Demonstratie met Echte Nao
```bash
# Terminal 1: Start server
cd Kahoot-server
python app.py

# Terminal 2: Verbind Nao
cd ../nao
# Edit nao_kahoot.py: TEST_API_ONLY = False
python nao_kahoot.py
```

### Scenario 3: Spelers toevoegen
1. Start server (zoals boven)
2. Spelers: ga naar `http://localhost:5000/join`
3. Admin view: ga naar `http://localhost:5000/admin`

## 🧪 Test Checklist

Volg deze stappen om alles te testen:

- [ ] Installeer dependencies: `pip install -r requirements.txt`
- [ ] Start server → zie "Server Starting" bericht
- [ ] Open `http://localhost:5000/admin` → zie admin dashboard
- [ ] Open `http://localhost:5000/join` → voeg speler toe
- [ ] Run `nao/nao_kahoot.py` → zie debug output
- [ ] Check dat Nao vragen leest
- [ ] Check dat spelers kunnen antwoorden

## 🔨 Uitbreiden

### Nieuwe Vragen Toevoegen
1. Edit `Kahoot-server/quiz_data.py`
2. Voeg vraag toe aan `QUESTIONS` lijst
3. Restart server

### Nao Gedrag Aanpassen
1. Edit `nao/nao_kahoot.py`
2. Pas functies in `NaoQuizMaster` class aan
3. Run opnieuw

### Nieuwe API Endpoints
1. Edit `Kahoot-server/app.py`
2. Voeg route toe
3. Update `nao/nao_kahoot.py` om endpoint te gebruiken

## 🐛 Veelvoorkomende Problemen

### Server start niet
```bash
# Check of poort 5000 al in gebruik is
netstat -an | findstr :5000

# Of gebruik andere poort in app.py:
app.run(port=5001)
```

### Nao kan niet verbinden
1. Check of server draait
2. Check `SERVER_URL` in `nao_kahoot.py`
3. Probeer eerst `TEST_API_ONLY = True`

### Geen spelers zichtbaar
1. Check of je `/join` pagina hebt bezocht
2. Check of je naam hebt ingevoerd
3. Check browser console voor errors

### Dependencies installeren lukt niet
```bash
# Probeer apart installeren
pip install flask flask-cors qrcode[pil] requests

# Voor Nao (alleen als nodig):
pip install social-interaction-cloud
```

## 📝 Best Practices

### Bij Ontwikkelen
- ✅ Test altijd eerst met `TEST_API_ONLY = True`
- ✅ Gebruik print statements om te debuggen
- ✅ Test met 1-2 spelers eerst
- ✅ Commit vaak (kleine changes)

### Bij Presenteren
- ✅ Test complete flow vooraf
- ✅ Check Nao batterij
- ✅ Check WiFi verbinding
- ✅ Heb backup plan (TEST_API_ONLY mode)

## 🎯 Volgende Stappen

1. **Leer de basis**
   - Lees `Kahoot-server/README.md`
   - Lees `nao/QUICKSTART.md`
   - Run alles in test mode

2. **Test met spelers**
   - Voeg jezelf toe als speler
   - Zie de complete flow
   - Begrijp de interactie

3. **Verbind Nao**
   - Zet `TEST_API_ONLY = False`
   - Test met echte robot
   - Voeg grappen/gestures toe

4. **Breid uit**
   - Meer vragen
   - Nao gestures bij juiste/foute antwoorden
   - LED effecten
   - Scoring systeem

## 📞 Hulp Nodig?

### Error Messages
- Check `[API]` prints → server communicatie probleem
- Check `[NAO]` prints → robot probleem
- Check browser console → speler interface probleem

### Vragen Aanpassen
- Edit `Kahoot-server/quiz_data.py`
- Volg bestaand formaat exact

### Meer Features
- Voeg klein toe, test, dan volgende
- Gebruik print statements overal
- Houd functies klein (<20 regels)

---

**Veel succes met je Nao quiz master!** 🤖🎮
