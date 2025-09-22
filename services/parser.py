import httpx
import json
import redis
import logging
import os

from fastapi import HTTPException
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)


async def get_instagram_profile(username: str):
    cache_key = f"ig:{username}"
    cached = r.get(cache_key)
    if cached:
        logger.info(f"Cache hit for {username}")
        return json.loads(cached)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "x-ig-app-id": "936619743392459",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
            headers=headers
        )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="User not found")
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching Instagram data")

    try:
        data = response.json()
        user = data.get("data", {}).get("user")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.get("is_private"):
            raise HTTPException(status_code=403, detail="Profile is private")

        latest_photos = []
        media_edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
        for edge in media_edges[:5]:
            node = edge.get("node", {})
            if node.get("__typename") == "GraphImage":  # Only photos
                latest_photos.append(node.get("display_url"))
            if len(latest_photos) == 5:
                break
        # Ensure 3-5, but use available up to 5
        latest_photos = latest_photos[:5]

        profile = {
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "bio": user.get("biography"),
            "profile_pic_url": user.get("profile_pic_url_hd") or user.get("profile_pic_url"),
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "following": user.get("edge_follow", {}).get("count", 0),
            "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "latest_photos": latest_photos
        }

        # Cache for 10 minutes (600 seconds)
        r.set(cache_key, json.dumps(profile), ex=600)
        logger.info(f"Cache set for {username}")
        return profile

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error parsing Instagram data")
