import asyncio

import anyio
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from ..db import db
from ..models import Notion
from ..routes.auth import auth_scheme_optional
from ..utils.utils import convert_objectid
from ..utils.utils_notion import generate_tree

router = APIRouter()


@router.post("/notion")
async def save_notion(
    notion: Notion,
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    await db.notion.insert_one(notion.dict(by_alias=True))
    return {"status": "received"}


@router.post("/fetch_notion", status_code=202)
async def fetch_notion(_: HTTPAuthorizationCredentials = Depends(auth_scheme_optional)):
    asyncio.create_task(save_notion_tree())
    return {"status": "received"}


async def save_notion_tree():
    tree = await anyio.to_thread.run_sync(generate_tree)
    notion = Notion(tree=tree)
    await db.notion.insert_one(notion.dict(by_alias=True))


@router.get("/notion")
async def get_notion(
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    notion_doc = await db.notion.find_one(sort=[("submitted_at", -1)])
    if notion_doc:
        return convert_objectid(notion_doc)
    else:
        return {"status": "No notion documents found"}
