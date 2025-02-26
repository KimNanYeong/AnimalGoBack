from core.firebase import db

class PersonalityUtil:
    def __init__(self):
        self.personality_dict = {}

    async def load_personality(self):
        personality_doc = db.collection("personality_traits").get()
        for personality in personality_doc:
            self.personality_dict[personality.id] = personality.to_dict()

    async def get_all_personality(self):
        return self.personality_dict

    async def get_personality(self, personality_id : str):
        return self.personality_dict[personality_id]

personality_util = PersonalityUtil()

async def load_personality():
    await personality_util.load_personality()

async def get_all_personality():
    return await personality_util.get_all_personality()

async def get_personality(personality_id : str):
    return await personality_util.get_personality(personality_id)