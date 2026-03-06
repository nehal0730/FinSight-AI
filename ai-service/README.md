# FinSight AI Service

FastAPI service for PDF analysis + RAG indexing/query.

## What it does

- `POST /analyze`: extract + clean PDF text and index it for retrieval
- `POST /query/query`: answer document-specific questions
- `GET /query/documents`: list indexed document IDs
- `GET /health`: health check

## Setup

```bash
cd ai-service
python -m venv .venv
.venv\Scripts\activate   # Windows
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

Docs: `http://localhost:8000/docs`

## Notes

- Uses HuggingFace embeddings + FAISS vector store (local)
- Uses Groq for answer generation
- Optional developer scripts in `scripts/`:
  - `example_rag_workflow.py` (smoke test)
  - `evaluate_retrieval.py` (retrieval metrics)

These scripts are not required for runtime.

MIT
