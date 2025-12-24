from datetime import datetime
from typing import List, Dict


def format_welcome_message() -> str:
    """Format the welcome message for /start command"""
    return """Welcome to InterviewAlarm Bot!

I help you track interview scheduling pages and notify you when new time slots become available.

Commands:
/start - Show this help message
/add <url> - Start tracking a needle.co.il interview page
/list - Show all your tracked URLs
/remove <url> - Stop tracking a URL

How it works:
1. Send me a needle.co.il interview scheduling URL using /add
2. I'll show you the available time slots
3. I'll check every 5 minutes for new slots
4. You'll get notified immediately when new slots appear!

Example:
/add https://needle.co.il/candidate-slots/1d22a516-a3a5-4f9a-a2c2-896eddea945e"""


def format_slot_summary(company_name: str, url: str, slots: List[Dict]) -> str:
    """
    Format a summary of available time slots

    Args:
        company_name: Name of the company
        url: The interview scheduling URL
        slots: List of time slot dictionaries with start_time and end_time
    """
    if not slots:
        return f"""**{company_name}**

No available time slots found.

URL: {url}"""

    # Format slots
    formatted_slots = []
    for slot in slots[:20]:  # Limit to first 20 slots
        start_dt = parse_iso_datetime(slot['start_time'])
        end_dt = parse_iso_datetime(slot['end_time'])

        if start_dt and end_dt:
            date_str = start_dt.strftime("%Y-%m-%d")
            start_time = start_dt.strftime("%H:%M")
            end_time = end_dt.strftime("%H:%M")
            formatted_slots.append(f"  {date_str} | {start_time} - {end_time}")

    slots_text = "\n".join(formatted_slots)

    if len(slots) > 20:
        slots_text += f"\n  ... and {len(slots) - 20} more slots"

    return f"""**{company_name}**

Available time slots ({len(slots)} total):
{slots_text}

URL: {url}

I'm now monitoring this URL. You'll be notified when new slots appear!"""


def format_new_slot_notification(company_name: str, url: str, new_slots: List[Dict]) -> str:
    """
    Format notification message for new time slots

    Args:
        company_name: Name of the company
        url: The interview scheduling URL
        new_slots: List of new time slot dictionaries
    """
    if not new_slots:
        return ""

    # Format new slots
    formatted_slots = []
    for slot in new_slots[:10]:  # Limit to first 10 new slots
        start_dt = parse_iso_datetime(slot['start_time'])
        end_dt = parse_iso_datetime(slot['end_time'])

        if start_dt and end_dt:
            date_str = start_dt.strftime("%Y-%m-%d")
            start_time = start_dt.strftime("%H:%M")
            end_time = end_dt.strftime("%H:%M")
            formatted_slots.append(f"  {date_str} | {start_time} - {end_time}")

    slots_text = "\n".join(formatted_slots)

    if len(new_slots) > 10:
        slots_text += f"\n  ... and {len(new_slots) - 10} more new slots"

    return f"""**NEW TIME SLOTS AVAILABLE!**

Company: {company_name}

New slots ({len(new_slots)}):
{slots_text}

Book now: {url}"""


def format_tracked_urls_list(tracked_urls: List[Dict]) -> str:
    """
    Format list of tracked URLs

    Args:
        tracked_urls: List of tracked URL dictionaries from database
    """
    if not tracked_urls:
        return """You're not tracking any URLs yet.

Use /add <url> to start tracking an interview page."""

    urls_list = []
    for i, tracked_url in enumerate(tracked_urls, 1):
        company = tracked_url.get('company_name', 'Unknown')
        url = tracked_url['url']
        # Shorten URL for display
        short_url = url[:50] + "..." if len(url) > 50 else url
        urls_list.append(f"{i}. **{company}**\n   {short_url}")

    return f"""You're tracking {len(tracked_urls)} URL(s):

{chr(10).join(urls_list)}

Use /remove <url> to stop tracking a URL."""


def format_error_message(error: str) -> str:
    """Format an error message"""
    return f"Error: {error}"


def format_success_message(message: str) -> str:
    """Format a success message"""
    return f"{message}"


def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO 8601 datetime string"""
    try:
        # Handle ISO string with Z suffix
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'
        return datetime.fromisoformat(iso_string)
    except Exception:
        return None
