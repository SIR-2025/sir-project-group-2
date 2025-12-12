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
from llm_integration_groq import stream_llm_response_to_nao
from mic import NaoShowController
from prompts import (
    PROMPT_PLAYER_NAMES,
    PROMPT_WRONG_ANSWER,
    PROMPT_COHOST_ROAST,
    PROMPT_AUDIENCE,
    PROMPT_COHOST_REACT,
    PROMPT_WINNER,
    PROMPT_LOSER,
    COHOST_QUESTIONS,
    PROMPT_COHOST_DIRECT,
    PROMPT_COHOST_SILENT,
    PROMPT_WRONG_ANSWER_TRANSITION,
)

# Load environment variables (for GROQ_API_KEY)
load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

NAO_IP = "10.0.0.239"
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
        
        # Initialize show controller for mic pose and gestures
        print(f"[INIT] Setting up show controller...")
        self.show = NaoShowController(
            nao=self.nao,
            nao_ip=nao_ip,
            auto_start_airborne_monitor=True
        )
        print(f"[INIT] ✓ Show controller ready")
        
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
    
    def say_with_mic(self, text: str, point_to_screen: bool = False, speed: int = 90, pitch: int = 110):
        """
        Make NAO speak while holding mic pose.
        NOTE: Mic is held UP for the entire show (no up/down per call).
        Optionally point to screen with free hand.
        
        Args:
            text: Text to speak
            point_to_screen: If True, point to screen with right hand
            speed: Speech speed (default 90)
            pitch: Voice pitch (default 110)
        """
        # Point to screen with RIGHT arm (left arm stays in mic pose)
        if point_to_screen:
            self.show._point_to_screen(duration=0.4)
            self.show._look_screen()
        
        # Speak (blocking)
        self.say(text, speed=speed, pitch=pitch, block=True)
        
        # Return right arm to neutral if we pointed
        if point_to_screen:
            self.show._arm_neutral(duration=0.3)
    
    def start_mic_pose(self):
        """
        Start mic pose for the entire show.
        Call this once at the beginning.
        - Puts left arm in mic position
        - Disables left arm swing during walking
        """
        print("[MIC] Starting mic pose for show...")
        self.show._mic_up()
        self.show._set_walk_arm_swing(False, True)  # Left arm fixed, right arm free
        print("[MIC] ✓ Mic pose active")
    
    def end_mic_pose(self):
        """
        End mic pose at the end of the show.
        - Returns left arm to neutral
        - Re-enables arm swing
        """
        print("[MIC] Ending mic pose...")
        self.show._mic_down()
        self.show._set_walk_arm_swing(True, True)  # Both arms free
        print("[MIC] ✓ Mic pose ended")
    
    def say_with_pacing(self, text: str, point_to_screen: bool = False, speed: int = 90, pitch: int = 110):
        """
        Make NAO speak while doing small pacing movement.
        Good for longer speeches to add dynamism.
        Stays in same area (small side steps, returns to start).
        
        Args:
            text: Text to speak
            point_to_screen: If True, point to screen first
            speed: Speech speed (default 90)
            pitch: Voice pitch (default 110)
        """
        import threading
        
        # Point to screen first if needed
        if point_to_screen:
            self.show._point_to_screen(duration=0.4)
            self.show._look_screen()
        
        # Start speech (non-blocking) so we can pace while talking
        self.say(text, speed=speed, pitch=pitch, block=False)
        
        # Do small pacing in parallel with speech
        self.show.pace_small_circle(steps=2, step_size=0.12)
        
        # Return arm to neutral if we pointed
        if point_to_screen:
            self.show._arm_neutral(duration=0.3)
    
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
        joke = stream_llm_response_to_nao(self,context, prompt)
        print(f"[JOKE] Generated: {joke}")
        
        return joke
    
    def ask_cohost(self, question: str = None) -> str:
        """
        Ask cohost a question and generate LLM response to their answer.
        Uses mic pose and looks at cohost.
        
        Args:
            question: Optional specific question. If None, picks random.
        
        Returns:
            str: LLM-generated comeback to cohost's response
        """
        # Pick a random question if none provided
        if question is None:
            question = random.choice(COHOST_QUESTIONS)
        
        # Look at cohost and ask with mic pose
        self.show.start_face_tracking()
        print(f"[COHOST] NAO asks: {question}")
        self.say_with_mic(question)
        
        # Listen to cohost response
        cohost_response = self.listen_to_cohost()
        
        if not cohost_response:
            # No response - generate silence joke
            silence_joke = stream_llm_response_to_nao(self,
                "The co-host didn't respond",
                PROMPT_COHOST_SILENT
            )
            return silence_joke
        
        # Generate comeback using LLM
        comeback = stream_llm_response_to_nao(self,cohost_response, PROMPT_COHOST_REACT)
        
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
        else:
            # Just roast the cohost directly (no input needed)
            print("[COHOST] Roasting cohost directly...")
            self.roast_cohost_direct()
    
    def roast_cohost_direct(self):
        """
        Make a direct joke about the cohost, addressing them as "co-host".
        Uses mic pose and looks at cohost direction.
        """
        print("[COHOST] Direct roast at co-host...")
        
        # Look at cohost direction
        self.show.start_face_tracking()
        
        # Generate direct roast using LLM
        joke = stream_llm_response_to_nao(self,
            "Make a direct jab at the co-host",
            PROMPT_COHOST_DIRECT
        )
        
        # Deliver with mic pose
        print(f"[COHOST] Said: {joke}")
    
    def joke_about_silent_cohost(self):
        """
        Make a joke when cohost doesn't respond.
        """
        print("[COHOST] Cohost is silent, making joke...")
        
        # Generate silence joke
        joke = stream_llm_response_to_nao(self,
            "The co-host didn't respond",
            PROMPT_COHOST_SILENT
        )
        
        print(f"[COHOST] Silent joke: {joke}")
    
    # =========================================================================
    # GAME PHASES
    # =========================================================================
    
    def phase_intro(self):
        """
        Phase 1: Opening with cohost interaction.
        
        Flow:
        1. NAO introduces himself with mic pose
        2. NAO introduces cohost as "assistant" with direct jab
        3. Listen to cohost response
        4. NAO makes LLM-generated sarcastic comeback (or silence joke)
        5. Extra cohost roast for fun
        """
        print("\n" + "="*60)
        print("PHASE: INTRO")
        print("="*60)
        self.show.face_audience()
        # 1. NAO introduces himself with wave gesture
        print("[INTRO] NAO introduces himself...")
        self.say_with_gesture(
            "Hello everyone! I'm Nao, your quiz host today!",
            animation="animations/Stand/Gestures/Hey_1"
        )
        
        
        # Start mic pose AFTER the gesture (gestures cancel arm positions)
        self.start_mic_pose()

        
        # 2. NAO introduces cohost with a jab
        print("[INTRO] NAO introduces cohost...")
        self.show.start_face_tracking()
        self.say_with_mic(
            "And this is my assistant. They're here for... moral support, I guess."
        )
        

        self.end_mic_pose()
        time.sleep(0.5)

        # 3. Listen to cohost response
        cohost_response = self.listen_to_cohost()
        self.show.stop_all_tracking
        if not cohost_response:
            self.show._look_audience_left()
            # Cohost didn't respond - make a joke about it
            print("[INTRO] No cohost response, making silence joke...")
            self.joke_about_silent_cohost()
        else:
            self.show._look_audience_left()
            # 4. Generate sarcastic comeback using LLM
            print("[INTRO] Generating LLM response...")
            comeback = stream_llm_response_to_nao(self, cohost_response, PROMPT_COHOST_REACT)
            
            # NAO delivers comeback with mic pose
            print(f"[INTRO] NAO says comeback: {comeback}")

        
        
        
        time.sleep(1)
        
        # 5. Extra direct roast at cohost for fun
        print("[INTRO] Extra cohost roast...")
        self.show._look_audience_right()
        self.show.start_face_tracking()
        self.roast_cohost_direct()
        self.show.stop_all_tracking()
        self.show._look_audience_left()
        time.sleep(1)
        print("[INTRO] ✓ Intro phase complete\n")
    
    def phase_wait_for_players(self):
        """
        Phase 2: Wait for players to join and make jokes.
        
        Flow:
        1. NAO tells people to join via QR code (points to screen)
        2. Loop: check player count every 5 seconds
        3. Make jokes about player names as they join
        4. Interact with cohost if waiting too long
        5. When minimum reached: continue to quiz
        """
        print("\n" + "="*60)
        print("PHASE: WAITING FOR PLAYERS")
        print("="*60)
        
        # Reset quiz to start fresh
        print("[PLAYERS] Resetting quiz...")
        self.api.reset_quiz()
        
        # 1. Instructions to join (point to screen)
        print("[PLAYERS] NAO gives instructions...")
        self.say_with_mic(
            "Get your phones ready and join the game by scanning the QR code on the screen!",
            point_to_screen=True
        )
        
        time.sleep(1)
        self.say_with_mic("Type in your name. Don't worry, I don't judge your username choices... much.")
        self.show._say_with_mic_walk_turn_and_gaze_internal("I want to play it myself I am going to sit in the audience!")
        self.end_mic_pose()
        time.sleep(3)
        # 2. Wait for players to join
        print(f"[PLAYERS] Waiting for {self.minimum_players} players...")
        
        jokes_made = 0  # Track how many jokes we made
        wait_cycles = 0  # Track how long we've been waiting
        last_player_count = 0
        
        while True:
            # Get current player status
            status = self.api.get_status()
            player_count = status.get("player_count", 0)
            
            print(f"[PLAYERS] Current players: {player_count}/{self.minimum_players}")
            
            # Check if we reached minimum
            if player_count >= self.minimum_players:
                print(f"[PLAYERS] ✓ Minimum players reached!")
                break
            
            # New player joined - make a joke about their name
            if player_count > last_player_count and player_count > 0:
                print("[PLAYERS] New player joined! Making joke...")
                player_names = self.api.get_players()
                
                if player_names:
                    # Get the newest player (last in list)
                    newest_name = player_names[-1] if player_names else "someone"
                    joke = stream_llm_response_to_nao(self,
                        f"New player just joined with name: {newest_name}",
                        PROMPT_PLAYER_NAMES
                    )
                    jokes_made += 1
                
                last_player_count = player_count
            
            # If waiting too long (every 3 cycles = 15 sec), interact with cohost
            wait_cycles += 1
            if wait_cycles % 3 == 0 and wait_cycles > 0:
                print("[PLAYERS] Waiting long, talking to cohost...")
                self.show.start_face_tracking()
                # Simple yes/no question - easier for cohost to answer
                self.say_with_mic("Hey co-host, they're taking a while right?")
                
                # Listen for cohost response
                response = self.listen_to_cohost()
                if response:
                    comeback = stream_llm_response_to_nao(self, response, PROMPT_COHOST_REACT)
                else:
                    self.joke_about_silent_cohost()
            
            # Wait before checking again
            time.sleep(5)
        
        # All players joined - celebrate
        print("[PLAYERS] All players joined!")
        self.say_with_mic("Great! Everyone is here. Let's get started!")
        
        # Quick cohost jab before starting - no response needed
        self.show.start_face_tracking()
        self.say_with_mic("Let's go co-host! Try to keep up this time.")
        
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
        
        self.say_with_mic("Alright! Let's begin. Get ready... focus... okay maybe a little pressure.")
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
            # Note: "current_question" is the index (int), "current_question_data" is the dict
            status = self.api.get_status()
            current_question = status.get("current_question_data", {})
            
            # Check if quiz is finished
            if status.get("phase") == "finished":
                quiz_finished = True
                break
            
            # 1. Read the question aloud with mic pose
            # NOTE: Server returns "text" field, not "question"
            question_text = current_question.get("text", f"Question {question_num}")
            print(f"[QUIZ] Question: {question_text}")
            
            # Point to screen while reading question
            self.say_with_mic(f"Question {question_num}. {question_text}", point_to_screen=True)
            
            time.sleep(1)
            
            # 2. Reveal options (this starts the timer on the server)
            print("[QUIZ] Revealing options...")
            self.api.reveal_options()
            
            # Read options aloud with mic pose
            options = current_question.get("options", [])
            if options:
                options_text = ". ".join([f"{chr(65+i)}, {opt}" for i, opt in enumerate(options)])
                self.say_with_mic(options_text, point_to_screen=True)
            
            
            # 3. Wait for answers (poll until time's up or all answered)
            print("[QUIZ] Waiting for answers...")
            self._wait_for_answers()
            
            # 4. Show correct answer
            print("[QUIZ] Showing answer...")
            result = self.api.show_answers()
            
            if result:
                # Use letter + text for readable answer (e.g., "A, Amsterdam")
                letter = result.get("correct_answer_letter", "A")
                text = result.get("correct_answer_text", "")
                self.say_with_mic(f"Time's up! The correct answer is... {letter}, {text}!", point_to_screen=True)
                time.sleep(1)
                
                # 5. Make a joke (rotating type)
                self._do_joke_for_question(result)
            
            time.sleep(1)
            
            # 6. Show leaderboard
            print("[QUIZ] Showing leaderboard...")
            leaderboard = self.api.show_leaderboard()
            
            if leaderboard and len(leaderboard) > 0:
                leader = leaderboard[0]
                self.say_with_mic(f"In the lead: {leader['name']} with {leader['score']} points!", point_to_screen=True)
            
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
        Wait for all players to answer or timeout (max 30 sec).
        After timeout, moves on even if not everyone answered.
        
        Args:
            timeout: Max seconds to wait (default 30)
            poll_interval: Seconds between checks (default 2)
        """
        print(f"[QUIZ] Waiting for answers (max {timeout}s)...")
        elapsed = 0
        
        while elapsed < timeout:
            results = self.api.get_results()
            
            if results:
                answered = results.get("answered_count", 0)
                total = results.get("total_players", 1)
                remaining = timeout - elapsed
                
                print(f"[QUIZ] Answers: {answered}/{total} ({remaining}s left)")
                
                # All players answered - done early
                if answered >= total:
                    print("[QUIZ] ✓ All players answered!")
                    return
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        # Timeout reached - move on anyway
        print(f"[QUIZ] ⏱ Timeout ({timeout}s) - moving on")
    
    def _do_joke_for_question(self, result: dict):
        """
        Make jokes during answer reveal transition.
        
        Flow:
        1. ALWAYS make a joke about wrong answer players (if any)
        2. Then do rotating cohost/audience interaction
        
        Args:
            result: The answer result from show_answers API
        """
        # 1. ALWAYS joke about wrong answer players first
        wrong_players = result.get("wrong_players", [])
        
        if wrong_players:
            print("[JOKE] Making joke about wrong answer players...")
            names_str = ", ".join(wrong_players[:3])
            
            # Use the transition-specific prompt for wrong answers
            joke = stream_llm_response_to_nao(self,
                f"Players who got it wrong: {names_str}",
                PROMPT_WRONG_ANSWER_TRANSITION
            )
            time.sleep(1)
        else:
            # Everyone got it right - be impressed
            self.say_with_mic("Wait, everyone got that right? I'm impressed... and suspicious.")
            time.sleep(1)
        
        # 2. Rotating interaction: cohost or audience
        # Simplified rotation: alternates cohost and audience (no wrong_answer since we do that above)
        self.joke_index += 1
        
        if self.joke_index % 2 == 0:
            # Cohost moment - direct roast or ask
            print("[JOKE] Cohost interaction...")
            self.do_cohost_moment()
        else:
            # Audience/group joke
            print("[JOKE] Audience joke...")
            distribution = result.get("distribution", {})
            context = f"Answer distribution: {distribution}"
            joke = self.make_joke("audience", context)
    
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
            self.say_with_mic("Well, that was fun! Thanks for playing!")
            return
        
        # 1. Build tension
        print("[FINALE] Building tension...")
        self.say_with_mic("Alright everyone... the moment you've been waiting for...")
        time.sleep(2)
        
        self.say_with_mic("Let's see who proved they're NOT completely hopeless at trivia!")
        time.sleep(1)
        
        # 2. Announce winner
        winner = leaderboard[0]
        winner_name = winner.get("name", "Unknown")
        winner_score = winner.get("score", 0)
        
        print(f"[FINALE] Winner: {winner_name} with {winner_score} points")
        
        # Generate winner joke
        winner_context = f"Winner is {winner_name} with {winner_score} points"
        winner_joke = self.make_joke("winner", winner_context)
        
        self.say_with_mic("And the winner is...")
        time.sleep(2)
        self.say_with_gesture(
            f"{winner_name}! With {winner_score} points!",
            animation="animations/Stand/Gestures/Enthusiastic_4"
        )
        time.sleep(1)
        self.say_with_mic(winner_joke)
        
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
            
            self.say_with_mic("And in last place...")
            time.sleep(1)
            self.say_with_mic(f"{loser_name} with {loser_score} points.")
            time.sleep(1)
            self.say_with_mic(loser_joke)
        
        time.sleep(2)
        
        # 4. Ask cohost for closing words
        print("[FINALE] Asking cohost for closing words...")
        self.show.start_face_tracking()
        # Simple question - easier for cohost to respond to
        self.say_with_mic("Hey co-host, that was fun right?")
        
        cohost_response = self.listen_to_cohost()
        
        if cohost_response:
            # React to cohost
            comeback = stream_llm_response_to_nao(self, cohost_response, PROMPT_COHOST_REACT)
        else:
            # Cohost didn't respond - make a joke about it
            self.joke_about_silent_cohost()
        
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
            
            # NOTE: Mic pose starts INSIDE phase_intro() after the Hey gesture
            # (gestures cancel arm positions, so we do mic pose after)
            
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
            # End mic pose before rest
            print("\n[CLEANUP] Ending mic pose...")
            try:
                self.end_mic_pose()
            except:
                pass
            
            # Put NAO to rest
            print("[CLEANUP] Putting NAO to rest...")
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
