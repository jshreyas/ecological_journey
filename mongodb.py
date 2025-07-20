import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# uri = "mongodb+srv://shreyasjukanti:<db_password>@ecologicaljourney.fybtjh0.mongodb.net/?retryWrites=true&w=majority&appName=ecologicaljourney"
uri = os.getenv("MONGODB_URI")

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi("1"))

# Send a ping to confirm a successful connection
try:
    client.admin.command("ping")
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# from motor.motor_asyncio import AsyncIOMotorClient

# client = AsyncIOMotorClient(uri)
# db = client.get_default_database()
