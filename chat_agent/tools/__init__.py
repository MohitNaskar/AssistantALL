from tools.contact_management import (
    store_user_data,
    validate_contact_info,
    check_duplicate_contact,
    format_phone_number,
    get_all_contacts,
    search_contact,
)
from tools.intermediate_tools import google_search, get_news
from tools.session_management import summarize_conversation

all_tools = [
    store_user_data,
    validate_contact_info,
    check_duplicate_contact,
    format_phone_number,
    get_all_contacts,
    search_contact,
    google_search,
    get_news,
    summarize_conversation,
]
