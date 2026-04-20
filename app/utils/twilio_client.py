import json
from twilio.rest import Client
from app.config import settings
from app.utils.logger import logger
from app.utils.whatsapp_interactive import InteractivePrompt

def get_twilio_client() -> Client:
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)

def _normalize_whatsapp_to(to: str) -> str:
    if to.startswith("whatsapp:"):
        return to
    return f"whatsapp:{to}"

def _trim_text(value: str, max_len: int) -> str:
    normalized = " ".join((value or "").split()).strip()
    if not normalized:
        return "Option"
    return normalized[:max_len]

def _build_quick_reply_variables(prompt: InteractivePrompt) -> dict[str, str]:
    return {
        "1": _trim_text(prompt.prompt, 1024),
        "2": _trim_text(prompt.options[0] if len(prompt.options) > 0 else "Yes", 20),
        "3": _trim_text(prompt.options[1] if len(prompt.options) > 1 else "No", 20),
    }

def _build_list_picker_variables(prompt: InteractivePrompt) -> dict[str, str]:
    # Template placeholders are fixed. We send exactly 1..(1+slots).
    slots = max(2, min(10, int(settings.twilio_whatsapp_list_picker_option_slots)))
    trimmed_options = [_trim_text(opt, 24) for opt in prompt.options[:slots]]
    while len(trimmed_options) < slots:
        trimmed_options.append(f"Option {len(trimmed_options) + 1}")

    variables = {"1": _trim_text(prompt.prompt, 1024)}
    for idx, option in enumerate(trimmed_options, start=2):
        variables[str(idx)] = option
    return variables

def _build_list_picker_variable_candidates(prompt: InteractivePrompt) -> list[dict[str, str]]:
    """
    Build multiple candidate variable maps to handle unknown template placeholder counts.
    Twilio 21656 is commonly caused by sending keys that do not match template variables.
    """
    configured_slots = max(1, min(10, int(settings.twilio_whatsapp_list_picker_option_slots)))
    start_slots = configured_slots
    named_keys_raw = (settings.twilio_whatsapp_list_picker_variable_keys or "").strip()
    named_keys = [k.strip() for k in named_keys_raw.split(",") if k.strip()]
    button_key = (settings.twilio_whatsapp_list_picker_button_variable_key or "").strip()
    button_text = _trim_text(settings.twilio_whatsapp_list_picker_button_text, 20)

    candidates: list[dict[str, str]] = []
    for slots in range(start_slots, 0, -1):
        trimmed_options = [_trim_text(opt, 24) for opt in prompt.options[:slots]]
        while len(trimmed_options) < slots:
            trimmed_options.append(f"Option {len(trimmed_options) + 1}")

        if named_keys:
            # If a button variable key is configured, expected key order is:
            # prompt, button(optional), option1, option2...
            selected_count = slots + 1 + (1 if button_key else 0)
            selected_keys = named_keys[:selected_count]
            variables = {selected_keys[0]: _trim_text(prompt.prompt, 1024)}
            option_start_index = 1
            if button_key and len(selected_keys) > 1:
                variables[selected_keys[1]] = button_text
                option_start_index = 2
            for idx, option in enumerate(trimmed_options, start=option_start_index):
                if idx >= len(selected_keys):
                    break
                variables[selected_keys[idx]] = option
        else:
            variables = {"1": _trim_text(prompt.prompt, 1024)}
            if button_key:
                variables[button_key] = button_text
            for idx, option in enumerate(trimmed_options, start=2):
                variables[str(idx)] = option
        candidates.append(variables)

    # De-duplicate maps in case multiple loops generated identical payloads.
    unique: list[dict[str, str]] = []
    seen = set()
    for c in candidates:
        key = tuple(sorted(c.items()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique

def send_whatsapp_message(to: str, message: str) -> str:
    """
    Sends a WhatsApp message using Twilio's API.
    `to` should be in E.164 format (e.g., 'whatsapp:+1234567890').
    """
    try:
        client = get_twilio_client()
        to = _normalize_whatsapp_to(to)
            
        msg = client.messages.create(
            from_=settings.twilio_whatsapp_from,
            body=message,
            to=to
        )
        logger.info("Sent WhatsApp message", extra={"sid": msg.sid, "to": to})
        return msg.sid
    except Exception as e:
        logger.error("Failed to send WhatsApp message", extra={"error": str(e), "to": to})
        raise

def _send_whatsapp_content_template(to: str, content_sid: str, content_variables: dict[str, str]) -> str:
    client = get_twilio_client()
    to = _normalize_whatsapp_to(to)
    if settings.twilio_log_content_variables:
        logger.info(
            "Twilio content template payload",
            extra={
                "to": to,
                "content_sid": content_sid,
                "content_variables": content_variables,
            },
        )
    msg = client.messages.create(
        from_=settings.twilio_whatsapp_from,
        to=to,
        content_sid=content_sid,
        content_variables=json.dumps(content_variables),
    )
    logger.info("Sent WhatsApp content template", extra={"sid": msg.sid, "to": to, "content_sid": content_sid})
    return msg.sid

def send_whatsapp_interactive(to: str, prompt: InteractivePrompt) -> str:
    """
    Sends WhatsApp interactive content via Twilio Content Templates when configured.
    Falls back to plain text if interactive templates are not configured.
    """
    quick_reply_sid = settings.twilio_whatsapp_quick_reply_content_sid
    list_picker_sid = settings.twilio_whatsapp_list_picker_content_sid

    try:
        if prompt.kind == "yes_no" and quick_reply_sid:
            variables = _build_quick_reply_variables(prompt)
            return _send_whatsapp_content_template(to, quick_reply_sid, variables)

        if prompt.kind == "list" and list_picker_sid:
            candidates = _build_list_picker_variable_candidates(prompt)
            last_error: Exception | None = None
            for variables in candidates:
                try:
                    return _send_whatsapp_content_template(to, list_picker_sid, variables)
                except Exception as list_err:
                    last_error = list_err
                    logger.warning(
                        "List template candidate failed",
                        extra={
                            "to": to,
                            "content_sid": list_picker_sid,
                            "candidate_keys": list(variables.keys()),
                            "candidate_variables": variables if settings.twilio_log_content_variables else None,
                            "error": str(list_err),
                        },
                    )
            if last_error:
                raise last_error
    except Exception as template_err:
        logger.warning(
            "Interactive template send failed, falling back to plain text",
            extra={"error": str(template_err), "to": to, "kind": prompt.kind},
        )

    fallback_lines = [prompt.prompt, ""]
    for idx, option in enumerate(prompt.options, start=1):
        fallback_lines.append(f"{idx}. {option}")
    fallback_lines.append("")
    fallback_lines.append("Reply with the option number or text.")
    return send_whatsapp_message(to, "\n".join(fallback_lines))
