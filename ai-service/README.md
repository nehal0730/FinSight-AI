---
title: FinSight AI Service
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# FinSight AI Service

FastAPI service for PDF analysis, fraud risk scoring, and RAG query.

## API

- `POST /analyze` - full PDF analysis + indexing + fraud section
- `POST /risk-analysis` - focused fraud/risk pipeline with report output
- `POST /query/query` - ask questions over indexed documents
- `GET /query/documents` - list indexed document IDs
- `GET /health` - service health

## Quick Start

```bash
cd ai-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:

```env
GROQ_API_KEY=your_groq_api_key
```

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger: `http://localhost:8000/docs`

## Hugging Face Spaces

Use the included `Dockerfile` in this folder and set these Space secrets/variables:

```env
GROQ_API_KEY=your_groq_api_key
MONGODB_URI=your_mongodb_connection_string
FRONTEND_URL=https://your-frontend-domain
BACKEND_URL=https://your-backend-domain
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

The service listens on port `7860` in Spaces. After a fresh deploy, re-upload documents so they are indexed with the current embedding model.
