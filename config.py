# config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = Path(os.getenv("CHUMCRED_DB_PATH", str(BASE_DIR / "chumcred_lms.db")))
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", str(DATA_DIR / "uploads")))
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
