import hashlib
import tempfile
from pathlib import Path
from typing import AsyncIterator

from fastapi import UploadFile


class FileValidator:
    """Security validation for uploaded files"""

    # PDF magic bytes (file signature)
    PDF_MAGIC_BYTES = [
        b"%PDF-",  # Standard PDF header
    ]

    ALLOWED_CONTENT_TYPES = [
        "application/pdf",
        "application/x-pdf",
        "application/octet-stream",  # Some browsers send this
    ]

    @staticmethod
    def validate_pdf_extension(filename: str | None) -> bool:
        """Validate file has .pdf extension"""
        return filename is not None and filename.lower().endswith(".pdf")

    @staticmethod
    def validate_content_type(content_type: str | None) -> bool:
        """Validate MIME type is PDF"""
        if not content_type:
            return True  # Some clients don't send content-type
        return content_type.lower() in FileValidator.ALLOWED_CONTENT_TYPES

    @staticmethod
    def validate_pdf_magic_bytes(file_path: Path) -> bool:
        """
        Validate file is actually a PDF by checking magic bytes.
        
        Security: Prevents disguised files (e.g., .exe renamed to .pdf)
        """
        try:
            with open(file_path, "rb") as f:
                header = f.read(5)
                return any(header.startswith(magic) for magic in FileValidator.PDF_MAGIC_BYTES)
        except Exception:
            return False

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """
        Compute SHA256 hash for audit trail and duplicate detection.
        
        Returns:
            Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


class MalwareScanService:
    """Placeholder for malware scanning integration"""

    @staticmethod
    async def scan_file(file_path: Path) -> dict:
        """
        Scan file for malware (placeholder for production integration).
        
        Production integrations:
        - ClamAV (open-source)
        - VirusTotal API
        - AWS GuardDuty
        - Azure Defender
        
        Returns:
            dict with scan results
        """
        # TODO: Integrate actual malware scanner in production
        return {
            "scanned": False,  # Set to True when real scanner is integrated
            "clean": True,  # Assume clean for now
            "scanner": "placeholder",
            "threats_detected": 0,
        }


class FileHandler:
    """Handles temporary file operations for uploaded PDFs"""

    MAX_FILE_SIZE_MB = 30
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks

    @staticmethod
    async def read_upload_to_temp(
        file: UploadFile,
        size_limit_mb: int = MAX_FILE_SIZE_MB
    ) -> tuple[Path, int]:
        """
        Read uploaded file to temporary location with size validation.
        
        Args:
            file: FastAPI UploadFile object
            size_limit_mb: Maximum file size in MB
        
        Returns:
            Tuple of (temp_file_path, bytes_written)
        
        Raises:
            ValueError: If file exceeds size limit
        """
        bytes_written = 0
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = Path(temp_file.name)

        try:
            while True:
                chunk = await file.read(FileHandler.CHUNK_SIZE)
                if not chunk:
                    break

                bytes_written += len(chunk)
                if bytes_written > size_limit_mb * 1024 * 1024:
                    temp_path.unlink(missing_ok=True)
                    raise ValueError(
                        f"File exceeds {size_limit_mb}MB limit."
                    )

                temp_file.write(chunk)

            temp_file.close()
            return temp_path, bytes_written

        except Exception as exc:
            temp_path.unlink(missing_ok=True)
            raise exc

    @staticmethod
    def cleanup_temp_file(temp_path: Path | None) -> None:
        """Safely delete temporary file"""
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
