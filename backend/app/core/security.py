import hashlib
import uuid
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.exceptions import ParakhException

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".ogg", ".m4a"}

ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream"
}

def generate_secure_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{ext}"

def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def validate_resume_file(filename: str, content: bytes, content_type: str | None = None) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise ParakhException(
            f"Unsupported resume format '{ext}'. Allowed formats: {', '.join(ALLOWED_RESUME_EXTENSIONS)}"
        )
    
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise ParakhException(
            f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )
    
    if len(content) == 0:
        raise ParakhException("Uploaded file is empty.")

def validate_audio_file(filename: str, content: bytes) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise ParakhException(
            f"Unsupported audio format '{ext}'. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        )
    if len(content) == 0:
        raise ParakhException("Uploaded audio recording is empty.")
