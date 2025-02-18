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
        # try:
            # access_token = request.session.get("access_token")
            # refresh_token = request.session.get('refresh_token')

            # if not access_token or not refresh_token:
            #     raise HTTPException(status_code=401, detail="Not authenticated")

            # Verify the access token
            # token_data = verify_jwt_token(access_token)
            # request.state.user = token_data

        #     response = await call_next(request)
        # except HTTPException as e:
        #     response = Response(content=str(e.detail), status_code=e.status_code)
        # except Exception as e:
        #     response = Response(content="Internal Server Error", status_code=500)
        #     print(f"Unexpected error: {e}")

        # return response