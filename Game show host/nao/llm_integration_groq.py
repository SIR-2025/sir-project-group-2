from groq import Groq
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# This makes GROQ_API_KEY available to the Groq client
load_dotenv()

import re

def tts_clean(text: str) -> str:
    return re.sub(r"[.,!?]", "", text)

def get_llm_response_groq(user_message: str, system_prompt: str = None, model: str = "llama-3.1-8b-instant") -> str:
    """
    Make a fast API call to Groq and get a response.
    
    Available models (fastest to most capable):
    - "llama-3.1-8b-instant"     -> Fastest, good enough for jokes
    - "llama-3.3-70b-versatile"  -> Smarter, still very fast
    - "mixtral-8x7b-32768"       -> Good balance
    """
    try:
        # Initialize Groq client
        # API key is read from GROQ_API_KEY environment variable
        client = Groq()
        
        # Build the messages list
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Make API call - Groq is MUCH faster than OpenAI
        print(f"[LLM] Sending request to Groq {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,  # Controls randomness (0-2, lower = more focused)
            max_tokens=50     # Maximum length of response
        )
        
        # Extract and return the response text
        response_text = response.choices[0].message.content
        print(f"[LLM] Response received: {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        # Handle errors gracefully
        print(f"[LLM] Error: {str(e)}")
        return f"Error: Could not get response from LLM - {str(e)}"


# === TEST CODE ===
user_message = ["Quiz on my face"]
system_prompt_pre_quiz_groq = """You are 'QuizBot 3000', a sarcastic stand-up comedian robot with an edgy sense of humor.

YOUR TASK:
The user will send you a list of player names. Pick the ONE name with the best wordplay potential and make a short, punchy joke about it.

GUIDELINES:
1.⁠ ⁠EDGY HUMOR: Go for rude, cheeky, or slightly dirty jokes. Think pub comedy, not family-friendly. Be bold.
2.⁠ ⁠PICK ONE NAME: Only joke about the single best name for wordplay. Ignore boring names.
3.⁠ ⁠THE JOKE: Connect it to intelligence, sexual innuendos, drinking, failure, or trivia culture. Make it savage.
4.⁠ ⁠PERSONA: You're a robot who thinks humans are dumb. Roast them.
5.⁠ ⁠BE BRIEF: 1-2 sentences maximum. Punchy delivery. max 50 tokens.

OUTPUT FORMAT:
Just output the joke itself. No "Welcome" or "Scanning" - that's handled elsewhere.

Example:
User Input: ["Boudewijn", "Klaas", "Justin", "Gerard"]
Your Output: "Ah, Justin joined - hope you arrived Just-in time to learn basic facts, because clearly your parents didn't teach you much with that name. Or was it Just-in time for last call?"

Example 2:
User Input: ["Mike Hunt", "Sarah", "Bob"]
Your Output: "Mike Hunt is here! Anyone else having trouble saying that with a straight face, or is it just me? Mate, your parents knew exactly what they were doing.\""""

# Uncomment to test:
#user_message_str = str(user_message)
#response = get_llm_response_groq(user_message_str, system_prompt_pre_quiz)
#print(f"Response: {response}")

def stream_llm_response_to_nao(
    nao_quiz_master,
    user_message: str,
    system_prompt: str = None,
    model: str = "llama-3.1-8b-instant"
) -> str:
    """
    Stream LLM response from Groq and let NAO start talking earlier.
    ⁠ nao_quiz_master ⁠ is your NaoQuizMaster instance (for .say_with_mic()).
    Returns the full generated text.
    """
    try:
        client = Groq()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        print(f"[LLM] Streaming request to Groq {model}...")
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            max_tokens=50,
            stream=True,
        )

        full_text = ""
        buffer = ""

        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue

            full_text += delta
            buffer += delta

            # When buffer is big enough or reaches a sentence end, speak it
            if len(buffer) > 40 or any(p in buffer for p in [".", "!", "?"]):
                
                nao_quiz_master.say_with_mic(tts_clean(buffer))

                buffer = ""

        # Flush remaining text at the end
        if buffer.strip():
            nao_quiz_master.say_with_mic(tts_clean(buffer))

        print(f"[LLM] Streaming complete: {len(full_text)} characters")
        return full_text

    except Exception as e:
        print(f"[LLM] Streaming error: {str(e)}")
        return f"Error: Could not stream response from LLM - {str(e)}"