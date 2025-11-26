from re import A
from server_connection import KahootAPI
from nao_connection import connect_nao
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import NaoqiTextToSpeechRequest
import time


SERVER_URL = "http://localhost:5000"
# Connect to NAO
nao = connect_nao("10.0.0.137")

#start connection to server
api = KahootAPI(SERVER_URL)

#restart quiz
#api.reset_quiz()

nao.tts.request(NaoqiTextToSpeechRequest("Hello! Everyone scan the QR code to join the game!"))

number_of_players = 0

#get players from server
while number_of_players < 3:
    player_number = api.get_status()["player_count"]
    player_names = api.get_players()
    if player_number == 3:
        break
    elif player_number == 1:
        nao.tts.request(NaoqiTextToSpeechRequest(f"{player_names[0]} needs some more competition, more people need to join the game!"))
        time.sleep(1)
    else:
        nao.tts.request(NaoqiTextToSpeechRequest(f"We still need some more players to start the game!"))
    print("Waiting for 10 seconds")
    number_of_players = player_number
    time.sleep(3)