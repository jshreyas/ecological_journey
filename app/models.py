# ---------------- app/models.py ----------------
from pydantic import BaseModel, Field
from typing import List, Optional

class Clip(BaseModel):
    start: int
    end: int
    type: str
    title: str
    description: str
    labels: List[str] = []
    partners: List[str] = []

class Video(BaseModel):
    video_id: str
    youtube_url: str
    title: str
    notes: Optional[str] = ""
    date: Optional[str] = ""
    type: Optional[str] = ""
    partners: List[str] = []
    duration_seconds: float
    positions: List[str] = []
    labels: List[str] = []
    clips: List[Clip] = []
