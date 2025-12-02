"""
Player API Routes Module
========================
REST API endpoints for player actions.
"""

from flask import Blueprint, request, jsonify
import uuid
from core.state import quiz_state, get_current_question_data, get_answer_time

player_api_bp = Blueprint('player_api', __name__, url_prefix='/api/player')


@player_api_bp.route('/join', methods=['POST'])
def join():
    """Player joins the quiz."""
    data = request.get_json()
    player_name = data.get('name', 'Anonymous')
    player_id = str(uuid.uuid4())

    quiz_state["players"][player_id] = {
        "name": player_name,
        "answers": []
    }
    quiz_state["player_scores"][player_id] = 0

    return jsonify({"player_id": player_id, "player_name": player_name})


@player_api_bp.route('/answer', methods=['POST'])
def answer():
    """Player submits an answer with timing."""
    data = request.get_json()
    player_id = data.get('player_id')
    answer_idx = data.get('answer')

    if player_id not in quiz_state["players"]:
        return jsonify({"error": "Invalid player_id"}), 400

    if not quiz_state["options_revealed"]:
        return jsonify({"error": "Options not revealed yet"}), 400

    if not isinstance(answer_idx, int) or not 0 <= answer_idx < 4:
        return jsonify({"error": "Invalid answer"}), 400

    # Record answer with time
    answer_time = get_answer_time()
    quiz_state["current_answers"][player_id] = {
        "answer": answer_idx,
        "time": answer_time
    }

    quiz_state["players"][player_id]["answers"].append({
        "question": quiz_state["current_question"],
        "answer": answer_idx,
        "time": answer_time
    })

    return jsonify({"success": True})


@player_api_bp.route('/status', methods=['GET'])
def status():
    """Get quiz status for player polling."""
    player_id = request.args.get('player_id')

    response = {
        "is_active": quiz_state["is_active"],
        "phase": quiz_state["phase"],
        "current_question": quiz_state["current_question"],
        "options_revealed": quiz_state["options_revealed"]
    }

    # Only send question data when options are revealed
    if quiz_state["is_active"] and quiz_state["options_revealed"]:
        question = get_current_question_data()
        if question:
            response["question_data"] = {
                "id": question["id"],
                "text": question["text"],
                "options": question["options"]
            }

    if player_id:
        response["has_answered"] = player_id in quiz_state["current_answers"]
        response["score"] = quiz_state["player_scores"].get(player_id, 0)

    return jsonify(response)
