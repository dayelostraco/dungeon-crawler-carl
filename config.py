import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
MODEL: str = os.getenv("MODEL", "claude-sonnet-4-5")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "400"))

REFERENCE_AUDIO_DIR: Path = PROJECT_ROOT / "reference_audio"
TRANSCRIPTS_DIR: Path = PROJECT_ROOT / "transcripts"
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", str(PROJECT_ROOT / "output")))
ARCHIVE_FILE: Path = Path(os.getenv("ARCHIVE_FILE", str(PROJECT_ROOT / "achievements.json")))
DB_PATH: Path = Path(os.getenv("DB_PATH", str(PROJECT_ROOT / "achievements.db")))

# Storage mode: "local" (SQLite + filesystem) or "cloud" (DynamoDB + S3)
STORAGE_MODE: str = os.getenv("STORAGE_MODE", "local")
DYNAMODB_TABLE: str = os.getenv("DYNAMODB_TABLE", "achievements")
S3_BUCKET: str = os.getenv("S3_BUCKET", "achievement-intercom-audio")
CDN_DOMAIN: str = os.getenv("CDN_DOMAIN", "")

OUTPUT_DIR.mkdir(exist_ok=True)
REFERENCE_AUDIO_DIR.mkdir(exist_ok=True)
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT = (PROJECT_ROOT / "system_prompt.txt").read_text()
