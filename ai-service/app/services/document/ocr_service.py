import pytesseract

from PIL import ImageEnhance, ImageOps


class OCRService:
    """Optical Character Recognition for scanned PDFs using Tesseract"""

    def __init__(self, resolution: int = 300, contrast_factor: float = 2.0):
        """
        Initialize OCR service.
        
        Args:
            resolution: Image resolution for OCR (higher = better quality, slower)
            contrast_factor: Contrast enhancement factor (2.0 = 2x contrast)
        """
        self.resolution = resolution
        self.contrast_factor = contrast_factor
        
    def extract_text_from_page_image(self, page) -> str:
        """
        Extract text from a PDF page using Tesseract OCR.
        
        Args:
            page: pdfplumber page object
        
        Returns:
            Extracted text string (empty if OCR fails)
        """

        try:
            # Convert PDF page to high-resolution image
            image = page.to_image(resolution=self.resolution).original.convert("RGB")

            # Convert to grayscale for better OCR accuracy
            grayscale = ImageOps.grayscale(image)

            # Enhance contrast to improve readability
            enhanced = ImageEnhance.Contrast(grayscale).enhance(self.contrast_factor)

            # Extract text using Tesseract
            return pytesseract.image_to_string(enhanced, config="--oem 3 --psm 6")
        except Exception as e:
            # If OCR fails for any reason, return empty string
            print(f"OCR extraction failed: {e}")
            return ""
