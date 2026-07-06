from typing import Any, Dict

from livekit.agents import llm

from .common import logger


@llm.function_tool(description="Generate a professional email template.")
async def draft_email(recipient_name: str, subject: str, purpose: str) -> str:
    """Generate a professional email template."""
    email_template = f"""
Subject: {subject}

Dear {recipient_name},

Thank you for your time and interest in connecting.

Purpose: {purpose}

I look forward to hearing from you.

Best regards,
Mohit Sharma
"""
    logger.info(f"Generated email draft for {recipient_name}")
    return email_template.strip()


@llm.function_tool(description="Create an SMS or message template.")
async def draft_message(recipient_name: str, message_type: str, content_hint: str) -> str:
    """Generate message template for SMS or chat."""
    messages = {
        "followup": f"Hi {recipient_name}, just following up on our conversation about {content_hint}. Let me know if you'd like to discuss further!",
        "greeting": f"Hi {recipient_name}, great connecting with you! Looking forward to {content_hint}.",
        "inquiry": f"Hi {recipient_name}, I'm reaching out regarding {content_hint}. Would love to chat more!",
        "thank_you": f"Thank you {recipient_name} for taking the time to discuss {content_hint}. Talk soon!",
    }

    template = messages.get(message_type, f"Hi {recipient_name}, {content_hint}")
    logger.info(f"Generated {message_type} message for {recipient_name}")
    return template


@llm.function_tool(description="Schedule a follow-up reminder for contacting someone.")
async def schedule_followup(
    contact_name: str,
    phone_number: str,
    followup_date: str,
    reminder_type: str = "call",
) -> Dict[str, Any]:
    """Schedule a follow-up reminder."""
    try:
        reminder_text = (
            f"Reminder: {reminder_type.capitalize()} {contact_name} "
            f"({phone_number}) on {followup_date}"
        )

        logger.info(f"Scheduled followup: {reminder_text}")

        return {
            "success": True,
            "reminder": reminder_text,
            "contact": contact_name,
            "date": followup_date,
            "type": reminder_type,
        }
    except Exception as e:
        logger.error(f"Error scheduling followup: {e}")
        return {"success": False, "error": str(e)}
