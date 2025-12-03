"""
NAO Quiz Host - Main Script
============================
Clean, modular structure for NAO quiz show host.
Phase 1a: Intro with cohost + waiting for players

Author: Quiz Team
Date: 2025
"""

import time
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
                    from llm_integration_groq import system_prompt_pre_quiz_groq
                    
                    player_names_str = str(player_names)
                    joke = get_llm_response_groq(player_names_str, system_prompt_pre_quiz_groq)
                    
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
    
    def phase_start_quiz(self):
        """
        Phase 3: Start the quiz.
        
        TODO: Implement quiz flow here
        TODO: - Read questions
        TODO: - Show options
        TODO: - Reveal answers
        TODO: - Show leaderboard
        TODO: - Announce winner
        """
        print("\n" + "="*60)
        print("PHASE: START QUIZ")
        print("="*60)
        
        print("[QUIZ] Starting quiz...")
        self.api.start_quiz()
        
        self.say("Alright! Let's begin. Get ready... focus... okay maybe a little pressure.")
        
        # TODO: Implement full quiz flow here
        print("[QUIZ] TODO: Implement quiz questions flow")
        print("[QUIZ] ✓ Quiz phase placeholder complete\n")
    
    # =========================================================================
    # MAIN RUNNER
    # =========================================================================
    
    def run(self):
        """
        Main orchestrator: runs all quiz phases in sequence.
        
        Phases:
        1. Intro with cohost
        2. Wait for players
        3. Run quiz (placeholder)
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
            
            # Run phases
            self.phase_intro()
            self.phase_wait_for_players()
            #self.phase_start_quiz()
            
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
