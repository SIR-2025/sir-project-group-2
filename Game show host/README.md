# Nao Game Show Host

A modular quiz system where the Nao robot acts as the quiz master.

## 📦 What Is This?

This project consists of **two independent modules** that work together:


```
Game show host/
├── requirements.txt ← Install here (for both modules)
├── Kahoot-server/ ← Quiz server (Flask web app)
└── nao/ ← Nao robot code (SIC framework)
```


### Module 1: Kahoot-server
- **What**: A simple Flask web server for quiz management  
- **Does**: Keeps quiz state, sends questions to players  
- **For**: Players (via browser) and Nao (via API)  
- **Technology**: Pure Python Flask, no database  

### Module 2: nao
- **What**: Nao robot application that presents the quiz  
- **Does**: Connects to server, reads questions aloud, announces results  
- **For**: Nao robot  
- **Technology**: SIC framework  

## 🎯 How Does It Work?



```
┌─────────────┐
│   Players   │  → Browser: http://localhost:5000/join
│  (Browser)  │
└──────┬──────┘
       │
       ↓ HTTP Requests
┌─────────────────────────────────────────┐
│         Kahoot-server/                  │
│         Flask Server (app.py)           │
│                                         │
│  • Maintains quiz state                 │
│  • Receives answers from players        │
│  • Provides REST API for Nao            │
└──────┬──────────────────────────────────┘
       │
       ↓ REST API (JSON)
┌──────────────────────────────────┐
│         nao/                     │
│         Nao Robot Application    │
│                                  │
│  • Fetches questions via API     │
│  • Reads questions alou          │
│  • Announces results             │
└──────────────────────────────────┘
```


## 🚀 Quick Start (3 minutes)

### Step 1: Install Dependencies

```bash
# Install all dependencies (one time)
cd "Game show host"
pip install -r requirements.txt

```

**What gets installed**:
- Flask + CORS (for server)
- QR code generator (for players to join)
- Requests (for API communication)
- SIC framework (commented out — only needed for real Nao)

### Step 2: Start de Quiz Server

```bash
# Terminal 1: Start server
cd "Game show host/Kahoot-server"
python app.py

```

You'll see:
```
🎮 Simple Kahoot Server Starting
Server: http://localhost:5000
```

### Step 3: Test the Nao Code (without robot)

```bash
# Terminal 2: Test Nao application
cd "Game show host/nao"
python nao_kahoot.py
```

Debug output:
```
[API] Getting status...
[NAO SAYS] Hello everyone! Welcome to the quiz!
```

✅ **Done!** The modules work together.
### Step 4: Add Players (optional)

Open in your browser:
- `http://localhost:5000/join`

## 📚 Documentation Per Module

### Kahoot-server Module

**Read**: `Kahoot-server/README.md`

Contains:
- Detailed API documentation
- How to adjust questions (`quiz_data.py`)
- Explanation of all endpoints
- How to extend functionality

### Nao Module

**Read**: `nao/QUICKSTART.md`

Contains:
- Step-by-step instructions
- Test mode (no Nao required)
- How to connect to a real Nao
- Code examples

## 🔧 Configuration

### Server Configuration
In `Kahoot-server/quiz_data.py`:
```python
QUIZ_TITLE = "Nao's Fun Quiz"
QUESTIONS = [...]  # Edit questions here
```

### Nao Configuration
In \`nao/nao_kahoot.py\`:
\`\`\`python
SERVER_URL = "http://localhost:5000"  # Server address
NAO_IP = "10.0.0.137"                  # Nao IP address
TEST_API_ONLY = True                   # True = test without Nao
\`\`\`

### SIC Framework (Real Nao)
If you want to work with a real Nao:
1. Edit \`requirements.txt\`
2. Uncomment the line: \`# social-interaction-cloud\`
3. Run: \`pip install -r requirements.txt\`

## 💡 Why Modular?

### ✅ Advantages

1. **Independent testing**
   - Test server without Nao
   - Test Nao code without the real robot

2. **Easy to expand**
   - Add server features without touching Nao code
   - Add Nao behavior without modifying the server

3. **Clear responsibilities**
   - Server: Quiz logic and data
   - Nao: Presentation and interaction

4. **Learn and understand**
   - Every module is small and readable
   - Clear API boundaries

## 📖 Code Structure Details

### Project Root
```
Game show host/
├── requirements.txt    # Central dependencies (use this!)
├── README.md           # This file
├── Kahoot-server/      # Server module
└── nao/                # Nao module
```

### Kahoot-server Files
```
Kahoot-server/
├── app.py              # Flask server with all routes
├── quiz_data.py        # Questions (EDIT HERE)
├── templates/          # HTML for players
│   ├── admin.html      # Admin dashboard
│   ├── join.html       # Player join page
│   └── play.html       # Quiz interface
└── static/
    └── css/
        └── style.css   # Styling
```

### Nao Files
```
nao/
├── nao_kahoot.py       # Main Nao application
└── QUICKSTART.md       # Detailed explanation
```

## 🎓 Usage Scenarios

### Scenario 1: Development and Testing
```bash
# One-time: install dependencies
cd "Game show host"
pip install -r requirements.txt

# Terminal 1: start server
cd Kahoot-server
python app.py

# Terminal 2: test Nao (without robot)
cd ../nao
python nao_kahoot.py
```

### Scenario 2: Demo with Real Nao
```bash
# Terminal 1: start server
cd Kahoot-server
python app.py

# Terminal 2: connect Nao
cd ../nao
# Edit nao_kahoot.py: TEST_API_ONLY = False
python nao_kahoot.py
```

### Scenario 3: Add Players
1. Start server (as above)
2. Players: go to `http://localhost:5000/join`
3. Admin view: go to `http://localhost:5000/admin`

## 🧪 Test Checklist

Follow these steps to test everything:

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Start server → see "Server Starting" message
- [ ] Open `http://localhost:5000/admin` → admin dashboard appears
- [ ] Open `http://localhost:5000/join` → add a player
- [ ] Run `nao/nao_kahoot.py` → see debug output
- [ ] Check that Nao reads questions
- [ ] Check that players can answer

## 🔨 Extending

### Add New Questions
1. Edit `Kahoot-server/quiz_data.py`
2. Add a question to the `QUESTIONS` list
3. Restart server

### Modify Nao Behavior
1. Edit `nao/nao_kahoot.py`
2. Modify functions in the `NaoQuizMaster` class
3. Run again

### Add New API Endpoints
1. Edit `Kahoot-server/app.py`
2. Add a new route
3. Update `nao/nao_kahoot.py` to use the endpoint

## 🐛 Common Issues

### Server won't start
```bash
# Check if port 5000 is already in use
netstat -an | findstr :5000

# Or use a different port in app.py:
app.run(port=5001)
```

### Nao can't connect
1. Check if the server is running
2. Check `SERVER_URL` in `nao_kahoot.py`
3. Try `TEST_API_ONLY = True` first

### No players visible
1. Check if you visited the `/join` page
2. Check if you entered a name
3. Check browser console for errors

### Dependencies won't install
```bash
# Try installing separately
pip install flask flask-cors qrcode[pil] requests

# For Nao (only if needed):
pip install social-interaction-cloud
```

## 📝 Best Practices

### During Development
- ✅ Always test first with `TEST_API_ONLY = True`
- ✅ Use print statements to debug
- ✅ Test with 1–2 players first
- ✅ Commit often (small changes)

### During Presentation
- ✅ Test full flow beforehand
- ✅ Check Nao’s battery
- ✅ Check WiFi connection
- ✅ Have a backup plan (TEST_API_ONLY mode)

## 🎯 Next Steps

1. **Learn the basics**
   - Read `Kahoot-server/README.md`
   - Read `nao/QUICKSTART.md`
   - Run everything in test mode

2. **Test with players**
   - Add yourself as a player
   - Observe the full flow
   - Understand the interaction

3. **Connect Nao**
   - Set `TEST_API_ONLY = False`
   - Test with the real robot
   - Add jokes/gestures

4. **Expand**
   - More questions
   - Nao gestures for correct/incorrect answers
   - LED effects
   - Scoring system

## 📞 Need Help?

### Error Messages
- Check `[API]` prints → server communication issue
- Check `[NAO]` prints → robot issue
- Check browser console → player interface issue

### Adjust Questions
- Edit `Kahoot-server/quiz_data.py`
- Follow existing format exactly

### More Features
- Add small changes, test, then add more
- Use print statements everywhere
- Keep functions small (<20 lines)

---

**Good luck with your Nao quiz master!** 🤖🎮
