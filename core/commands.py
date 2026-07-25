from configs.config import MODEL_NAME
from memory.storage import list_sessions


def execute(command: str, jarvis) -> bool:
    command = command.strip().lower()

    if command == "/help":
        print("\nAvailable Commands:")
        print("/help     - Show commands")
        print("/clear    - Clear conversation")
        print("/history  - Show conversation history")
        print("/model    - Show current model")
        print("/sessions - List saved sessions")
        print("/voice     - Start voice mode")
        print("/assistant - Start wake word mode")
        print("/exit      - Exit Jarvis")
        return True

    if command == "/model":
        print(f"\nCurrent Model: {MODEL_NAME}")
        return True

    if command == "/clear":
        jarvis.history.clear()
        from memory.storage import save_history
        save_history(jarvis.history, jarvis.session_name)
        print("\nConversation cleared.")
        return True

    if command == "/history":
        print("\nConversation History:\n")

        if not jarvis.history:
            print("No conversation yet.")
            return True

        for message in jarvis.history:
            print(f"{message['role']}: {message['content']}")

        return True

    if command == "/sessions":
        sessions = list_sessions()

        print("\nAvailable Sessions:")

        if not sessions:
            print("No saved sessions.")
        else:
            for session in sessions:
                print(f"- {session}")

        return True

    if command == "/voice":
        return "voice"

    if command == "/assistant":
        return "assistant"

    return False
