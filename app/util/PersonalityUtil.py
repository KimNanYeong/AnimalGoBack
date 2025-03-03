from core.firebase import db


class PersonalityUtil:
    """성격 특성을 관리하는 유틸리티 클래스"""

    def __init__(self):
        """
        PersonalityUtil 클래스 초기화
        personality_dict: 성격 특성 정보를 저장하는 딕셔너리
        """
        self.personality_dict = {}

    async def load_personality(self):
        """
        Firebase에서 성격 특성 데이터를 로드하여 메모리에 캐시

        성격 특성 컬렉션의 모든 문서를 가져와서 personality_dict에 저장
        문서 ID를 키로, 문서 데이터를 값으로 사용
        """
        personality_doc = db.collection("personality_traits").get()
        for personality in personality_doc:
            self.personality_dict[personality.id] = personality.to_dict()

    async def get_all_personality(self):
        """
        캐시된 모든 성격 특성 정보를 반환

        Returns:
            dict: 모든 성격 특성 정보가 담긴 딕셔너리
        """
        return self.personality_dict

    async def get_personality(self, personality_id: str):
        """
        특정 성격 특성 정보를 반환

        Args:
            personality_id (str): 조회할 성격 특성의 ID

        Returns:
            dict: 해당 ID의 성격 특성 정보

        Raises:
            KeyError: 존재하지 않는 personality_id인 경우
        """
        return self.personality_dict[personality_id]


# 전역 PersonalityUtil 인스턴스 생성
personality_util = PersonalityUtil()


async def load_personality():
    """
    성격 특성 데이터 초기 로드를 위한 전역 함수
    애플리케이션 시작 시 호출되어야 함
    """
    await personality_util.load_personality()


async def get_all_personality():
    """
    모든 성격 특성 정보를 반환하는 전역 함수

    Returns:
        dict: 모든 성격 특성 정보
    """
    return await personality_util.get_all_personality()


async def get_personality(personality_id: str):
    """
    특정 성격 특성 정보를 반환하는 전역 함수

    Args:
        personality_id (str): 조회할 성격 특성의 ID

    Returns:
        dict: 해당 ID의 성격 특성 정보

    Raises:
        KeyError: 존재하지 않는 personality_id인 경우
    """
    return await personality_util.get_personality(personality_id)
