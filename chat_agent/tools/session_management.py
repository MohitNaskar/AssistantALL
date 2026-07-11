from langchain_core.tools import tool

from tools.common import logger

conversation_history: list[dict] = []


@tool
def summarize_conversation(messages: list[dict] | None = None) -> str:
    """Summarize the current conversation history.

    Uses the provided messages list if given, otherwise falls back to the
    module-level conversation_history buffer.

    Each message should be a dict with 'role' ('human' or 'ai') and
    'content' (str) keys.

    Args:
        messages: Optional list of message dicts to summarize. If omitted,
                  the internal conversation buffer is used.

    Returns:
        A plain-text summary string suitable for speaking aloud.
    """
    history = messages if messages is not None else conversation_history

    if not history:
        return "No conversation history recorded yet."

    mentioned_contacts: set[str] = set()
    mentioned_skills: set[str] = set()
    skill_keywords = {"python", "machine learning", "web", "api", "database", "ai", "nlp", "genai"}

    for item in history:
        text = str(item.get("content", item))
        lower = text.lower()
        if "phone" in lower or "email" in lower or "contact" in lower:
            mentioned_contacts.add(text[:80])
        if any(sk in lower for sk in skill_keywords):
            mentioned_skills.add(text[:80])

    parts = [f"Conversation Summary ({len(history)} messages):"]
    if mentioned_contacts:
        parts.append("Contact info discussed: " + " | ".join(list(mentioned_contacts)[:3]))
    if mentioned_skills:
        parts.append("Technical topics: " + " | ".join(list(mentioned_skills)[:3]))

    logger.info("Generated conversation summary")
    return "\n".join(parts)
