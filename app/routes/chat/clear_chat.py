from firebase_admin import firestore
from fastapi import APIRouter, HTTPException
from vectorstore.faiss_cleanup import delete_faiss_index  # ✅ FAISS 인덱스 삭제 함수 불러오기

router = APIRouter()
db = firestore.client()

@router.delete("/chat/delete_chat/{chat_id}",
               tags=["chat"],
               summary="채팅방 삭제",
               description="채팅방 및 관련 데이터를 Firestore와 FAISS에서 삭제합니다.")
async def delete_chat(chat_id: str):
    """🔥 Firestore에서 채팅방 및 관련 데이터 삭제"""
    try:
        # ✅ Firestore 채팅방 문서 삭제
        chat_ref = db.collection("chats").document(chat_id)
        chat_ref.delete()

        # ✅ Firestore 메시지 컬렉션 삭제
        messages_ref = db.collection("chats").document(chat_id).collection("messages")
        docs = messages_ref.stream()
        for doc in docs:
            doc.reference.delete()

        # ✅ Firestore의 faiss_indices 컬렉션에서도 해당 chat_id 삭제
        faiss_ref = db.collection("faiss_indices").document(chat_id)
        faiss_ref.delete()
        print(f"✅ Firestore faiss_indices 삭제 완료: {chat_id}")

        # ✅ FAISS 인덱스 파일 삭제
        delete_faiss_index(chat_id)  # 🔥 FAISS 벡터 DB 삭제
        print(f"✅ FAISS 벡터 데이터 삭제 완료: {chat_id}")

        return {"message": f"✅ 채팅방 {chat_id} 및 관련 데이터가 삭제되었습니다."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채팅방 삭제 중 오류 발생: {str(e)}")
