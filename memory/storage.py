import json
from pathlib import Path

SESSION_DIR = Path("memory/sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)


def get_session_file(session_name="default"):
    return SESSION_DIR / f"{session_name}.json"


def save_history(history, session_name="default"):
    with open(get_session_file(session_name), "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def load_history(session_name="default"):
    file = get_session_file(session_name)

    if not file.exists():
        return []

    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def list_sessions():
    return sorted(path.stem for path in SESSION_DIR.glob("*.json"))
