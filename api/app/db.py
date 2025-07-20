# ---------------- app/db.py ----------------
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

client: AsyncIOMotorClient = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["ecological_journey"]
