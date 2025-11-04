"""
Simple NAO + GPT Demo

NAO robot integrated with OpenAI GPT to generate funny responses and speak them.
NAO listens to your speech using Whisper, sends it to ChatGPT, and speaks the response.

SETUP INSTRUCTIONS:
1. Install required services:
   pip install --upgrade social-interaction-cloud[openai-gpt]
   pip install --upgrade social-interaction-cloud[whisper-speech-to-text]
   
2. Create a .env file in the workspace root with your OpenAI API key:
   OPENAI_API_KEY=your_api_key_here
   
3. Start the services (in SEPARATE terminals):
   Terminal 1: run-gpt
   Terminal 2: run-whisper
   
4. Run this script:
   python nao_gpt.py
"""

from sic_framework.core.sic_application import SICApplication
from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest
from sic_framework.services.openai_gpt.gpt import GPT, GPTConf, GPTRequest
from sic_framework.services.openai_whisper_stt.whisper_stt import (
    SICWhisper,
    WhisperConf,
    GetTranscript
)
from os import environ
from dotenv import load_dotenv

class SimpleNaoGPT(SICApplication):
    """
    Simple demo: NAO listens to your speech, sends it to ChatGPT,
    and speaks the funny response back to you.
    """
    
    def __init__(self):
        super(SimpleNaoGPT, self).__init__()
        
        # Configuration
        self.nao_ip = "10.0.0.137"  # Your NAO's IP
        self.context = []  # Conversation memory
        
        self.setup()
    
    def setup(self):
        """Initialize NAO and GPT."""
        # Initialize NAO
        self.nao = Nao(ip=self.nao_ip, dev_test=False)
        
        # Load OpenAI API key from .env file in workspace root
        # The .env file should contain: OPENAI_API_KEY=your_api_key_here
        load_dotenv()  # Loads from current directory or searches parent directories
        
        # Check if API key exists
        if "OPENAI_API_KEY" not in environ:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables.\n"
                "Please create a .env file in the workspace root with:\n"
                "OPENAI_API_KEY=your_api_key_here"
            )
        
        # Configure GPT as a comedian
        conf = GPTConf(
            openai_key=environ["OPENAI_API_KEY"],
            system_message="You are a funny stand-up comedian robot. Make short, witty jokes.",
            model="gpt-4o-mini",
            temp=0.8,  # Creative
            max_tokens=50  # Short responses
        )
        
        self.gpt = GPT(conf=conf)
        
        # Setup Whisper Speech-to-Text for listening
        # Uses the same OpenAI API key as GPT - simple and effective!
        whisper_conf = WhisperConf(
            openai_key=environ["OPENAI_API_KEY"]  # Same key as GPT
        )
        
        # Connect Whisper to NAO's microphone
        self.stt = SICWhisper(
            input_source=self.nao.mic,
            conf=whisper_conf
        )
        
        print("Whisper speech-to-text initialized and ready to listen!")
    
    def listen_to_user(self):
        """
        Listen to user speech and return text transcript.
        
        Returns:
            str: The text transcript of what the user said
        """
        print("🎤 Listening... (speak now)")
        
        # Request transcript from NAO's microphone
        # timeout: Maximum time to wait for speech to start (seconds)
        # phrase_time_limit: Maximum duration of the phrase (seconds)
        transcript_msg = self.stt.request(GetTranscript(
            timeout=10,  # Wait up to 10 seconds for user to start speaking
            phrase_time_limit=8  # Stop recording after 8 seconds of speech
        ))
        
        return transcript_msg.transcript
    
    def run(self):
        """Main loop."""
        try:
            # NAO greets
            self.nao.tts.request(NaoqiTextToSpeechRequest("Hello! I'm a comedy bot!"))
            
            # 5 conversation turns - NAO listens, GPT responds, NAO speaks
            for i in range(1):
                # Listen to user speech via NAO's microphone
                user_input = self.listen_to_user()
                print("You said: " + user_input)
                
                # Send to ChatGPT
                reply = self.gpt.request(GPTRequest(
                    input=user_input,
                    context_messages=self.context
                ))
                
                # NAO speaks the response
                response = reply.response
                print("NAO: " + response)
                self.nao.tts.request(NaoqiTextToSpeechRequest(response))
                
                # Add to conversation history for context
                self.context.append(user_input)
            
            self.shutdown()
            
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
            self.shutdown()
        except Exception as e:
            print("Error: " + str(e))
            import traceback
            traceback.print_exc()
            self.shutdown()

if __name__ == "__main__":
    demo = SimpleNaoGPT()
    demo.run()