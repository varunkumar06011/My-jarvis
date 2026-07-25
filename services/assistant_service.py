from brain.llm import LLM
from core.router import route
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

    wake_detector = WakeWordDetector()
    stt = SpeechToText()

    while True:
        wake_detector.listen()

        speaker.speak("Yes?")

        while True:
            print("\n🎤 Listening...")
            text = stt.listen()

            if not text or len(text.strip()) < 2:
                continue

            print(f"\nYou: {text}")

            if text.lower().strip() in ("goodbye", "exit", "quit", "bye"):
                print("\nEnding conversation...")
                speaker.speak("Goodbye!")
                break

            write_log("VOICE USER", text)

            tool_reply = route(text)

            if tool_reply is not None:
                print(f"\nJarvis: {tool_reply}")
                write_log("JARVIS", tool_reply)
                speaker.speak(tool_reply)
                continue

            reply = jarvis.chat(text)

            print(f"\nJarvis: {reply}")

            speaker.speak(reply)
