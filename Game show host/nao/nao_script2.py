from re import A
from server_connection import KahootAPI
from nao_connection import connect_nao
import time
from nao_listener import NaoListener 
from llm_integration_groq import get_llm_response_groq
from functionsforscript import NaoQuizMaster
from sic_framework.devices import Nao
from os.path import abspath, join

import time 

NAO_IP = "10.0.0.137"
SERVER_URL = "http://localhost:5000"
GOOGLE_KEY = abspath(join("..", "..", "conf", "google", "google-key.json"))

nao = connect_nao("10.0.0.137")
api = KahootAPI(SERVER_URL)

class RunQuiz():
    def __init__(self, nao_ip: str):
        self.nao_ip = nao_ip
        self.nao = Nao(ip=NAO_IP)
        self.listener = NaoListener(self.nao, GOOGLE_KEY, quiet=True)
        self.api = KahootAPI(SERVER_URL)

    def run_quiz(self):
        naofunctions = NaoQuizMaster(nao_ip=NAO_IP)
        naofunctions.stand_up()
        naofunctions.say_something("Hello everyone! I am Nao your quiz host today!", False)
        naofunctions.hello()
        naofunctions.say_something("And this is my assistant ")
        textperson1 = self.listener.listen()
        prompt1 = """You are 'QuizBot 3000', 
        a sarcastic stand-up comedian robot with an edgy sense of humor,
        you are making fun of the co-host in the quiz"""
        respons1 = get_llm_response_groq(textperson1, prompt1)
        naofunctions.say_something(respons1)

def main():
    quiz_master = RunQuiz(nao_ip=NAO_IP)
    quiz_master.run_quiz()

if __name__ == "__main__":
    main()     
