from typing import Any

from bson import ObjectId
from bunnet import Document
from data.models import Cliplist, Playlist
from utils.cache import cache_result


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


@cache_result("playlists", ttl_seconds=3600)
def load_playlists():
    print("Loading playlists from database...")
    playlists = Playlist.find_all().run()
    return to_dicts(playlists)


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
