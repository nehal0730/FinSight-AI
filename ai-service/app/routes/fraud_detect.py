"""
Fraud Detection Endpoint

Standalone CSV fraud detection endpoint for transaction analysis.
Accepts CSV files with transaction data and returns risk assessment.

Author: FinSight AI
"""

import csv
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.fraud import FeatureEngineer, FraudDetector, ReportGenerator
from app.services.fraud.transaction_extractor import TransactionExtractor
from app.utils.logging import api_logger, request_id_var

router = APIRouter(prefix="", tags=["fraud-detection"])


class FraudDetectionResponse(BaseModel):
    """Response model for fraud detection endpoint."""

    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(..., description="Analysis timestamp")
    transactions_analyzed: int = Field(..., description="Number of transactions processed")
    risk_score: float = Field(..., ge=0, le=100, description="Overall fraud risk score (0-100)")
    fraud_score: float = Field(..., ge=0, le=100, description="Rule-based fraud score")
    ml_risk_score: float = Field(..., description="ML anomaly score")
    is_fraud: bool = Field(..., description="Final fraud verdict")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH")
    detected_issues: list[str] = Field(default=[], description="List of flagged risk patterns")
    key_metrics: dict = Field(..., description="Transaction summary statistics")
    recommendation: str = Field(..., description="Compliance recommendation")


@router.post("/fraud-detect", response_model=FraudDetectionResponse)
async def fraud_detect(file: UploadFile = File(...)):
    """
    Analyze transactions from CSV file for fraud patterns.

    Expected CSV format:
    - Headers: date, amount, type, merchant (or description)
    - date: YYYY-MM-DD or DD-MM-YYYY
    - amount: numeric value
    - type: debit or credit
    - merchant: merchant name or transaction description

    Example CSV:
    ```
    date,amount,type,merchant
    2024-01-15,250.00,debit,Amazon
    2024-01-15,5000.00,debit,Crypto Exchange
    2024-01-15,100.00,credit,Salary Deposit
    ```

    Returns:
        Fraud risk assessment with score, verdict, and recommendations
    """
    req_id = str(uuid.uuid4())[:8]
    request_id_var.set(req_id)

    try:
        # Validate file type
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")

        # Read CSV content
        content = await file.read()
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Invalid CSV encoding. Use UTF-8.")

        # Parse CSV
        csv_reader = csv.DictReader(StringIO(text_content))
        
        # Validate headers
        required_headers = {'date', 'amount', 'type', 'merchant'}
        alternative_headers = {'date', 'amount', 'type', 'description'}
        
        fieldnames = set(h.lower().strip() for h in csv_reader.fieldnames or [])
        
        if not (required_headers.issubset(fieldnames) or alternative_headers.issubset(fieldnames)):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain headers: {required_headers} or {alternative_headers}"
            )

        # Extract transactions
        transactions = []
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Normalize keys
                normalized_row = {k.lower().strip(): v.strip() for k, v in row.items()}
                
                merchant = normalized_row.get('merchant') or normalized_row.get('description', 'Unknown')
                
                transaction = {
                    'date': normalized_row['date'],
                    'amount': float(normalized_row['amount']),
                    'type': normalized_row['type'].lower(),
                    'merchant': merchant
                }
                
                # Validate transaction type
                if transaction['type'] not in ['debit', 'credit']:
                    api_logger.warning(f"Row {row_num}: Invalid type '{transaction['type']}', skipping")
                    continue
                
                transactions.append(transaction)
                
            except (KeyError, ValueError) as e:
                api_logger.warning(f"Row {row_num}: Parsing error - {e}, skipping")
                continue

        if not transactions:
            raise HTTPException(
                status_code=400,
                detail="No valid transactions found in CSV. Check format and data."
            )

        api_logger.info(f"Parsed {len(transactions)} transactions from CSV")

        # Feature engineering
        features = FeatureEngineer.engineer_features(transactions)

        # Fraud detection
        from ml.predict import get_inference_engine
        
        try:
            inference_engine = get_inference_engine()
            ml_prediction = inference_engine.predict_fraud(features)
        except Exception as ml_error:
            api_logger.warning(f"ML inference failed: {ml_error}. Using rule-based only.")
            ml_prediction = {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'ml_risk_level': 'LOW'
            }

        # Combine ML + Rules
        hybrid_result = FraudDetector.combine_fraud_verdict(
            ml_is_fraud=ml_prediction['is_anomaly'],
            ml_risk_score=ml_prediction['anomaly_score'],
            features=features
        )

        # Generate report
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=hybrid_result['combined_score'],
            anomaly_score=ml_prediction['anomaly_score'],
            is_fraud=hybrid_result['is_fraud'],
            features=features,
            transactions=transactions,
            document_name=file.filename,
        )

        # Build response
        return FraudDetectionResponse(
            request_id=req_id,
            timestamp=datetime.now().isoformat(),
            transactions_analyzed=len(transactions),
            risk_score=hybrid_result['combined_score'],
            fraud_score=hybrid_result['rule_fraud_score'],
            ml_risk_score=ml_prediction['anomaly_score'],
            is_fraud=hybrid_result['is_fraud'],
            risk_level=report['risk_level'],
            detected_issues=report['detected_issues'],
            key_metrics=report['key_metrics'],
            recommendation=report['recommendation']
        )

    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Fraud detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fraud detection failed: {str(e)}")
