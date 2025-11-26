import requests
from typing import Dict, Optional, List


SERVER_URL = "http://localhost:5000"

class KahootAPI:
    """
    API wrapper for communicating with Kahoot server.
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        print(f"[API] Initialized with server: {server_url}")

    def get_players(self) -> List[str]:
        print("[API] Getting players...")
        try:
            response = requests.get(f"{self.server_url}/api/players")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Players received: {data}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: Could not get players: {e}")
            return []


    def get_status(self) -> Dict:
        print("[API] Getting status...")
        try:
            response = requests.get(f"{self.server_url}/api/status")
            response.raise_for_status()
            data = response.json()

            print(f"[API] Status received:")
            print(f"      - Active: {data.get('is_active')}")
            print(f"      - Question: {data.get('current_question')} / {data.get('total_questions')}")
            print(f"      - Players: {data.get('player_count')}")
            print(f"      - Answers: {data.get('answered_count')}")

            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: Could not get status: {e}")
            return {}

    def start_quiz(self) -> bool:
        print("[API] Starting quiz...")
        try:
            response = requests.post(f"{self.server_url}/api/start")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Quiz started: {data.get('message')}")
            return data.get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: Could not start quiz: {e}")
            return False

    def next_question(self) -> bool:
        print("[API] Moving to next question...")
        try:
            response = requests.post(f"{self.server_url}/api/next")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Next question: {data.get('message')}")
            return data.get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: Could not move to next question: {e}")
            return False

    def get_results(self) -> Optional[Dict]:
        print("[API] Getting results...")
        try:
            response = requests.get(f"{self.server_url}/api/results")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Results received:")
            print(f"      - Correct answer: {data.get('correct_answer')}")
            print(f"      - Answered: {data.get('answered_count')} / {data.get('total_players')}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: Could not get results: {e}")
            return None

    def reset_quiz(self) -> bool:
        print("[API] Resetting quiz...")
        try:
            response = requests.post(f"{self.server_url}/api/reset")
            response.raise_for_status()
            data = response.json()
            print(f"[API] Quiz reset: {data.get('message')}")
            return data.get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: Could not reset quiz: {e}")
            return False


#print("testing the server connection")
#api = KahootAPI(SERVER_URL)
#api.get_players()
#api.get_status()
#print(api.get_results())
#player_answers = api.get_results()["player_answers"]
#print(f"Player answers: {player_answers}")


