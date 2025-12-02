"""
Scoring Module
==============
Kahoot-style score calculation based on answer speed.
"""

MAX_POINTS = 1000
MAX_TIME_SECONDS = 20


def calculate_score(answer_time_seconds: float, is_correct: bool) -> int:
    """Calculate score based on answer time. Returns 0-1000 points."""
    if not is_correct:
        return 0

    # Clamp time to max
    time_used = min(answer_time_seconds, MAX_TIME_SECONDS)

    # Kahoot formula: faster = more points (minimum 500 for correct)
    time_factor = 1 - (time_used / MAX_TIME_SECONDS) / 2
    score = int(MAX_POINTS * time_factor)

    return max(score, 500)  # Minimum 500 for correct answer


def get_rankings(player_scores: dict) -> list:
    """Get sorted rankings from player scores. Returns list of (player_id, score, rank)."""
    sorted_players = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)
    return [(pid, score, rank + 1) for rank, (pid, score) in enumerate(sorted_players)]


def calculate_rank_changes(current_rankings: list, previous_rankings: dict) -> list:
    """Calculate position changes for each player."""
    result = []
    for player_id, score, current_rank in current_rankings:
        previous_rank = previous_rankings.get(player_id, current_rank)
        change = previous_rank - current_rank  # Positive = moved up
        result.append({
            "player_id": player_id,
            "score": score,
            "rank": current_rank,
            "change": change
        })
    return result
