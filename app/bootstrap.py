import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.lifecycle import State, LifecycleManager
from app.startup import run_startup
from app.tray import TrayIcon

from core.event_bus import bus
from core.service_registry import registry
from core.health_manager import health
from core.task_queue import task_queue


def bootstrap():
    lifecycle = LifecycleManager()

    print("=" * 50)
    print("🤖 Jarvis - Production Mode")
    print("=" * 50)

    if not run_startup():
        print("\nCannot start Jarvis. Fix errors above.")
        input("Press Enter to exit...")
        sys.exit(1)

    lifecycle.transition(State.STARTING)

    registry.register("lifecycle", lifecycle)
    registry.register("event_bus", bus)
    registry.register("task_queue", task_queue)

    print("\nLoading LLM...")
    from brain.llm import LLM
    jarvis = LLM()
    registry.register("llm", jarvis)
    print("✓ LLM loaded")

    print("\nLoading TTS...")
    from voice.tts import TextToSpeech
    speaker = TextToSpeech()
    registry.register("tts", speaker)
    print("✓ TTS loaded")

    print("\nLoading STT + VAD...")
    from voice.stt import SpeechToText
    stt = SpeechToText()
    registry.register("stt", stt)
    print("✓ STT loaded")

    print("\nLoading Wake Word...")
    from voice.wake_word import WakeWordDetector
    wake_detector = WakeWordDetector()
    registry.register("wake_word", wake_detector)
    print("✓ Wake word loaded")

    print("\nLoading Plugins...")
    from core.tool_registry import TOOLS
    registry.register("tools", TOOLS)
    print(f"✓ {len(TOOLS)} plugins loaded: {', '.join(TOOLS.keys())}")

    print("\nLoading Router...")
    from core.router import route
    registry.register("router", route)
    print("✓ Router loaded")

    print("\nRegistering health checks...")
    health.register_check("llm", lambda: registry.has("llm"))
    health.register_check("tts", lambda: registry.has("tts"))
    health.register_check("stt", lambda: registry.has("stt"))
    health.register_check("wake_word", lambda: registry.has("wake_word"))
    health.start()
    print("✓ Health monitoring started")

    bus.publish("ApplicationStarted", {"services": registry.list_services()})

    lifecycle.transition(State.READY)

    def on_exit():
        lifecycle.transition(State.SHUTDOWN)
        bus.publish("ApplicationStopped", None)

    tray = TrayIcon(lifecycle, on_exit=on_exit)
    tray.start()
    registry.register("tray", tray)

    print("\n🤖 Jarvis is ready. Say \"Hey Jarvis\" to start.\n")

    from services.assistant_service import start_assistant

    def assistant_loop():
        start_assistant(jarvis, speaker)

    assistant_thread = threading.Thread(target=assistant_loop, daemon=True)
    assistant_thread.start()

    try:
        while lifecycle.is_running():
            assistant_thread.join(timeout=1)
            if not assistant_thread.is_alive():
                break
    except KeyboardInterrupt:
        print("\nShutting down...")
        lifecycle.transition(State.SHUTDOWN)

    health.stop()
    task_queue.shutdown()
    tray.stop()
    bus.clear()
    print("Jarvis stopped.")


if __name__ == "__main__":
    bootstrap()
