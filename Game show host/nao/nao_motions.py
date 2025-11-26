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

class NaoQuizMaster():

    def __init__(self, nao_ip: str):
        self.nao_ip = nao_ip
        self.nao = Nao(ip=NAO_IP)
        

    def stand_up(self):
        self.nao.motion.request(NaoPostureRequest("Stand", 0.5))

    def sit_down(self):   
        self.nao.motion.request(NaoPostureRequest("Sit", 0.5))
    
    def walk(self, straight, side, curve):
        self.nao.motion.request(NaoqiMoveToRequest(x=straight, y=side, theta=curve))

    def hello_walk(self):
        self.nao.tts.request(NaoqiTextToSpeechRequest("Hello everyone"), block=False)
        self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Gestures/Hey_6"), block=False)

    def shake_head(self):
        self.nao.tts.request(NaoqiTextToSpeechRequest("nooo you are wrong"), block=False)
        self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Gestures/No_3"))

    def run_quiz(self):
        self.stand_up()
        time.sleep(3)
        self.shake_head()
        time.sleep(4)
        self.hello()

        time.sleep(5)
        #self.sit_down()

def main():
    quiz_master = NaoQuizMaster(nao_ip=NAO_IP,)
    quiz_master.run_quiz()

if __name__ == "__main__":
    main()