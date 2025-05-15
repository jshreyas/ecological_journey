# app/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from bson import ObjectId
from .auth_models import PyObjectId


class Clip(BaseModel):
    start: int
    end: int
    type: str
    description: str
    title: str
    labels: List[str] = []
    partners: List[str] = []  # Usernames or IDs


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
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Playlist(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str
    video_ids: List[str] = []
    owner_type: Literal["user", "team"] = "user"
    owner_id: Optional[PyObjectId] = None  # will be filled in route if not provided
    team_id: Optional[PyObjectId] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
