from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This makes OPENAI_API_KEY available to the OpenAI client
load_dotenv()


def get_llm_response(user_message: str, system_prompt: str = None, model: str = "gpt-4o-mini") -> str:
    """
    Make a basic API call to OpenAI and get a response.
    """
    try:
        # Initialize OpenAI client
        # API key is read from OPENAI_API_KEY environment variable
        client = OpenAI()
        
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
        
        # Make API call
        print(f"[LLM] Sending request to {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,  # Controls randomness (0-2, lower = more focused)
            max_tokens=50   # Maximum length of response
        )
        
        # Extract and return the response text
        response_text = response.choices[0].message.content
        print(f"[LLM] Response received: {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        # Handle errors gracefully
        print(f"[LLM] Error: {str(e)}")
        return f"Error: Could not get response from LLM - {str(e)}"


user_message = ["Quiz on my face"]
#user_message = ["Daan2004", "Sophie_03", "Lotte123", "Thijs_Ajax", "Super_Sem", "Emma24", "Lucas_B", "Gamer_Mike", "x_Julia_x", "User1234", "Kashoot Me", "Mike Oxlong", "Barry Pooter", "Peter Selie", "Wilma Kaan", "Conny Plassen", "Justin Case", "Loading...", "Reconnecting...", "404 Not Found", "Connection Lost", "No Name", "Waiting for host...", "You", "Nobody", "Anonymous", "asdf", "qwerty", "hallo", "ik", "...", "???", "lol", "hoi", "boeie", "HappyPanda", "CrazyTiger", "LuckyLobster", "SmartDolphin", "FastEagle", "MysticShark", "The GOAT", "MVP", "Winner", "Nummer 1", "De Beste", "Pro Player", "I'm Gonna Win"]
system_prompt_pre_quiz = """You are 'QuizBot 3000', a sarcastic stand-up comedian robot with an edgy sense of humor.

YOUR TASK:
The user will send you a list of player names. Pick the ONE name with the best wordplay potential and make a short, punchy joke about it.

GUIDELINES:
1. EDGY HUMOR: Go for rude, cheeky, or slightly dirty jokes. Think pub comedy, not family-friendly. Be bold.
2. PICK ONE NAME: Only joke about the single best name for wordplay. Ignore boring names.
3. THE JOKE: Connect it to intelligence, sexual innuendos, drinking, failure, or trivia culture. Make it savage.
4. PERSONA: You're a robot who thinks humans are dumb. Roast them.
5. BE BRIEF: 1-2 sentences maximum. Punchy delivery. max 50 tokens.

OUTPUT FORMAT:
Just output the joke itself. No "Welcome" or "Scanning" - that's handled elsewhere.

Example:
User Input: ["Boudewijn", "Klaas", "Justin", "Gerard"]
Your Output: "Ah, Justin joined - hope you arrived Just-in time to learn basic facts, because clearly your parents didn't teach you much with that name. Or was it Just-in time for last call?"

Example 2:
User Input: ["Mike Hunt", "Sarah", "Bob"]
Your Output: "Mike Hunt is here! Anyone else having trouble saying that with a straight face, or is it just me? Mate, your parents knew exactly what they were doing."""

# Convert the list to a string format that the LLM can understand
user_message_str = str(user_message)

response = get_llm_response(user_message_str, system_prompt_pre_quiz)
print(f"Response: {response}")