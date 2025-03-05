import firebase_admin
from firebase_admin import credentials, firestore
import itertools
#from google.cloud import firestore
from firebase_admin import credentials, firestore

# 🔹 Firebase 인증 정보 설정 (JSON 키 파일 필요)
FIREBASE_CRED_PATH = "c:/data/fbkeys/fbkey.json"  # 🔹 Firebase 인증 키 파일 경로
cred = credentials.Certificate(FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred)

# 🔹 Firestore 클라이언트 초기화
db = firestore.client()

def create_chatroom_between_characters(character_id_a: str, character_id_b: str):
    try:
        # 알파벳 순서로 캐릭터 ID 정렬 후 채팅방 ID 생성 (형식: {첫번째 캐릭터_id}_{두번째 캐릭터_id})
        sorted_ids = sorted([character_id_a, character_id_b])
        chat_room_id = f"{sorted_ids[0]}_{sorted_ids[1]}"

        # 채팅방 문서 참조 생성 및 존재 여부 확인
        chat_ref = db.collection("chats").document(chat_room_id)
        chat_doc = chat_ref.get()

        user_id = character_id_a.to_dict().get("user_id")



        if chat_doc.exists:
            print(f"채팅방 '{chat_room_id}'은(는) 이미 존재합니다.")
            return {
                "chat_room_id": chat_room_id,
                "message": "채팅방이 이미 존재합니다.",
                "chat_created": False
            }
        else:
            # 새로운 채팅방 데이터 생성
            chat_data = {
                "chat_id": chat_room_id,
                "participants": [character_id_a, character_id_b],
                "create_at": firestore.SERVER_TIMESTAMP,
                "last_active_at": None,
                "last_message": None,
                "user_id": user_id
            }
            chat_ref.set(chat_data)
            print(f"채팅방 '{chat_room_id}'이(가) 생성되었습니다.")
            return {
                "chat_room_id": chat_room_id,
                "message": "채팅방이 성공적으로 생성되었습니다.",
                "chat_created": True
            }
    except Exception as e:
        print(f"Error creating chatroom for '{character_id_a}' and '{character_id_b}': {e}")
        return {"chat_room_id": None, "error": str(e)}

def create_chatrooms_for_all_characters():
    try:
        # Firestore의 "characters" 컬렉션에서 모든 문서를 조회
        characters_ref = db.collection("characters")
        characters_docs = characters_ref.get()

        # "character_path" 필드에 값이 존재하는 문서만 대상 (수정된 부분)
        character_ids = [doc.id for doc in characters_docs if doc.to_dict().get("character_path")]
        print(f"총 {len(character_ids)} 개의 캐릭터(유효한 character_path 존재)를 찾았습니다.")

        results = []
        # 가능한 모든 2개 조합에 대해 채팅방 생성
        for id_a, id_b in itertools.combinations(character_ids, 2):
            result = create_chatroom_between_characters(id_a, id_b)
            results.append(result)
        return results
    except Exception as e:
        print(f"Error during batch processing: {e}")
        return []

if __name__ == "__main__":
    # batch_results가 None일 경우 빈 리스트 반환 (수정된 부분)
    batch_results = create_chatrooms_for_all_characters() or []
    print("Batch process results:")
    for res in batch_results:
        print(res)
