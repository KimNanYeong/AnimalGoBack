# Chat Router 설정
from .chat.send_message import router as chat_send_message_router
from .chat.chat_history import router as chat_history_router
from .chat.chat_list import router as chat_list_router
from .chat.clear_chat import router as clear_chat_router

# Pets Router 설정
from .pets.traits_api import router as traits_router
from .pets.characters import router as characters_router

# User Router 설정
from .users.user import router as user_router

# Home Router 설정
from .home.base import router as base_router
from .home.image_upload import router as image_router
from .home.character_api import router as character_router
from .home.register import router as register_router

from .image.ShowImageRoutes import router as show_image_router

from .create.CreateRouter import router as create_router
from .home.login import router as login_router