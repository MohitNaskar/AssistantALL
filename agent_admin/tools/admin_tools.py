import hashlib
import time
from functools import wraps

from livekit.agents import llm
from .common import DB, logger

import os

ADMIN_PHONE_HASH = os.getenv("ADMIN_PHONE_HASH")
ADMIN_SECRET_TOKEN = os.getenv("ADMIN_SECRET_TOKEN")

# Load admin credentials from env; deny all admin access when misconfigured.
ADMIN_CREDENTIALS = {}
if ADMIN_PHONE_HASH and ADMIN_SECRET_TOKEN:
    ADMIN_CREDENTIALS[ADMIN_PHONE_HASH] = ADMIN_SECRET_TOKEN
else:
    logger.error(
        "Admin auth is not configured. Set ADMIN_PHONE_HASH and ADMIN_SECRET_TOKEN."
    )

# rate limiting tracker
RATE_LIMIT = {}
MAX_ATTEMPTS = 3
LOCKDOWN_DURATION = 300  # Time window in seconds

def hash_phone(phone: str) -> str:
    """Hash the phone number using SHA-256."""
    normalized_phone = phone.strip()
    return hashlib.sha256(normalized_phone.encode("utf-8")).hexdigest()


def _update_rate_limit(phone_hash: str):
    """Track failed attempts."""
    if phone_hash not in RATE_LIMIT:
        RATE_LIMIT[phone_hash] = (1, time.time())
    else:
        attempts, _ = RATE_LIMIT[phone_hash]
        RATE_LIMIT[phone_hash] = (attempts + 1, time.time())


def _is_locked(phone_hash: str) -> bool:
    if phone_hash not in RATE_LIMIT:
        return False

    attempts, last_attempt = RATE_LIMIT[phone_hash]
    within_window = (time.time() - last_attempt) < LOCKDOWN_DURATION
    return within_window and attempts >= MAX_ATTEMPTS

def admin_only(func):
    """Decorator requiring admin_phone + admin_token for access."""
    @wraps(func)
    async def wrapper(admin_phone: str, admin_token: str, *args, **kwargs):
        if not ADMIN_CREDENTIALS:
            return "Admin access is unavailable due to server configuration."

        phone_hash = hash_phone(admin_phone)

        # Check rate limiting
        if _is_locked(phone_hash):
            logger.warning(f"Account {phone_hash} locked due to too many failed attempts")
            return "Too many failed attempts. Account locked for 5 minutes."

        # Verify credentials
        if phone_hash not in ADMIN_CREDENTIALS:
            logger.warning(f"Unauthorized access attempt - invalid phone: {phone_hash}")
            _update_rate_limit(phone_hash)
            return "Access denied. Invalid credentials."

        if ADMIN_CREDENTIALS[phone_hash] != admin_token:
            logger.warning(f"Unauthorized access attempt - invalid token for {phone_hash}")
            _update_rate_limit(phone_hash)
            return "Access denied. Invalid credentials."

        # Reset rate limit on success
        RATE_LIMIT[phone_hash] = (0, time.time())
        logger.info(f"Admin {phone_hash} accessed function: {func.__name__}")

        return await func(*args, **kwargs)

    return wrapper


# function to retrieve all the data from the database and list all contacts
@llm.function_tool(description="List all saved contacts in the database (admin only).")
@admin_only
async def list_all_contacts(
    admin_phone: str,
    admin_token: str,
    include_messages: bool = False,
) -> str:
    """List all contacts with basic info."""
    try:
        contacts = DB.get_all_contacts()

        if not contacts:
            return "No contacts found in database."

        contact_list = "All Contacts:\n"
        for idx, contact in enumerate(contacts, 1):
            contact_list += (
                f"\n{idx}. {contact.name}\n"
                f"   Phone: {contact.phone_number}\n"
                f"   Email: {contact.email or 'N/A'}\n"
            )
            if include_messages and contact.message:
                contact_list += f"   Message: {contact.message}\n"

        logger.info(f"Listed {len(contacts)} contacts")
        return contact_list
    except Exception as e:
        logger.error(f"Error listing contacts: {e}")
        return f"Failed to retrieve contacts: {e}"
    

# function to get the details using the phone number from the database
@llm.function_tool(description="Get contact details by phone number (admin only).")
@admin_only
async def get_contact_details_by_phone(
    admin_phone: str,
    admin_token: str,
    phone_number: str,
) -> str:
    """Retrieve contact details by phone number."""
    try:
        contact = DB.get_contact_by_phone(phone_number)
        if not contact:
            return f"No contact found with phone number: {phone_number}"

        details = (
            f"Contact Details:\n"
            f"Name: {contact.name}\n"
            f"Phone: {contact.phone_number}\n"
            f"Email: {contact.email or 'N/A'}\n"
            f"Message: {contact.message or 'N/A'}\n"
        )
        logger.info(f"Retrieved contact details for phone number: {phone_number}")
        return details
    except Exception as e:
        logger.error(f"Error retrieving contact details: {e}")
        return f"Failed to retrieve contact details: {e}"