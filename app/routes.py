# ---------------- app/routes.py ----------------
from fastapi import APIRouter, Depends
from .models import Video
from .db import db
from .auth import verify_token
from bson import ObjectId

router = APIRouter()

@router.get("/videos")
async def get_videos():
    videos = await db.videos.find().to_list(100)
    # Convert ObjectId to string for each video
    for video in videos:
        video["_id"] = str(video["_id"])
    return videos

@router.post("/videos")
async def add_video(video: Video, user=Depends(verify_token)):
# async def add_video(video: Video):
    video_dict = video.dict()
    result = await db.videos.insert_one(video_dict)
    return {"inserted_id": str(result.inserted_id)}
