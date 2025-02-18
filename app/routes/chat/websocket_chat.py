from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from services.chat_service import generate_ai_response, get_character_data, initialize_chat
from firebase_admin import firestore
from db.faiss_db import store_chat_in_faiss  # ✅ 채팅방별 FAISS 저장
import json

router = APIRouter()
db = firestore.client()

# WebSocket을 통해 연결된 클라이언트 관리
test_active_connections = []

@router.websocket("/chat/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    await websocket.accept()
    test_active_connections.append(websocket)
    
    try:
        # ✅ 클라이언트가 처음 접속할 때 기존 메시지 가져오기
        chat_ref = db.collection("chats").document(chat_id)
        chat_data = chat_ref.get()
        if (chat_data.exists):
            messages = chat_data.to_dict().get("messages", [])
            await websocket.send_text(json.dumps({"chat_id": chat_id, "messages": messages}))
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_id = message_data.get("user_id")
            message = message_data.get("message")

            # Firestore에 메시지 저장
            chat_ref.update({"messages": firestore.ArrayUnion([{ "user_id": user_id, "message": message }])})
            
            # 모든 클라이언트에게 메시지 전송
            for conn in test_active_connections:
                await conn.send_text(json.dumps({"chat_id": chat_id, "user_id": user_id, "message": message}))
    except WebSocketDisconnect:
        test_active_connections.remove(websocket)

@router.post("/send_message",
             tags=["chat"], 
             summary="AI와 메시지 주고받기", 
             description="AI와 채팅 메시지를 주고받습니다.")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    charac_id: str = Query(..., description="Character ID")
):

    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}-{charac_id}"

    # ✅ 캐릭터 데이터 가져오기
    character_data = get_character_data(user_id, charac_id)
    if character_data is None:
        raise HTTPException(status_code=404, detail="Character data not found")

    # ✅ 채팅방이 존재하지 않으면 자동 생성
    initialize_chat(user_id, charac_id, character_data)  # 🔥 여기에 추가

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, charac_id, user_input)
    if error:
        raise HTTPException(status_code=500, detail=error)

    # ✅ Firestore `chats/{chat_id}` 문서의 `last_message` 업데이트 (대화 유지용)
    chat_ref = db.collection("chats").document(chat_id)
    try:
        chat_ref.set(
            {
                "last_message": {"content": ai_response, "sender": charac_id},
                "last_active_at": firestore.SERVER_TIMESTAMP
            },
            merge=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Firestore 저장 중 오류 발생")

    # ✅ Firestore 저장 후 해당 채팅방의 FAISS 벡터 DB에 저장
    store_chat_in_faiss(chat_id, charac_id)  # 🔥 채팅방별 벡터 DB 저장

    # ✅ WebSocket을 통해 메시지 전송
    for conn in test_active_connections:
        await conn.send_text(json.dumps({"chat_id": chat_id, "user_id": user_id, "message": user_input}))

    response = {"response": ai_response}
    return response
