# app/models.py
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from bson import ObjectId
from pydantic import BaseModel, Field

from .auth_models import PyObjectId


class Feedback(BaseModel):
    text: str
    submitted_at: datetime = datetime.utcnow()


class Clip(BaseModel):
    clip_id: str = Field(default_factory=lambda: str(uuid4()))
    start: int
    end: int
    description: str
    title: str
    labels: List[str] = []
    partners: List[str] = []  # Usernames or IDs
    speed: float = 1.0


class Video(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
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

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Playlist(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str
    video_ids: List[str] = []
    owner_id: Optional[PyObjectId] = None  # will be filled in route if not provided
    team_id: Optional[PyObjectId] = None
    playlist_id: Optional[str] = None

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Cliplist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    name: str
    filters: Optional[Dict] = None  # can include labels, partners, type, date ranges
    clip_ids: Optional[List[str]] = []  # optional list of clips for manual or snapshot
    ordered: bool = True  # for swipeable/reel mode
    owner_id: Optional[PyObjectId] = None
    team_id: Optional[PyObjectId] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
