from brain.llm import LLM
from core.router import route
from logs.logger import write_log
from voice.stt import SpeechToText
from voice.tts import TextToSpeech


def start_voice_chat(jarvis: LLM, speaker: TextToSpeech):
    print("\n" + "=" * 50)
    print("🎤 VOICE MODE")
    print("Say 'exit voice' to return to keyboard mode")
    print("=" * 50)

    stt = SpeechToText()

    while True:
        text = stt.listen()

        if not text or len(text.strip()) < 2:
            continue

        print(f"\nYou: {text}")

        if text.lower().strip() in ("exit voice", "exit", "quit"):
            print("\nExiting voice mode...\n")
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
