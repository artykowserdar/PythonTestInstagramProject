from fastapi import FastAPI, Path, HTTPException, Depends, Request, Header
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from dotenv import load_dotenv
import os
from services.parser import get_instagram_profile

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("API_KEY")


def get_remote_ip(request: Request):
    client_host = request.client.host
    return {"client_host": client_host}


async def api_key_auth(api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    return response


@app.get("/api/instagram/{username}")
@limiter.limit("20/minute")
async def get_profile(request: Request, username: str = Path(...), api_key=Depends(api_key_auth)):
    logger.debug("Instagram user get info - %s - %s", username, get_remote_ip(request))
    try:
        profile = await get_instagram_profile(username)
        return profile
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing {username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
