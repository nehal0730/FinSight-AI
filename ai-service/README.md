# FinSight AI Service - Phase 2

Production-grade FastAPI service for PDF document processing with text extraction, OCR, and financial pattern detection.

## Architecture

```
app/
├── main.py              # FastAPI application factory
├── routes/
│   └── analyze.py       # /analyze endpoint (PDF processing)
├── services/
│   ├── pdf_processor.py      # Core PDF text extraction
│   ├── ocr_service.py        # Tesseract OCR for scanned pages
│   ├── text_cleaner.py       # Text normalization and cleaning
│   ├── pattern_detector.py   # Financial pattern recognition
│   └── text_store.py         # Local text file storage
├── schemas/
│   └── response_schema.py    # Pydantic models for type safety
└── utils/
    └── file_handler.py       # File upload and validation
uploads/                 # Extracted text storage (auto-created)
requirements.txt         # Python dependencies
```

## Quick Start

### 1. Installation

```bash
cd ai-service
pip install -r requirements.txt
```

### 2. System Dependency: Tesseract OCR

**Windows:**
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Install to: `C:\Program Files\Tesseract-OCR`

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Run Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Open API Docs

Visit: `http://127.0.0.1:8000/docs`

Interactive Swagger UI to test endpoints with file uploads.

## API Endpoints

### GET /health

Server health check.

**Response:**
```json
{
  "status": "UP",
  "service": "AI Service",
  "phase": "phase-2-pdf-processing"
}
```

### POST /analyze

Analyze uploaded PDF file.

**Request:**
- File: PDF document (max 30MB)

**Response:**
```json
{
  "filename": "report.pdf",
  "pages": 12,
  "word_count": 5423,
  "currency_mentions": 18,
  "sample_preview": "Financial statement for Q4 2025...",
  "full_text": "Complete extracted text...",
  "storage_ref": {
    "id": "report_20260302154230_a3f8b21c",
    "path": "/app/uploads/extracted_text/report_20260302154230_a3f8b21c.txt"
  }
}
```

## Features

### PDF Text Extraction
- **Digital PDFs:** Fast native text extraction via pdfplumber
- **Scanned PDFs:** Automatic OCR fallback via Tesseract
- Smart threshold: Only runs OCR if native extraction yields < 25 words

### Text Processing
- Unicode normalization (NFKC)
- Line break standardization
- Whitespace normalization
- Empty line removal
- Paragraph preservation

### Pattern Detection
- **Currency Detection:** `$1,234.56`, `₹50,000`, `€1000`, `1234 USD`, `5000 INR`
- **Email Detection:** `user@example.com`
- **Phone Detection:** `(123) 456-7890`, `+1-234-567-8900`

### Safety
- 30MB file size limit (configurable)
- Chunked streaming upload validation
- Automatic temp file cleanup
- Comprehensive error handling

## Performance

| PDF Type | Pages | Time | Notes |
|----------|-------|------|-------|
| Digital | 10 | ~0.5s | Fast native extraction |
| Scanned | 10 | ~15s | OCR required per page |
| Mixed | 10 | ~5-10s | Adaptive OCR |

## Development

### Project Structure Rationale

- **Services:** Pure business logic, easily testable
- **Routes:** Thin HTTP layer, delegates to services
- **Schemas:** Pydantic models for type validation
- **Utils:** Shared utilities (file handling, validation)

### Key Classes

#### PDFProcessor
Orchestrates text extraction with OCR fallback.

```python
processor = PDFProcessor()
result = processor.extract_text(Path("document.pdf"))
```

#### TextCleaner
Normalizes and counts words.

```python
cleaned = TextCleaner.clean(raw_text)
word_count = TextCleaner.word_count(cleaned)
```

#### PatternDetector
Detects business patterns.

```python
currencies = PatternDetector.detect_currencies(text)
emails = PatternDetector.detect_email_addresses(text)
phones = PatternDetector.detect_phone_numbers(text)
```

#### TextStore
Saves extracted text locally.

```python
store = TextStore()
ref = store.save("document.pdf", cleaned_text)
# Returns: StorageRef(id="...", path="...")
```

#### FileHandler
Validates and streams uploads safely.

```python
temp_path, bytes_written = await FileHandler.read_upload_to_temp(file)
FileHandler.cleanup_temp_file(temp_path)
```

## Integration

### With Node.js Backend

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const form = new FormData();
form.append('file', fs.createReadStream('document.pdf'));

const response = await axios.post(
  'http://localhost:8000/analyze',
  form,
  { headers: form.getHeaders() }
);

console.log(response.data);
```

## Configuration

Edit `FileHandler.MAX_FILE_SIZE_MB` to change upload limit:

```python
# In app/utils/file_handler.py
MAX_FILE_SIZE_MB = 50  # Increase to 50MB
```

Edit `PDFProcessor` OCR threshold:

```python
# In app/routes/analyze.py
processor = PDFProcessor(ocr_threshold_words=50)  # Only OCR if < 50 words
```

## Troubleshooting

### ImportError: No module named 'pdfplumber'

```bash
pip install -r requirements.txt
```

### Tesseract not found

Install Tesseract OCR (see Quick Start section).

### File too large

Increase `FileHandler.MAX_FILE_SIZE_MB`.

### OCR returns garbled text

Increase OCR resolution in `app/services/ocr_service.py`:

```python
self.resolution = 400  # Higher resolution = better quality
```

## Phase 3: RAG Integration

This service is architecture-ready for Phase 3:

- ✅ Text stored locally with metadata
- ✅ Analytics pre-computed (word count, patterns)
- ✅ Modular structure (easy to add embedding service)
- ✅ Pydantic schemas (compatible with vector DB)

Next: Add vector embeddings and retrieval without refactoring core logic.

## License

MIT
