import logging
import sys
import time
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class StructuredLogger:
    """Structured logging for production observability"""

    def __init__(self, name: str, log_file: Path | None = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler with structured format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (if specified)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _enrich_message(self, message: str, extra: Dict[str, Any] | None = None) -> str:
        """Add request ID and extra context to log message"""
        request_id = request_id_var.get()
        parts = []
        
        if request_id:
            parts.append(f"[req_id={request_id}]")
        
        parts.append(message)
        
        if extra:
            extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
            parts.append(f"| {extra_str}")
        
        return " ".join(parts)

    def info(self, message: str, **extra):
        """Log info message with context"""
        self.logger.info(self._enrich_message(message, extra))

    def warning(self, message: str, **extra):
        """Log warning message with context"""
        self.logger.warning(self._enrich_message(message, extra))

    def error(self, message: str, exc_info=False, **extra):
        """Log error message with context"""
        self.logger.error(self._enrich_message(message, extra), exc_info=exc_info)

    def debug(self, message: str, **extra):
        """Log debug message with context"""
        self.logger.debug(self._enrich_message(message, extra))


class PerformanceTimer:
    """Context manager for measuring execution time"""

    def __init__(self, logger: StructuredLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation}",
                duration_seconds=f"{self.elapsed:.2f}"
            )
        else:
            self.logger.error(
                f"Failed {self.operation}",
                duration_seconds=f"{self.elapsed:.2f}",
                error=str(exc_val)
            )


# Global logger instances
pdf_logger = StructuredLogger("pdf_processor")
ocr_logger = StructuredLogger("ocr_service")
api_logger = StructuredLogger("api")
security_logger = StructuredLogger("security")


def log_file_upload(filename: str, size_bytes: int, file_hash: str):
    """Log file upload event"""
    api_logger.info(
        "File uploaded",
        filename=filename,
        size_mb=f"{size_bytes / (1024*1024):.2f}",
        hash=file_hash[:16]
    )


def log_ocr_usage(page_num: int, total_pages: int):
    """Log OCR processing"""
    ocr_logger.info(
        f"OCR processing page {page_num}/{total_pages}",
        page=page_num,
        total=total_pages
    )


def log_security_validation(filename: str, validation_results: dict):
    """Log security validation results"""
    security_logger.info(
        "Security validation completed",
        filename=filename,
        **validation_results
    )


def log_error(operation: str, error: Exception, context: dict | None = None):
    """Log error with full context"""
    api_logger.error(
        f"Error in {operation}: {str(error)}",
        exc_info=True,
        **(context or {})
    )