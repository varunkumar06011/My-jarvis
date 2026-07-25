from brain.llm import LLM
from configs.config import APP_NAME, VERSION
from core.commands import execute
from voice.tts import TextToSpeech


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

        if execute(user, jarvis):
            continue

        reply = jarvis.chat(user)

        print(f"\nJarvis: {reply}")

        speaker.speak(reply)


if __name__ == "__main__":
    main()
