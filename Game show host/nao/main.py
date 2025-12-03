"""
NAO Quiz Host - Main Script
============================
Clean, modular structure for NAO quiz show host.
Phase 1a: Intro with cohost + waiting for players

Author: Quiz Team
Date: 2025
"""

import time
import random
from os.path import abspath, join
from dotenv import load_dotenv

# SIC Framework imports
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import NaoqiTextToSpeechRequest
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiAnimationRequest,
)
from sic_framework.devices.common_naoqi.naoqi_autonomous import (
    NaoWakeUpRequest,
    NaoRestRequest,
)

# Local imports
from server_connection import KahootAPI
from nao_listener import NaoListener
from llm_integration_groq import get_llm_response_groq
from prompts import (
    PROMPT_PLAYER_NAMES,
    PROMPT_WRONG_ANSWER,
    PROMPT_COHOST_ROAST,
    PROMPT_AUDIENCE,
    PROMPT_COHOST_REACT,
    PROMPT_WINNER,
    PROMPT_LOSER,
    COHOST_QUESTIONS,
)

# Load environment variables (for GROQ_API_KEY)
load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

NAO_IP = "10.0.0.137"
SERVER_URL = "http://localhost:5000"
GOOGLE_KEY = abspath(join("..", "..", "conf", "google", "google-key.json"))
MINIMUM_PLAYERS = 2


# =============================================================================
# NAO QUIZ MASTER CLASS
# =============================================================================

class NaoQuizMaster:
    """
    NAO Quiz Host controller.
    Manages all NAO behaviors for the quiz show.
    """
    
    def __init__(self, nao_ip: str, server_url: str, google_key_path: str, minimum_players: int = 2):
        """
        Initialize NAO Quiz Master.
        
        Args:
            nao_ip: IP address of NAO robot
            server_url: URL of Kahoot server
            google_key_path: Path to Google Cloud credentials
            minimum_players: Minimum players needed to start
        """
        print(f"[INIT] Initializing NaoQuizMaster...")
        
        # Store configuration
        self.nao_ip = nao_ip
        self.minimum_players = minimum_players
        
        # Connect to NAO (single connection)
        print(f"[INIT] Connecting to NAO at {nao_ip}...")
        self.nao = Nao(ip=nao_ip)
        print(f"[INIT] ✓ NAO connected")
        
        # Setup speech-to-text listener
        print(f"[INIT] Setting up listener...")
        self.listener = NaoListener(self.nao, google_key_path, quiet=True)
        print(f"[INIT] ✓ Listener ready")
        
        # Connect to Kahoot server API
        print(f"[INIT] Connecting to server at {server_url}...")
        self.api = KahootAPI(server_url)
        print(f"[INIT] ✓ Server connected")
        
        # Joke rotation tracking
        # Cycles through: wrong_answer -> cohost -> audience
        self.joke_index = 0
        self.cohost_interaction_toggle = False  # Alternates between roast and ask
        
        print(f"[INIT] NaoQuizMaster ready!\n")
    
    # =========================================================================
    # SPEECH & MOTION HELPERS
    # =========================================================================
    
    def say(self, text: str, speed: int = 90, pitch: int = 110, block: bool = True):
        """
        Make NAO speak with custom voice settings.
        
        Args:
            text: Text to speak
            speed: Speech speed (default 90)
            pitch: Voice pitch (default 110)
            block: Wait for speech to finish (default True)
        """
        # NAO voice markup: \vct=pitch \rspd=speed
        formatted_text = f"\\vct={pitch}\\ \\rspd={speed}\\ {text}"
        self.nao.tts.request(NaoqiTextToSpeechRequest(formatted_text), block=block)
    
    def say_with_gesture(self, text: str, animation: str, speed: int = 90, pitch: int = 110):
        """
        Make NAO speak and perform animation simultaneously.
        
        Args:
            text: Text to speak
            animation: NAO animation name (e.g., "animations/Stand/Gestures/Hey_1")
            speed: Speech speed (default 90)
            pitch: Voice pitch (default 110)
        """
        # Start speech (non-blocking)
        self.say(text, speed=speed, pitch=pitch, block=False)
        
        # Perform gesture (blocking)
        self.nao.motion.request(NaoqiAnimationRequest(animation))
    
    def listen_to_cohost(self) -> str:
        """
        Listen to cohost response using Google Speech-to-Text.
        
        Returns:
            str: Transcribed text, or empty string if nothing detected
        """
        print("\n[LISTEN] Waiting for cohost response...")
        text = self.listener.listen()
        
        if text:
            print(f"[LISTEN] ✓ Cohost said: \"{text}\"")
        else:
            print(f"[LISTEN] ✗ Nothing detected")
        
        return text
    
    # =========================================================================
    # JOKE HELPERS
    # =========================================================================
    
    def make_joke(self, joke_type: str, context: str) -> str:
        """
        Generate a joke using LLM based on joke type.
        
        Args:
            joke_type: One of "wrong_answer", "cohost", "audience"
            context: Context for the joke (e.g., player names, scores)
        
        Returns:
            str: The generated joke
        """
        # Select the right prompt based on joke type
        prompts = {
            "wrong_answer": PROMPT_WRONG_ANSWER,
            "cohost": PROMPT_COHOST_ROAST,
            "audience": PROMPT_AUDIENCE,
            "winner": PROMPT_WINNER,
            "loser": PROMPT_LOSER,
        }
        
        prompt = prompts.get(joke_type, PROMPT_AUDIENCE)
        
        print(f"[JOKE] Generating {joke_type} joke...")
        joke = get_llm_response_groq(context, prompt)
        print(f"[JOKE] Generated: {joke}")
        
        return joke
    
    def ask_cohost(self, question: str = None) -> str:
        """
        Ask cohost a question and generate LLM response to their answer.
        
        Args:
            question: Optional specific question. If None, picks random.
        
        Returns:
            str: LLM-generated comeback to cohost's response
        """
        # Pick a random question if none provided
        if question is None:
            question = random.choice(COHOST_QUESTIONS)
        
        # Ask the question
        print(f"[COHOST] NAO asks: {question}")
        self.say(question)
        
        # Listen to cohost response
        cohost_response = self.listen_to_cohost()
        
        if not cohost_response:
            # No response, make a joke about it
            return "Okay, silent treatment. I see how it is."
        
        # Generate comeback using LLM
        comeback = get_llm_response_groq(cohost_response, PROMPT_COHOST_REACT)
        
        return comeback
    
    def get_next_joke_type(self) -> str:
        """
        Get the next joke type in rotation.
        Cycles: wrong_answer -> cohost -> audience -> repeat
        
        Returns:
            str: The joke type for this round
        """
        joke_types = ["wrong_answer", "cohost", "audience"]
        joke_type = joke_types[self.joke_index % len(joke_types)]
        self.joke_index += 1
        return joke_type
    
    def do_cohost_moment(self):
        """
        Handle cohost interaction - alternates between roast and asking input.
        """
        # Toggle between roasting and asking
        self.cohost_interaction_toggle = not self.cohost_interaction_toggle
        
        if self.cohost_interaction_toggle:
            # Ask cohost for input
            print("[COHOST] Asking cohost for input...")
            comeback = self.ask_cohost()
            self.say(comeback)
        else:
            # Just roast the cohost (no input needed)
            print("[COHOST] Roasting cohost...")
            joke = self.make_joke("cohost", "Make a quick jab at the human co-host")
            self.say(joke)
    
    # =========================================================================
    # GAME PHASES
    # =========================================================================
    
    def phase_intro(self):
        """
        Phase 1: Opening with cohost interaction.
        
        Flow:
        1. NAO introduces himself
        2. NAO introduces cohost as "assistant"
        3. Listen to cohost response
        4. NAO makes LLM-generated sarcastic comeback
        """
        print("\n" + "="*60)
        print("PHASE: INTRO")
        print("="*60)
        
        # 1. NAO introduces himself with wave gesture
        print("[INTRO] NAO introduces himself...")
        self.say_with_gesture(
            "Hello everyone! I'm Nao, your quiz host today!",
            animation="animations/Stand/Gestures/Hey_1"
        )
        
        time.sleep(1)
        
        # 2. NAO introduces cohost (gesture to the side)
        print("[INTRO] NAO introduces cohost...")
        self.say_with_gesture(
            "And this is my assistant",
            animation="animations/Stand/Gestures/ShowSky_2"
        )
        
        # 3. Listen to cohost response
        cohost_response = self.listen_to_cohost()
        
        if not cohost_response:
            print("[INTRO] No cohost response, continuing anyway...")
            self.say("Right... anyway, let's continue!")
            return
        
        # 4. Generate sarcastic comeback using LLM
        print("[INTRO] Generating LLM response...")
        llm_prompt = """You are 'QuizBot 3000', a sarcastic stand-up comedian robot with an edgy sense of humor.
You are making fun of the co-host in the quiz. Keep it short and punchy (max 2 sentences, max 50 tokens)."""
        
        comeback = get_llm_response_groq(cohost_response, llm_prompt)
        
        # 5. NAO delivers comeback
        print(f"[INTRO] NAO says comeback: {comeback}")
        self.say(comeback)
        
        time.sleep(1)
        print("[INTRO] ✓ Intro phase complete\n")
    
    def phase_wait_for_players(self):
        """
        Phase 2: Wait for players to join and make jokes.
        
        Flow:
        1. NAO tells people to join via QR code
        2. Loop: check player count every 5 seconds
        3. When halfway to minimum: make LLM joke about player name
        4. When minimum reached: continue to quiz
        
        TODO: Add walking/gaze behavior from mic.py here
        TODO: Add check for offensive usernames
        """
        print("\n" + "="*60)
        print("PHASE: WAITING FOR PLAYERS")
        print("="*60)
        
        # Reset quiz to start fresh
        print("[PLAYERS] Resetting quiz...")
        self.api.reset_quiz()
        
        # 1. Instructions to join
        print("[PLAYERS] NAO gives instructions...")
        self.say("Get your phones ready and join the game by scanning the QR code on the screen!")
        
        time.sleep(1)
        self.say("Type in your name. Don't worry, I don't judge your username choices... much.")
        
        # 2. Wait for players to join
        print(f"[PLAYERS] Waiting for {self.minimum_players} players...")
        
        joke_made = False  # Track if we already made a joke
        
        while True:
            # Get current player status
            status = self.api.get_status()
            player_count = status.get("player_count", 0)
            
            print(f"[PLAYERS] Current players: {player_count}/{self.minimum_players}")
            
            # Check if we reached minimum
            if player_count >= self.minimum_players:
                print(f"[PLAYERS] ✓ Minimum players reached!")
                break
            
            # Make joke when halfway there (only once)
            if not joke_made and player_count >= self.minimum_players / 2 and player_count > 0:
                print("[PLAYERS] Halfway there! Making joke about player names...")
                
                # Get player names
                player_names = self.api.get_players()
                
                if player_names:
                    # Generate LLM joke about the names
                    player_names_str = str(player_names)
                    joke = get_llm_response_groq(player_names_str, PROMPT_PLAYER_NAMES)
                    
                    print(f"[PLAYERS] NAO makes joke: {joke}")
                    self.say(joke)
                    
                    joke_made = True
            
            # Wait before checking again
            time.sleep(5)
        
        # All players joined
        print("[PLAYERS] All players joined!")
        self.say("Great! Everyone is here. Let's get started!")
        
        time.sleep(1)
        print("[PLAYERS] ✓ Wait for players phase complete\n")
    
    def phase_quiz_loop(self):
        """
        Phase 3: Main quiz loop - go through all questions.
        
        Per question:
        1. Read question aloud
        2. Reveal answer options (starts timer)
        3. Wait for all answers
        4. Show correct answer + distribution
        5. Make a joke (rotates: wrong_answer, cohost, audience)
        6. Show leaderboard
        """
        print("\n" + "="*60)
        print("PHASE: QUIZ LOOP")
        print("="*60)
        
        # Start the quiz on the server
        print("[QUIZ] Starting quiz...")
        self.api.start_quiz()
        
        self.say("Alright! Let's begin. Get ready... focus... okay maybe a little pressure.")
        time.sleep(1)
        
        # Get initial status to know total questions
        status = self.api.get_status()
        total_questions = status.get("total_questions", 5)
        
        print(f"[QUIZ] Total questions: {total_questions}")
        
        # Loop through each question
        question_num = 1
        quiz_finished = False
        
        while not quiz_finished:
            print(f"\n--- QUESTION {question_num}/{total_questions} ---")
            
            # Get current question from status
            status = self.api.get_status()
            current_question = status.get("current_question", {})
            
            # Check if quiz is finished
            if status.get("phase") == "finished":
                quiz_finished = True
                break
            
            # 1. Read the question aloud
            question_text = current_question.get("question", f"Question {question_num}")
            print(f"[QUIZ] Question: {question_text}")
            self.say(f"Question {question_num}. {question_text}")
            
            time.sleep(1)
            
            # 2. Reveal options (this starts the timer on the server)
            print("[QUIZ] Revealing options...")
            self.api.reveal_options()
            
            # Read options aloud
            options = current_question.get("options", [])
            if options:
                options_text = ". ".join([f"{chr(65+i)}, {opt}" for i, opt in enumerate(options)])
                self.say(options_text)
            
            self.say("Answer now!")
            
            # 3. Wait for answers (poll until time's up or all answered)
            print("[QUIZ] Waiting for answers...")
            self._wait_for_answers()
            
            # 4. Show correct answer
            print("[QUIZ] Showing answer...")
            result = self.api.show_answers()
            
            if result:
                correct = result.get("correct_answer", "A")
                self.say(f"Time's up! The correct answer is... {correct}!")
                time.sleep(1)
                
                # 5. Make a joke (rotating type)
                self._do_joke_for_question(result)
            
            time.sleep(1)
            
            # 6. Show leaderboard
            print("[QUIZ] Showing leaderboard...")
            leaderboard = self.api.show_leaderboard()
            
            if leaderboard and len(leaderboard) > 0:
                leader = leaderboard[0]
                self.say(f"In the lead: {leader['name']} with {leader['score']} points!")
            
            time.sleep(2)
            
            # Move to next question
            print("[QUIZ] Moving to next question...")
            next_result = self.api.next_question()
            
            if not next_result:
                # No more questions
                quiz_finished = True
            else:
                question_num += 1
        
        print("[QUIZ] ✓ Quiz loop complete\n")
    
    def _wait_for_answers(self, timeout: int = 30, poll_interval: int = 2):
        """
        Wait for all players to answer or timeout.
        
        Args:
            timeout: Max seconds to wait
            poll_interval: Seconds between checks
        """
        elapsed = 0
        
        while elapsed < timeout:
            results = self.api.get_results()
            
            if results:
                answered = results.get("answered_count", 0)
                total = results.get("total_players", 1)
                
                print(f"[QUIZ] Answers: {answered}/{total}")
                
                # All players answered
                if answered >= total:
                    print("[QUIZ] All players answered!")
                    return
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        print("[QUIZ] Timeout reached")
    
    def _do_joke_for_question(self, result: dict):
        """
        Make a joke based on rotating joke type.
        
        Args:
            result: The answer result from show_answers API
        """
        # Get next joke type in rotation
        joke_type = self.get_next_joke_type()
        
        print(f"[JOKE] Joke type for this round: {joke_type}")
        
        if joke_type == "wrong_answer":
            # Get names of players who got it wrong
            wrong_players = result.get("wrong_players", [])
            
            if wrong_players:
                # Pick one or a few names for the joke
                names_str = ", ".join(wrong_players[:3])
                joke = self.make_joke("wrong_answer", f"Players who got it wrong: {names_str}")
                self.say(joke)
            else:
                # Everyone got it right - make audience joke instead
                self.say("Wait, everyone got that right? I'm impressed... and suspicious.")
        
        elif joke_type == "cohost":
            # Cohost moment - alternates between asking and roasting
            self.do_cohost_moment()
        
        elif joke_type == "audience":
            # Joke about the whole group
            distribution = result.get("distribution", {})
            context = f"Answer distribution: {distribution}"
            joke = self.make_joke("audience", context)
            self.say(joke)
    
    def phase_finale(self):
        """
        Phase 4: Finale - announce winner and loser with jokes.
        
        Flow:
        1. Build tension
        2. Announce winner + joke
        3. Announce loser + joke
        4. Ask cohost for closing words
        5. NAO closes the show
        """
        print("\n" + "="*60)
        print("PHASE: FINALE")
        print("="*60)
        
        # Get final leaderboard
        leaderboard = self.api.show_leaderboard()
        
        if not leaderboard or len(leaderboard) == 0:
            self.say("Well, that was fun! Thanks for playing!")
            return
        
        # 1. Build tension
        print("[FINALE] Building tension...")
        self.say("Alright everyone... the moment you've been waiting for...")
        time.sleep(2)
        
        self.say("Let's see who proved they're NOT completely hopeless at trivia!")
        time.sleep(1)
        
        # 2. Announce winner
        winner = leaderboard[0]
        winner_name = winner.get("name", "Unknown")
        winner_score = winner.get("score", 0)
        
        print(f"[FINALE] Winner: {winner_name} with {winner_score} points")
        
        # Generate winner joke
        winner_context = f"Winner is {winner_name} with {winner_score} points"
        winner_joke = self.make_joke("winner", winner_context)
        
        self.say("And the winner is...")
        time.sleep(2)
        self.say_with_gesture(
            f"{winner_name}! With {winner_score} points!",
            animation="animations/Stand/Gestures/Enthusiastic_4"
        )
        time.sleep(1)
        self.say(winner_joke)
        
        time.sleep(2)
        
        # 3. Announce loser (if more than 1 player)
        if len(leaderboard) > 1:
            loser = leaderboard[-1]
            loser_name = loser.get("name", "Unknown")
            loser_score = loser.get("score", 0)
            
            print(f"[FINALE] Loser: {loser_name} with {loser_score} points")
            
            # Generate loser joke
            loser_context = f"Last place is {loser_name} with {loser_score} points"
            loser_joke = self.make_joke("loser", loser_context)
            
            self.say("And in last place...")
            time.sleep(1)
            self.say(f"{loser_name} with {loser_score} points.")
            time.sleep(1)
            self.say(loser_joke)
        
        time.sleep(2)
        
        # 4. Ask cohost for closing words
        print("[FINALE] Asking cohost for closing words...")
        self.say("Any final words for our players?")
        
        cohost_response = self.listen_to_cohost()
        
        if cohost_response:
            # React to cohost
            comeback = get_llm_response_groq(cohost_response, PROMPT_COHOST_REACT)
            self.say(comeback)
        else:
            self.say("Nothing? Okay, I'll do all the work as usual.")
        
        time.sleep(1)
        
        # 5. NAO closes the show
        print("[FINALE] Closing the show...")
        self.say_with_gesture(
            "Thank you all for playing! You've been a wonderful audience. Until next time!",
            animation="animations/Stand/Gestures/BowShort_1"
        )
        
        print("[FINALE] ✓ Finale complete\n")
    
    # =========================================================================
    # MAIN RUNNER
    # =========================================================================
    
    def run(self):
        """
        Main orchestrator: runs all quiz phases in sequence.
        
        Phases:
        1. Intro - NAO introduces himself and cohost
        2. Wait for players - Players join via QR code
        3. Quiz loop - Go through all questions with jokes
        4. Finale - Announce winner/loser with roasts
        """
        print("\n" + "="*60)
        print("🤖 NAO QUIZ MASTER - STARTING")
        print("="*60)
        
        try:
            # Wake up NAO and stand
            print("\n[SETUP] Waking up NAO...")
            self.nao.autonomous.request(NaoWakeUpRequest())
            self.nao.motion.request(NaoPostureRequest("Stand", 0.7))
            time.sleep(2)
            
            # Run all phases in sequence
            self.phase_intro()
            self.phase_wait_for_players()
            self.phase_quiz_loop()
            self.phase_finale()
            
            print("\n" + "="*60)
            print("✓ QUIZ COMPLETE")
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n\n[STOPPED] Quiz interrupted by user")
        
        except Exception as e:
            print(f"\n[ERROR] Something went wrong: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Put NAO to rest
            print("\n[CLEANUP] Putting NAO to rest...")
            try:
                self.nao.autonomous.request(NaoRestRequest())
            except:
                pass
            
            print("[CLEANUP] Done.\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Entry point for NAO quiz host script."""
    
    print("\n" + "="*60)
    print("NAO QUIZ HOST - CONFIGURATION")
    print("="*60)
    print(f"NAO IP:          {NAO_IP}")
    print(f"Server URL:      {SERVER_URL}")
    print(f"Google Key:      {GOOGLE_KEY}")
    print(f"Min Players:     {MINIMUM_PLAYERS}")
    print("="*60 + "\n")
    
    # Create quiz master and run
    quiz_master = NaoQuizMaster(
        nao_ip=NAO_IP,
        server_url=SERVER_URL,
        google_key_path=GOOGLE_KEY,
        minimum_players=MINIMUM_PLAYERS
    )
    
    quiz_master.run()


if __name__ == "__main__":
    main()
