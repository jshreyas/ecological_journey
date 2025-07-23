import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .routes import router

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

app.include_router(router)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("JWT_SECRET"))
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["ecological-journey-api.duckdns.org", "*.duckdns.org"])
app.add_middleware(ProxyHeadersMiddleware)
