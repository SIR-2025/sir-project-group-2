from re import A
from server_connection import KahootAPI
from nao_listener import NaoListener
from nao_connection import connect_nao
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import NaoqiTextToSpeechRequest
import time
from os.path import abspath, join
from llm_integration import get_llm_response, system_prompt_pre_quiz

SERVER_URL = "http://localhost:5000"
# Connect to NAO
nao = connect_nao("10.0.0.137")

#setup listener
GOOGLE_KEY = abspath(join("..", "..", "conf", "google", "google-key.json"))
listener = NaoListener(nao, GOOGLE_KEY, quiet=True)

#start connection to server
api = KahootAPI(SERVER_URL)

#restart quiz
api.reset_quiz()


nao.tts.request(NaoqiTextToSpeechRequest("Hello! Everyone we are going to start the game, please scan the QR code to join the game!"))

number_of_players = 0
minimum_players = 2

#get players from server
while number_of_players < minimum_players:
    player_number = api.get_status()["player_count"]
    player_names = api.get_players()
    if player_number == minimum_players:
        break

    elif player_number == minimum_players/2:
        user_message_str = str(player_names)
        response =get_llm_response(user_message_str, system_prompt_pre_quiz)
        nao.tts.request(NaoqiTextToSpeechRequest(f"{response}"))
        #nao.tts.request(NaoqiTextToSpeechRequest(f"We still need some more players to start the game!"))
        time.sleep(1)

    else:
        nao.tts.request(NaoqiTextToSpeechRequest(f"We still need some more players to start the game!"))
    
    number_of_players = player_number
    time.sleep(5)