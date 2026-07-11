import re
from typing import Any

from langchain_core.tools import tool

from tools.common import get_db, logger


@tool
def validate_contact_info(email: str, phone_number: str) -> dict[str, Any]:
    """Validate email and phone number format before saving.

    Args:
        email: Email address to validate.
        phone_number: Phone number to validate (10-15 digits, spaces/dashes/parens allowed).

    Returns:
        Dict with 'valid' (bool) and 'errors' (list of strings).
    """
    errors = []

    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email.strip()):
        errors.append(f"Invalid email format: {email}")

    if not re.match(r"^[\d\s\-\+\(\)]{10,15}$", phone_number.strip()):
        errors.append(f"Invalid phone format: {phone_number}")

    return {"valid": len(errors) == 0, "errors": errors}


@tool
def format_phone_number(phone_number: str) -> str:
    """Format a phone number to a standard (xxx) xxx-xxxx or +1 (xxx) xxx-xxxx form.

    Args:
        phone_number: Raw phone number string.

    Returns:
        Formatted phone string, or the original if it cannot be normalized.
    """
    digits = re.sub(r"\D", "", phone_number.strip())

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    if len(digits) == 11:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return phone_number


@tool
def check_duplicate_contact(phone_number: str, email: str) -> dict[str, Any]:
    """Check if a contact with the given phone number or email already exists.

    Args:
        phone_number: Phone number to check.
        email: Email address to check.

    Returns:
        Dict with 'exists' (bool), 'reason' ('phone'|'email'|None), and 'message' (str).
    """
    formatted_phone = format_phone_number.invoke({"phone_number": phone_number})
    formatted_email = email.strip().lower()

    conn = get_db()
    try:
        phone_row = conn.execute(
            "SELECT name, phone_number, email FROM contacts WHERE phone_number = ?",
            (formatted_phone,),
        ).fetchone()

        if phone_row:
            return {
                "exists": True,
                "reason": "phone",
                "message": (
                    f"This phone number is already registered to "
                    f"{phone_row['name']} ({phone_row['phone_number']})."
                ),
            }

        email_row = conn.execute(
            "SELECT name, phone_number, email FROM contacts WHERE email = ?",
            (formatted_email,),
        ).fetchone()

        if email_row:
            return {
                "exists": True,
                "reason": "email",
                "message": (
                    f"This email is already registered to "
                    f"{email_row['name']} ({email_row['email']})."
                ),
            }

        return {"exists": False, "reason": None, "message": "No duplicate found."}
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        return {"exists": None, "reason": "error", "message": str(e)}
    finally:
        conn.close()


@tool
def store_user_data(
    name: str,
    phone_number: str,
    email: str,
    message: str = "",
) -> str:
    """Validate and store a user's contact details in the database.

    Runs validation and duplicate checks before inserting. Returns a plain
    English success or failure message suitable for speaking aloud.

    Args:
        name: Full name of the contact.
        phone_number: Phone number (any common format).
        email: Email address.
        message: Optional message or note left by the contact.

    Returns:
        A plain-text result string.
    """
    validation = validate_contact_info.invoke({"email": email, "phone_number": phone_number})
    if not validation["valid"]:
        issues = "; ".join(validation["errors"])
        logger.warning(f"Validation failed: {issues}")
        return f"Please re-enter valid contact details. {issues}"

    formatted_phone = format_phone_number.invoke({"phone_number": phone_number})

    duplicate = check_duplicate_contact.invoke({"phone_number": formatted_phone, "email": email})
    if duplicate.get("exists"):
        reason = duplicate.get("reason")
        logger.warning(f"Duplicate contact ({reason}): {duplicate.get('message')}")
        if reason == "phone":
            return (
                "That phone number is already registered. "
                "Please share a different phone number or email."
            )
        if reason == "email":
            return (
                "That email is already registered. "
                "Please share a different email or phone number."
            )
        return "Your contact is already registered. Please re-enter different contact details."

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO contacts (name, phone_number, email, message) VALUES (?, ?, ?, ?)",
            (name.strip(), formatted_phone, email.strip().lower(), message.strip()),
        )
        conn.commit()
        logger.info(f"Stored contact: {name}, {formatted_phone}, {email}")
        return "Contact saved successfully."
    except Exception as e:
        logger.error(f"Error storing contact: {e}")
        return f"Failed to save contact: {e}"
    finally:
        conn.close()


@tool
def get_all_contacts() -> list[dict]:
    """Retrieve all saved contacts from the database.

    Admin-only — only call after admin credentials have been verified.

    Returns:
        List of contact dicts with id, name, phone_number, email, message, created_at.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, name, phone_number, email, message, created_at FROM contacts ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@tool
def search_contact(query: str) -> list[dict]:
    """Search contacts by name, email, or phone number (partial match).

    Args:
        query: Search string matched against name, email, and phone_number fields.

    Returns:
        List of matching contact dicts. Empty list if nothing matches.
    """
    conn = get_db()
    like = f"%{query.strip()}%"
    try:
        rows = conn.execute(
            """
            SELECT id, name, phone_number, email, message, created_at FROM contacts
            WHERE name LIKE ? OR email LIKE ? OR phone_number LIKE ?
            ORDER BY name
            """,
            (like, like, like),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
