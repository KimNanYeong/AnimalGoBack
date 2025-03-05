import os
import warnings
import firebase_admin
from firebase_admin import credentials, firestore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import google.generativeai as genai
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=DeprecationWarning)

FIREBASE_CRED_PATH = r"C:/data/fbkeys/fbkey0305.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
genai.configure(api_key=GEMINI_API_KEY)

def save_message_and_update_chat(chat_id, sender, message):
    chat_ref = db.collection("chats").document(chat_id)

    if not chat_ref.get().exists:
        chat_ref.set({
            "last_message": {"content": "", "sender": ""},
            "last_active_at": firestore.SERVER_TIMESTAMP
        })

    db.collection("chats").document(chat_id).collection("messages").add({
        "content": message,
        "sender": sender,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    chat_ref.set({
        "last_message": {"content": message, "sender": sender},
        "last_active_at": firestore.SERVER_TIMESTAMP
    }, merge=True)

# 수정: gemini-pro 모델 사용
llm = ChatGoogleGenerativeAI(google_api_key=GEMINI_API_KEY, model="gemini-pro")
memory = ConversationBufferMemory()
conversation = ConversationChain(llm=llm, memory=memory)

def chat_with_memory(chat_id, sender, message):
    save_message_and_update_chat(chat_id, sender, message)
    print("chat_id =", chat_id, " message =", message)
    response = conversation.run(message)
    print("chat_id =", chat_id, " response ==", response)
    save_message_and_update_chat(chat_id, "bot", response)
    return response

if __name__ == "__main__":
    print(chat_with_memory("sp1_for_langchain", "user", "안녕, 어제 뭐했어?"))
    print(chat_with_memory("sp1_for_langchain", "user", "그럼 오늘은?"))