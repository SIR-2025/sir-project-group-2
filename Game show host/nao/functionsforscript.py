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

    def stand_up(self):
        self.nao.motion.request(NaoPostureRequest("Stand", 0.5))   

    def hello(self):          
        self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Gestures/Hey_1"))
    
    def say_something(self, textje, setting=True):
        self.nao.tts.request(
            NaoqiTextToSpeechRequest(f"\\vct=110\\ \\rspd=90\\ {textje}"), block=setting)
    
    