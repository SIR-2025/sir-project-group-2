"""
Kahoot Server Application
=========================

Simple Flask server for quiz management.
Provides web interface for players and REST API for Nao robot.

Architecture:
- Web routes: HTML pages for players (/, /admin, /join, /play)
- API routes: REST endpoints for Nao (/api/...)
- In-memory state: No database required

State stored in quiz_state dictionary.
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import qrcode
import io
import base64
import socket
from quiz_data import QUIZ_TITLE, QUESTIONS, validate_questions

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests for API

# ============================================================================
# GLOBAL STATE (In-Memory)
# ============================================================================

# Main quiz state dictionary
quiz_state = {
    "is_active": False,              # Is quiz currently running?
    "current_question": -1,          # Current question index (-1 = not started)
    "players": {},                   # Player data: {player_id: {name, answers}}
    "current_answers": {}            # Current question answers: {player_id: answer_idx}
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_local_ip():
    """
    Get the local IP address of this machine on the network.
    This allows other devices on the same WiFi network to connect.
    
    Returns:
        str: Local IP address (e.g. "192.168.1.100")
    """
    try:
        # Create a socket connection to determine local IP
        # We connect to an external address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS server
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # Fallback to localhost if detection fails
        return "localhost"


def reset_state():
    """
    Reset all quiz state to initial values.
    Called when quiz is reset or restarted.
    """
    quiz_state["is_active"] = False
    quiz_state["current_question"] = -1
    quiz_state["players"] = {}
    quiz_state["current_answers"] = {}


def get_current_question_data():
    """
    Get current question data.
    Returns None if no question is active.
    """
    idx = quiz_state["current_question"]
    if 0 <= idx < len(QUESTIONS):
        return QUESTIONS[idx]
    return None


def calculate_results():
    """
    Calculate results for current question.
    
    Returns:
        dict: Results containing:
            - answer_distribution: Count per option
            - correct_answer: Index of correct answer
            - player_answers: List of player answer data
    """
    question = get_current_question_data()
    if not question:
        return None
    
    # Count answers per option
    distribution = {0: 0, 1: 0, 2: 0, 3: 0}
    player_answer_list = []
    
    for player_id, answer_idx in quiz_state["current_answers"].items():
        # Update distribution
        if answer_idx in distribution:
            distribution[answer_idx] += 1
        
        # Add to player list
        player_name = quiz_state["players"].get(player_id, {}).get("name", "Unknown")
        is_correct = (answer_idx == question["correct_answer"])
        
        player_answer_list.append({
            "player_id": player_id,
            "player_name": player_name,
            "answer": answer_idx,
            "is_correct": is_correct
        })
    
    return {
        "answer_distribution": distribution,
        "correct_answer": question["correct_answer"],
        "player_answers": player_answer_list,
        "total_players": len(quiz_state["players"]),
        "answered_count": len(quiz_state["current_answers"])
    }


def generate_qr_code(url):
    """
    Generate QR code for given URL.
    Returns base64 encoded PNG image.
    """
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"


# ============================================================================
# WEB ROUTES (HTML Pages for Players)
# ============================================================================

@app.route('/')
def index():
    """
    Home page - redirects to admin dashboard.
    """
    return render_template('admin.html')


@app.route('/admin')
def admin():
    """
    Admin dashboard page.
    Shows quiz status, player count, and QR code for joining.
    """
    # Get local IP address for network access
    local_ip = get_local_ip()
    
    # Generate QR code for join URL using local IP
    # This allows other devices on the same WiFi to connect
    join_url = f"http://{local_ip}:5000/join"
    qr_code = generate_qr_code(join_url)
    
    return render_template('admin.html', 
                         quiz_title=QUIZ_TITLE,
                         total_questions=len(QUESTIONS),
                         qr_code=qr_code,
                         join_url=join_url)


@app.route('/join')
def join():
    """
    Player join page.
    Players enter their name here to join the quiz.
    """
    return render_template('join.html', quiz_title=QUIZ_TITLE)


@app.route('/play')
def play():
    """
    Quiz play page.
    Shows questions and answer options to players.
    """
    player_id = request.args.get('player_id', '')
    player_name = quiz_state["players"].get(player_id, {}).get("name", "Unknown")
    
    return render_template('play.html', 
                         player_id=player_id,
                         player_name=player_name,
                         quiz_title=QUIZ_TITLE)


# ============================================================================
# API ROUTES - Player Actions
# ============================================================================

@app.route('/api/player/join', methods=['POST'])
def api_player_join():
    """
    API endpoint for player to join quiz.
    
    Request body:
        {name: string}
    
    Returns:
        {player_id: string, player_name: string}
    """
    data = request.get_json()
    player_name = data.get('name', 'Anonymous')
    
    # Generate unique player ID
    import uuid
    player_id = str(uuid.uuid4())
    
    # Store player
    quiz_state["players"][player_id] = {
        "name": player_name,
        "answers": []
    }
    
    return jsonify({
        "player_id": player_id,
        "player_name": player_name
    })


@app.route('/api/player/answer', methods=['POST'])
def api_player_answer():
    """
    API endpoint for player to submit answer.
    
    Request body:
        {player_id: string, answer: integer}
    
    Returns:
        {success: boolean}
    """
    data = request.get_json()
    player_id = data.get('player_id')
    answer = data.get('answer')
    
    # Validate
    if player_id not in quiz_state["players"]:
        return jsonify({"error": "Invalid player_id"}), 400
    
    if not isinstance(answer, int) or not 0 <= answer < 4:
        return jsonify({"error": "Invalid answer"}), 400
    
    # Store answer
    quiz_state["current_answers"][player_id] = answer
    
    # Add to player's answer history
    quiz_state["players"][player_id]["answers"].append({
        "question": quiz_state["current_question"],
        "answer": answer
    })
    
    return jsonify({"success": True})


@app.route('/api/player/status', methods=['GET'])
def api_player_status():
    """
    API endpoint for player to check quiz status.
    Used for polling to detect question changes.
    
    Returns:
        {
            is_active: boolean,
            current_question: integer,
            question_data: object (if active)
        }
    """
    player_id = request.args.get('player_id')
    
    response = {
        "is_active": quiz_state["is_active"],
        "current_question": quiz_state["current_question"]
    }
    
    # Add question data if quiz is active
    if quiz_state["is_active"]:
        question = get_current_question_data()
        if question:
            # Send question without correct answer
            response["question_data"] = {
                "id": question["id"],
                "text": question["text"],
                "options": question["options"]
            }
        
        # Check if player already answered
        if player_id:
            response["has_answered"] = player_id in quiz_state["current_answers"]
    
    return jsonify(response)


# ============================================================================
# API ROUTES - Nao Robot Control
# ============================================================================

@app.route('/api/players', methods=['GET'])
def api_get_players():
    """
    API endpoint for Nao to get list of players.
    """
    player_names = [quiz_state["players"].get(player_id, {}).get("name", "Unknown") for player_id in quiz_state["players"].keys()]
    return jsonify(player_names)



@app.route('/api/status', methods=['GET'])
def api_status():
    """
    API endpoint for Nao to check quiz status.
    
    Returns complete quiz state including current question.
    Used by Nao to decide what to do next.
    """
    question = get_current_question_data()
    
    response = {
        "is_active": quiz_state["is_active"],
        "current_question": quiz_state["current_question"],
        "total_questions": len(QUESTIONS),
        "player_count": len(quiz_state["players"]),
        "answered_count": len(quiz_state["current_answers"]),
        "current_question_data": question
    }
    
    return jsonify(response)


@app.route('/api/start', methods=['POST'])
def api_start():
    """
    API endpoint to start the quiz.
    
    Sets quiz to active and moves to first question.
    Clears any previous answers.
    """
    quiz_state["is_active"] = True
    quiz_state["current_question"] = 0
    quiz_state["current_answers"] = {}
    
    return jsonify({"success": True, "message": "Quiz started"})


@app.route('/api/next', methods=['POST'])
def api_next():
    """
    API endpoint to move to next question.
    
    Increments question counter and clears answers.
    """
    current = quiz_state["current_question"]
    
    # Move to next question
    if current < len(QUESTIONS) - 1:
        quiz_state["current_question"] = current + 1
        quiz_state["current_answers"] = {}
        return jsonify({"success": True, "message": "Next question"})
    else:
        # No more questions
        quiz_state["is_active"] = False
        return jsonify({"success": True, "message": "Quiz finished"})


@app.route('/api/previous', methods=['POST'])
def api_previous():
    """
    API endpoint to move to previous question (optional).
    
    Used if Nao wants to go back.
    """
    current = quiz_state["current_question"]
    
    if current > 0:
        quiz_state["current_question"] = current - 1
        quiz_state["current_answers"] = {}
        return jsonify({"success": True, "message": "Previous question"})
    else:
        return jsonify({"error": "Already at first question"}), 400


@app.route('/api/results', methods=['GET'])
def api_results():
    """
    API endpoint to get results for current question.
    
    Returns answer distribution and player answers.
    Used by Nao to announce results.
    """
    results = calculate_results()
    
    if results:
        return jsonify(results)
    else:
        return jsonify({"error": "No active question"}), 400


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """
    API endpoint to reset entire quiz.
    
    Clears all state, removes all players.
    """
    reset_state()
    return jsonify({"success": True, "message": "Quiz reset"})


# ============================================================================
# MAIN - Start Server
# ============================================================================

if __name__ == '__main__':
    # Validate quiz data on startup
    try:
        validate_questions()
        print("✅ Quiz data validated successfully")
        print(f"✅ Loaded {len(QUESTIONS)} questions")
    except ValueError as e:
        print(f"❌ Quiz data validation failed: {e}")
        exit(1)
    
    # Get local IP address
    local_ip = get_local_ip()
    
    # Start server
    print("\n" + "="*50)
    print("🎮 Simple Kahoot Server Starting")
    print("="*50)
    print(f"Local Access:  http://localhost:5000")
    print(f"Network Access: http://{local_ip}:5000")
    print(f"")
    print(f"📱 For players on other devices:")
    print(f"   Admin Dashboard: http://{local_ip}:5000/admin")
    print(f"   Player Join:     http://{local_ip}:5000/join")
    print("="*50 + "\n")
    
    # Run Flask app
    # host='0.0.0.0' allows connections from other devices on network
    app.run(host='0.0.0.0', port=5000, debug=True)

