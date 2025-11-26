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
from typing import Dict, Optional, List
import audioop
import speech_recognition as sr

from openai import OpenAI
from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiAnimationRequest,
)

llm_client = OpenAI()

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVER_URL = "http://localhost:5000"  # Kahoot server address
NAO_IP = "10.0.0.137"  # Your Nao's IP address
TEST_API_ONLY = False  # Set to False to use real Nao

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
    from sic_framework.devices.common_naoqi.naoqi_motion import (
        NaoPostureRequest,
        NaoqiAnimationRequest,
    )

else:
    # Dummy base class for test mode
    class SICApplication:
        def __init__(self):
            pass
        def shutdown(self):
            pass

    class Nao:
        def __init__(self, ip: str):
            pass

import math

try:
    from naoqi import ALProxy
except ImportError:
    ALProxy = None
    print("[NAO] WARNING: naoqi Python SDK not found. "
          "Low-level mic pose and turning will fall back to gestures.")



# ============================================================================
# KAHOOT API CLASS - Server Communication
# ============================================================================

class KahootAPI:
    """
    API wrapper for communicating with Kahoot server.
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        print(f"[API] Initialized with server: {server_url}")

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

    def set_quiz(self, questions: List[Dict]) -> bool:
        """
        Send a full quiz (list of questions) to the server.
        Each question dict:
           {
              "text": str,
              "options": [str, str, str, str],
              "correct_index": int,
              "difficulty": "easy"/"medium"/"hard"/"very hard"
           }
        """
        print("[API] Sending generated quiz to server...")
        try:
            payload = {"questions": questions}
            response = requests.post(f"{self.server_url}/api/set_quiz", json=payload)
            response.raise_for_status()
            data = response.json()
            print(f"[API] set_quiz: {data.get('message')}")
            return data.get('success', False)
        except requests.exceptions.RequestException as e:
            print(f"[API] ERROR: Could not set quiz: {e}")
            return False


# ============================================================================
# NAO QUIZ MASTER CLASS - Robot Control & Quiz Flow
# ============================================================================
class NaoQuizMaster(SICApplication):

    def __init__(self, nao_ip: str, server_url: str, test_mode: bool = False):
        super().__init__()

        print("[NAO] Initializing Nao Quiz Master...")

        self.nao_ip = nao_ip
        self.test_mode = test_mode

        # Initialize API client
        self.api = KahootAPI(server_url)
        self.question_history: List[Dict] = []
        self.correct_streak = 0
        self.best_streak = 0

        # LLM client (you can also pass this in)
        self.llm = llm_client

        self.nao = None
        self.led_proxy = None   # kept for set_led_color, but we don't use ALProxy
        # NEW: low-level NAOqi proxies (if available)
        self.motion_proxy = None
        self.posture_proxy = None

        if not self.test_mode:
            try:
                print(f"[NAO] Connecting to Nao at {nao_ip}...")
                self.nao = Nao(ip=nao_ip)
                print("[NAO] Connected to Nao successfully")

                # Try to connect NAOqi low-level motion if SDK is installed
                if ALProxy is not None:
                    try:
                        self.motion_proxy = ALProxy("ALMotion", nao_ip, 9559)
                        self.posture_proxy = ALProxy("ALRobotPosture", nao_ip, 9559)
                        print("[NAO] Connected to NAOqi ALMotion/ALRobotPosture")
                    except Exception as e:
                        print(f"[NAO] WARNING: Could not create ALMotion/ALRobotPosture proxies: {e}")
                else:
                    print("[NAO] NAOqi Python SDK not available; "
                        "using only SIC animations for motion.")

            except Exception as e:
                print(f"[NAO] ERROR: Could not connect to Nao: {e}")
                print("[NAO] Switching to test mode...")
                self.test_mode = True
        else:
            print("[NAO] Running in TEST MODE (no Nao connection)")

    # ----------------------------------------------------------------------
    # BASIC SPEECH + MIC GESTURE
    # ----------------------------------------------------------------------
    def say(self, text: str):
        """
        Basic speech: just say the text (no mic gesture).
        """
        print(f"[NAO SAYS] {text}")
        if not self.test_mode and self.nao:
            try:
                self.nao.tts.request(NaoqiTextToSpeechRequest(text))
            except Exception as e:
                print(f"[NAO] ERROR: Could not speak: {e}")

    # ----------------------------------------------------------------------
    # BASIC SPEECH + MIC POSE
    # ----------------------------------------------------------------------
    def say(self, text: str):
        """
        Basic speech: just say the text (no mic pose control).
        """
        print(f"[NAO SAYS] {text}")
        if not self.test_mode and self.nao:
            try:
                self.nao.tts.request(NaoqiTextToSpeechRequest(text))
            except Exception as e:
                print(f"[NAO] ERROR: Could not speak: {e}")

    def _mic_pose_gesture(self):
        """
        Fallback mic pose using a built-in gesture (up/down once).
        Used when NAOqi ALMotion is not available.
        """
        if self.test_mode or not self.nao:
            print("[NAO] TEST MODE: mic pose gesture")
            return

        try:
            self.nao.motion.request(
                NaoqiAnimationRequest("animations/Stand/Gestures/Explain_1")
            )
        except Exception as e:
            print(f"[NAO] ERROR in _mic_pose_gesture: {e}")

    def mic_pose_start(self):
        """
        Raise left arm into a 'holding mic' pose and HOLD it there
        using low-level ALMotion, if available.
        """
        if self.test_mode:
            print("[NAO] TEST MODE: mic_pose_start")
            return

        if self.motion_proxy is None:
            # no NAOqi SDK -> fallback to simple gesture
            self._mic_pose_gesture()
            return

        try:
            # Make sure the left arm is stiff enough to hold the pose
            self.motion_proxy.setStiffnesses("LArm", 1.0)

            # Joint list and target angles (in radians) for a mic-at-mouth pose
            names = [
                "LShoulderPitch",
                "LShoulderRoll",
                "LElbowYaw",
                "LElbowRoll",
                "LWristYaw",
            ]
            angles = [
                1.0,    # Shoulder forward
                0.25,   # Slight outward/inward
                -1.2,   # Elbow yaw
                -0.5,   # Elbow roll (bring hand towards face)
                0.0,    # Wrist neutral
            ]
            speed = 0.2

            self.motion_proxy.angleInterpolation(
                names,
                angles,
                [speed] * len(names),
                True  # blocking
            )
        except Exception as e:
            print(f"[NAO] ERROR in mic_pose_start: {e}")

    def mic_pose_end(self):
        """
        Return left arm to a more neutral pose.
        """
        if self.test_mode or self.motion_proxy is None:
            return

        try:
            names = [
                "LShoulderPitch",
                "LShoulderRoll",
                "LElbowYaw",
                "LElbowRoll",
                "LWristYaw",
            ]
            # Approximate default stand-ish pose for left arm
            angles = [
                1.4,   # down-ish
                0.15,
                -1.2,
                -0.5,
                0.0,
            ]
            speed = 0.2

            self.motion_proxy.angleInterpolation(
                names,
                angles,
                [speed] * len(names),
                True
            )
        except Exception as e:
            print(f"[NAO] ERROR in mic_pose_end: {e}")

    def say_with_mic(self, text: str):
        """
        Do mic pose, speak, then lower arm again.
        With NAOqi: arm stays up while speaking.
        Without NAOqi: falls back to a simple gesture.
        """
        if self.motion_proxy is None:
            # Fallback: short gesture then speak
            self._mic_pose_gesture()
            time.sleep(0.3)
            self.say(text)
            return

        # NAOqi path: hold pose while speaking
        self.mic_pose_start()

        # Approximate how long to hold arm based on text length
        approx_duration = max(1.5, len(text) / 12.0)  # ~12 chars/sec

        self.say(text)
        time.sleep(approx_duration)

        self.mic_pose_end()

    # ----------------------------------------------------------------------
    # LED HELPERS (SAFE NO-OP IF NO LED PROXY)
    # ----------------------------------------------------------------------
    def set_led_color(self, r: int, g: int, b: int, duration: float = 0.5):
        """
        Set face LEDs to a given RGB color over 'duration' seconds.
        Currently a no-op unless you wire in an LED proxy yourself.
        """
        if self.test_mode or not self.led_proxy:
            return
        try:
            color = (r << 16) + (g << 8) + b
            self.led_proxy.fadeRGB("FaceLeds", color, duration)
        except Exception as e:
            print(f"[NAO] ERROR setting LED color: {e}")

    def show_quiz_generating_start(self):
        """
        Visual + verbal feedback while generating quiz.
        """
        self.say_with_mic("I'm generating your quiz, please wait!")
        self.set_led_color(0, 0, 255, 0.5)

    def show_quiz_generating_end(self, success: bool, topic: str):
        """
        Visual + verbal feedback after generating quiz.
        """
        if success:
            self.set_led_color(0, 255, 0, 0.5)
            self.say_with_mic(f"We have a {topic} quiz, let's go!")
        else:
            self.set_led_color(255, 0, 0, 0.5)
            self.say_with_mic("I couldn't generate your quiz properly. I'll use the default questions.")

    # ----------------------------------------------------------------------
    # MOTION HELPERS
    # ----------------------------------------------------------------------
    def clap_hands(self):
        """
        Makes Nao do an applause-like gesture using a built-in animation.
        Uses SIC motion requests instead of raw NAOqi calls.
        """
        if self.test_mode or not self.nao:
            print("[NAO] TEST MODE: Pretending to clap hands")
            return

        try:
            try:
                self.nao.motion.request(
                    NaoqiAnimationRequest("animations/Stand/Gestures/Applause_1")
                )
            except Exception:
                print("[NAO] Applause_1 not available, falling back to Hey_1")
                self.nao.motion.request(
                    NaoqiAnimationRequest("animations/Stand/Gestures/Hey_1")
                )
        except Exception as e:
            print(f"[NAO] ERROR during clap motion: {e}")

    def turn_left_right(self):
        """
        Small in-place turns left and right.
        """
        recording = NaoqiMotionRecording.load("../../demos/nao/wave_motion")

        try:
            angle = math.radians(angle_degrees)

            # Turn slightly left
            self.motion_proxy.moveTo(0.0, 0.0, angle)
            time.sleep(0.2)

            # Turn slightly right back to original orientation
            self.motion_proxy.moveTo(0.0, 0.0, -angle)
            time.sleep(0.2)

        except Exception as e:
            print(f"[NAO] ERROR in turn_left_right: {e}")


    # ----------------------------------------------------------------------
    # QUIZ GENERATION (LLM)
    # ----------------------------------------------------------------------
    def generate_quiz_with_llm(self, topic: str):
        # ... keep your existing implementation here unchanged ...
        # (I’m not repeating it to save space – your last version was fine)
        prompt = f"""
        Create a quiz of exactly 6 multiple-choice questions about: "{topic}".
        Requirements:
        - Questions go from easy to hard.
        - Each question has exactly 4 answer options.
        - Mark the correct option by index (0-3).
        - Include a difficulty label per question: "easy", "medium", "hard", or "very hard".
        Return ONLY valid JSON, in this format:

        [
          {{
            "text": "Question text...",
            "options": ["option A", "option B", "option C", "option D"],
            "correct_index": 0,
            "difficulty": "easy"
          }},
          ...
        ]
        """
        try:
            print("[LLM] Requesting quiz generation...")
            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = response.choices[0].message.content

            import json
            content_str = content.strip()
            if content_str.startswith("```"):
                content_str = content_str.strip("`")
                content_str = content_str.replace("json", "", 1).strip()

            questions = json.loads(content_str)
            print("[LLM] Generated questions:")
            for q in questions:
                print("  -", q.get("text"))
            return questions
        except Exception as e:
            print(f"[LLM] ERROR generating quiz: {e}")
            return None

    # ----------------------------------------------------------------------
    # QUIZ FLOW METHODS
    # ----------------------------------------------------------------------
    def greet_players(self):
        print("\n[NAO] === GREETING PLAYERS ===")
        self.say_with_mic("Hello everyone! Welcome to the quiz!")
        time.sleep(1)

        status = self.api.get_status()
        player_count = status.get('player_count', 0)

        if player_count == 0:
            self.say_with_mic("Hmm, no players have joined yet. Please join using your phone or computer!")
        elif player_count == 1:
            self.say_with_mic("Great! We have one player. Let's get started!")
        else:
            self.say_with_mic(f"Awesome! We have {player_count} players. Let's begin!")
        time.sleep(1)

    def volume_check(self, threshold=3500, listen_seconds=3):
        """
        Ask the audience to make noise and measure loudness
        using the LAPTOP microphone (SpeechRecognition).
        """
        if self.test_mode:
            print("[NAO] TEST MODE: Skipping volume check")
            return True

        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        self.say_with_mic("Are we all ready? Make some noise!")
        time.sleep(0.5)
        self.say("I'll listen for a moment!")

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, phrase_time_limit=listen_seconds)

        raw = audio.get_raw_data()
        rms = audioop.rms(raw, 2)
        print(f"[NAO] Loudness detected: {rms}")

        if rms < threshold:
            self.say("I can't hear you! Let's try again. Be louder!")
            return False

        self.say("Great! You're loud and ready!")
        time.sleep(0.5)
        self.clap_hands()
        time.sleep(0.5)
        self.say("Let's start!")
        return True

    def announce_question(self, question_data: Dict):
        print("\n[NAO] === ANNOUNCING QUESTION ===")

        question_text = question_data.get('text', '')
        self.say_with_mic(f"Here is the question: {question_text}")
        time.sleep(2)

        options = question_data.get('options', [])
        self.say("The options are:")
        time.sleep(1)

        for idx, option in enumerate(options):
            self.turn_left_right()
            self.say(f"Option {idx + 1}: {option}")
            time.sleep(1)

    def wait_for_answers(self, wait_time: int = WAIT_FOR_ANSWERS_TIME):
        print(f"\n[NAO] === WAITING FOR ANSWERS ({wait_time}s) ===")
        self.say(f"You have {wait_time} seconds to answer!")

        intervals = [wait_time // 2, 5, 0]
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
                time.sleep(5)
                self.say("Time's up!")

    def comment_on_past_performance(self, current_q: int, total_q: int):
        if not self.question_history:
            return

        last = self.question_history[-1]
        correct = last["correct_count"]
        total = last["total_answered"]
        difficulty = last["difficulty"]

        if total > 0:
            ratio = float(correct) / float(total)
        else:
            ratio = 0.0

        if difficulty == "very hard":
            self.say("That last question was really difficult. Nobody got it right!")
        elif difficulty == "hard":
            self.say("The previous question was pretty tough. Only a few of you got it!")
        elif difficulty == "easy":
            self.say("Nice job! The last question was easy for most of you!")
        else:
            self.say("You did okay on the last question. Let's see how you do now!")

        if self.best_streak >= 3 and self.correct_streak >= 2:
            self.say("You're on a streak! Keep it up!")

    def announce_results(self, results_data: Dict):
        print("\n[NAO] === ANNOUNCING RESULTS ===")

        correct_answer = results_data.get('correct_answer', 0)
        distribution = results_data.get('answer_distribution', {})
        player_answers = results_data.get('player_answers', [])

        self.say_with_mic(f"The correct answer was option {correct_answer + 1}!")
        time.sleep(2)

        correct_count = sum(1 for p in player_answers if p.get('is_correct', False))
        total_answered = len(player_answers)

        if correct_count == 0:
            self.say("Oh no! Nobody got it right. Better luck next time!")
        elif correct_count == total_answered:
            self.say("Excellent! Everyone got it right! Amazing!")
        else:
            self.say(f"{correct_count} out of {total_answered} players got it right!")
        time.sleep(2)

        print(f"[NAO] Answer distribution: {distribution}")

        if total_answered > 0:
            ratio = float(correct_count) / float(total_answered)
        else:
            ratio = 0.0

        if correct_count == 0:
            difficulty = "very hard"
        elif ratio < 0.4:
            difficulty = "hard"
        elif ratio > 0.8:
            difficulty = "easy"
        else:
            difficulty = "medium"

        self.question_history.append({
            "correct_count": correct_count,
            "total_answered": total_answered,
            "difficulty": difficulty,
        })

        if total_answered > 0 and correct_count == total_answered:
            self.correct_streak += 1
            if self.correct_streak > self.best_streak:
                self.best_streak = self.correct_streak
        else:
            self.correct_streak = 0

    # ----------------------------------------------------------------------
    # MAIN QUIZ LOOP
    # ----------------------------------------------------------------------
    def run_quiz(self):
        print("\n" + "="*60)
        print("🤖 NAO QUIZ MASTER STARTING")
        print("="*60)

        # 0. Human chooses topic
        self.say_with_mic("Before we start, what topic should the quiz be about?")
        print("\n[HUMAN INPUT] Enter a topic for the quiz:")
        topic = input("> ").strip()
        if not topic:
            topic = "general knowledge"

        self.say(f"Okay, I will create a quiz about {topic}.")

        # 1. Generate quiz via LLM
        self.show_quiz_generating_start()
        questions = self.generate_quiz_with_llm(topic)

        if questions and isinstance(questions, list) and len(questions) == 6:
            success = self.api.set_quiz(questions)
        else:
            success = False

        self.show_quiz_generating_end(success, topic)

        # 2. Greet players
        self.greet_players()
        time.sleep(2)
        if not self.test_mode and self.nao:
            self.say("Let me stand up first!")
            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            time.sleep(2)

        # 3. Volume check (Are we all ready?)
        ready = False
        while not ready:
            ready = self.volume_check()
            time.sleep(1)

        # 4. Start quiz
        print("\n[NAO] === STARTING QUIZ ===")
        if not self.api.start_quiz():
            print("[NAO] ERROR: Could not start quiz!")
            return

        self.say_with_mic("Let's start the quiz!")
        time.sleep(2)

        # 5. Question loop
        while True:
            status = self.api.get_status()

            if not status.get('is_active', False):
                print("[NAO] Quiz is no longer active")
                break

            question_data = status.get('current_question_data')
            if not question_data:
                print("[NAO] No question data available")
                break

            current_q = status.get('current_question', 0)
            total_q = status.get('total_questions', 0)

            print(f"\n[NAO] === QUESTION {current_q + 1} / {total_q} ===")
            self.say(f"Question {current_q + 1} of {total_q}")
            time.sleep(1)

            self.comment_on_past_performance(current_q, total_q)
            self.announce_question(question_data)

            self.wait_for_answers()

            results = self.api.get_results()
            if not results:
                print("[NAO] ERROR: Could not get results")
                break

            self.announce_results(results)

            if current_q + 1 >= total_q:
                print("[NAO] That was the last question!")
                break

            self.say("Let's move to the next question!")
            time.sleep(PAUSE_BETWEEN_QUESTIONS)

            if not self.api.next_question():
                print("[NAO] ERROR: Could not move to next question")
                break

        # 6. End quiz
        print("\n[NAO] === ENDING QUIZ ===")
        self.say_with_mic("That's all for today! Thank you for playing!")
        time.sleep(1)
        self.say("I hope you had fun! See you next time!")

        print("\n" + "="*60)
        print("🤖 NAO QUIZ MASTER FINISHED")
        print("="*60)

        self.shutdown()



# ============================================================================
# MAIN - Entry Point
# ============================================================================

def main():
    print("\n" + "="*60)
    print("🎮 NAO KAHOOT QUIZ APPLICATION")
    print("="*60)
    print(f"Server URL: {SERVER_URL}")
    print(f"Nao IP: {NAO_IP}")
    print(f"Test Mode: {TEST_API_ONLY}")
    print("="*60 + "\n")

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
