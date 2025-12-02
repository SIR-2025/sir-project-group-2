"""
Quiz Data Module
================

This module contains all quiz questions and configuration.
Edit this file to change quiz title and questions.

Structure:
- QUIZ_TITLE: Name of the quiz (shown in interface)
- QUESTIONS: List of question dictionaries

Each question has:
- id: Unique identifier (integer)
- text: The question text
- options: List of 4 answer options
- correct_answer: Index of correct answer (0-3)
"""

# Quiz configuration
QUIZ_TITLE = "Nao's Fun Quiz"

# Question list
# Edit here to add/modify questions
QUESTIONS = [
    {
        "id": 0,
        "text": "What is the capital of the Netherlands?",
        "options": [
            "Amsterdam",
            "Rotterdam",
            "The Hague",
            "Utrecht"
        ],
        "correct_answer": 0  # Amsterdam (index 0)
    },
    {
        "id": 1,
        "text": "How many legs does a spider have?",
        "options": [
            "6 legs",
            "8 legs",
            "10 legs",
            "12 legs"
        ],
        "correct_answer": 1  # 8 legs (index 1)
    },
    {
        "id": 2,
        "text": "What color is the sky on a clear day?",
        "options": [
            "Green",
            "Red",
            "Blue",
            "Yellow"
        ],
        "correct_answer": 2  # Blue (index 2)
    }
]


# Validation function
def validate_questions():
    """
    Validates question data structure.
    Checks for required fields and correct format.
    """
    for i, q in enumerate(QUESTIONS):
        # Check required fields
        required = ['id', 'text', 'options', 'correct_answer']
        for field in required:
            if field not in q:
                raise ValueError(f"Question {i}: Missing field '{field}'")
        
        # Check options count
        if len(q['options']) != 4:
            raise ValueError(f"Question {i}: Must have exactly 4 options")
        
        # Check correct_answer range
        if not 0 <= q['correct_answer'] < 4:
            raise ValueError(f"Question {i}: correct_answer must be 0-3")
    
    return True


# Run validation on import
if __name__ == "__main__":
    try:
        validate_questions()
        print(f"✅ Quiz data is valid!")
        print(f"✅ Title: {QUIZ_TITLE}")
        print(f"✅ Questions: {len(QUESTIONS)}")
    except ValueError as e:
        print(f"❌ Error: {e}")

