from fastapi import FastAPI, HTTPException, UploadFile, File
from database import users_collection, files_collection
from datetime import datetime, timezone
from pydantic import BaseModel
from bson import ObjectId

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class FolderCreate(BaseModel):
    path: str
    filename: str

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

@app.post("/users/{user_id}/files")
async def user_upload_file(user_id : str, path: str, file : UploadFile = File(...)):
    try:
        owner_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    existing = await users_collection.find_one({"_id": owner_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = await files_collection.find_one({"folder_path": path,
                                                "filename": file.filename,
                                                "owner_id": owner_id})
    if existing:
        raise HTTPException(status_code=400, detail="File has duplicate path")
    
    # ADD MINIO LOGIC 

    minio_key = "placeholder"

    result = await files_collection.insert_one({
        "filename": file.filename,
        "content_type": file.content_type,
        "owner_id": owner_id,
        "folder_path": path,
        "minio_key": minio_key,
        "is_folder": False,
        "upload_timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"id": str(result.inserted_id), "filename": file.filename}

@app.post("/users/{user_id}/folders")
async def user_create_folder(user_id : str, folder: FolderCreate):
    try:
        owner_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    existing = await users_collection.find_one({"_id": owner_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = await files_collection.find_one({"folder_path": folder.path, 
                                                "filename": folder.filename,
                                                "owner_id": owner_id})
    if existing:
        raise HTTPException(status_code=400, detail="Folder has duplicate path")

    result = await files_collection.insert_one({
        "filename": folder.filename,
        "owner_id": owner_id,
        "folder_path": folder.path,
        "is_folder": True,
        "upload_timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"id": str(result.inserted_id), "filename": folder.filename}

@app.delete("/files/{file_id}")
async def delete_file(file_id : str):
    try:
        f_id = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID")
    
    # ADD MINIO CLEANUP 

    result = await files_collection.delete_one({"_id": f_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"status": "success", "deleted_id": file_id}

@app.delete("/folders/{file_id}")
async def delete_folder(file_id : str):
    try:
        folder_id = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID")
    
    existing = await files_collection.find_one({"_id": folder_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Folder not found")
    else:
        files_inside = await files_collection.find_one({"folder_path": existing["folder_path"] + f"/{existing['filename']}/"})
        if files_inside:
            raise HTTPException(status_code=400, detail="Folder not empty")

    result = await files_collection.delete_one({"_id": folder_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"status": "success", "deleted_id": file_id}