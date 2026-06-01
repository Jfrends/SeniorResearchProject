# File Search System

## Overview
This is a full-stack document management and AI search system that allows users to upload files, organize them into folders, search semantically, and ask natural language questions over their documents.

It is built with:
- **Frontend:** React + Material UI
- **Backend:** FastAPI + MongoDB + Elasticsearch + SentenceTransformers + Ollama (phi3)

---

# Backend

## Overview
The backend provides APIs for file management, semantic search, and LLM-based question answering over user documents.

---

## Core FastAPI Responsibilities
- User authentication (signup/login/delete)
- File and folder management
- File upload and text extraction
- Semantic search over embeddings
- AI question answering (RAG pipeline)

---

## File Processing Pipeline
1. Extract text from uploaded `.txt` or `.pdf`
2. Chunk text with overlap
3. Generate embeddings using `all-MiniLM-L6-v2`
4. Store metadata in MongoDB
5. Store chunks + embeddings in Elasticsearch

---

## Semantic Search
- Endpoint: `/semantic-search`
- Uses cosine similarity over embeddings
- Filters by user and folder path
- Returns ranked file snippets

---

## AI Question Answering (/ask)
- Retrieves relevant chunks from Elasticsearch
- Builds context window
- Sends to local LLM (Ollama phi3)
- Returns:
  - AI-generated answer
  - Source files

---

## Storage

### MongoDB
- Users
- File and folder metadata

### Elasticsearch
- Text chunks
- Vector embeddings (384-dim)
- Search + filtering support

---

## API Summary
- `POST /signup`, `POST /login`
- `GET /files`, `DELETE /files/{id}`
- `POST /users/{id}/files`
- `POST /users/{id}/folders`
- `DELETE /folders/{id}`
- `GET /files/{id}/text`
- `GET /semantic-search`
- `POST /ask`

---

## ML Components
- **Embeddings:** SentenceTransformers `all-MiniLM-L6-v2`
- **LLM:** Ollama `phi3` for contextual QA

---

# Frontend

## Overview
The frontend is a React + MUI interface for browsing files, searching content, and interacting with an AI assistant.

---

## Core Features
- File and folder navigation
- File upload and deletion
- File preview
- Semantic search
- AI question answering (RAG interface)

---

## File Explorer
- Displays files and folders based on current path
- Supports folder navigation (enter/back)
- Uploads files via API
- Deletes files and folders with confirmation

---

## File Preview
- Loads file text via `/files/{id}/text`
- Displays extracted document content in a preview panel

---

## Search & AI

### Semantic Search
- Queries `/semantic-search`
- Returns ranked document matches

### Ask AI
- Calls `/ask`
- Displays:
  - AI-generated answer
  - Source files used

---

## UI Layout
- **Left panel:** file/folder list + search results
- **Right panel:** file preview OR AI response

---

## State Management
Key state includes:
- Files + folders
- Current path
- Selected file
- Search query + results
- AI answer + sources
- Loading states

---

## System Flow
1. User uploads and organizes files
2. Backend extracts and embeds content
3. User searches or asks questions
4. Backend retrieves relevant context
5. LLM generates grounded responses
6. Frontend displays results or file previews

---

## Summary
This system combines structured file storage with semantic search and LLM-based Q&A, creating an interactive document assistant with both browsing and intelligent retrieval capabilities.