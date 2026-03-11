# FinSight AI

Full-stack financial document analysis platform with authentication, PDF upload, RAG indexing, chat-based Q&A, fraud detection, and risk analysis.

## Stack

- **Frontend:** React 19 + Vite + Tailwind CSS (`frontend`, port `5173`)
- **Backend:** Node.js + Express + MongoDB (`backend`, port `5000`)
- **AI Service:** FastAPI + FAISS + HuggingFace + Groq (`ai-service`, port `8000`)

## Core Features

- **Document Upload & Chat** — Upload PDFs, auto-index via RAG, query documents through chat
- **Fraud Detection** — ML-based fraud classification on transaction data (CSV or PDF-extracted)
- **Risk Analysis** — End-to-end pipeline: PDF → transaction extraction → feature engineering → fraud scoring → risk explanation
- **Reports & Dashboards** — Visual risk analysis dashboards with charts and detailed reports
- **Role-Based Access** — Admin sees all documents; users see only their own uploads
- **Auth** — JWT-based signup/login with optional admin secret and "Remember Me" persistence

## Core Flow

1. User signs up / logs in
2. User uploads PDF
3. AI service extracts + indexes document for RAG
4. Chat queries retrieve only allowed documents
   - admin: all docs
   - user: only own uploads
5. Risk analysis can be triggered on uploaded financial PDFs
6. Fraud detection reports are generated with ML predictions and explanations

## Prerequisites

- Node.js 18+
- Python 3.10+
- MongoDB Atlas/local URI
- Groq API key

## Environment Variables

### backend/.env

```env
PORT=5000
MONGODB_URI=your_mongodb_connection_string
JWT_SECRET=your_jwt_secret
AI_SERVICE_URL=http://localhost:8000
ADMIN_SECRET_KEY=your_strong_admin_secret
```

### ai-service/.env

```env
GROQ_API_KEY=your_groq_api_key
```

## Run Locally

### 1) Backend

```bash
cd backend
npm install
npm start
```

### 2) AI Service

```bash
cd ai-service
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

## Important Behavior

- Remember Me:
	- checked → login persists (`localStorage`)
	- unchecked → session login only (`sessionStorage`)
- Admin creation:
	- no auto “first-user admin”
	- admin role only when signup includes correct `adminSecret`
- Chat document visibility:
	- enforced in backend routes using user role + document ownership

## Useful Endpoints

### Backend (Express)

- `POST /auth/register` — Register user (optional `adminSecret` for admin role)
- `POST /auth/login` — Authenticate user
- `POST /upload` — Upload PDF for processing
- `GET /query/documents` — List documents (role-filtered)
- `POST /query` — Query documents via RAG
- `POST /risk-analysis` — Trigger risk analysis pipeline
- `GET /health` — Health check

### AI Service (FastAPI)

- `POST /analyze` — Comprehensive PDF analysis (patterns, compliance, financial signals)
- `POST /risk-analysis` — PDF → transaction extraction → fraud detection → risk report
- `POST /fraud-detection` — Standalone CSV fraud detection
- `POST /query` — RAG document query
- `GET /query` — List indexed documents
- `GET /docs` — Swagger UI (`http://localhost:8000/docs`)

## AI Service Architecture

### Document Processing
- PDF extraction and parsing with OCR support
- Text cleaning, chunking, and pattern detection
- Financial signal and compliance flag identification

### RAG System
- FAISS vector database with `all-mpnet-base-v2` embeddings
- Semantic search with role-based document filtering
- Groq LLM for answer generation

### Fraud Detection Pipeline
- Transaction extraction from PDFs
- Feature engineering (time-based, amount-based, velocity features)
- ML classification with interpretable risk explanations
- LLM-enhanced report generation via Groq

### ML Model Training
- Training scripts in `ai-service/ml/`
- `train_model.py` — Base model training
- `train_model_engineered.py` — Training with engineered features
- Feature spec: `ai-service/models/feature_names_engineered.json`

### Tests
- `ai-service/tests/` — Unit tests for transaction extraction, feature engineering, inference, risk explanation, and report generation

## Notes

- `ai-service/scripts/example_rag_workflow.py` and `ai-service/scripts/evaluate_retrieval.py` are developer utilities (not required for runtime).

Create `.env` files for each service:

### Frontend `.env`
```env
VITE_API_URL=http://localhost:5000
VITE_AI_URL=http://localhost:8000
```

### Backend `.env`
```env
PORT=5000
AI_SERVICE_URL=http://localhost:8000
```

### AI Service `.env`
```env
PORT=8000
```

## 🤝 Contributing

This is a learning/demo project. Feel free to:
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is for educational purposes.

## 🎉 Acknowledgments

- React Team for React 19
- Tailwind Labs for Tailwind CSS
- Chart.js community
- FastAPI team

---

Built with ❤️ using React, Tailwind, and Chart.js
