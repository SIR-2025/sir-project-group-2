"""
NAO Listener - Google Cloud Speech-to-Text (STREAMING)
=======================================================
Snelle real-time spraakherkenning voor dynamische gesprekken.

Voordat je runt:
1. run-google-stt
2. Zorg dat google-key.json in conf/google/ staat
"""

import json
import logging
from sic_framework.devices import Nao
from sic_framework.services.google_stt.google_stt import (
    GoogleSpeechToText,
    GoogleSpeechToTextConf,
    GetStatementRequest,
)


class NaoListener:
    """
    Snelle streaming listener met Google Speech-to-Text.
    Detecteert automatisch wanneer je stopt met praten.
    """
    
    def __init__(self, nao, google_keyfile_path, quiet=True):
        """
        Setup de listener.
    
        """
        if quiet:
            logging.getLogger().setLevel(logging.WARNING)
        
        self.nao = nao
        
        # Load Google credentials
        keyfile_json = json.load(open(google_keyfile_path))
        
        # Setup Google STT (streaming, real-time)
        stt_conf = GoogleSpeechToTextConf(
            keyfile_json=keyfile_json,
            sample_rate_hertz=16000,      # NAO's sample rate
            language="en-US",             # Nederlands! Of "en-US" voor Engels
            interim_results=False,        # Alleen finale resultaat
            timeout=None,                 # <-- VERANDER DIT van 10.0 naar None
        )
        
        self.stt = GoogleSpeechToText(
            conf=stt_conf, 
            input_source=nao.mic
        )
        
        print("[LISTENER] Ready! (Google Cloud STT)")
    
    def listen(self):
        """
        Luister naar spraak en geef tekst terug.
        Stopt AUTOMATISCH als je stopt met praten!
        """
        print("\n🎤 LISTENING... (speak now, I'll detect when you stop)")
        
        try:
            result = self.stt.request(GetStatementRequest())
            
            if result and hasattr(result.response, 'alternatives') and result.response.alternatives:
                transcript = result.response.alternatives[0].transcript.strip()
                if transcript:
                    print(f"✓ HEARD: {transcript}")
                    return transcript
            
            print("✗ No speech detected")
            return ""
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return ""


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    import time
    from os.path import abspath, join
    
    NAO_IP = "10.0.0.137"
    GOOGLE_KEY = abspath(join("..", "..", "conf", "google", "google-key.json"))
    
    print("\n" + "="*50)
    print("NAO LISTENER TEST (Google Cloud STT)")
    print("="*50)
    
    # 1. Connect to NAO
    print(f"\nConnecting to NAO at {NAO_IP}...")
    nao = Nao(ip=NAO_IP)
    print("Connected!\n")
    
    time.sleep(2)
    
    # 2. Setup listener
    listener = NaoListener(nao, GOOGLE_KEY, quiet=True)
    
    # 3. Test loop
    print("\n" + "="*50)
    print("READY! Just speak - I'll detect when you're done.")
    print("Press Ctrl+C to stop.")
    print("="*50)
    
    try:
        while True:
            text = listener.listen()
            
            if text:
                print(f"\n>>> You said: \"{text}\"\n")
            else:
                print("(Try again)\n")
                
    except KeyboardInterrupt:
        print("\n\nStopped.")