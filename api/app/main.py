import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .routes.auth import router as auth_router
from .routes.cliplists import router as cliplists_router
from .routes.feedback import router as feedback_router
from .routes.notion import router as notion_router
from .routes.playlists import router as playlists_router
from .routes.teams import router as teams_router
from .routes.users import router as users_router

load_dotenv()

app = FastAPI(
    title="Ecological Journey API",
    description="Video and Clip management with team-scoped access",
    security=[{"bearerAuth": []}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(teams_router)
app.include_router(playlists_router)
app.include_router(cliplists_router)
app.include_router(feedback_router)
app.include_router(notion_router)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("JWT_SECRET"))
if os.environ.get("ENVIRONMENT") == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["ecological-journey-api.duckdns.org", "*.duckdns.org"])
