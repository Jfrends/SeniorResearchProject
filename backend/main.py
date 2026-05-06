from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from datetime import datetime, timezone
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
from elasticsearch import AsyncElasticsearch
from pdfminer.high_level import extract_text
from io import BytesIO
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

from .database import users_collection, files_collection
from .models import UserCreate, UserLogin, FolderCreate
from .auth import register_user_controller, login_user_controller, get_current_user

# ---------------- Elasticsearch ----------------

es = AsyncElasticsearch(
    hosts=[{"host": "localhost", "port": 9200, "scheme": "http"}],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not await es.ping():
        raise RuntimeError("Elasticsearch not reachable at http://localhost:9200")

    exists = await es.indices.exists(index="file_texts")
    if not exists:
        await es.indices.create(
            index="file_texts",
            mappings={
                "properties": {
                    "file_id": {"type": "keyword"},
                    "owner_id": {"type": "keyword"},
                    "filename": {"type": "keyword"},
                    "folder_path": {"type": "keyword"},
                    "text": {"type": "text"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384  # MiniLM-L6-v2 output size
                    },
                    "upload_timestamp": {"type": "date"}
                }
            }
        )
        print("Index 'file_texts' created!")
    else:
        print("Index 'file_texts' already exists")

    yield
    await es.close()

app = FastAPI(lifespan=lifespan)

# ---------------- CORS ----------------

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Text Extraction ----------------

async def extract_text_from_upload(upload_file: UploadFile) -> str:
    content = await upload_file.read()
    name = upload_file.filename.lower()

    if name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        return extract_text(BytesIO(content))

    return ""

# ---------------- Helpers ----------------

def serialize_file(file):
    return {
        "id": str(file["_id"]),
        "filename": file.get("filename"),
        "content_type": file.get("content_type"),
        "owner_id": str(file.get("owner_id")),
        "folder_path": file.get("folder_path"),
        "upload_timestamp": file.get("upload_timestamp"),
        "is_folder": file.get("is_folder", False),
    }

# ---------------- Root ----------------

@app.get("/")
def root():
    return {"Hello": "World"}

# ---------------- Users ----------------

@app.get("/users")
async def list_users():
    users = []
    async for user in users_collection.find({}):
        users.append({
            "id": str(user["_id"]),
            "email": user.get("email"),
            "username": user.get("username"),
        })
    return jsonable_encoder(users)

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

# ---------------- Files ----------------

@app.get("/files")
async def list_files():
    files = []
    async for file in files_collection.find({}):
        files.append(serialize_file(file))
    return jsonable_encoder(files)

@app.post("/users/{user_id}/files")
async def user_upload_file(user_id: str, path: str = Form(...), file: UploadFile = File(...)):
    try:
        owner_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    existing_user = await users_collection.find_one({"_id": owner_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    extracted_text = await extract_text_from_upload(file)
    embedding = get_embedding(extracted_text)

    result = await files_collection.insert_one({
        "filename": file.filename,
        "content_type": file.content_type,
        "owner_id": owner_id,
        "folder_path": path,
        "is_folder": False,
        "upload_timestamp": datetime.now(timezone.utc)
    })

    file_id = result.inserted_id

    await es.index(
        index="file_texts",
        id=str(file_id),
        document={
            "file_id": str(file_id),
            "owner_id": str(owner_id),
            "filename": file.filename,
            "folder_path": path,
            "text": extracted_text,
            "embedding": embedding,  # 👈 NEW
            "upload_timestamp": datetime.now(timezone.utc)
        }
    )

    return serialize_file(await files_collection.find_one({"_id": file_id}))

@app.get("/files/{file_id}/text", response_class=PlainTextResponse)
async def get_file_text(
    file_id: str, 
    current_user_id: str = Depends(get_current_user)  # <--- enforce auth
):
    try:
        result = await es.get(index="file_texts", id=file_id)
        file_owner_id = result["_source"]["owner_id"]
        if file_owner_id != current_user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        text = result["_source"]["text"]
    except Exception:
        raise HTTPException(status_code=404, detail="Text not found")

    return text


# ---------------- Folders ----------------

@app.post("/users/{user_id}/folders")
async def user_create_folder(user_id: str, folder: FolderCreate):
    try:
        owner_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    existing_user = await users_collection.find_one({"_id": owner_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_folder = await files_collection.find_one({
        "folder_path": folder.path,
        "filename": folder.filename,
        "owner_id": owner_id
    })
    if existing_folder:
        raise HTTPException(status_code=400, detail="Folder has duplicate path")

    result = await files_collection.insert_one({
        "filename": folder.filename,
        "owner_id": owner_id,
        "folder_path": folder.path,
        "is_folder": True,
        "upload_timestamp": datetime.now(timezone.utc)
    })

    return serialize_file(await files_collection.find_one({"_id": result.inserted_id}))

@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    try:
        f_id = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    await es.delete(index="file_texts", id=file_id, ignore=[404])

    result = await files_collection.delete_one({"_id": f_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "success", "deleted_id": file_id}

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    try:
        f_id = ObjectId(folder_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid folder ID")

    folder = await files_collection.find_one({"_id": f_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    files_inside = await files_collection.find_one({
        "folder_path": folder["folder_path"] + f"{folder['filename']}/"
    })
    if files_inside:
        raise HTTPException(status_code=400, detail="Folder not empty")

    result = await files_collection.delete_one({"_id": f_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Folder not deleted")
    return {"status": "success", "deleted_id": folder_id}

# ---------------- Auth ----------------

@app.post("/signup")
async def signup(user: UserCreate):
    return await register_user_controller(user)

@app.post("/login")
async def login(credentials: UserLogin):
    return await login_user_controller(credentials)

# ---------------- Search ----------------

def get_embedding(text: str):
    return model.encode(text).tolist()  # convert to list for ES

@app.get("/semantic-search")
async def semantic_search(query: str, current_path: str, owner_id: str):
    if not current_path.endswith("/"):
        current_path += "/"

    query_embedding = get_embedding(query)

    resp = await es.search(
        index="file_texts",
        size=20,
        query={
            "script_score": {
                "query": {
                    "bool": {
                        "filter": [
                            {"prefix": {"folder_path": current_path}},
                            {"term": {"owner_id": owner_id}}
                        ]
                    }
                },
                "script": {
                    "source": """
                        cosineSimilarity(params.query_vector, 'embedding') + 1.0
                    """,
                    "params": {
                        "query_vector": query_embedding
                    }
                }
            }
        }
    )

    return [
        {
            "file_id": hit["_source"]["file_id"],
            "filename": hit["_source"]["filename"],
            "folder_path": hit["_source"]["folder_path"],
            "score": hit["_score"]
        }
        for hit in resp["hits"]["hits"]
        if hit["_score"] > 1.2
    ]

# ---------------- LLM ----------------

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100):
    words = text.split()
    chunks = []

    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap

    return chunks
