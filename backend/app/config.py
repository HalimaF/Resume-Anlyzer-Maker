import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env if present, so local settings do not have to be exported.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _split_env_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Centralized Flask configuration."""

    # Per-file cap the UI advertises, and the total request cap that has to be
    # large enough to hold a full bulk batch of them.
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10 MB per file
    MAX_BULK_FILES = int(os.getenv("MAX_BULK_FILES", 25))
    MAX_CONTENT_LENGTH = int(
        os.getenv("MAX_CONTENT_LENGTH", MAX_FILE_SIZE * MAX_BULK_FILES + 2 * 1024 * 1024)
    )

    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "docx", "txt"}
    SKILLS_FILE = Path(__file__).resolve().parent / "data" / "skills.json"
    OCR_ENGINE = os.getenv("OCR_ENGINE", "rapidocr")

    # Comma-separated list of allowed browser origins. "*" keeps the API open,
    # which is the default so opening the frontend from any local server works.
    CORS_ORIGINS = _split_env_list("CORS_ORIGINS", "*")

    # ---- Optional LLM enrichment ------------------------------------------
    # Off by default. The analyzer is fully functional without it; enabling it
    # adds catalog-independent skill detection and bullet rewriting.
    # Defaults target Ollama, which is free, open source, and runs locally.
    LLM_ENABLED = _flag("LLM_ENABLED", "false")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 45))
