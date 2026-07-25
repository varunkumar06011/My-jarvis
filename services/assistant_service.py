from brain.llm import LLM
from core.router import route
from core.event_bus import bus
from logs.logger import write_log
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from voice.wake_word import WakeWordDetector


def start_assistant(jarvis: LLM, speaker: TextToSpeech):
    print("\n" + "=" * 50)
    print("🤖 JARVIS ASSISTANT MODE")
    print("Say \"Hey Jarvis\" to start a conversation")
    print("Say \"goodbye\" to end a conversation")
    print("Press Ctrl+C to quit")
    print("=" * 50)

    from core.service_registry import registry

    if registry.has("wake_word"):
        wake_detector = registry.get("wake_word")
    else:
        wake_detector = WakeWordDetector()
        registry.register("wake_word", wake_detector)

    if registry.has("stt"):
        stt = registry.get("stt")
    else:
        stt = SpeechToText()
        registry.register("stt", stt)

    while True:
        wake_detector.listen()
        bus.publish("WakeWordDetected", None)

        speaker.speak("Yes?")
        bus.publish("SpeechStarted", {"text": "Yes?"})

        while True:
            print("\n🎤 Listening...")
            text = stt.listen()

            if not text or len(text.strip()) < 2:
                continue

            print(f"\nYou: {text}")
            bus.publish("SpeechFinished", {"text": text})

            if text.lower().strip() in ("goodbye", "exit", "quit", "bye"):
                print("\nEnding conversation...")
                speaker.speak("Goodbye!")
                bus.publish("SpeechStarted", {"text": "Goodbye!"})
                break

            write_log("VOICE USER", text)

            tool_reply = route(text)

            if tool_reply is not None:
                print(f"\nJarvis: {tool_reply}")
                write_log("JARVIS", tool_reply)
                bus.publish("ToolExecuted", {"input": text, "result": tool_reply})
                speaker.speak(tool_reply)
                bus.publish("SpeechStarted", {"text": tool_reply})
                continue

            reply = jarvis.chat(text)

            print(f"\nJarvis: {reply}")

            write_log("JARVIS", reply)
            bus.publish("LLMResponse", {"input": text, "response": reply})
            speaker.speak(reply)
            bus.publish("SpeechStarted", {"text": reply})
