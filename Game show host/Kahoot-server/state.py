"""
Quiz State Module
=================
Global state management for the quiz.
"""

import time
from quiz_data import QUESTIONS

# Quiz phases
PHASE_WAITING = "waiting"
PHASE_QUESTION = "question"
PHASE_ANSWERING = "answering"
PHASE_RESULTS = "results"
PHASE_LEADERBOARD = "leaderboard"

# Main quiz state dictionary
quiz_state = {
    "is_active": False,
    "phase": PHASE_WAITING,
    "current_question": -1,
    "players": {},              # {player_id: {name, answers}}
    "current_answers": {},      # {player_id: {answer, time}}
    "player_scores": {},        # {player_id: total_score}
    "previous_rankings": {},    # {player_id: previous_rank}
    "question_start_time": None,
    "options_revealed": False
}


def reset_state():
    """Reset all quiz state to initial values."""
    quiz_state["is_active"] = False
    quiz_state["phase"] = PHASE_WAITING
    quiz_state["current_question"] = -1
    quiz_state["players"] = {}
    quiz_state["current_answers"] = {}
    quiz_state["player_scores"] = {}
    quiz_state["previous_rankings"] = {}
    quiz_state["question_start_time"] = None
    quiz_state["options_revealed"] = False


def get_current_question_data():
    """Get current question data. Returns None if no question is active."""
    idx = quiz_state["current_question"]
    if 0 <= idx < len(QUESTIONS):
        return QUESTIONS[idx]
    return None


def start_answer_timer():
    """Start the timer for answer scoring."""
    quiz_state["question_start_time"] = time.time()
    quiz_state["options_revealed"] = True
    quiz_state["phase"] = PHASE_ANSWERING


def get_answer_time() -> float:
    """Get seconds since options were revealed."""
    if quiz_state["question_start_time"]:
        return time.time() - quiz_state["question_start_time"]
    return 0.0


def get_answer_distribution():
    """Get count of answers per option."""
    distribution = {0: 0, 1: 0, 2: 0, 3: 0}
    for answer_data in quiz_state["current_answers"].values():
        answer_idx = answer_data["answer"]
        if answer_idx in distribution:
            distribution[answer_idx] += 1
    return distribution


def save_current_rankings():
    """Save current rankings for comparison after next question."""
    from scoring import get_rankings
    rankings = get_rankings(quiz_state["player_scores"])
    quiz_state["previous_rankings"] = {pid: rank for pid, _, rank in rankings}
