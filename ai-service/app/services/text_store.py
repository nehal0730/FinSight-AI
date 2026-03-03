from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.response_schema import StorageRef


class TextStore:
    """Store extracted text locally for retrieval and future RAG integration"""

    def __init__(self, base_dir: Path | None = None):
        """
        Initialize text store.
        
        Args:
            base_dir: Base directory for storage (default: app/uploads/extracted_text)
        """
        default_dir = (
            Path(__file__).resolve().parents[1] / "uploads" / "extracted_text"
        )
        self.base_dir = base_dir or default_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, source_filename: str, text: str) -> StorageRef:
        """
        Save extracted text to local file.
        
        Filename format: {original_name}_{timestamp}_{random_id}.txt
        
        Args:
            source_filename: Original PDF filename
            text: Cleaned extracted text
        
        Returns:
            StorageRef with file ID and path
        """
        safe_stem = Path(source_filename).stem.replace(" ", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        file_id = f"{safe_stem}_{timestamp}_{uuid4().hex[:8]}"
        output_path = self.base_dir / f"{file_id}.txt"

        output_path.write_text(text, encoding="utf-8")

        return StorageRef(
            id=file_id,
            path=str(output_path),
        )
