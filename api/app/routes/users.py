from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from ..db import db
from ..routes.auth import auth_scheme_optional
from ..utils import convert_objectid

router = APIRouter()


@router.get("/users")
async def get_users(
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    projection = {"_id": 1, "username": 1, "team_ids": 1}
    users = await db.users.find({}, projection).to_list(length=None)
    return convert_objectid(users)
