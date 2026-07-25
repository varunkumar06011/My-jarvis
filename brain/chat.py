import ollama

print("=" * 50)
print("🤖 JARVIS v1")
print("Type 'exit' to quit")
print("=" * 50)

history = []

while True:
    user = input("\nYou: ")

    if user.lower() == "exit":
        print("\nGoodbye!")
        break

    history.append({
        "role": "user",
        "content": user
    })

    response = ollama.chat(
        model="qwen2.5-coder:7b",
        messages=history
    )

    reply = response["message"]["content"]

    print(f"\nJarvis: {reply}")

    history.append({
        "role": "assistant",
        "content": reply
    })
