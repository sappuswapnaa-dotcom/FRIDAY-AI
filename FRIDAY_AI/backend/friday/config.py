from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
WORKSPACE = Path(os.getenv("FRIDAY_WORKSPACE", ROOT / "user_files")).resolve()
DATA_DIR = Path(os.getenv("FRIDAY_DATA_DIR", ROOT / "data")).resolve()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("FRIDAY_MODEL", "")
WORKSPACE.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
