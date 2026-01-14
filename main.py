from fastapi import FastAPI, HTTPException, UploadFile, File
from database import users_collection, files_collection
from datetime import datetime, UTC
from pydantic import BaseModel
from bson import ObjectId

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class FileCreate(BaseModel):
    filename: str
    folder_path: str

app = FastAPI()
port = 8000

@app.get("/")
def root():
    return {"Hello" : "World"}

@app.get("/users")
async def list_users():
    users = []
    async for user in users_collection.find({}):
        users.append({
            "id": str(user["_id"]),
            "email": user.get("email"),
            "username": user.get("username"),
            "password": user.get("password")
        })
    return users

@app.post("/users")
async def create_user(user: UserCreate):
    existing = await users_collection.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    # NEED TO HASH PASSWORD ETC FOR AUTH

    result = await users_collection.insert_one({
        "email": user.email,
        "username": user.username,
        "password": user.password
    })
    
    return {"id": str(result.inserted_id), "username": user.username}

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await users_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"status": "success", "deleted_id": user_id}

@app.get("/files")
async def list_files():
    files = []
    async for file in files_collection.find({}):
        files.append({
            "id": str(file["_id"]),
            "filename": file.get("filename"),
            "content_type": file.get("content_type"),
            "owner_id": file.get("owner_id"),
            "folder_path": file.get("folder_path"),
            "minio_key": file.get("minio_key"),
            "upload_timestamp": file.get("upload_timestamp")
        })
    return files

@app.post("/user/{user_id}/files")
async def user_upload_file(user_id : str, folder_path: str, file : UploadFile = File(...)):
    try:
        owner_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    existing = await users_collection.find_one({"_id": owner_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = await files_collection.find_one({"folder_path": file.folder_path, 
                                                "owner_id": owner_id})
    if existing:
        raise HTTPException(status_code=400, detail="File has duplicate path")
    
    # ADD MINIO LOGIC 

    minio_key = "placeholder"

    result = await files_collection.insert_one({
        "filename": file.filename,
        "content_type": file.content_type,
        "owner_id": owner_id,
        "folder_path": folder_path,
        "minio_key": minio_key,
        "upload_timestamp": str(datetime.now(UTC))
    })

    return {"id": str(result.inserted_id), "filename": file.filename}