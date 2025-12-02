from re import A
from server_connection import KahootAPI
from nao_connection import connect_nao
import time
from nao_listening import NaoListener 

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
    
    def run_quiz(self):
        self.hello("Hello everyone! I am Nao your quiz host today!")
        self.sleep(5)
        self.look_to_left_right("And this is my assistant ")

def main():
    quiz_master = NaoQuizMaster(nao_ip=NAO_IP)
    quiz_master.run_quiz()

if __name__ == "__main__":
    main()
 