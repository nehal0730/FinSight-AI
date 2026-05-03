import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

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
async def risk_analysis(file: UploadFile = File(...), use_llm: bool = Form(False)):
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
            use_llm=use_llm,
        )

        if result is None:
            return RiskAnalysisResponse(
                risk_score=0.0,
                final_risk_level="LOW",
                is_fraud=False,
                reasons=["No transactions detected in the uploaded document."],
                transactions=[],
                transactions_extracted=0,
                report={
                    "document_name": file.filename,
                    "message": "No transactions detected for risk analysis.",
                },
                model_metadata={
                    "pipeline_version": "balanced-ml-rules-v1",
                    "scoring_method": "80% ML anomaly + 20% rule-based validation",
                    "model_source": "Kaggle creditcard dataset",
                    "expected_feature_count": 0,
                    "provided_feature_count": 0,
                    "feature_alignment_action": "none",
                },
            )

        # Use the pipeline's final, takeover-aware score/level when present
        final_score = round(
            max(float(result.get("combined_score", 0.0)), float(result.get("takeover_score", 0.0))),
            2,
        )
        final_risk_level = str(result.get("final_risk_level", result.get("hybrid_risk_level", "LOW"))).upper()
        final_is_fraud = bool(result.get("is_fraud", result.get("model_is_fraud", False)))

        return RiskAnalysisResponse(
            risk_score=final_score,
            final_risk_level=final_risk_level,
            is_fraud=final_is_fraud,
            reasons=list(result["reasons"]),
            transactions=[Transaction(**txn) for txn in result["transactions"][:10]],
            transactions_extracted=len(result["transactions"]),
            report=result["report"],
            model_metadata=result.get("model_metadata", {}),
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
