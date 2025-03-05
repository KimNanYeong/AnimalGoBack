import firebase_admin
from firebase_admin import credentials, db

# Firebase 초기화 (중복 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/data/fbkeys/fbkey.json")
    firebase_admin.initialize_app(cred)

#firebase_admin.initialize_app(cred)
init_object = firebase_admin.initialize_app(cred, {'databaseURL': 'https://animalstart-f52e8-default-rtdb.firebaseio.com/'  })

print(init_object)

ref=db.reference('/')
print(ref)
print(ref.get())
#print(ref.get()['a1'])
#print(ref.get()['a2'])  # KeyError: 'a2'
