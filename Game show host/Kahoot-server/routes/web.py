"""
Web Routes Module
=================
HTML page routes for players, admin, and host display.
"""

from flask import Blueprint, render_template, request
from data.quiz_data import QUIZ_TITLE, QUESTIONS
from core.state import quiz_state
from core.helpers import get_local_ip, generate_qr_code

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    """Home page - redirects to admin dashboard."""
    return render_template('admin.html')


@web_bp.route('/admin')
def admin():
    """Admin dashboard with QR code for joining."""
    local_ip = get_local_ip()
    join_url = f"http://{local_ip}:5000/join"
    qr_code = generate_qr_code(join_url)

    return render_template('admin.html',
                         quiz_title=QUIZ_TITLE,
                         total_questions=len(QUESTIONS),
                         qr_code=qr_code,
                         join_url=join_url)


@web_bp.route('/join')
def join():
    """Player join page."""
    return render_template('join.html', quiz_title=QUIZ_TITLE)


@web_bp.route('/play')
def play():
    """Quiz play page for players on their phones."""
    player_id = request.args.get('player_id', '')
    player_name = quiz_state["players"].get(player_id, {}).get("name", "Unknown")

    return render_template('play.html',
                         player_id=player_id,
                         player_name=player_name,
                         quiz_title=QUIZ_TITLE)


@web_bp.route('/quiz')
def quiz():
    """Host display screen for projector/TV."""
    # Generate QR code and join URL for the waiting screen
    local_ip = get_local_ip()
    join_url = f"http://{local_ip}:5000/join"
    qr_code = generate_qr_code(join_url)

    return render_template('quiz.html',
                         quiz_title=QUIZ_TITLE,
                         total_questions=len(QUESTIONS),
                         qr_code=qr_code,
                         join_url=join_url)
