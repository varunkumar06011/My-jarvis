import ollama

from configs.config import MODEL_NAME
from logs.logger import write_log
from memory.storage import save_history, load_history


class LLM:
    def __init__(self, model=MODEL_NAME, session_name="default"):
        self.model = model
        self.session_name = session_name
        self.history = load_history(session_name)

    def chat(self, message: str) -> str:
        self.history.append({
            "role": "user",
            "content": message
        })

        write_log("USER", message)

        try:
            response = ollama.chat(
                model=self.model,
                messages=self.history
            )

            reply = response["message"]["content"]

        except Exception as e:
            reply = f"Error: {e}"

        write_log("JARVIS", reply)

        self.history.append({
            "role": "assistant",
            "content": reply
        })

        save_history(self.history, self.session_name)

        return reply
