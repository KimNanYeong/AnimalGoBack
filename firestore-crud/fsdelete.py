import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/data/fbkeys/fbstorekey.json")
    firebase_admin.initialize_app(cred)

# Firestore 클라이언트
firestore_db = firestore.client()

def delete_collection(collection_name, batch_size=10):
    """ Firestore의 특정 컬렉션을 삭제하는 함수 """
    collection_ref = firestore_db.collection(collection_name)
    docs = collection_ref.limit(batch_size).stream()

    deleted = 0
    for doc in docs:
        print(f"🔥 Deleting document {doc.id} in {collection_name}")
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(collection_name, batch_size)

def delete_all_collections():
    """ Firestore의 모든 컬렉션을 삭제하는 함수 """
    collections = firestore_db.collections()
    for collection in collections:
        print(f"🚀 Deleting collection: {collection.id}")
        delete_collection(collection.id)

# 실행 (Firestore의 모든 데이터 삭제)
delete_all_collections()
print("✅ Firestore 모든 데이터 삭제 완료!")

