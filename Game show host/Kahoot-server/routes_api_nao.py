"""
Nao Robot API Routes Module
===========================
REST API endpoints for Nao robot control.
"""

from flask import Blueprint, jsonify
from quiz_data import QUESTIONS
from state import (
    quiz_state, get_current_question_data, reset_state,
    start_answer_timer, get_answer_distribution, save_current_rankings,
    PHASE_WAITING, PHASE_QUESTION, PHASE_ANSWERING, PHASE_RESULTS, PHASE_LEADERBOARD
)
from scoring import calculate_score, get_rankings, calculate_rank_changes

nao_api_bp = Blueprint('nao_api', __name__, url_prefix='/api')


@nao_api_bp.route('/players', methods=['GET'])
def get_players():
    """Get list of player names."""
    player_names = [p.get("name", "Unknown") for p in quiz_state["players"].values()]
    return jsonify(player_names)


@nao_api_bp.route('/status', methods=['GET'])
def status():
    """Get complete quiz status."""
    return jsonify({
        "is_active": quiz_state["is_active"],
        "phase": quiz_state["phase"],
        "current_question": quiz_state["current_question"],
        "total_questions": len(QUESTIONS),
        "player_count": len(quiz_state["players"]),
        "answered_count": len(quiz_state["current_answers"]),
        "options_revealed": quiz_state["options_revealed"],
        "current_question_data": get_current_question_data()
    })


@nao_api_bp.route('/start', methods=['POST'])
def start():
    """Start the quiz at first question."""
    quiz_state["is_active"] = True
    quiz_state["current_question"] = 0
    quiz_state["current_answers"] = {}
    quiz_state["options_revealed"] = False
    quiz_state["phase"] = PHASE_QUESTION
    
    # Initialize scores for all players
    for player_id in quiz_state["players"]:
        if player_id not in quiz_state["player_scores"]:
            quiz_state["player_scores"][player_id] = 0
    
    return jsonify({"success": True, "message": "Quiz started"})


@nao_api_bp.route('/reveal_options', methods=['POST'])
def reveal_options():
    """Reveal answer options and start timer."""
    if not quiz_state["is_active"]:
        return jsonify({"error": "Quiz not active"}), 400
    
    start_answer_timer()
    return jsonify({"success": True, "message": "Options revealed"})


@nao_api_bp.route('/show_answers', methods=['POST'])
def show_answers():
    """Close answering and show answer distribution."""
    if not quiz_state["is_active"]:
        return jsonify({"error": "Quiz not active"}), 400
    
    question = get_current_question_data()
    if not question:
        return jsonify({"error": "No active question"}), 400
    
    # Calculate scores for this question
    for player_id, answer_data in quiz_state["current_answers"].items():
        is_correct = answer_data["answer"] == question["correct_answer"]
        points = calculate_score(answer_data["time"], is_correct)
        quiz_state["player_scores"][player_id] = quiz_state["player_scores"].get(player_id, 0) + points
    
    quiz_state["phase"] = PHASE_RESULTS
    
    return jsonify({
        "success": True,
        "distribution": get_answer_distribution(),
        "correct_answer": question["correct_answer"]
    })


@nao_api_bp.route('/show_leaderboard', methods=['POST'])
def show_leaderboard():
    """Show top 10 leaderboard with rank changes."""
    save_current_rankings()
    quiz_state["phase"] = PHASE_LEADERBOARD
    return jsonify({"success": True, "leaderboard": get_leaderboard_data()})


@nao_api_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get current leaderboard data (without changing phase)."""
    return jsonify({"leaderboard": get_leaderboard_data()})


def get_leaderboard_data():
    """Helper: build leaderboard list with top 10 players."""
    rankings = get_rankings(quiz_state["player_scores"])
    rank_data = calculate_rank_changes(rankings, quiz_state["previous_rankings"])
    
    leaderboard = []
    for entry in rank_data[:10]:
        player = quiz_state["players"].get(entry["player_id"], {})
        leaderboard.append({
            "name": player.get("name", "Unknown"),
            "score": entry["score"],
            "rank": entry["rank"],
            "change": entry["change"]
        })
    return leaderboard


@nao_api_bp.route('/next', methods=['POST'])
def next_question():
    """Move to next question."""
    current = quiz_state["current_question"]
    
    # Save rankings before moving to next question
    save_current_rankings()
    
    if current < len(QUESTIONS) - 1:
        quiz_state["current_question"] = current + 1
        quiz_state["current_answers"] = {}
        quiz_state["options_revealed"] = False
        quiz_state["question_start_time"] = None
        quiz_state["phase"] = PHASE_QUESTION
        return jsonify({"success": True, "message": "Next question"})
    else:
        quiz_state["is_active"] = False
        quiz_state["phase"] = PHASE_WAITING
        return jsonify({"success": True, "message": "Quiz finished"})


@nao_api_bp.route('/results', methods=['GET'])
def results():
    """Get results for current question."""
    question = get_current_question_data()
    if not question:
        return jsonify({"error": "No active question"}), 400
    
    return jsonify({
        "distribution": get_answer_distribution(),
        "correct_answer": question["correct_answer"],
        "total_players": len(quiz_state["players"]),
        "answered_count": len(quiz_state["current_answers"])
    })


@nao_api_bp.route('/reset', methods=['POST'])
def reset():
    """Reset entire quiz."""
    reset_state()
    return jsonify({"success": True, "message": "Quiz reset"})
