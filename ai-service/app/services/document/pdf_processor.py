from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from app.services.document.ocr_service import OCRService


@dataclass
class ExtractionResult:
    """Result of PDF text extraction"""
    filename: str
    pages: int
    extracted_text: str
    page_ranges: list  # List of (page_num, page_text) tuples
    ocr_pages_count: int  # Track OCR usage


class PDFProcessor:
    """Extract text from PDF files using native text extraction + OCR fallback"""

    def __init__(self):
        """
        Initialize PDF processor.
        """
        self.ocr_service = OCRService()

    def extract_text(self, pdf_path: Path) -> ExtractionResult:
        """
                Extract text from PDF page-by-page.

                Strategy:
                - Try native PDF text extraction first (fast path for text-based PDFs).
                - Fall back to Tesseract OCR only when native extraction returns no usable text
                    (for scanned/image-based pages).
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            ExtractionResult with filename, page count, extracted text, page_ranges, and OCR metrics
        """
        page_text_chunks: list[str] = []
        page_ranges: list = []  # Track (page_num, text) for each page
        ocr_pages_count = 0

        with pdfplumber.open(str(pdf_path)) as pdf:
            total_pages = len(pdf.pages)

            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1  # 1-indexed
                native_text = (page.extract_text() or "").strip()

                if native_text:
                    page_text_chunks.append(native_text)
                    page_ranges.append((page_num, native_text))
                    continue

                ocr_pages_count += 1
                ocr_text = self.ocr_service.extract_text_from_page_image(page).strip()
                if ocr_text:
                    page_text_chunks.append(ocr_text)
                    page_ranges.append((page_num, ocr_text))

        # Combine all pages, filtering empty chunks
        combined_text = "\n\n".join(
            chunk for chunk in page_text_chunks if chunk
        )

        return ExtractionResult(
            filename=pdf_path.name,
            pages=total_pages,
            extracted_text=combined_text,
            page_ranges=page_ranges,
            ocr_pages_count=ocr_pages_count,
        )
