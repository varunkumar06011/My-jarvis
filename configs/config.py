import os

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "qwen2.5-coder:7b"

# Set to 0 to force CPU-only inference, or a number to limit GPU layers
# None = let Ollama decide (use all GPU layers)
GPU_LAYERS = 0

# Max retries when Ollama fails (OOM, connection, etc.)
LLM_MAX_RETRIES = 3

# Seconds to wait between retries
LLM_RETRY_DELAY = 5

APP_NAME = "Jarvis"

VERSION = "2.0"

WHISPER_MODEL = "small"

SAMPLE_RATE = 16000

SILENCE_TIMEOUT = 1.0

MAX_RECORD_SECONDS = 20

WAKE_WORD = "hey_jarvis"

WAKE_THRESHOLD = 0.3

WAKE_TIMEOUT = 30

# ── API Server ────────────────────────────────────────────────────────────

API_HOST = os.getenv("JARVIS_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("JARVIS_API_PORT", "8100"))

API_DEFAULT_KEY = os.getenv("JARVIS_API_DEFAULT_KEY", "jarvis-local-dev-key")

API_RATE_LIMIT_PER_MINUTE = int(os.getenv("JARVIS_RATE_LIMIT_PER_MINUTE", "30"))
API_RATE_LIMIT_PER_HOUR = int(os.getenv("JARVIS_RATE_LIMIT_PER_HOUR", "100"))

API_JWT_SECRET = os.getenv("JARVIS_JWT_SECRET", "jarvis-jwt-secret-change-in-production")
API_JWT_EXPIRE_SECONDS = int(os.getenv("JARVIS_JWT_EXPIRE_SECONDS", "3600"))

API_ENABLE_DOCS = os.getenv("JARVIS_API_ENABLE_DOCS", "true").lower() in ("true", "1", "yes")

# ── Config Version (for migration support) ────────────────────────────────

CONFIG_VERSION = 1
