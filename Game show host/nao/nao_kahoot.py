"""
Nao Kahoot Quiz Master Application
===================================

Simple and modular Nao quiz application using SIC framework.

Components:
- KahootAPI: Communicates with Flask server
- NaoQuizMaster: Controls Nao and quiz flow (inherits from SICApplication)

Usage:
- TEST_API_ONLY = True: Test without Nao robot
- TEST_API_ONLY = False: Use real Nao robot
"""

import requests
import time
from typing import Dict, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVER_URL = "http://localhost:5000"  # Kahoot server address
NAO_IP = "10.0.0.137"  # Your Nao's IP address
TEST_API_ONLY = True  # Set to False to use real Nao

# Timing (in seconds)
WAIT_FOR_ANSWERS_TIME = 15
PAUSE_BETWEEN_QUESTIONS = 3

# ============================================================================
# SIC FRAMEWORK IMPORTS - Only if not in test mode
# ============================================================================

if not TEST_API_ONLY:
    from sic_framework.core.sic_application import SICApplication
    from sic_framework.devices import Nao
    from sic_framework.devices.common_naoqi.naoqi_text_to_speech import (
        NaoqiTextToSpeechRequest
    )
else:
    # Dummy base class for test mode
    class SICApplication:
        def __init__(self):
            pass
        def shutdown(self):
            pass


# ============================================================================
# KAHOOT API CLASS - Server Communication
# ============================================================================

class KahootAPI:
    """
    API wrapper for communicating with Kahoot server.
    
    This class handles all HTTP requests to the Flask server.
    Each method corresponds to one API endpoint.
    
    All methods include print statements for debugging.
    """
    
    def __init__(self, server_url: str):
        """
        Initialize API client.
        
        Args:
            server_url: Base URL of the Kahoot server (e.g. "http://localhost:5000")
        """
        self.server_url = server_url
        print(f"[API] Initialized with server: {server_url}")
    
    def get_status(self) -> Dict:
        """
        Get current quiz status.
        
        Returns complete state including:
        - is_active: Is quiz running?
        - current_question: Current question index
        - player_count: Number of joined players
        - answered_count: Number of answers received
        
        Returns:
            dict: Quiz status data
        """
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
        """
        Start the quiz.
        
        Activates the quiz and moves to first question.
        Clears any previous answers.
        
        Returns:
            bool: True if successful, False otherwise
        """
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
        """
        Move to next question.
        
        Increments question counter and clears current answers.
        If no more questions, ends the quiz.
        
        Returns:
            bool: True if successful, False otherwise
        """
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
        """
        Get results for current question.
        
        Returns answer distribution and which players answered correctly.
        
        Returns:
            dict: Results data containing:
                - answer_distribution: Count per option {0: count, 1: count, ...}
                - correct_answer: Index of correct answer
                - player_answers: List of player answer data
                - total_players: Total number of players
                - answered_count: Number of players who answered
            None: If no results available
        """
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
        """
        Reset entire quiz.
        
        Clears all state and removes all players.
        Use this to start fresh.
        
        Returns:
            bool: True if successful, False otherwise
        """
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


# ============================================================================
# NAO QUIZ MASTER CLASS - Robot Control & Quiz Flow
# ============================================================================

class NaoQuizMaster(SICApplication):
    """
    Main quiz master class.
    
    Inherits from SICApplication to control Nao robot.
    Manages complete quiz flow from greeting to end.
    
    Quiz Flow:
    1. Greet players
    2. Start quiz
    3. For each question: announce → wait → results
    4. End quiz
    """
    
    def __init__(self, nao_ip: str, server_url: str, test_mode: bool = False):
        """
        Initialize Nao Quiz Master.
        
        Args:
            nao_ip: IP address of Nao robot
            server_url: URL of Kahoot server
            test_mode: If True, don't use actual Nao robot
        """
        super(NaoQuizMaster, self).__init__()
        
        print("[NAO] Initializing Nao Quiz Master...")
        
        # Store configuration
        self.nao_ip = nao_ip
        self.test_mode = test_mode
        
        # Initialize API client
        self.api = KahootAPI(server_url)
        
        # Initialize Nao device (if not in test mode)
        self.nao = None
        if not self.test_mode:
            try:
                print(f"[NAO] Connecting to Nao at {nao_ip}...")
                self.nao = Nao(ip=nao_ip)
                print("[NAO] Connected to Nao successfully")
            except Exception as e:
                print(f"[NAO] ERROR: Could not connect to Nao: {e}")
                print("[NAO] Switching to test mode...")
                self.test_mode = True
        else:
            print("[NAO] Running in TEST MODE (no Nao connection)")
    
    def say(self, text: str):
        """
        Make Nao speak text.
        
        In test mode: Only prints the text.
        In robot mode: Uses Nao's text-to-speech via SIC framework.
        
        Args:
            text: Text for Nao to speak
        """
        print(f"[NAO SAYS] {text}")
        
        if not self.test_mode and self.nao:
            try:
                # Use SIC framework to make Nao speak
                self.nao.tts.request(NaoqiTextToSpeechRequest(text))
            except Exception as e:
                print(f"[NAO] ERROR: Could not speak: {e}")
    
    def greet_players(self):
        """
        Greet players and introduce the quiz.
        
        This is the opening of the quiz.
        Can be customized with jokes or personality.
        """
        print("\n[NAO] === GREETING PLAYERS ===")
        
        self.say("Hello everyone! Welcome to the quiz!")
        time.sleep(1)
        
        # Get current status to see how many players joined
        status = self.api.get_status()
        player_count = status.get('player_count', 0)
        
        if player_count == 0:
            self.say("Hmm, no players have joined yet. Please join using your phone or computer!")
        elif player_count == 1:
            self.say("Great! We have one player. Let's get started!")
        else:
            self.say(f"Awesome! We have {player_count} players. Let's begin!")
        
        time.sleep(1)
    
    def announce_question(self, question_data: Dict):
        """
        Announce a question and its options.
        
        Args:
            question_data: Question data from server containing:
                - text: Question text
                - options: List of 4 option texts
        """
        print("\n[NAO] === ANNOUNCING QUESTION ===")
        
        # Read the question
        question_text = question_data.get('text', '')
        self.say(f"Here is the question: {question_text}")
        time.sleep(2)
        
        # Read the options
        options = question_data.get('options', [])
        self.say("The options are:")
        time.sleep(1)
        
        # Announce each option
        for idx, option in enumerate(options):
            self.say(f"Option {idx + 1}: {option}")
            time.sleep(1)
    
    def wait_for_answers(self, wait_time: int = WAIT_FOR_ANSWERS_TIME):
        """
        Wait for players to submit their answers.
        
        Counts down and provides encouragement.
        
        Args:
            wait_time: How many seconds to wait for answers
        """
        print(f"\n[NAO] === WAITING FOR ANSWERS ({wait_time}s) ===")
        
        self.say(f"You have {wait_time} seconds to answer!")
        
        # Wait and check progress
        intervals = [wait_time // 2, 5, 0]  # Announce at half time, 5 seconds, and end
        
        for interval in intervals:
            if interval > 0:
                wait_duration = wait_time - interval
                print(f"[NAO] Waiting... ({wait_duration}s elapsed)")
                time.sleep(wait_duration)
                
                if interval == wait_time // 2:
                    status = self.api.get_status()
                    answered = status.get('answered_count', 0)
                    total = status.get('player_count', 0)
                    print(f"[NAO] Progress: {answered}/{total} answered")
                elif interval == 5:
                    self.say("5 seconds left!")
            else:
                # Final wait
                time.sleep(5)
                self.say("Time's up!")
    
    def announce_results(self, results_data: Dict):
        """
        Announce results for the current question.
        
        Shows correct answer and how many players got it right.
        
        Args:
            results_data: Results from server containing:
                - correct_answer: Index of correct answer
                - answer_distribution: Count per option
                - player_answers: List of player answer data
        """
        print("\n[NAO] === ANNOUNCING RESULTS ===")
        
        # Get result data
        correct_answer = results_data.get('correct_answer', 0)
        distribution = results_data.get('answer_distribution', {})
        player_answers = results_data.get('player_answers', [])
        
        # Announce correct answer
        self.say(f"The correct answer was option {correct_answer + 1}!")
        time.sleep(2)
        
        # Count how many players got it right
        correct_count = sum(1 for p in player_answers if p.get('is_correct', False))
        total_answered = len(player_answers)
        
        # Provide feedback based on results
        if correct_count == 0:
            self.say("Oh no! Nobody got it right. Better luck next time!")
        elif correct_count == total_answered:
            self.say("Excellent! Everyone got it right! Amazing!")
        else:
            self.say(f"{correct_count} out of {total_answered} players got it right!")
        
        time.sleep(2)
        
        # Optional: Announce answer distribution
        print(f"[NAO] Answer distribution: {distribution}")
    
    def run_quiz(self):
        """
        Main quiz flow.
        
        This is the main method that runs the entire quiz from start to finish.
        
        Flow:
        1. Greet players
        2. Start quiz
        3. Loop through questions:
           - Announce question
           - Wait for answers
           - Announce results
           - Move to next question
        4. End quiz
        """
        print("\n" + "="*60)
        print("🤖 NAO QUIZ MASTER STARTING")
        print("="*60)
        
        # Step 1: Greet players
        self.greet_players()
        time.sleep(2)
        
        # Step 2: Start the quiz
        print("\n[NAO] === STARTING QUIZ ===")
        if not self.api.start_quiz():
            print("[NAO] ERROR: Could not start quiz!")
            return
        
        self.say("Let's start the quiz!")
        time.sleep(2)
        
        # Step 3: Loop through questions
        while True:
            # Get current status
            status = self.api.get_status()
            
            # Check if quiz is still active
            if not status.get('is_active', False):
                print("[NAO] Quiz is no longer active")
                break
            
            # Get current question data
            question_data = status.get('current_question_data')
            if not question_data:
                print("[NAO] No question data available")
                break
            
            current_q = status.get('current_question', 0)
            total_q = status.get('total_questions', 0)
            
            print(f"\n[NAO] === QUESTION {current_q + 1} / {total_q} ===")
            
            # Announce question number
            self.say(f"Question {current_q + 1} of {total_q}")
            time.sleep(1)
            
            # Step 3a: Announce the question
            self.announce_question(question_data)
            
            # Step 3b: Wait for answers
            self.wait_for_answers()
            
            # Step 3c: Get results
            results = self.api.get_results()
            if not results:
                print("[NAO] ERROR: Could not get results")
                break
            
            # Step 3d: Announce results
            self.announce_results(results)
            
            # Check if there are more questions
            if current_q + 1 >= total_q:
                print("[NAO] That was the last question!")
                break
            
            # Step 3e: Move to next question
            self.say("Let's move to the next question!")
            time.sleep(PAUSE_BETWEEN_QUESTIONS)
            
            if not self.api.next_question():
                print("[NAO] ERROR: Could not move to next question")
                break
        
        # Step 4: End quiz
        print("\n[NAO] === ENDING QUIZ ===")
        self.say("That's all for today! Thank you for playing!")
        time.sleep(1)
        self.say("I hope you had fun! See you next time!")
        
        print("\n" + "="*60)
        print("🤖 NAO QUIZ MASTER FINISHED")
        print("="*60)
        
        # Shutdown SIC application
        self.shutdown()


# ============================================================================
# MAIN - Entry Point
# ============================================================================

def main():
    """
    Main entry point.
    
    Creates and runs the Nao Quiz Master application.
    """
    print("\n" + "="*60)
    print("🎮 NAO KAHOOT QUIZ APPLICATION")
    print("="*60)
    print(f"Server URL: {SERVER_URL}")
    print(f"Nao IP: {NAO_IP}")
    print(f"Test Mode: {TEST_API_ONLY}")
    print("="*60 + "\n")
    
    # Create and run quiz master
    try:
        quiz_master = NaoQuizMaster(
            nao_ip=NAO_IP,
            server_url=SERVER_URL,
            test_mode=TEST_API_ONLY
        )
        quiz_master.run_quiz()
    except KeyboardInterrupt:
        print("\n[NAO] Quiz interrupted by user")
    except Exception as e:
        print(f"\n[NAO] ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[NAO] Application finished")


if __name__ == "__main__":
    main()

