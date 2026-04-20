import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class InteractivePrompt:
    prompt: str
    options: list[str]
    kind: str  # yes_no or list


_YES_NO_PATTERN = re.compile(r"reply\s+yes\s+or\s+no", flags=re.IGNORECASE)
_NUMBERED_OPTION_PATTERN = re.compile(r"^\s*(?:option\s*)?(\d{1,2})[\).:-]\s+(.+)$", flags=re.IGNORECASE)
_GO_AHEAD_PATTERN = re.compile(r"^\s*should\s+i\s+go\s+ahead\??\s*$", flags=re.IGNORECASE)


def _clean_prompt_text(message: str) -> str:
    cleaned = _YES_NO_PATTERN.sub("", message)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned

def _normalize_option_label(value: str) -> str:
    value = re.sub(r"^\s*[-*•]+\s*", "", value).strip()
    value = re.sub(r"\s+", " ", value)
    # Keep option text compact for WhatsApp interactive list titles.
    return value[:72].strip() or "Option"

def _extract_numbered_options(text: str) -> tuple[list[str], str]:
    lines = text.splitlines()
    prompt_lines: list[str] = []
    numbered: list[tuple[int, str]] = []

    for line in lines:
        match = _NUMBERED_OPTION_PATTERN.match(line)
        if match:
            idx = int(match.group(1))
            title = _normalize_option_label(match.group(2))
            numbered.append((idx, title))
        else:
            prompt_lines.append(line)

    if len(numbered) < 2:
        return [], text

    numbered.sort(key=lambda x: x[0])
    deduped: list[tuple[int, str]] = []
    seen = set()
    for idx, title in numbered:
        if idx in seen:
            continue
        seen.add(idx)
        deduped.append((idx, title))

    options = [title for _, title in deduped][:10]
    prompt = "\n".join(prompt_lines).strip() or "Please choose an option"
    return options, prompt


def detect_interactive_prompt(message: str) -> Optional[InteractivePrompt]:
    if not message:
        return None

    text = message.strip()
    lowered = text.lower()

    if _YES_NO_PATTERN.search(text) or "yes or no" in lowered or bool(_GO_AHEAD_PATTERN.match(text)):
        return InteractivePrompt(
            prompt=_clean_prompt_text(text) or "Should I go ahead?",
            options=["Yes", "No"],
            kind="yes_no",
        )

    options, prompt = _extract_numbered_options(text)
    if len(options) < 2:
        return None

    return InteractivePrompt(prompt=prompt, options=options, kind="list")


def extract_interactive_user_input(
    body: str = "",
    button_text: str | None = None,
    button_payload: str | None = None,
    list_title: str | None = None,
    list_id: str | None = None,
    interactive_data: str | None = None,
) -> str:
    # Prefer human-readable selected label over opaque payload/id.
    for value in [button_text, list_title, button_payload, list_id]:
        if value and value.strip():
            return value.strip()

    def _extract_from_nested(obj) -> str | None:
        if isinstance(obj, dict):
            for key in ["title", "text", "label", "name", "display_text"]:
                value = obj.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for key in ["payload", "id"]:
                value = obj.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for value in obj.values():
                nested = _extract_from_nested(value)
                if nested:
                    return nested
        elif isinstance(obj, list):
            for item in obj:
                nested = _extract_from_nested(item)
                if nested:
                    return nested
        return None

    if interactive_data:
        try:
            parsed = json.loads(interactive_data)
            nested_value = _extract_from_nested(parsed)
            if nested_value:
                return nested_value
        except Exception:
            pass

    return (body or "").strip()
