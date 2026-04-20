import re


def _extract_text_field(message: str, key: str) -> str:
    """
    Extract free text after keys like:
    - win finished chapter 3
    - blocker phone distraction
    - note felt scattered
    Stops at the next comma/semicolon or end-of-line.
    """
    pattern = rf"\b{key}\b\s*[:=-]?\s*(.+?)(?=(?:\s*,\s*|\s*;\s*|$))"
    match = re.search(pattern, message, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_checkin_message(message: str) -> dict | None:
    """
    Parse compact check-in style text.
    Expected examples:
    - mood 7 energy 6 sleep 7.5 win finished assignment blocker phone distraction
    - mood:8, energy:5, sleep:6, note headache

    Returns parsed payload dict for momentum tool or None if not a check-in message.
    """
    mood_match = re.search(r"\bmood\b\s*[:=-]?\s*(\d{1,2})\b", message, flags=re.IGNORECASE)
    energy_match = re.search(r"\benergy\b\s*[:=-]?\s*(\d{1,2})\b", message, flags=re.IGNORECASE)

    # Require both mood and energy to avoid accidental misclassification.
    if not mood_match or not energy_match:
        return None

    sleep_match = re.search(r"\bsleep\b\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?)\b", message, flags=re.IGNORECASE)

    payload = {
        "mood": int(mood_match.group(1)),
        "energy": int(energy_match.group(1)),
        "sleep_hours": float(sleep_match.group(1)) if sleep_match else 0.0,
        "daily_win": _extract_text_field(message, "win"),
        "blocker": _extract_text_field(message, "blocker"),
        "note": _extract_text_field(message, "note"),
    }
    return payload
