# ---------------- app/main.py ----------------
from fastapi import FastAPI
from .routes import router
from fastapi.middleware.cors import CORSMiddleware

# Define security globally (optional)
app = FastAPI(
    title="My API",
    description="API with JWT Auth",
    security=[{"bearerAuth": []}]  # This adds the 'Authorization' input field in Swagger UI
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
