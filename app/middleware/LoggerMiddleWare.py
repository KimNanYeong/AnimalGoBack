import os
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.background import BackgroundTask

# Ensure the log directory exists
log_directory = 'log'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# ✅ 로깅 설정 (시간 포함)
logger = logging.getLogger("main_logger")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(os.path.join(log_directory, 'info.log'), encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_info(req_method, req_url, req_headers, req_body, res_status, res_headers, res_body):
    logger.info("")
    logger.info(f"Request Method: {req_method}")
    logger.info(f"Request URL: {req_url}")
    logger.info(f"Request Headers: {req_headers}")
    logger.info(f"Request Body: {req_body}")
    logger.info(f"Response Status: {res_status}")
    logger.info(f"Response Headers: {res_headers}")
    logger.info(f"Response Body: {res_body}")
    logger.info("")

class LoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_method = request.method
        req_url = str(request.url)
        req_headers = dict(request.headers)
        req_body = await request.body()

        response = await call_next(request)

        res_status = response.status_code
        res_headers = dict(response.headers)
        res_body = b''
        async for chunk in response.body_iterator:
            res_body += chunk

        task = BackgroundTask(log_info, req_method, req_url, req_headers, req_body, res_status, res_headers, res_body)
        return Response(content=res_body, status_code=res_status,
                        headers=res_headers, media_type=response.media_type, background=task)