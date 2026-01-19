import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()  # loads .env

MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["seniorproject_db"]

# Access collections
users_collection = db["users"]
files_collection = db["files"]

def serialize_user(user):
    user["id"] = str(user["_id"])
    del user["_id"]
    return user