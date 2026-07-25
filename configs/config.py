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
