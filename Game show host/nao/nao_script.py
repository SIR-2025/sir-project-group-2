from re import A
from server_connection import KahootAPI
from nao_connection import connect_nao
import time
from nao_listener import NaoListener 
from llm_integration import get_llm_response

from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest
from sic_framework.devices.nao_stub import NaoStub
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import NaoqiTextToSpeechRequest

# Import message types and requests
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiMoveToRequest,
    NaoqiAnimationRequest,
)

import time 

NAO_IP = "10.0.0.137"
SERVER_URL = "http://localhost:5000"
nao = connect_nao("10.0.0.137")
api = KahootAPI(SERVER_URL)

class NaoQuizMaster():

    def __init__(self, nao_ip: str):
        self.nao_ip = nao_ip
        self.nao = Nao(ip=NAO_IP)
        
    def hello(self, textje):
        self.nao.tts.request(
            NaoqiTextToSpeechRequest(f"\\vct=110\\ \\rspd=90\\ {textje}"),
            block=False)
            
        self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Gestures/Hey_1"), 
                            block=False)

    def look_to_left_right(self, textje):
        self.nao.tts.request(
            NaoqiTextToSpeechRequest(f"\\vct=110\\ \\rspd=90\\ {textje}"),
            block=False)
        
        self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Head/TurnLeftRight"))
    
    def say_something(self, textje):
        self.nao.tts.request(
            NaoqiTextToSpeechRequest(f"\\vct=110\\ \\rspd=90\\ {textje}"))
    
    def run_quiz(self):
        self.hello("Hello everyone! I am Nao your quiz host today!")
        self.look_to_left_right("And this is my assistant ")
        textperson1 = NaoListener.listen()
        prompt1 = """You are 'QuizBot 3000', 
        a sarcastic stand-up comedian robot with an edgy sense of humor,
        you are making fun of the co-host in the quiz"""
        respons1 = get_llm_response(textperson1, prompt1)
        self.say_something(respons1)


def main():
    quiz_master = NaoQuizMaster(nao_ip=NAO_IP)
    quiz_master.run_quiz()

if __name__ == "__main__":
    main()
 