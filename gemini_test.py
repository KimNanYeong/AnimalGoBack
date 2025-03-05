import google.generativeai as genai
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

#GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"
GEMINI_MODEL = "gemini-2.0-flash"

model = genai.GenerativeModel(GEMINI_MODEL)

print ("~~~~~~~~~~key : ", GEMINI_API_KEY)
print ("~~~~~~~~~~model : ", GEMINI_MODEL)

response = model.generate_content("Hello, Gemini!")

print(response.text)