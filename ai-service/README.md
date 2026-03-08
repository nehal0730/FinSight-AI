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
