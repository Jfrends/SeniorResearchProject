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

from pydantic import BaseModel

class FolderCreate(BaseModel):
    filename: str
    path: str

class SearchRequest(BaseModel):
    query: str
    results: list


# ---------------- ML Model ----------------

model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str):
    return model.encode(text).tolist()


# ---------------- External LLM ----------------

OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "phi3"


# ---------------- DB placeholders ----------------
# (keep your existing Mongo collections)

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
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384
                    },
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


# ---------------- Health ----------------

@app.get("/")
def root():
    return {"status": "ok"}


# ---------------- USERS ----------------

@app.get("/users")
async def list_users():
    users = []
    async for u in users_collection.find({}):
        users.append({
            "id": str(u["_id"]),
            "email": u.get("email"),
            "username": u.get("username")
        })
    return jsonable_encoder(users)


@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(400, "Invalid user ID")

    res = await users_collection.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(404, "User not found")

    return {"status": "deleted"}


# ---------------- FILES ----------------

@app.get("/files")
async def list_files():
    files = []
    async for f in files_collection.find({}):
        files.append({
            "id": str(f["_id"]),
            "filename": f["filename"],
            "folder_path": f["folder_path"],
            "is_folder": f.get("is_folder", False),
        })
    return files


# ---------------- CREATE / DELETE FOLDER ----------------

@app.post("/users/{user_id}/folders")
async def create_folder(user_id: str, folder: FolderCreate):

    owner_id = ObjectId(user_id)

    user = await users_collection.find_one({"_id": owner_id})
    if not user:
        raise HTTPException(404, "User not found")

    existing = await files_collection.find_one({
        "owner_id": owner_id,
        "folder_path": folder.path,
        "filename": folder.filename,
        "is_folder": True
    })

    if existing:
        raise HTTPException(400, "Folder already exists")

    res = await files_collection.insert_one({
        "filename": folder.filename,
        "owner_id": owner_id,
        "folder_path": folder.path,
        "is_folder": True,
        "upload_timestamp": datetime.now(timezone.utc)
    })

    return {"id": str(res.inserted_id), "filename": folder.filename}

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):

    try:
        oid = ObjectId(folder_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid folder ID")

    folder = await files_collection.find_one({"_id": oid})

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not folder.get("is_folder"):
        raise HTTPException(status_code=400, detail="Not a folder")

    # check if folder contains files
    prefix = folder["folder_path"] + folder["filename"] + "/"

    child = await files_collection.find_one({
        "folder_path": prefix
    })

    if child:
        raise HTTPException(status_code=400, detail="Folder not empty")

    # delete folder metadata
    await files_collection.delete_one({"_id": oid})

    return {"status": "deleted", "id": folder_id}


# ---------------- UPLOAD / DELETE FILE ----------------

@app.post("/users/{user_id}/files")
async def upload_file(user_id: str, path: str = Form(...), file: UploadFile = File(...)):

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

    chunks = chunk_text(text)

    for i, chunk in enumerate(chunks):
        await es.index(
            index="file_texts",
            document={
                "file_id": file_id,
                "chunk_id": i,
                "owner_id": str(owner_id),
                "filename": file.filename,
                "folder_path": path,
                "text": chunk,
                "embedding": get_embedding(chunk),
                "upload_timestamp": datetime.now(timezone.utc)
            }
        )

    return {"id": file_id, "filename": file.filename}

@app.delete("/files/{file_id}")
async def delete_file(file_id: str):

    # validate ID
    try:
        oid = ObjectId(file_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    # check file exists
    file = await files_collection.find_one({"_id": oid})

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # delete from MongoDB
    await files_collection.delete_one({"_id": oid})

    # delete ALL chunks from Elasticsearch
    await es.delete_by_query(
        index="file_texts",
        query={
            "term": {
                "file_id": file_id
            }
        }
    )

    return {
        "status": "deleted",
        "file_id": file_id
    }


# ---------------- GET FILE TEXT ----------------

@app.get("/files/{file_id}/text", response_class=PlainTextResponse)
async def get_file_text(file_id: str, current_user_id: str = Depends(get_current_user)):

    res = await es.search(
        index="file_texts",
        query={"term": {"file_id": file_id}},
        size=50
    )

    if not res["hits"]["hits"]:
        raise HTTPException(404, "Not found")

    chunks = [h["_source"]["text"] for h in res["hits"]["hits"]]
    return "\n".join(chunks)


# ---------------- SEMANTIC SEARCH (FILES ONLY) ----------------

RELEVANCE_THRESHOLD = 1.15
MIN_SNIPPETS = 1

@app.get("/semantic-search")
async def semantic_search(query: str, current_path: str, owner_id: str):

    if not current_path.endswith("/"):
        current_path += "/"

    query_vec = get_embedding(query)

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
                            "params": {"q": query_vec}
                        }
                    }
                }
            }
        }
    )

    files = defaultdict(lambda: {
        "file_id": None,
        "filename": None,
        "folder_path": None,
        "score": 0,
        "snippets": []
    })

    for hit in resp["hits"]["hits"]:
        score = hit["_score"]

        if score < RELEVANCE_THRESHOLD:
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
        if f["score"] >= RELEVANCE_THRESHOLD and len(f["snippets"]) >= MIN_SNIPPETS
    ]

    return sorted(results, key=lambda x: x["score"], reverse=True)


# ---------------- LLM SUMMARIZER ----------------

import time
import httpx
from fastapi import HTTPException

@app.post("/ask")
async def ask(payload: dict):

    start = time.time()
    print("\n================ ASK START ================")

    query = payload["query"]
    current_path = payload["current_path"]
    owner_id = payload["owner_id"]

    print(f"[1] Query: {query}")
    print(f"[1] Path: {current_path}")
    print(f"[1] Owner: {owner_id}")

    if not current_path.endswith("/"):
        current_path += "/"

    # ---------------- embedding ----------------
    print("[2] Generating embedding...")
    t0 = time.time()
    query_vec = get_embedding(query)
    print(f"[2 DONE] embedding size={len(query_vec)} time={time.time() - t0:.3f}s")

    # ---------------- Elasticsearch ----------------
    print("[3] Running Elasticsearch search...")

    try:
        t1 = time.time()

        resp = await es.search(
            index="file_texts",
            size=20,
            request_timeout=30,
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
                                "params": {"q": query_vec}
                            }
                        }
                    }
                }
            }
        )

        print(f"[3 DONE] ES time={time.time() - t1:.3f}s")
        print(f"[3 DONE] hits={len(resp['hits']['hits'])}")

    except Exception as e:
        print("❌ Elasticsearch failed:", repr(e))
        raise HTTPException(500, "Elasticsearch error")

    # ---------------- context building ----------------
    print("[4] Building context...")

    context_blocks = []

    for i, hit in enumerate(resp["hits"]["hits"][:3]):
        src = hit["_source"]

        print(f"  - chunk {i} file={src['filename']} score={hit['_score']:.3f}")

        context_blocks.append(
        f"[{src['filename']}] {src['text'][:400]}"
)

    context = "\n---\n".join(context_blocks)

    print(f"[4 DONE] context length={len(context)} chars")

    # ---------------- prompt ----------------
    prompt = f"""
You are a document QA system.

Rules:
- Only use the context below
- If answer is not in context, say "I don't know based on your files"
- Be concise

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:
"""

    print("[5] Sending request to LLM...")

    # ---------------- LLM call ----------------
    try:
        t2 = time.time()

        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi3",
                    "prompt": prompt,
                    "stream": False
                }
            )

        print(f"[5 DONE] LLM time={time.time() - t2:.3f}s")

    except Exception as e:
        print("❌ LLM request failed:", repr(e))
        raise HTTPException(500, "LLM error")

    # ---------------- response ----------------
    print(f"[6] Total time={time.time() - start:.3f}s")
    print("================ ASK END ================\n")

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


# ---------------- AUTH ----------------

@app.post("/signup")
async def signup(user: dict):
    return await register_user_controller(user)


@app.post("/login")
async def login(user: dict):
    return await login_user_controller(user)