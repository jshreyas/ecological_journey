import os

from bunnet import init_bunnet
from data.models import Cliplist, Feedback, Learnings, Notion, Playlist, Team, User, Video
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")


# Bunnet uses Pymongo client under the hood
client = MongoClient(MONGODB_URI)

# Initialize bunnet with the Product document class
init_bunnet(
    database=client.ecological_journey,
    document_models=[Cliplist, Playlist, Video, Notion, Team, User, Feedback, Learnings],
)
