# models.py
from pydantic import BaseModel
from typing import List, Optional

class Clip(BaseModel):
    start: int
    end: int
    type: str
    description: str
    labels: List[str]
    title: str
    partners: List[str]

class Video(BaseModel):
    video_id: str
    youtube_url: str
    title: str
    date: str
    duration_seconds: float
    type: Optional[str] = ""
    partners: List[str] = []
    positions: List[str] = []
    notes: Optional[str] = ""
    labels: List[str] = []
    clips: List[Clip] = []

class Playlist(BaseModel):
    name: str
    videos: List[Video]
