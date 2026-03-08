import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.response_schema import RiskAnalysisResponse, Transaction
from app.services.document import PDFProcessor, TextCleaner
from app.services.fraud import RiskAnalysisService
from app.utils.file_handler import FileHandler, FileValidator, MalwareScanService
from app.utils.logging import api_logger, request_id_var

router = APIRouter(prefix="", tags=["risk-analysis"])


def cleanup_temp(file_path: Path | None):
    """Best-effort temporary file cleanup."""
    if file_path:
        FileHandler.cleanup_temp_file(file_path)


@router.post("/risk-analysis", response_model=RiskAnalysisResponse)
async def risk_analysis(file: UploadFile = File(...)):
    """Run the focused risk analysis pipeline on a PDF statement.

    Pipeline:
    PDF -> transaction extraction -> feature engineering -> ML fraud detection
    -> risk explanation -> report generation
    """
    req_id = str(uuid.uuid4())[:8]
    request_id_var.set(req_id)

    temp_path: Path | None = None

    try:
        if not FileValidator.validate_pdf_extension(file.filename):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        if not FileValidator.validate_content_type(file.content_type):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}. Expected application/pdf.",
            )

        temp_path, _bytes_written = await FileHandler.read_upload_to_temp(
            file,
            size_limit_mb=FileHandler.MAX_FILE_SIZE_MB,
        )

        if not FileValidator.validate_pdf_magic_bytes(temp_path):
            raise HTTPException(status_code=400, detail="File is not a valid PDF")

        malware_scan_result = await MalwareScanService.scan_file(temp_path)
        if not malware_scan_result["clean"]:
            raise HTTPException(status_code=400, detail="File failed malware scan")

        processor = PDFProcessor()
        extracted = processor.extract_text(temp_path)
        cleaned_text = TextCleaner.clean(extracted.extracted_text)

        result = RiskAnalysisService.analyze_text(
            cleaned_text=cleaned_text,
            document_name=file.filename,
            document_insights={
                "pages": extracted.pages,
                "ocr_pages": extracted.ocr_pages_count,
            },
        )

        if result is None:
            return RiskAnalysisResponse(
                risk_score=0.0,
                final_risk_level="LOW",
                reasons=["No transactions detected in the uploaded document."],
                transactions=[],
                fraud_score=0.0,
                anomaly_score=0.0,
                model_is_fraud=False,
                ml_risk_level="low",
                is_fraud=False,
                combined_score=0.0,
                transactions_extracted=0,
                report={
                    "document_name": file.filename,
                    "message": "No transactions detected for risk analysis.",
                },
            )

        risk_score = max(0.0, min(1.0, float(result["anomaly_score"])))

        return RiskAnalysisResponse(
            risk_score=round(risk_score, 4),
            final_risk_level=str(result["final_risk_level"]).upper(),
            reasons=list(result["reasons"]),
            transactions=[Transaction(**txn) for txn in result["transactions"][:10]],
            fraud_score=round(float(result["fraud_score"]), 2),
            anomaly_score=float(result["anomaly_score"]),
            model_is_fraud=bool(result["model_is_fraud"]),
            ml_risk_level=str(result["model_risk_level"]),
            is_fraud=bool(result["is_fraud"]),
            combined_score=round(float(result["combined_score"]), 2),
            transactions_extracted=len(result["transactions"]),
            report=result["report"],
        )

    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    except HTTPException:
        raise

    except Exception as exc:
        api_logger.error(f"Risk analysis failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {exc}") from exc

    finally:
        await file.close()
        cleanup_temp(temp_path)
