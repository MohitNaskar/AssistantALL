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


@llm.function_tool(description="Export current session chat transcript as text or PDF.")
async def export_session_data(
    export_format: str = "text",
    include_metadata: bool = True,
) -> Dict[str, Any]:
    """Export session data in requested format."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"session_export_{timestamp}"

        if export_format == "text":
            filename += ".txt"
            content = "=== SESSION TRANSCRIPT ===\n"
            if include_metadata:
                content += f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += "\n".join(str(msg) for msg in conversation_history)
        elif export_format == "pdf":
            filename += ".pdf"
            content = "PDF export not yet implemented (requires reportlab)"
        else:
            return {"success": False, "error": "Unsupported format"}

        logger.info(f"Exported session data: {filename}")
        return {
            "success": True,
            "filename": filename,
            "format": export_format,
            "message_count": len(conversation_history),
            "preview": content[:200] + "..." if len(content) > 200 else content,
        }
    except Exception as e:
        logger.error(f"Error exporting session: {e}")
        return {"success": False, "error": str(e)}


@llm.function_tool(
    description="Recall specific information from the conversation (e.g., 'What was their email again?')."
)
async def recall_specific_info(query: str, contact_phone: Optional[str] = None) -> str:
    """Retrieve specific information from conversation or contact database."""
    try:
        if contact_phone:
            contact = DB.get_contact_by_phone(contact_phone)
            if contact:
                if "email" in query.lower():
                    return f"Email: {contact.email or 'Not recorded'}"
                if "phone" in query.lower():
                    return f"Phone: {contact.phone_number}"
                if "name" in query.lower():
                    return f"Name: {contact.name}"
                if "message" in query.lower():
                    return f"Message: {contact.message or 'No message recorded'}"
                return (
                    f"Contact Info for {contact.name}:\n"
                    f"Phone: {contact.phone_number}\n"
                    f"Email: {contact.email}\n"
                    f"Message: {contact.message}"
                )

        for item in conversation_history:
            if query.lower() in str(item).lower():
                return f"Found: {item}"

        return "Information not found in current session."
    except Exception as e:
        logger.error(f"Error recalling info: {e}")
        return f"Failed to recall: {e}"
