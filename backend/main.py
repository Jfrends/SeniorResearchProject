from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager

from datetime import datetime, timezone
from bson import ObjectId
from collections import defaultdict

from elasticsearch import AsyncElasticsearch
from pdfminer.high_level import extract_text
from io import BytesIO

from sentence_transformers import SentenceTransformer
import httpx

# ---------------- Models ----------------

from .models import UserLogin, UserCreate, FolderCreate


# ---------------- ML ----------------

model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str):
    return model.encode(text).tolist()


# ---------------- DB ----------------

from .database import users_collection, files_collection
from .auth import register_user_controller, login_user_controller, get_current_user


# ---------------- Elasticsearch ----------------

es = AsyncElasticsearch(
    hosts=[{"host": "localhost", "port": 9200, "scheme": "http"}],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not await es.ping():
        raise RuntimeError("Elasticsearch not reachable")

    exists = await es.indices.exists(index="file_texts")

    if not exists:
        await es.indices.create(
            index="file_texts",
            mappings={
                "properties": {
                    "file_id": {"type": "keyword"},
                    "chunk_id": {"type": "integer"},
                    "owner_id": {"type": "keyword"},
                    "filename": {"type": "keyword"},
                    "folder_path": {"type": "keyword"},
                    "text": {"type": "text"},
                    "embedding": {"type": "dense_vector", "dims": 384},
                    "upload_timestamp": {"type": "date"}
                }
            }
        )

    yield
    await es.close()


app = FastAPI(lifespan=lifespan)


# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Helpers ----------------

def chunk_text(text: str, chunk_size=500, overlap=100):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks


async def extract_text_from_upload(file: UploadFile):
    content = await file.read()
    name = file.filename.lower()

    if name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        return extract_text(BytesIO(content))

    return ""


# =========================================================
# AUTH ROUTES
# =========================================================

@app.post("/signup")
async def signup(user: UserCreate):
    return await register_user_controller(user)


@app.post("/login")
async def login(user: UserLogin):
    return await login_user_controller(user)


# =========================================================
# FILE LIST (USER-SCOPED FIX)
# =========================================================

@app.get("/files")
async def list_files(current_user_id: str = Depends(get_current_user)):
    files = []

    async for f in files_collection.find({"owner_id": ObjectId(current_user_id)}):
        files.append({
            "id": str(f["_id"]),
            "filename": f["filename"],
            "folder_path": f["folder_path"],
            "is_folder": f.get("is_folder", False),
        })

    return files


# =========================================================
# UPLOAD FILE (USER-SCOPED FIX)
# =========================================================

@app.post("/users/{user_id}/files")
async def upload_file(
    user_id: str,
    path: str = Form(...),
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user)
):
    if current_user_id != user_id:
        raise HTTPException(403, "Not allowed")

    owner_id = ObjectId(user_id)
    text = await extract_text_from_upload(file)

    file_doc = await files_collection.insert_one({
        "filename": file.filename,
        "owner_id": owner_id,
        "folder_path": path,
        "is_folder": False,
        "upload_timestamp": datetime.now(timezone.utc)
    })

    file_id = str(file_doc.inserted_id)

    for i, chunk in enumerate(chunk_text(text)):
        await es.index(
            index="file_texts",
            document={
                "file_id": file_id,
                "chunk_id": i,
                "owner_id": user_id,
                "filename": file.filename,
                "folder_path": path,
                "text": chunk,
                "embedding": get_embedding(chunk),
                "upload_timestamp": datetime.now(timezone.utc)
            }
        )

    return {"id": file_id, "filename": file.filename}


# =========================================================
# GET FILE TEXT (SECURED)
# =========================================================

@app.get("/files/{file_id}/text", response_class=PlainTextResponse)
async def get_file_text(file_id: str, current_user_id: str = Depends(get_current_user)):

    res = await es.search(
        index="file_texts",
        query={
            "bool": {
                "must": [
                    {"term": {"file_id": file_id}},
                    {"term": {"owner_id": current_user_id}}
                ]
            }
        },
        size=50
    )

    if not res["hits"]["hits"]:
        raise HTTPException(404, "Not found")

    return "\n".join([h["_source"]["text"] for h in res["hits"]["hits"]])


# =========================================================
# DELETE FILE (SECURED)
# =========================================================

@app.delete("/files/{file_id}")
async def delete_file(file_id: str, current_user_id: str = Depends(get_current_user)):

    oid = ObjectId(file_id)

    file = await files_collection.find_one({
        "_id": oid,
        "owner_id": ObjectId(current_user_id)
    })

    if not file:
        raise HTTPException(404, "File not found")

    await files_collection.delete_one({"_id": oid})

    await es.delete_by_query(
        index="file_texts",
        query={
            "bool": {
                "must": [
                    {"term": {"file_id": file_id}},
                    {"term": {"owner_id": current_user_id}}
                ]
            }
        }
    )

    return {"status": "deleted"}


# =========================================================
# SEMANTIC SEARCH (SECURED FIX)
# =========================================================

@app.get("/semantic-search")
async def semantic_search(
    query: str,
    current_path: str,
    owner_id: str
):

    # ensure folder path format
    if not current_path.endswith("/"):
        current_path += "/"

    # embed query
    query_vec = get_embedding(query)

    # elasticsearch search
    resp = await es.search(
        index="file_texts",
        size=50,
        query={
            "bool": {
                "filter": [
                    {"prefix": {"folder_path": current_path}},
                    {"term": {"owner_id": owner_id}}
                ],
                "must": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.q, 'embedding') + 1.0",
                            "params": {
                                "q": query_vec
                            }
                        }
                    }
                }
            }
        }
    )

    # ---------------- RELEVANCE THRESHOLD ----------------
    MIN_RELEVANCE_SCORE = 1.15

    files = defaultdict(lambda: {
        "file_id": None,
        "filename": None,
        "folder_path": None,
        "score": 0,
        "snippets": []
    })

    for hit in resp["hits"]["hits"]:
        score = hit["_score"]

        # HARD FILTER (this is the key change)
        if score < MIN_RELEVANCE_SCORE:
            continue

        src = hit["_source"]
        fid = src["file_id"]

        files[fid]["file_id"] = fid
        files[fid]["filename"] = src["filename"]
        files[fid]["folder_path"] = src["folder_path"]

        files[fid]["score"] = max(files[fid]["score"], score)

        if len(files[fid]["snippets"]) < 3:
            files[fid]["snippets"].append(src["text"])

    results = [
        f for f in files.values()
        if f["score"] >= MIN_RELEVANCE_SCORE and len(f["snippets"]) >= 1
    ]

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================================================
# ASK (SECURED FIX)
# =========================================================

@app.post("/ask")
async def ask(payload: dict, current_user_id: str = Depends(get_current_user)):

    query = payload["query"]
    current_path = payload["current_path"]

    if not current_path.endswith("/"):
        current_path += "/"

    query_vec = get_embedding(query)

    resp = await es.search(
        index="file_texts",
        size=20,
        query={
            "bool": {
                "filter": [
                    {"prefix": {"folder_path": current_path}},
                    {"term": {"owner_id": current_user_id}}
                ],
                "must": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.q, 'embedding') + 1.0",
                            "params": {"q": query_vec}
                        }
                    }
                }
            }
        }
    )

    context = "\n---\n".join(
        f"[{h['_source']['filename']}] {h['_source']['text'][:400]}"
        for h in resp["hits"]["hits"][:3]
    )

    prompt = f"""
Use only context.

{context}

QUESTION:
{query}

ANSWER:
"""

    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "phi3", "prompt": prompt, "stream": False}
        )

    return {
        "answer": res.json().get("response", ""),
        "sources": [
            {
                "file_id": h["_source"]["file_id"],
                "filename": h["_source"]["filename"]
            }
            for h in resp["hits"]["hits"][:3]
        ]
    }

# =========================================================
# CREATE FOLDER (SECURED)
# =========================================================

@app.post("/users/{user_id}/folders")
async def create_folder(
    user_id: str,
    folder: FolderCreate,
    current_user_id: str = Depends(get_current_user)
):

    # 🔒 prevent cross-user folder creation
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    owner_id = ObjectId(user_id)

    # verify user exists
    user = await users_collection.find_one({"_id": owner_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # check duplicate folder
    existing = await files_collection.find_one({
        "owner_id": owner_id,
        "folder_path": folder.path,
        "filename": folder.filename,
        "is_folder": True
    })

    if existing:
        raise HTTPException(status_code=400, detail="Folder already exists")

    # create folder
    result = await files_collection.insert_one({
        "filename": folder.filename,
        "owner_id": owner_id,
        "folder_path": folder.path,
        "is_folder": True,
        "upload_timestamp": datetime.now(timezone.utc)
    })

    return {
        "id": str(result.inserted_id),
        "filename": folder.filename
    }


# =========================================================
# DELETE FOLDER (SECURED)
# =========================================================

@app.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user_id: str = Depends(get_current_user)
):

    try:
        oid = ObjectId(folder_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid folder ID")

    folder = await files_collection.find_one({
        "_id": oid,
        "owner_id": ObjectId(current_user_id)
    })

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not folder.get("is_folder"):
        raise HTTPException(status_code=400, detail="Not a folder")

    # check if folder contains files
    prefix = folder["folder_path"] + folder["filename"] + "/"

    child = await files_collection.find_one({
        "owner_id": ObjectId(current_user_id),
        "folder_path": prefix
    })

    if child:
        raise HTTPException(status_code=400, detail="Folder not empty")

    await files_collection.delete_one({"_id": oid})

    return {"status": "deleted", "id": folder_id}