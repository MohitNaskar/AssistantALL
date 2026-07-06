from datetime import datetime
from typing import Any, Dict, Optional

from livekit.agents import llm

from .common import DB, logger

conversation_history = []


@llm.function_tool(description="Summarize what the user told you so far in the conversation.")
async def summarize_conversation() -> str:
    """Summarize the current conversation."""
    try:
        if not conversation_history:
            return "No conversation history recorded yet."

        summary = "Conversation Summary:\n\n"
        summary += "Key Information Shared:\n"

        mentioned_contacts = set()
        mentioned_skills = set()

        for item in conversation_history:
            item_text = str(item)
            if "phone" in item_text.lower():
                mentioned_contacts.add(item_text)
            if any(
                skill in item_text.lower()
                for skill in ["python", "machine learning", "web", "api", "database"]
            ):
                mentioned_skills.add(item_text)

        if mentioned_contacts:
            summary += f"\nContacts: {', '.join(mentioned_contacts)}\n"
        if mentioned_skills:
            summary += f"\nSkills Mentioned: {', '.join(mentioned_skills)}\n"

        summary += f"\nTotal messages: {len(conversation_history)}"

        logger.info("Generated conversation summary")
        return summary
    except Exception as e:
        logger.error(f"Error summarizing conversation: {e}")
        return f"Failed to summarize: {e}"