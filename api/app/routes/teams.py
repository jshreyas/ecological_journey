from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials

from ..db import db
from ..models import Team
from ..routes.auth import auth_scheme_optional, get_current_user
from ..utils.utils import convert_objectid

router = APIRouter()


async def get_teams_owned_by(user_id: str) -> list:
    return await db.teams.find({"owner_id": ObjectId(user_id)}).to_list(length=None)


async def get_teams_member_of(user_id: str) -> list:
    return await db.teams.find({"member_ids": ObjectId(user_id)}).to_list(length=None)


async def get_teams_for_user(user_id: str) -> dict:
    owned = await get_teams_owned_by(user_id)
    member = await get_teams_member_of(user_id)
    filtered_member = [team for team in member if team["_id"] not in {t["_id"] for t in owned}]
    return {"owned": owned, "member": filtered_member}


@router.get("/teams")
async def get_teams(
    user_id: Optional[str] = Query(None),
    filter: Literal["owned", "member", "all"] = "all",
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    if user_id:
        if filter == "owned":
            teams = await get_teams_owned_by(user_id)
        elif filter == "member":
            teams = await get_teams_member_of(user_id)
        else:
            teams = await get_teams_for_user(user_id)
    else:
        teams = await db.teams.find().to_list(length=None)
    return convert_objectid(teams)


@router.post("/teams")
async def create_team(team: Team, user=Depends(get_current_user)):
    team.owner_id = user["_id"]
    team.member_ids = [user["_id"]]
    result = await db.teams.insert_one(team.dict(by_alias=True))
    await db.users.update_one({"_id": user["_id"]}, {"$push": {"team_ids": result.inserted_id}})
    return {"id": str(result.inserted_id)}


@router.post("/teams/{team_id}/add_user/{user_id}")
async def add_user_to_team(team_id: str, user_id: str, user=Depends(get_current_user)):
    team = await db.teams.find_one({"_id": ObjectId(team_id)})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team["owner_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Only owner can add members")
    await db.teams.update_one({"_id": ObjectId(team_id)}, {"$addToSet": {"member_ids": ObjectId(user_id)}})
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"team_ids": ObjectId(team_id)}})
    return {"msg": "User added to team"}


@router.get("/teams/{team_id}/members")
async def get_team_members(team_id: str, user=Depends(get_current_user)):
    team = await db.teams.find_one({"_id": ObjectId(team_id)})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if user["_id"] not in team["member_ids"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    members = await db.users.find({"_id": {"$in": team["member_ids"]}}).to_list(length=None)
    return [{"id": str(m["_id"]), "email": m["email"], "username": m["username"]} for m in members]
