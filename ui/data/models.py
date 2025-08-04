from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from bson import ObjectId
from bunnet import Document
from pydantic import BaseModel, Field


class Clip(Document):
    clip_id: str = Field(default_factory=lambda: str(uuid4()))
    start: int
    end: int
    description: str
    title: str
    labels: List[str] = []
    partners: List[str] = []  # Usernames or IDs
    speed: float = 1.0


class Video(Document):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
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


class Playlist(Document):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    name: str
    videos: List[Video] = []
    owner_id: Optional[ObjectId] = None
    team_id: Optional[ObjectId] = None
    playlist_id: Optional[str] = None

    class Settings:
        name = "playlists"

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Cliplist(Document):
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    name: str
    filters: Optional[Dict] = None
    clip_ids: Optional[List[str]] = []
    ordered: bool = True
    owner_id: Optional[ObjectId] = None
    team_id: Optional[ObjectId] = None

    class Settings:
        name = "cliplists"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TreeNode(BaseModel):
    id: str
    title: str
    embed_url: str
    children: List["TreeNode"] = []  # Recursive typing


TreeNode.model_rebuild()


class Notion(Document):
    tree: List[TreeNode]
    submitted_at: datetime = datetime.utcnow()

    class Settings:
        name = "notion"


class Team(Document):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    name: str
    owner_id: Optional[ObjectId] = None
    member_ids: List[ObjectId] = []

    class Settings:
        name = "teams"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
