from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.security import HTTPAuthorizationCredentials

from ..db import db
from ..emailer import send_feedback_email
from ..models import Feedback
from ..routes.auth import auth_scheme_optional

router = APIRouter()


@router.post("/feedback", status_code=202)
async def receive_feedback(
    feedback: Feedback,
    background_tasks: BackgroundTasks,
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    await db.feedback.insert_one(feedback.dict(by_alias=True))
    background_tasks.add_task(send_feedback_email, feedback.dict())
    return {"status": "received"}
