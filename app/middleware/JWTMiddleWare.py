from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException
import jwt
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

EXCLUDE_PATHS = ["/home/login", "/home/register","/docs","/openapi.json"]
SECRET_KEY = os.getenv("SECRET_KEY")
"""
    미들웨어
    토큰 검증 시작
"""

def verify_jwt_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    if payload["exp"] < datetime.now(timezone.utc).timestamp():
        return payload
    
class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print('middle ware')
        if request.url.path in EXCLUDE_PATHS:
            return await call_next(request)
        try:
            access_token = request.session.get("access_token")
            refresh_token = request.session.get('refresh_token')

            if not access_token or not refresh_token:
                raise HTTPException(status_code=401, detail="Not authenticated")

            # Verify the access token
            token_data = verify_jwt_token(access_token)
            # request.state.user = token_data
            response = await call_next(request)
        except jwt.ExpiredSignatureError as e:
            try:
                refresh_data = verify_jwt_token(refresh_token)
                response = await call_next(request)
            except jwt.ExpiredSignatureError as e:
                response = Response(content=str(e.detail))
        except HTTPException as e:
            response = Response(content=str(e.detail), status_code=e.status_code)
        except Exception as e:
            response = Response(content="Internal Server Error", status_code=500)
            print(f"Unexpected error: {e}")
        return response
