import re
from typing import Any, Dict

from livekit.agents import llm

from .common import DB, logger
from .contact_management import format_phone_number


@llm.function_tool(description="Verify if an email address has valid syntax.")
async def verify_email_format(email: str) -> Dict[str, Any]:
    """Validate email format with detailed feedback."""
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    is_valid = bool(re.match(email_pattern, email))

    feedback = []
    if not is_valid:
        if "@" not in email:
            feedback.append("Missing '@' symbol")
        if not email.split("@")[-1]:
            feedback.append("Missing domain")
        if "." not in email.split("@")[-1]:
            feedback.append("Domain missing extension (e.g., .com)")

    return {
        "email": email,
        "valid": is_valid,
        "feedback": feedback if feedback else ["Email format is valid!"],
    }


@llm.function_tool(description="Clean contact data by removing duplicates and fixing formatting.")
async def clean_contact_data() -> Dict[str, Any]:
    """Clean and deduplicate contact database."""
    try:
        contacts = DB.get_all_contacts()
        if not contacts:
            return {
                "success": True,
                "message": "No contacts to clean",
                "stats": {"removed_duplicates": 0},
            }

        seen_phones = {}
        duplicates = []

        for contact in contacts:
            formatted_phone = await format_phone_number(contact.phone_number)

            if formatted_phone in seen_phones:
                duplicates.append(contact.id)
            else:
                seen_phones[formatted_phone] = contact.id
                contact.phone_number = formatted_phone
                contact.email = contact.email.lower() if contact.email else None
                DB.save_contact_details(contact)

        logger.info(f"Cleaned database: removed {len(duplicates)} duplicates")
        return {
            "success": True,
            "stats": {
                "total_contacts": len(contacts),
                "removed_duplicates": len(duplicates),
                "duplicate_ids": duplicates,
            },
            "message": f"Cleaned {len(contacts)} contacts, removed {len(duplicates)} duplicates",
        }
    except Exception as e:
        logger.error(f"Error cleaning contacts: {e}")
        return {"success": False, "error": str(e)}
