import os
from pathlib import Path


class Config:
    """Centralized Flask configuration."""

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10 MB
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "docx", "txt"}
    SKILLS_FILE = Path(__file__).resolve().parent / "data" / "skills.json"
