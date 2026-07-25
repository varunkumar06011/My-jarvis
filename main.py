from brain.llm import LLM
from configs.config import APP_NAME, VERSION
from core.commands import execute
from core.router import route
from voice.tts import TextToSpeech
from services.voice_service import start_voice_chat
from services.assistant_service import start_assistant


def main():
    print("=" * 50)
    print(f"🤖 {APP_NAME} v{VERSION}")
    print("Type 'exit' to quit")
    print("=" * 50)

    jarvis = LLM()
    speaker = TextToSpeech()

    while True:
        user = input("\nYou: ")

        if user.lower() == "exit":
            print("\nGoodbye!")
            break

        result = execute(user, jarvis)

        if result == "voice":
            start_voice_chat(jarvis, speaker)
            continue

        if result == "assistant":
            start_assistant(jarvis, speaker)
            continue

        if result:
            continue

        tool_reply = route(user)

        if tool_reply is not None:
            print(f"\nJarvis: {tool_reply}")
            speaker.speak(tool_reply)
            continue

        reply = jarvis.chat(user)

        print(f"\nJarvis: {reply}")

        speaker.speak(reply)


if __name__ == "__main__":
    main()
