"""
Server Connection Module
========================
API wrapper for communicating with Kahoot server.
"""

import requests
from typing import Dict, Optional, List

SERVER_URL = "http://localhost:5000"


class KahootAPI:
    """API wrapper for Kahoot server communication."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        print(f"[API] Initialized with server: {server_url}")

    def get_players(self) -> List[str]:
        """Get list of player names."""
        print("[API] Getting players...")
        try:
            response = requests.get(f"{self.server_url}/api/players")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Players: {data}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return []

    def get_status(self) -> Dict:
        """Get complete quiz status."""
        print("[API] Getting status...")
        try:
            response = requests.get(f"{self.server_url}/api/status")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Phase: {data.get('phase')}, Q: {data.get('current_question')}/{data.get('total_questions')}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return {}

    def start_quiz(self) -> bool:
        """Start the quiz."""
        print("[API] Starting quiz...")
        try:
            response = requests.post(f"{self.server_url}/api/start")
            response.raise_for_status()
            print(f"[API] Quiz started")
            return response.json().get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return False

    def reveal_options(self) -> bool:
        """Reveal answer options and start timer."""
        print("[API] Revealing options...")
        try:
            response = requests.post(f"{self.server_url}/api/reveal_options")
            response.raise_for_status()
            print(f"[API] Options revealed")
            return response.json().get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return False

    def show_answers(self) -> Optional[Dict]:
        """Close answering and show answer distribution."""
        print("[API] Showing answers...")
        try:
            response = requests.post(f"{self.server_url}/api/show_answers")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Distribution: {data.get('distribution')}, Correct: {data.get('correct_answer')}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return None

    def show_leaderboard(self) -> Optional[List[Dict]]:
        """Show top 10 leaderboard with rank changes."""
        print("[API] Showing leaderboard...")
        try:
            response = requests.post(f"{self.server_url}/api/show_leaderboard")
            response.raise_for_status()
            data = response.json()
            leaderboard = data.get('leaderboard', [])
            for entry in leaderboard[:5]:
                print(f"[API]   #{entry['rank']} {entry['name']}: {entry['score']} ({entry['change']:+d})")
            return leaderboard
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return None

    def next_question(self) -> bool:
        """Move to next question."""
        print("[API] Next question...")
        try:
            response = requests.post(f"{self.server_url}/api/next")
            response.raise_for_status()
            data = response.json()
            print(f"[API] {data.get('message')}")
            return data.get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return False

    def get_results(self) -> Optional[Dict]:
        """Get results for current question."""
        print("[API] Getting results...")
        try:
            response = requests.get(f"{self.server_url}/api/results")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Answered: {data.get('answered_count')}/{data.get('total_players')}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return None

    def reset_quiz(self) -> bool:
        """Reset entire quiz."""
        print("[API] Resetting quiz...")
        try:
            response = requests.post(f"{self.server_url}/api/reset")
            response.raise_for_status()
            print(f"[API] Quiz reset")
            return response.json().get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: {e}")
            return False


# Test connection when run directly
if __name__ == "__main__":
    api = KahootAPI(SERVER_URL)
    print("\n--- Testing API ---")
    api.get_status()
    api.get_players()
