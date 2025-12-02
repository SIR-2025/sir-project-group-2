"""
NAO + GPT Quiz Host Demo
Includes:
- Volume Check ("Are we all ready?")
- GPT conversation support
- Microphone loudness measurement
"""

import time
from naoqi import ALProxy
from openai import OpenAI


class SimpleNaoGPT:
    def __init__(self, robot_ip="127.0.0.1", model="gpt-4o-mini"):
        # --- Robot speech setup ---
        self.tts = ALProxy("ALTextToSpeech", robot_ip, 9559)
        self.tts.setVolume(0.9)

        # --- Microphone setup ---
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # --- GPT Client ---
        self.client = OpenAI()
        self.model = model

        # Volume threshold (tweak this for your room)
        self.VOLUME_THRESHOLD = 3500   # Lower number = easier to pass
        self.READY_TIMEOUT = 4         # Seconds to listen

    # -----------------------------------------------------------------
    # LISTEN AND GET RAW AUDIO + LOUDNESS
    # -----------------------------------------------------------------
    def listen_for_volume(self, timeout=None):
        with self.microphone as source:
            print("Listening for loudness...")
            audio = self.recognizer.listen(source, timeout=timeout)

        # Convert audio to raw data
        raw = audio.get_wav_data()

        # Measure RMS loudness
        rms = audioop.rms(raw, 2)  # 16-bit depth → width=2
        print("Loudness RMS =", rms)
        return rms

    # -----------------------------------------------------------------
    # FULL SPEECH-TO-TEXT (GPT Whisper)
    # -----------------------------------------------------------------
    def listen_and_transcribe(self):
        with self.microphone as source:
            print("Listening for speech...")
            audio = self.recognizer.listen(source)

        audio_bytes = audio.get_wav_data()

        try:
            response = self.client.audio.transcriptions.create(
                model="gpt-4o-mini-tts",
                file=("speech.wav", audio_bytes)
            )
            text = response["text"]
            return text
        except Exception as e:
            print("Transcription error:", e)
            return ""

    # -----------------------------------------------------------------
    # SEND MESSAGE TO GPT
    # -----------------------------------------------------------------
    def ask_gpt(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.choices[0].message["content"]
            return answer
        except Exception as e:
            print("GPT error:", e)
            return "Sorry, I had trouble thinking just now."

    # -----------------------------------------------------------------
    # ROBOT SPEECH
    # -----------------------------------------------------------------
    def robot_speak(self, text):
        print("Robot:", text)
        self.tts.say(text)

    # -----------------------------------------------------------------
    # QUIZ READINESS CHECK
    # -----------------------------------------------------------------
    def volume_check(self):
        self.robot_speak("Are we all ready? Make some noise!")

        time.sleep(1)

        # Measure crowd loudness
        loudness = self.listen_for_volume(timeout=self.READY_TIMEOUT)

        if loudness < self.VOLUME_THRESHOLD:
            # Not loud enough
            self.robot_speak("I can't hear you! A little louder please!")
            return False
        else:
            # Good loudness
            self.robot_speak("Great! You sound ready. Let's begin the quiz!")
            return True

    # -----------------------------------------------------------------
    # MAIN LOOP
    # -----------------------------------------------------------------
    def run(self):
        # First, check if the audience is ready
        ready = False
        while not ready:
            ready = self.volume_check()

        # After volume check → continue with normal GPT chat
        self.robot_speak("Feel free to talk to me or ask questions!")

        while True:
            try:
                text = self.listen_and_transcribe()
                if not text:
                    continue

                print("User said:", text)

                reply = self.ask_gpt(text)
                self.robot_speak(reply)

            except Exception as e:
                print("Error:", e)
                continue


if __name__ == "__main__":
    bot = SimpleNaoGPT()
    bot.run()
