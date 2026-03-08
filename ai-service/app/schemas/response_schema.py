from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StorageRef(BaseModel):
    """Reference to stored extracted text file"""
    id: str = Field(..., description="Unique file identifier")
    path: str = Field(..., description="Absolute path to stored text file")


class DocumentMetadata(BaseModel):
    """Document-level metadata"""
    filename: str = Field(..., description="Original uploaded filename")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    file_hash: str = Field(..., description="SHA256 hash for integrity verification")
    pages: int = Field(..., ge=1, description="Total number of pages")
    upload_timestamp: str = Field(..., description="ISO 8601 timestamp of upload")
    processing_time_seconds: float = Field(..., ge=0, description="Total processing time")


class Statistics(BaseModel):
    """Document text statistics"""
    word_count: int = Field(..., ge=0, description="Total word count")
    character_count: int = Field(..., ge=0, description="Total character count")
    line_count: int = Field(..., ge=0, description="Total line count")
    avg_words_per_page: float = Field(..., ge=0, description="Average words per page")


class FinancialSignals(BaseModel):
    """Detected financial patterns and indicators"""
    currency_mentions: int = Field(..., ge=0, description="Count of currency values (₹, $, etc.)")
    percentage_mentions: int = Field(..., ge=0, description="Count of percentage values")
    large_numbers: Dict[str, int] = Field(..., description="Crores, lakhs, millions, billions")
    date_mentions: int = Field(..., ge=0, description="Count of date occurrences")
    email_addresses: int = Field(..., ge=0, description="Count of email addresses")
    phone_numbers: int = Field(..., ge=0, description="Count of phone numbers")


class ComplianceFlags(BaseModel):
    """Compliance and risk indicators"""
    pan_numbers_detected: int = Field(..., ge=0, description="Count of Indian PAN numbers")
    gstin_numbers_detected: int = Field(..., ge=0, description="Count of GSTIN numbers")
    account_numbers_detected: int = Field(..., ge=0, description="Count of potential account numbers")
    contains_sensitive_data: bool = Field(..., description="True if PII/sensitive data found")
    risk_level: str = Field(..., description="Risk assessment: low, medium, high")


class Transaction(BaseModel):
    """Individual transaction record"""
    date: str = Field(..., description="Transaction date")
    amount: float = Field(..., ge=0, description="Transaction amount")
    type: str = Field(..., description="Transaction type: debit or credit")
    merchant: str = Field(..., description="Merchant or description")


class FraudDetection(BaseModel):
    """AI fraud detection results using Isolation Forest"""
    transactions_extracted: int = Field(..., ge=0, description="Number of transactions found")
    transactions: List[Transaction] = Field(default=[], description="Parsed transaction records")
    fraud_score: float = Field(..., ge=0, le=100, description="Overall fraud risk score (0-100)")
    combined_score: float = Field(..., ge=0, le=100, description="Hybrid score combining rule and model signals (0-100)")
    anomaly_score: float = Field(..., description="Isolation Forest anomaly score")
    model_is_fraud: bool = Field(..., description="Raw model anomaly decision")
    ml_risk_level: str = Field(..., description="Raw ML model risk level: low, medium, high")
    is_fraud: bool = Field(..., description="Final hybrid fraud verdict")
    final_risk_level: str = Field(..., description="Final hybrid risk level: low, medium, high")
    high_risk_features: List[str] = Field(default=[], description="Key fraud indicators detected")


class ProcessingMetrics(BaseModel):
    """Internal processing metrics"""
    ocr_pages_processed: int = Field(..., ge=0, description="Number of pages that required OCR")
    ocr_used: bool = Field(..., description="True if OCR was used")
    malware_scanned: bool = Field(..., description="True if malware scan was performed")
    malware_clean: bool = Field(..., description="True if file is clean")


class SecurityValidation(BaseModel):
    """Security validation results"""
    extension_valid: bool
    magic_bytes_valid: bool
    content_type_valid: bool
    malware_scan_result: dict


class AnalyzeResponse(BaseModel):
    """Structured API response for PDF analysis"""
    
    # Core document info
    document_metadata: DocumentMetadata
    
    # Text statistics
    statistics: Statistics
    
    # Financial pattern detection
    financial_signals: FinancialSignals
    
    # Compliance and risk
    compliance_flags: ComplianceFlags
    
    # Fraud detection (AI-powered)
    fraud_detection: Optional[FraudDetection] = Field(None, description="AI fraud detection results")
    
    # Processing metrics
    processing_metrics: ProcessingMetrics
    
    # Security validation
    security_validation: SecurityValidation
    
    # Text content
    sample_preview: str = Field(..., max_length=500, description="First 500 characters")
    full_text: str = Field(..., description="Complete extracted and cleaned text")
    
    # Storage reference
    storage_ref: StorageRef
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "document_metadata": {
                    "filename": "financial_report.pdf",
                    "file_size_bytes": 2457600,
                    "file_hash": "a3f8b21c9d4e5f6...",
                    "pages": 12,
                    "upload_timestamp": "2026-03-02T15:42:30Z",
                    "processing_time_seconds": 2.34
                },
                "statistics": {
                    "word_count": 5423,
                    "character_count": 32180,
                    "line_count": 412,
                    "avg_words_per_page": 451.92
                },
                "financial_signals": {
                    "currency_mentions": 18,
                    "percentage_mentions": 12,
                    "large_numbers": {
                        "crores": 3,
                        "lakhs": 5,
                        "millions": 2,
                        "billions": 0
                    },
                    "date_mentions": 8,
                    "email_addresses": 2,
                    "phone_numbers": 1
                },
                "compliance_flags": {
                    "pan_numbers_detected": 0,
                    "gstin_numbers_detected": 1,
                    "account_numbers_detected": 0,
                    "contains_sensitive_data": False,
                    "risk_level": "low"
                },
                "processing_metrics": {
                    "ocr_pages_processed": 2,
                    "ocr_used": True,
                    "malware_scanned": False,
                    "malware_clean": True
                },
                "security_validation": {
                    "extension_valid": True,
                    "magic_bytes_valid": True,
                    "content_type_valid": True,
                    "malware_scan_result": {"clean": True}
                },
                "sample_preview": "Financial Statement Q4 2025...",
                "full_text": "Complete text...",
                "storage_ref": {
                    "id": "financial_report_20260302154230_a3f8b21c",
                    "path": "/app/uploads/extracted_text/financial_report_20260302154230_a3f8b21c.txt"
                }
            }
        }


# Legacy simple response for backward compatibility (if needed)
class ExtractionResult(BaseModel):
    """Internal model for PDF extraction"""
    filename: str
    pages: int
    extracted_text: str


class RiskAnalysisResponse(BaseModel):
    """Focused response for /risk-analysis endpoint."""

    risk_score: float = Field(..., ge=0, le=1, description="ML risk score (0-1)")
    final_risk_level: str = Field(..., description="Final hybrid risk level: LOW, MEDIUM, HIGH")
    reasons: List[str] = Field(default=[], description="Detected anomaly reasons")
    transactions: List[Transaction] = Field(default=[], description="Parsed transaction records")
    fraud_score: float = Field(..., ge=0, le=100, description="Rule-based fraud score (0-100)")
    anomaly_score: float = Field(..., description="Raw anomaly score from model")
    model_is_fraud: bool = Field(..., description="Raw model anomaly decision")
    ml_risk_level: str = Field(..., description="Raw ML model risk level: low, medium, high")
    is_fraud: bool = Field(..., description="Final hybrid fraud verdict")
    combined_score: float = Field(..., ge=0, le=100, description="Hybrid score (0-100)")
    transactions_extracted: int = Field(..., ge=0, description="Number of extracted transactions")
    report: Dict[str, Any] = Field(..., description="Structured compliance report output")
