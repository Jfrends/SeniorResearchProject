# File Search System

## Backend
The backend was built using FastAPI, MongoDB, and Elasticsearch to support secure file storage, semantic search, and LLM-powered question answering over uploaded documents.

---

## FastAPI

### Core Responsibilities
FastAPI serves as the main application layer and handles:
- User authentication and management (signup, login, deletion)
- File and folder creation and organization
- File upload and processing pipeline
- Semantic search over document embeddings
- Retrieval-augmented question answering via an LLM (phi3 via Ollama)

---

### Key Features

#### File Upload & Processing
- Accepts `.txt` and `.pdf` files via multipart upload
- Extracts raw text using `pdfminer` for PDFs
- Splits documents into overlapping chunks
- Generates embeddings using `SentenceTransformer (all-MiniLM-L6-v2)`
- Stores metadata in MongoDB and chunk embeddings in Elasticsearch

---

#### Semantic Search
- Uses Elasticsearch `script_score` with cosine similarity over embeddings
- Filters results by:
  - User ID (`owner_id`)
  - Folder path (`current_path`)
- Returns ranked files with representative text snippets

---

#### Question Answering (/ask)
- Retrieves relevant document chunks from Elasticsearch
- Builds a context window from top matches
- Sends prompt to local LLM (Ollama phi3 model)
- Enforces strict grounding:
  - Answers must come only from retrieved context
  - Returns “I don’t know based on your files” if context is insufficient
- Outputs:
  - Generated answer
  - Source file references

---

## Data Storage

### MongoDB
Used for persistent metadata storage:
- User accounts
- File records
- Folder structure
- Ownership relationships

---

### Elasticsearch
Used for document retrieval and semantic search:
- Stores text chunks from uploaded files
- Stores vector embeddings (384-dim)
- Enables cosine similarity search via `script_score`
- Supports filtering by user and folder

---

## Machine Learning Components

### Embedding Model
- `all-MiniLM-L6-v2` from SentenceTransformers
- Converts document chunks and queries into vector embeddings

### LLM (Ollama)
- Model: `phi3`
- Runs locally via `http://localhost:11434/api/generate`
- Used for contextual question answering over retrieved documents

---

## API Summary

### User Routes
- `POST /signup` → create user
- `POST /login` → authenticate user
- `GET /users` → list users
- `DELETE /users/{user_id}` → delete user

---

### File & Folder Routes
- `POST /users/{user_id}/files` → upload file
- `GET /files` → list files
- `DELETE /files/{file_id}` → delete file + embeddings
- `POST /users/{user_id}/folders` → create folder
- `DELETE /folders/{folder_id}` → delete folder
- `GET /files/{file_id}/text` → retrieve full file text

---

### Search & QA Routes
- `GET /semantic-search` → semantic file search
- `POST /ask` → LLM-powered question answering over files

---

## System Flow

1. User uploads a file
2. Backend extracts and chunks text
3. Embeddings are generated
4. Data is stored in MongoDB + Elasticsearch
5. User queries system
6. Elasticsearch retrieves relevant chunks
7. LLM generates grounded answer