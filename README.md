# FinSight AI

Full-stack financial document analysis platform with authentication, PDF upload, RAG indexing, and chat-based Q&A.

## Stack

- Frontend: React + Vite (`frontend`, port `5173`)
- Backend: Node.js + Express + MongoDB (`backend`, port `5000`)
- AI Service: FastAPI + FAISS + HuggingFace + Groq (`ai-service`, port `8000`)

## Core Flow

1. User signs up / logs in
2. User uploads PDF
3. AI service extracts + indexes document for RAG
4. Chat queries retrieve only allowed documents
	 - admin: all docs
	 - user: only own uploads

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

- `POST /auth/register`
- `POST /auth/login`
- `POST /upload`
- `GET /query/documents`
- `POST /query`
- `GET http://localhost:8000/docs` (AI service Swagger)

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
