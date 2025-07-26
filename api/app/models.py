# app/models.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, GetCoreSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: core_schema.CoreSchema, handler: Any) -> JsonSchemaValue:
        return {"type": "string"}

    @classmethod
    def validate(cls, v: Any) -> "PyObjectId":
        if isinstance(v, ObjectId):
            return cls(str(v))
        if ObjectId.is_valid(v):
            return cls(v)
        raise ValueError("Invalid ObjectId")


class RegisterUser(BaseModel):
    username: str
    email: EmailStr
    password: str  # raw password input from client


class User(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    username: str
    email: EmailStr
    hashed_password: str
    team_ids: List[PyObjectId] = []
    oauth_provider: Optional[str] = None
    oauth_sub: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Team(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str
    owner_id: Optional[PyObjectId] = None  # will be filled in route if not provided
    member_ids: List[PyObjectId] = []

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


class Notion(BaseModel):
    tree: List[TreeNode]
    submitted_at: datetime = datetime.utcnow()


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
