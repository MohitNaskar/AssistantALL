from api import agent, extract_text

if __name__ == "__main__":
    print("Gulu is ready. Type 'exit' or 'quit' to stop.\n")
    chat_history = []

    while True:
        query = input("You: ").strip()
        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            print("Gulu: Goodbye!")
            break

        chat_history.append({"role": "human", "content": query})
        response = agent.invoke({"messages": chat_history})
        reply = extract_text(response["messages"][-1].content)
        chat_history.append({"role": "ai", "content": reply})
        print(f"Gulu: {reply}\n")
