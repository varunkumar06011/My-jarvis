import os
import sys
from pathlib import Path


def check_requirements():
    errors = []

    root = Path(__file__).parent.parent

    required_dirs = [
        "brain",
        "configs",
        "core",
        "memory",
        "voice",
        "plugins",
        "services",
        "assets/piper",
        "assets/piper/voices",
    ]

    for d in required_dirs:
        if not (root / d).exists():
            errors.append(f"Missing directory: {d}")

    piper_exe = root / "assets" / "piper" / "piper.exe"
    if not piper_exe.exists():
        errors.append(f"Missing Piper executable: {piper_exe}")

    voice_model = root / "assets" / "piper" / "voices" / "en_US-lessac-medium.onnx"
    if not voice_model.exists():
        errors.append(f"Missing voice model: {voice_model}")

    try:
        import ollama
    except ImportError:
        errors.append("ollama package not installed")

    try:
        import whisper
    except ImportError:
        errors.append("openai-whisper package not installed")

    try:
        import sounddevice
    except ImportError:
        errors.append("sounddevice package not installed")

    try:
        from silero_vad import load_silero_vad
    except ImportError:
        errors.append("silero-vad package not installed")

    try:
        from openwakeword import Model
    except ImportError:
        errors.append("openwakeword package not installed")

    try:
        import psutil
    except ImportError:
        errors.append("psutil package not installed")

    try:
        import fastapi
    except ImportError:
        errors.append("fastapi package not installed")

    try:
        import uvicorn
    except ImportError:
        errors.append("uvicorn package not installed")

    try:
        import pydantic
    except ImportError:
        errors.append("pydantic package not installed")

    try:
        import websockets
    except ImportError:
        errors.append("websockets package not installed")

    try:
        import requests
    except ImportError:
        errors.append("requests package not installed")

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        errors.append("cryptography package not installed")

    try:
        import websocket
    except ImportError:
        errors.append("websocket-client package not installed")

    try:
        from dotenv import load_dotenv
    except ImportError:
        errors.append("python-dotenv package not installed")

    return errors


def ensure_directories():
    root = Path(__file__).parent.parent

    dirs = [
        "logs",
        "memory/sessions",
        "data",
        "data/telemetry",
        "data/macros",
        "data/artifacts",
        "data/reminders",
        "models",
        "backups",
        "flags",
    ]

    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)


def run_startup():
    print("Running startup checks...")

    ensure_directories()

    errors = check_requirements()

    if errors:
        print("\n❌ Startup failed:\n")
        for err in errors:
            print(f"  - {err}")
        print()
        return False

    print("✓ All checks passed\n")
    return True
