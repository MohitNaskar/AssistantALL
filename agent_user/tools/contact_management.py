import re
from typing import Any, Dict

from livekit.agents import llm

from db_driver import Contact_details
from .common import DB, logger


import hashlib
import time
from typing import Any, Dict
from functools import wraps


# to store the data in the database
@llm.function_tool(description="Store user data in the database.")
async def store_user_data(
    name: str,
    phone_number: str,
    email: str,
    message: str,
    update_existing: bool = False,
) -> str:
    """Store user data in the database."""

    validation_result = await validate_contact_info(email, phone_number)
    if not validation_result["valid"]:
        issues = "; ".join(validation_result["errors"])
        logger.warning(f"Validation failed for user data: {issues}")
        return f"Please re-enter valid contact details. {issues}"

    formatted_phone = await format_phone_number(phone_number)
    duplicate = await check_duplicate_contact(formatted_phone, email)

    if duplicate.get("exists"):
        reason = duplicate.get("reason")
        logger.warning(f"Duplicate contact found ({reason}): {duplicate.get('message')}")

        if reason == "phone":
            return (
                "That phone number is already registered. "
                "For security reasons, I cannot update existing records. "
                "Please share a different phone number or a different email."
            )

        if reason == "email":
            return (
                "That email is already registered. "
                "For security reasons, I cannot update existing records. "
                "Please share a different email or a different phone number."
            )

        return (
            "Your contact is already registered. "
            "For security reasons, I cannot update existing records. "
            "Please re-enter different contact details."
        )

    try:
        contact_details = Contact_details(
            id=0,
            name=name,
            phone_number=formatted_phone,
            email=email.lower(),
            message=message,
        )
        DB.save_contact_details(contact_details)
        logger.info(f"Stored user data: {contact_details}")
        return "User data stored successfully."
    except Exception as e:
        logger.error(f"Error storing user data: {e}")
        return f"Failed to store user data: {e}"

# to validate the email and phone number format before saving
@llm.function_tool(description="Validate email and phone number format before saving.")
async def validate_contact_info(email: str, phone_number: str) -> Dict[str, Any]:
    """Validate email and phone number format."""
    errors = []

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        errors.append(f"Invalid email format: {email}")

    phone_pattern = r"^[\d\s\-\+\(\)]{10,15}$"
    if not re.match(phone_pattern, phone_number):
        errors.append(f"Invalid phone format: {phone_number}")

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "errors": []}

# to retrieve the contact information to check if the user already exists in the database
# Replace your current check_duplicate_contact with this reason-specific version
@llm.function_tool(description="Check if a contact with this phone number or email already exists.")
async def check_duplicate_contact(phone_number: str, email: str) -> Dict[str, Any]:
    """Check for duplicate contacts by phone number and email."""
    try:
        formatted_phone = await format_phone_number(phone_number)
        formatted_email = email.lower().strip()

        phone_contact = DB.get_contact_by_phone(formatted_phone)
        email_contact = DB.get_contact_by_email(formatted_email)

        if phone_contact:
            return {
                "exists": True,
                "reason": "phone",
                "message": (
                    f"This phone number is already registered to "
                    f"{phone_contact.name} ({phone_contact.phone_number})."
                ),
                "contact": {
                    "name": phone_contact.name,
                    "phone": phone_contact.phone_number,
                    "email": phone_contact.email,
                },
            }

        if email_contact:
            return {
                "exists": True,
                "reason": "email",
                "message": (
                    f"This email is already registered to "
                    f"{email_contact.name} ({email_contact.email})."
                ),
                "contact": {
                    "name": email_contact.name,
                    "phone": email_contact.phone_number,
                    "email": email_contact.email,
                },
            }

        return {"exists": False, "reason": None, "message": "No duplicate found"}

    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        return {"exists": None, "reason": "error", "error": str(e)}

# to format the phone number to a standard format before saving
@llm.function_tool(description="Auto-format phone number to standard format (xxx) xxx-xxxx.")
async def format_phone_number(phone_number: str) -> str:
    """Format phone number to standard format."""
    digits = re.sub(r"\D", "", phone_number)

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    if len(digits) == 11:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return phone_number

