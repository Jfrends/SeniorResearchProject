# File Search System

## Overview
This project is a full-stack document management and AI-powered file search system. It allows users to upload files, organize them into folders, search semantically across content, and ask natural language questions over their documents using a local LLM.

The system is composed of:
- **Frontend:** React + Material UI
- **Backend:** FastAPI + MongoDB + Elasticsearch + SentenceTransformers + Ollama

---

# Backend

## Overview
The backend is built using **FastAPI** and integrates **MongoDB** for metadata storage and **Elasticsearch** for semantic search over document embeddings.

It supports:
- Authentication
- File/folder management
- Document ingestion pipeline
- Semantic search
- Retrieval-augmented generation (RAG) with a local LLM

---

## FastAPI

### Core Responsibilities
FastAPI serves as the main API layer and handles:
- User authentication (signup/login/delete)
- File and folder operations
- File upload and processing
- Semantic search over embeddings
- LLM-powered question answering

---

### File Upload Pipeline
When a file is uploaded:
1. Text is extracted (`pdfminer` or UTF-8 decoding)
2. Text is split into overlapping chunks
3. Each chunk is embedded using `all-MiniLM-L6-v2`
4. Chunks are stored in Elasticsearch with metadata

---

### Semantic Search
- Endpoint: `/semantic-search`
- Uses cosine similarity over embeddings via Elasticsearch `script_score`
- Filters by:
  - `owner_id`
  - `folder_path`
- Returns ranked files with representative text snippets

---

### Question Answering (/ask)
- Retrieves top matching document chunks from Elasticsearch
- Builds a context window
- Sends prompt to local LLM (Ollama `phi3`)
- Enforces strict grounding (answers only from provided context)
- Returns:
  - AI-generated answer
  - Source file references

---

### File & Folder Management
- `POST /users/{user_id}/files` → upload file
- `GET /files` → list files
- `DELETE /files/{file_id}` → delete file + embeddings
- `POST /users/{user_id}/folders` → create folder
- `DELETE /folders/{folder_id}` → delete folder (with safety checks)
- `GET /files/{file_id}/text` → retrieve raw file text

---

### User Management
- `POST /signup`
- `POST /login`
- `GET /users`
- `DELETE /users/{user_id}`

---

## Data Storage

### MongoDB
Stores:
- Users
- File metadata
- Folder structure

### Elasticsearch
Stores:
- Document chunks
- Embeddings (384-dim vectors)
- Metadata for filtering and search

---

## Machine Learning Components

### Embedding Model
- `all-MiniLM-L6-v2` (SentenceTransformers)
- Converts text into vector embeddings for semantic search

### LLM (Ollama)
- Model: `phi3`
- Runs locally via `http://localhost:11434/api/generate`
- Used for retrieval-augmented question answering

---

## System Flow (Backend)
1. File uploaded
2. Text extracted and chunked
3. Embeddings generated
4. Stored in MongoDB + Elasticsearch
5. Query arrives
6. Elasticsearch retrieves relevant chunks
7. LLM generates grounded response

---

# Frontend

## Overview
The frontend is built with **React** and **Material UI (MUI)**. It provides a file explorer interface with integrated semantic search and AI-powered document Q&A.

It connects to the backend to:
- Manage files and folders
- Upload and preview documents
- Perform semantic search
- Ask questions using AI

---

## Core Responsibilities
The frontend handles:
- File and folder navigation UI
- File uploads and deletions
- Folder creation and navigation
- Semantic search interface
- AI question answering interface
- File preview rendering

---

## Authentication
- Uses `AuthContext` for:
  - JWT token
  - User ID
- Redirects unauthenticated users to `/login`

---

## File Explorer

### File Listing
- Fetches files from `GET /files`
- Filters by current folder path (`currentPath`)
- Displays:
  - Files (document icon)
  - Folders (folder icon)

---

### Folder Navigation
- Supports hierarchical navigation using `currentPath`
- Features:
  - Enter folder
  - Back navigation
  - Path display

---

### File Upload
- Uses `POST /users/{userId}/files`
- Sends:
  - File (FormData)
  - Current folder path
- Displays upload progress state

---

### File Deletion
- Files: `DELETE /files/{fileId}`
- Folders: `DELETE /folders/{folderId}`
- Includes confirmation prompt before deletion

---

## File Preview
- Clicking a file fetches:
  - `GET /files/{fileId}/text`
- Displays extracted document content
- Shows loading state while fetching

---

## Folder Management
- Folder creation via modal UI
- Calls:
  - `POST /users/{userId}/folders`
- Prevents duplicates (backend enforced)

---

## Search & AI Features

### Semantic Search
- Endpoint: `GET /semantic-search`
- Parameters:
  - query
  - current_path
  - owner_id
- Displays ranked results based on semantic similarity

---

### Ask AI (RAG System)
- Endpoint: `POST /ask`
- Sends:
  - query
  - current_path
  - owner_id

#### Response
- AI-generated answer
- Source file references

---

## UI Layout

### Left Panel
- File/folder list
- Search results
- Loading indicators

### Right Panel
Displays:
- File preview OR
- AI answer with sources OR
- Empty state message

---

## State Management
Key React state variables:
- `files` → file list
- `currentPath` → active folder
- `selectedItem` → selected file/folder
- `fileText` → file preview content
- `searchQuery` → input text
- `searchResults` → semantic results
- `askAnswer` → AI response
- `askSources` → cited files
- loading states for async operations

---

## System Flow (Frontend)
1. User logs in
2. Files are fetched for current folder
3. User can:
   - Navigate folders
   - Upload files
   - Search semantically
   - Ask AI questions
4. UI dynamically switches between:
   - File browsing
   - Search results
   - AI response view

---

## Summary
This system combines a structured file management UI with a powerful backend search and LLM pipeline. Together, they enable:
- Organized document storage
- Semantic search over content
- AI-assisted document understanding
- A smooth, interactive file explorer experience