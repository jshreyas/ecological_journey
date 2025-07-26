from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..db import db
from ..models import Cliplist
from ..routes.auth import auth_scheme_optional, get_current_user
from ..utils import convert_objectid

router = APIRouter()


async def get_cliplist_by_id(cliplist_id: str) -> dict:
    return await db.cliplists.find_one({"_id": cliplist_id})


async def insert_cliplist(cliplist: Cliplist):
    await db.cliplists.insert_one(cliplist.dict(by_alias=True))


async def update_cliplist(cliplist_id: str, cliplist_data: dict):
    await db.cliplists.update_one({"_id": cliplist_id}, {"$set": cliplist_data})


@router.get("/cliplists")
async def get_cliplists(
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    return convert_objectid(await db.cliplists.find().to_list(length=None))


@router.get("/cliplist/{cliplist_id}")
async def get_cliplist(cliplist_id: str, _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional)):
    cliplist = await get_cliplist_by_id(cliplist_id)
    if not cliplist:
        raise HTTPException(status_code=404, detail="Cliplist not found.")
    return convert_objectid(cliplist)


@router.post("/cliplist")
async def create_cliplist(
    cliplist: Cliplist,
    user=Depends(get_current_user),
):
    cliplist.owner_id = user["_id"]
    await insert_cliplist(cliplist)
    return {"msg": "Cliplist created successfully"}


@router.put("/cliplist/{cliplist_id}")
async def update_cliplist_filters(
    cliplist_id: str,
    cliplist: Cliplist,
    user=Depends(get_current_user),
):
    existing = await get_cliplist_by_id(cliplist_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cliplist not found.")

    if existing.get("owner_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied to update this cliplist.")

    await update_cliplist(cliplist_id, cliplist.dict(exclude={"id", "owner_id"}))
    return {"msg": "Cliplist updated successfully"}
