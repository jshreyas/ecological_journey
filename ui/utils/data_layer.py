import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from bson import ObjectId
from bunnet import Document, init_bunnet
from dotenv import load_dotenv
from pydantic import Field
from pymongo import MongoClient
from utils.cache import cache_result

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")


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


# Bunnet uses Pymongo client under the hood
client = MongoClient(MONGODB_URI)

# Initialize bunnet with the Product document class
init_bunnet(database=client.ecological_journey, document_models=[Cliplist])


def to_dicts(obj: Any) -> Any:
    # Case 1: Bunnet or Pydantic document
    if isinstance(obj, Document):
        return to_dicts(obj.model_dump(by_alias=True))

    # Case 2: ObjectId
    elif isinstance(obj, ObjectId):
        return str(obj)

    # Case 3: Dict (recursively process keys and values)
    elif isinstance(obj, dict):
        return {to_dicts(k): to_dicts(v) for k, v in obj.items()}

    # Case 4: List or tuple
    elif isinstance(obj, (list, tuple)):
        return [to_dicts(item) for item in obj]

    # Case 5: Anything else (primitive types, etc.)
    else:
        return obj


@cache_result("cliplists", ttl_seconds=3600)
def load_cliplists():
    print("Loading cliplists from database...")
    cliplists = Cliplist.find_all().run()
    return to_dicts(cliplists)


def load_cliplist(cliplist_id: str):
    for cliplist in load_cliplists():
        if cliplist.get("_id") == cliplist_id:
            return cliplist
    return None
