from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.get("/health")
def health():
    return {
        "status": "UP",
        "service": "AI Service",
    }

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...)):
    return {
        "success": True,
        "data": {
            "filename": file.filename,
            "message": "File received successfully"
        },
        "error": None
    }
