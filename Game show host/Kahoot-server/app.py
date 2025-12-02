"""
Kahoot Server Application
=========================
Main entry point. Registers all blueprints and starts the server.
"""

from flask import Flask
from flask_cors import CORS
from data.quiz_data import QUESTIONS, validate_questions
from core.helpers import get_local_ip

# Import blueprints
from routes.web import web_bp
from routes.api_player import player_api_bp
from routes.api_nao import nao_api_bp

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(web_bp)
app.register_blueprint(player_api_bp)
app.register_blueprint(nao_api_bp)


if __name__ == '__main__':
    # Validate quiz data
    try:
        validate_questions()
        print("✅ Quiz data validated successfully")
        print(f"✅ Loaded {len(QUESTIONS)} questions")
    except ValueError as e:
        print(f"❌ Quiz data validation failed: {e}")
        exit(1)
    
    # Get local IP and start server
    local_ip = get_local_ip()
    
    print("\n" + "="*50)
    print("🎮 Simple Kahoot Server Starting")
    print("="*50)
    print(f"Local Access:   http://localhost:5000")
    print(f"Network Access: http://{local_ip}:5000")
    print(f"")
    print(f"📺 Host Display: http://{local_ip}:5000/quiz")
    print(f"🔧 Admin:        http://{local_ip}:5000/admin")
    print(f"📱 Player Join:  http://{local_ip}:5000/join")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
