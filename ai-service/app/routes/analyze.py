import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.schemas.response_schema import (
    AnalyzeResponse,
    ComplianceFlags,
    DocumentMetadata,
    FinancialSignals,
    FraudDetection,
    ProcessingMetrics,
    SecurityValidation,
    Statistics,
    Transaction,
)
from app.services.document import PDFProcessor, PatternDetector, TextCleaner, TextStore
from app.services.fraud import RiskAnalysisService
from app.utils.file_handler import FileHandler, FileValidator, MalwareScanService
from app.utils.logging import (
    PerformanceTimer,
    api_logger,
    log_error,
    log_file_upload,
    log_security_validation,
    request_id_var,
)

router = APIRouter(prefix="", tags=["analysis"])


def cleanup_background(file_path: Path | None):
    """Background task to cleanup temp files"""
    if file_path:
        FileHandler.cleanup_temp_file(file_path)
        api_logger.info(f"Background cleanup completed for temp file")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Analyze uploaded PDF file with comprehensive security and financial pattern detection.
    
    Features:
    -  Multi-layer security validation (extension, magic bytes, content-type)
    -  Malware scanning hook (placeholder for production)
    -  Streaming upload with size limits (30MB default)
    -  Hybrid text extraction (native + OCR fallback)
    -  Advanced financial pattern detection (currencies, dates, PAN, GSTIN)
    -  Compliance risk flagging
    -  Structured logging and observability
    -  Performance metrics tracking
    
    Args:
        file: PDF file upload (max 30MB)
        background_tasks: FastAPI background tasks for cleanup
    
    Returns:
        Structured AnalyzeResponse with metadata, statistics, financial signals, compliance flags
    
    Raises:
        400: Invalid file type, missing file, or security validation failure
        413: File exceeds size limit
        500: Processing error
    """
    # Set request ID for distributed tracing
    req_id = str(uuid.uuid4())[:8]
    request_id_var.set(req_id)
    
    start_time = time.time()
    temp_path: Path | None = None

    try:
        api_logger.info(
            f"Received upload request",
            filename=file.filename,
            content_type=file.content_type
        )
        
        # Validate file extension
        if not FileValidator.validate_pdf_extension(file.filename):
            api_logger.warning("Invalid file extension", filename=file.filename)
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported. File must have .pdf extension.",
            )

        # Validate content type
        if not FileValidator.validate_content_type(file.content_type):
            api_logger.warning(
                "Invalid content type",
                filename=file.filename,
                content_type=file.content_type
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}. Expected application/pdf.",
            )

        # Stream file to temp location with size validation
        with PerformanceTimer(api_logger, "File upload streaming"):
            temp_path, bytes_written = await FileHandler.read_upload_to_temp(
                file,
                size_limit_mb=FileHandler.MAX_FILE_SIZE_MB,
            )

        # Validate PDF magic bytes (prevents .exe renamed to .pdf)
        if not FileValidator.validate_pdf_magic_bytes(temp_path):
            api_logger.error(
                "PDF magic bytes validation failed - possible file disguise attack",
                filename=file.filename
            )
            raise HTTPException(
                status_code=400,
                detail="File is not a valid PDF. Magic bytes validation failed.",
            )

        # Compute file hash for audit trail
        file_hash = FileValidator.compute_file_hash(temp_path)

        # Malware scan (placeholder - integrate real scanner in production)
        malware_scan_result = await MalwareScanService.scan_file(temp_path)
        if not malware_scan_result["clean"]:
            api_logger.error(
                "Malware detected in uploaded file",
                filename=file.filename,
                threats=malware_scan_result["threats_detected"]
            )
            raise HTTPException(
                status_code=400,
                detail="File failed malware scan. Upload rejected.",
            )

        security_validation = SecurityValidation(
            extension_valid=True,
            magic_bytes_valid=True,
            content_type_valid=True,
            malware_scan_result=malware_scan_result,
        )

        log_security_validation(file.filename, {
            "hash": file_hash[:16],
            "size_mb": f"{bytes_written / (1024*1024):.2f}",
            "malware_clean": malware_scan_result["clean"]
        })

        
        # Extract text from PDF (page-by-page, OCR fallback)
        with PerformanceTimer(api_logger, "PDF text extraction"):
            processor = PDFProcessor()
            extracted = processor.extract_text(temp_path)

        #TEXT CLEANING 
        with PerformanceTimer(api_logger, "Text cleaning"):
            cleaned_text = TextCleaner.clean(extracted.extracted_text)
        
        with PerformanceTimer(api_logger, "Pattern detection"):
            # Financial patterns
            currencies = PatternDetector.detect_currencies(cleaned_text)
            percentages = PatternDetector.detect_percentages(cleaned_text)
            large_numbers = PatternDetector.detect_large_numbers(cleaned_text)
            dates = PatternDetector.detect_dates(cleaned_text)
            emails = PatternDetector.detect_email_addresses(cleaned_text)
            phones = PatternDetector.detect_phone_numbers(cleaned_text)

            # Compliance patterns
            pan_numbers = PatternDetector.detect_pan_numbers(cleaned_text)
            gstin_numbers = PatternDetector.detect_gstin_numbers(cleaned_text)
            account_numbers = PatternDetector.detect_account_numbers(cleaned_text)

            # Determine risk level
            contains_sensitive = len(pan_numbers) > 0 or account_numbers > 0
            if account_numbers > 5 or len(pan_numbers) > 3:
                risk_level = "high"
            elif account_numbers > 0 or len(pan_numbers) > 0:
                risk_level = "medium"
            else:
                risk_level = "low"

            api_logger.info(
                "Pattern detection completed",
                currencies=currencies,
                percentages=percentages,
                dates=dates,
                risk_level=risk_level
            )

        # FRAUD DETECTION - AI-powered transaction analysis
        fraud_detection_result = None
        try:
            with PerformanceTimer(api_logger, "Fraud detection"):
                fraud_result = RiskAnalysisService.analyze_text(
                    cleaned_text=cleaned_text,
                    document_name=file.filename,
                    document_insights={
                        "pages": extracted.pages,
                        "ocr_pages": extracted.ocr_pages_count,
                    },
                )

                if fraud_result:
                    transactions = fraud_result["transactions"]
                    api_logger.info(f"Extracted {len(transactions)} transactions for fraud analysis")

                    fraud_detection_result = FraudDetection(
                        transactions_extracted=len(transactions),
                        transactions=[Transaction(**txn) for txn in transactions[:10]],  # First 10
                        fraud_score=float(fraud_result["fraud_score"]),
                        combined_score=float(fraud_result["combined_score"]),
                        anomaly_score=float(fraud_result["anomaly_score"]),
                        model_is_fraud=bool(fraud_result["model_is_fraud"]),
                        ml_risk_level=str(fraud_result["model_risk_level"]),
                        is_fraud=bool(fraud_result["is_fraud"]),
                        final_risk_level=str(fraud_result["final_risk_level"]),
                        high_risk_features=list(fraud_result["reasons"]),
                    )

                    api_logger.info(
                        "Fraud detection completed",
                        transactions=len(transactions),
                        fraud_score=fraud_result["fraud_score"],
                        combined_score=fraud_result["combined_score"],
                        model_risk=fraud_result["model_risk_level"],
                        hybrid_risk=fraud_result["hybrid_risk_level"],
                        final_risk=fraud_result["final_risk_level"],
                    )
                else:
                    api_logger.info("No transactions detected in document")
        except Exception as fraud_error:
            # Non-fatal: continue analysis even if fraud detection fails
            api_logger.error(f"Fraud detection failed (non-fatal): {fraud_error}")

        # STATISTICS CALCULATION       
        word_count = TextCleaner.word_count(cleaned_text)
        character_count = len(cleaned_text)
        line_count = cleaned_text.count("\n") + 1
        avg_words_per_page = word_count / extracted.pages if extracted.pages > 0 else 0

        # STORAGE        
        store = TextStore()
        storage_ref = store.save(file.filename, cleaned_text)

        # RAG INDEXING - Index document for question answering
        try:
            from app.services.rag.rag_pipeline import RAGPipeline
            from app.config.rag_config import get_rag_config
            
            # Get document ID from storage ref (unique file identifier)
            document_id = storage_ref.id
            
            api_logger.info(f"Indexing document for RAG: {document_id}")
            
            # Initialize RAG pipeline and index document
            rag_config = get_rag_config()
            rag_pipeline = RAGPipeline(rag_config)
            
            index_result = rag_pipeline.index_document(
                text=cleaned_text,
                document_id=document_id,
                page_ranges=extracted.page_ranges,
                force_reindex=True
            )
            
            api_logger.info(f"Document indexed successfully: {document_id}, chunks: {index_result.get('chunks_created', 'N/A')}")
        except Exception as index_error:
            # Don't fail analysis if indexing fails
            api_logger.error(f"RAG indexing failed (non-fatal): {index_error}")

        log_file_upload(file.filename, bytes_written, file_hash)
        
        # Schedule temp file cleanup as background task (non-blocking)
        background_tasks.add_task(cleanup_background, temp_path)
        temp_path = None  # Prevent cleanup in finally block

        
        processing_time = time.time() - start_time

        api_logger.info(
            "PDF analysis completed successfully",
            filename=file.filename,
            pages=extracted.pages,
            word_count=word_count,
            processing_time=f"{processing_time:.2f}s",
            ocr_pages=extracted.ocr_pages_count
        )
        
        return AnalyzeResponse(
            document_metadata=DocumentMetadata(
                filename=file.filename,
                file_size_bytes=bytes_written,
                file_hash=file_hash,
                pages=extracted.pages,
                upload_timestamp=datetime.utcnow().isoformat() + "Z",
                processing_time_seconds=round(processing_time, 2),
            ),
            statistics=Statistics(
                word_count=word_count,
                character_count=character_count,
                line_count=line_count,
                avg_words_per_page=round(avg_words_per_page, 2),
            ),
            financial_signals=FinancialSignals(
                currency_mentions=currencies,
                percentage_mentions=percentages,
                large_numbers=large_numbers,
                date_mentions=dates,
                email_addresses=emails,
                phone_numbers=phones,
            ),
            compliance_flags=ComplianceFlags(
                pan_numbers_detected=len(pan_numbers),
                gstin_numbers_detected=len(gstin_numbers),
                account_numbers_detected=account_numbers,
                contains_sensitive_data=contains_sensitive,
                risk_level=risk_level,
            ),
            fraud_detection=fraud_detection_result,
            processing_metrics=ProcessingMetrics(
                ocr_pages_processed=extracted.ocr_pages_count,
                ocr_used=extracted.ocr_pages_count > 0,
                malware_scanned=malware_scan_result["scanned"],
                malware_clean=malware_scan_result["clean"],
            ),
            security_validation=security_validation,
            sample_preview=cleaned_text[:500],
            full_text=cleaned_text,
            storage_ref=storage_ref,
        )

    except ValueError as exc:
        # File size limit exceeded
        log_error("File size validation", exc, {"filename": file.filename})
        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as exc:
        # Unexpected errors
        log_error("PDF analysis", exc, {"filename": file.filename})
        raise HTTPException(
            status_code=500,
            detail=f"PDF analysis failed: {str(exc)}",
        ) from exc
    
    finally:
        await file.close()
        # Cleanup temp file if not handed off to background task
        if temp_path:
            FileHandler.cleanup_temp_file(temp_path)
