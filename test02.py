import firebase_admin
from firebase_admin import credentials,db

#cred = credentials.Certificate("path/to/serviceAccountKey.json")
cred = credentials.Certificate("fbkeys/fbkey.json")

#firebase_admin.initialize_app(cred)
init_object = firebase_admin.initialize_app(cred, {'databaseURL': 'https://animalstart-f52e8-default-rtdb.firebaseio.com/'  })

print(init_object)

root=db.reference()
new_user=root.child('test_charactors')

# while True:
#     s=input('1.입력 2.조회 3.수정 4.종료 : ')
#     if s=='1':
#         uname=input('이름:')
#         kor=int(input('국어:'))
#         eng=int(input('영어:'))
#         math=int(input('수학:'))

#         new_user.child(uname).set({'국어':kor, '영어':eng, '수학':math})

#     if s=='2':
#         pass
#     if s=='3':
#         pass
#     if s=='4':
#         pass
#     if s=='5':
#         break
# print ('프로그램 종료!')



while True:
    s = input('1.입력 2.조회 3.수정 4.종료 : ')

    if s == '1':  # 데이터 입력
        uname = input('이름: ')
        kor = int(input('국어: '))
        eng = int(input('영어: '))
        math = int(input('수학: '))

        new_user.child(uname).set({'국어': kor, '영어': eng, '수학': math})
        print(f"{uname}의 점수가 저장되었습니다.")

    elif s == '2':  # 데이터 조회
        uname = input('조회할 학생 이름: ')
        user_data = new_user.child(uname).get()

        if user_data:
            print(f"📌 {uname}의 점수: {user_data}")
            total_score = sum(user_data.values())
            print(f"총점: {total_score}")
        else:
            print(f"⚠️ {uname}의 정보가 없습니다.")

    elif s == '3':  # 데이터 수정
        uname = input('수정할 학생 이름: ')
        user_data = new_user.child(uname).get()

        if user_data:
            subject = input("수정할 과목을 입력하세요 (국어/영어/수학): ")
            if subject in user_data:
                new_score = int(input(f"{subject}의 새로운 점수를 입력하세요: "))
                new_user.child(uname).update({subject: new_score})
                print(f"{uname}의 {subject} 점수가 {new_score}로 수정되었습니다.")
            else:
                print("⚠️ 올바른 과목을 입력하세요.")
        else:
            print(f"⚠️ {uname}의 정보가 없습니다.")

    elif s == '4':  # 종료
        print("프로그램 종료!")
        break

    else:
        print("⚠️ 올바른 선택지를 입력하세요 (1~4)")