from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException
import jwt

"""
    미들웨어
    토큰 검증 시작
"""
class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        
        print('middleware')

        access_token = request.session.get("access_token")
        refresh_token = request.session.get('refresh_token')

        # try:
        #     payload = jwt.decode(access_token)
        # except e:
        # access_token = request.session.get('access_token')
        # refresh_token = request.session.get('refresh_token')

        # if not access_token or not refresh_token:
        #     raise HTTPException(status_code=401, detail="Not authenticated")

        # # Add tokens to request state for further use in the application
        # request.state.access_token = access_token
        # request.state.refresh_token = refresh_token

        response = await call_next(request)
        return response