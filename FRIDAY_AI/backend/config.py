"""Local-first configuration. Nothing here changes OS security settings."""
from pathlib import Path
import os
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get('FRIDAY_DATA_DIR', str(ROOT / 'database'))).expanduser().resolve()
DB_PATH = DATA_DIR / 'friday.db'
PREVIEW = os.environ.get('FRIDAY_PREVIEW', '') == '1'
OLLAMA_URL = os.environ.get('FRIDAY_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
parsed = urlparse(OLLAMA_URL)
if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('localhost', '127.0.0.1', '::1') or parsed.username or parsed.password:
    raise RuntimeError('FRIDAY_OLLAMA_URL must point to a loopback Ollama server (localhost or 127.0.0.1).')
WORKSPACE = Path(os.environ.get('FRIDAY_WORKSPACE', str(Path.home() / 'FRIDAY'))).expanduser().resolve()
MAX_STEPS = max(1, min(25, int(os.environ.get('FRIDAY_MAX_STEPS', '12'))))
OLLAMA_CONTEXT = max(2048, min(32768, int(os.environ.get('FRIDAY_OLLAMA_CONTEXT', '8192'))))
MAX_FILE_BYTES = 10 * 1024 * 1024

def allowed_roots() -> list[Path]:
    extra = os.environ.get('FRIDAY_ALLOWED_ROOTS', '')
    if extra:
        candidates = [WORKSPACE] + [Path(p).expanduser() for p in extra.split(os.pathsep) if p.strip()]
    else:
        candidates = [WORKSPACE, Path.home() / 'Desktop', Path.home() / 'Documents', Path.home() / 'Downloads']
    return list(dict.fromkeys(p.resolve() for p in candidates))
