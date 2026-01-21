# FinSight AI 📊

An AI-powered financial document analysis platform that provides risk assessment, insights, and intelligent recommendations.

![Phase 1 Complete](https://img.shields.io/badge/Phase%201-Complete-brightgreen)
![React](https://img.shields.io/badge/React-19.2.0-blue)
![Tailwind](https://img.shields.io/badge/Tailwind-CSS-06B6D4)
![Node.js](https://img.shields.io/badge/Node.js-Backend-green)

## 🎯 Project Overview

FinSight AI analyzes financial documents (PDFs) and provides:
- **Risk Assessment** with detailed scoring
- **AI-Powered Insights** and recommendations
- **Interactive Dashboards** with beautiful visualizations
- **Real-time Chat** with AI assistant
- **Historical Reports** tracking

## ✨ Phase 1 - COMPLETE!

### Features Implemented

✅ **Authentication**
- Login/Signup pages with validation
- Session management

✅ **Document Upload**
- Drag & drop interface
- Progress bar
- File validation (PDF, max 50MB)
- Real-time feedback

✅ **Analysis Dashboard**
- Risk score meter (0-100) with color coding
- Key metrics cards (Revenue, Expenses, Profit)
- Interactive charts (Line, Bar, Doughnut)
- Risk factor breakdown
- AI-generated insights

✅ **Chat Interface**
- Real-time AI assistant
- Contextual responses
- Quick question buttons
- Typing indicators
- Message history

✅ **Reports Page**
- Historical analysis reports
- Export functionality (PDF/Excel)
- Summary statistics
- Report details view

✅ **Responsive Design**
- Mobile, Tablet, Desktop optimized
- Modern UI with Tailwind CSS
- Smooth animations

## 🚀 Quick Start

### Prerequisites
- Node.js (v16+)
- npm or yarn
- Python 3.8+ (for AI service)

### Option 1: Automated Start (Windows)
```bash
start-frontend.bat
```

### Option 2: Manual Start

#### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: `http://localhost:5173`

#### Backend
```bash
cd backend
npm install
npm start
```
Backend runs at: `http://localhost:5000`

#### AI Service
```bash
cd ai-service
myenv\Scripts\activate  # Windows
# or
source myenv/bin/activate  # Linux/Mac

python main.py
```
AI Service runs at: `http://localhost:8000`

## 📁 Project Structure

```
FinSight/
├── frontend/                  # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/       # Reusable components
│   │   │   └── Navbar.jsx
│   │   ├── pages/            # Page components
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Signup.jsx
│   │   │   ├── Upload.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Chat.jsx
│   │   │   └── Reports.jsx
│   │   ├── App.jsx           # Router setup
│   │   └── index.css         # Tailwind styles
│   ├── PHASE1_COMPLETE.md    # Phase 1 summary
│   └── PHASE1_GUIDE.md       # Installation guide
│
├── backend/                   # Node.js + Express
│   ├── src/
│   │   ├── routes/
│   │   ├── middleware/
│   │   └── app.js
│   └── uploads/              # Uploaded files
│
├── ai-service/               # Python + FastAPI
│   ├── main.py
│   └── myenv/                # Virtual environment
│
└── README.md                 # This file
```

## 🎨 Tech Stack

### Frontend
- **React 19.2.0** - UI framework
- **React Router DOM** - Routing
- **Tailwind CSS** - Styling
- **Chart.js** - Data visualization
- **Axios** - HTTP client
- **Vite** - Build tool

### Backend
- **Node.js** - Runtime
- **Express.js** - Web framework
- **Multer** - File upload handling

### AI Service
- **Python** - Language
- **FastAPI** - API framework
- **PyPDF2** - PDF processing

## 📱 Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Home | Landing page with features |
| `/login` | Login | User authentication |
| `/signup` | Signup | User registration |
| `/upload` | Upload | Document upload interface |
| `/dashboard` | Dashboard | Analysis results & charts |
| `/chat` | Chat | AI assistant interface |
| `/reports` | Reports | Historical reports |

## 🎯 User Flow

1. **Landing** → View features on home page
2. **Sign Up/Login** → Create account or login
3. **Upload** → Drop PDF document
4. **Analysis** → Wait for AI processing (with progress bar)
5. **Dashboard** → View risk scores and insights
6. **Chat** → Ask questions about analysis
7. **Reports** → Access historical analyses

## 🎨 Design System

### Colors
- **Primary**: Indigo `#4F46E5` - Trust & professionalism
- **Secondary**: Green `#10B981` - Growth & success
- **Danger**: Red `#EF4444` - High risk alerts
- **Warning**: Amber `#F59E0B` - Medium risk

### Components
- Cards with subtle shadows
- Rounded corners (8px, 12px)
- Smooth transitions (200ms)
- Hover effects on interactive elements

## 📊 Demo Mode

Phase 1 uses **dummy data** for demonstration:
- Login works with any credentials
- Upload connects to backend
- Dashboard shows sample analysis
- Chat provides contextual responses
- Reports display historical data

## 🔜 Next Phases

### Phase 2 - Backend Integration (Week 2)
- Real authentication with JWT
- Database integration (MongoDB/PostgreSQL)
- File processing pipeline
- API endpoints

### Phase 3 - AI Implementation (Week 3-4)
- LangChain integration
- Document analysis
- Risk calculation algorithms
- NLP for chat responses

### Phase 4 - Production (Week 5-6)
- Real-time features
- Email notifications
- Advanced analytics
- Deployment

## 📚 Documentation

- [Phase 1 Complete Guide](frontend/PHASE1_COMPLETE.md) - What's been built
- [Phase 1 Installation](frontend/PHASE1_GUIDE.md) - Setup instructions

## 🛠️ Development

### Available Scripts

#### Frontend
```bash
npm run dev      # Start dev server
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

#### Backend
```bash
npm start        # Start server
npm run dev      # Start with nodemon
```

## 🐛 Troubleshooting

### Frontend not starting?
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Tailwind styles not working?
Restart the dev server: `Ctrl+C` then `npm run dev`

### Charts not displaying?
```bash
npm install chart.js react-chartjs-2
```

## 📝 Environment Variables

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

**Phase 1 Status**: ✅ **COMPLETE & DEMO-READY**

Built with ❤️ using React, Tailwind, and Chart.js
