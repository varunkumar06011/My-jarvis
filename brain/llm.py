import os
import time
import subprocess

import ollama

from configs.config import MODEL_NAME, GPU_LAYERS, LLM_MAX_RETRIES, LLM_RETRY_DELAY
from logs.logger import write_log
from memory.storage import save_history, load_history


def _kill_stale_llama_servers():
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq llama-server.exe", "/FO", "CSV"],
            capture_output=True, text=True, timeout=10,
        )
        count = result.stdout.count("llama-server.exe")
        if count > 1:
            print(f"[LLM] Found {count} llama-server processes, cleaning up...")
            subprocess.run(
                ["taskkill", "/F", "/IM", "llama-server.exe"],
                capture_output=True, timeout=10,
            )
            time.sleep(2)
    except Exception:
        pass


def _ensure_model_available(model_name):
    try:
        models = ollama.list()
        installed = [m.model for m in models.models] if hasattr(models, "models") else []
        if model_name not in installed:
            print(f"[LLM] Model '{model_name}' not found. Pulling...")
            ollama.pull(model_name)
    except Exception as e:
        print(f"[LLM] Could not verify model availability: {e}")


class LLM:
    def __init__(self, model=MODEL_NAME, session_name="default"):
        self.model = model
        self.session_name = session_name
        self.history = load_history(session_name)

        self.options = {}
        if GPU_LAYERS is not None:
            self.options["num_gpu"] = GPU_LAYERS

        _kill_stale_llama_servers()
        _ensure_model_available(model)

    def chat(self, message: str) -> str:
        self.history.append({
            "role": "user",
            "content": message
        })

        write_log("USER", message)

        reply = None
        last_error = None

        for attempt in range(LLM_MAX_RETRIES):
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=self.history,
                    options=self.options
                )

                reply = response["message"]["content"]
                break

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if "out-of-memory" in error_str or "failed to allocate" in error_str:
                    print(f"[LLM] OOM on attempt {attempt + 1}/{LLM_MAX_RETRIES}, cleaning up...")
                    _kill_stale_llama_servers()
                elif "connection" in error_str or "refused" in error_str:
                    print(f"[LLM] Connection error on attempt {attempt + 1}/{LLM_MAX_RETRIES}, retrying...")
                else:
                    print(f"[LLM] Error on attempt {attempt + 1}/{LLM_MAX_RETRIES}: {e}")

                if attempt < LLM_MAX_RETRIES - 1:
                    time.sleep(LLM_RETRY_DELAY)

        if reply is None:
            reply = f"Sorry, I'm having trouble connecting to my brain right now. Error: {last_error}"

        write_log("JARVIS", reply)

        self.history.append({
            "role": "assistant",
            "content": reply
        })

        save_history(self.history, self.session_name)

        return reply
