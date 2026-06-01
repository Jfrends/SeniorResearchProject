# File Search System — Setup Guide

This guide explains how to run the full File Search System locally, including the FastAPI backend, React frontend, MongoDB, Elasticsearch, and Ollama LLM.

---

# Prerequisites

Before starting, install:

- Python 3.10+
- Node.js 18+
- Docker (recommended)
- Git
- Ollama (for local LLM)

---

# Clone the Project

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

---

# Backend Setup (FastAPI)

## 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Mac/Linux
# venv\Scripts\activate    # Windows
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Start MongoDB + Elasticsearch

### Using Docker (recommended)

```bash
docker run -d -p 27017:27017 --name mongo mongo
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0
```

### OR install locally

- MongoDB: mongodb://localhost:27017  
- Elasticsearch: http://localhost:9200  

---

## 4. Run Backend Server

```bash
uvicorn main:app --reload
```

Backend runs at:
```
http://localhost:8000
```

---

# LLM Setup (Ollama)

## 1. Install Ollama
https://ollama.com

---

## 2. Pull Model

```bash
ollama pull phi3
```

---

## 3. Start Ollama Server

```bash
ollama serve
```

LLM runs at:
```
http://localhost:11434
```

---

# Frontend Setup (React)

## 1. Install Dependencies

```bash
cd frontend
npm install
```

---

## 2. Start Frontend

```bash
npm run dev
```

Frontend runs at:
```
http://localhost:5173
```

---

# Environment Variables

Create a `.env` file in the `frontend/` directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

# System Overview

## How the System Works

1. User uploads a file in the frontend
2. Backend extracts and chunks the text
3. Embeddings are generated using SentenceTransformers
4. Data is stored in:
   - MongoDB (metadata)
   - Elasticsearch (chunks + embeddings)
5. User queries the system:
   - Semantic search → retrieves similar chunks
   - Ask AI → uses retrieved context with Ollama LLM

---

# Ports

| Service        | Port |
|----------------|------|
| Frontend       | 5173 |
| Backend        | 8000 |
| MongoDB        | 27017 |
| Elasticsearch  | 9200 |
| Ollama         | 11434 |

---

# Common Issues

## Elasticsearch not starting
- Increase Docker memory (2–4GB minimum)

## Ollama errors
- Run `ollama serve`
- Ensure model is installed (`ollama pull phi3`)

## No search results
- Check Elasticsearch index: `file_texts`

---

# Done 🚀

Once everything is running:
- Upload files
- Search semantically
- Ask AI questions over your documents
```