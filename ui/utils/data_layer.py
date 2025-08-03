import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from bson import ObjectId
from bunnet import Document, init_bunnet
from dotenv import load_dotenv
from pydantic import Field, GetCoreSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")


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


def to_dicts(docs: list[Document]) -> list[dict]:
    return [doc.model_dump(by_alias=True) for doc in docs]


def load_cliplist():
    print("Loading cliplists from database...")
    cliplists = Cliplist.find_all().run()
    return to_dicts(cliplists)
