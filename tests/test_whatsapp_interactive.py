from app.utils.whatsapp_interactive import detect_interactive_prompt, extract_interactive_user_input


def test_detect_yes_no_prompt():
    prompt = detect_interactive_prompt("Should I go ahead? Reply YES or NO")
    assert prompt is not None
    assert prompt.kind == "yes_no"
    assert prompt.options == ["Yes", "No"]
    assert "Reply YES or NO" not in prompt.prompt


def test_detect_go_ahead_confirmation_prompt():
    prompt = detect_interactive_prompt("Should I go ahead?")
    assert prompt is not None
    assert prompt.kind == "yes_no"
    assert prompt.options == ["Yes", "No"]
    assert prompt.prompt == "Should I go ahead?"


def test_detect_numbered_options_prompt():
    msg = (
        "I found 3 good options. Please choose one:\n"
        "1. Apollo Hospital\n"
        "2. Fortis Hospital\n"
        "3. Max Healthcare"
    )
    prompt = detect_interactive_prompt(msg)
    assert prompt is not None
    assert prompt.kind == "list"
    assert prompt.options == ["Apollo Hospital", "Fortis Hospital", "Max Healthcare"]


def test_detect_numbered_options_without_choose_hint():
    msg = (
        "Top options for your request:\n"
        "1. Dr. Mehta Clinic\n"
        "2. City Care Hospital\n"
        "3. Apollo Diagnostics"
    )
    prompt = detect_interactive_prompt(msg)
    assert prompt is not None
    assert prompt.kind == "list"
    assert prompt.options == ["Dr. Mehta Clinic", "City Care Hospital", "Apollo Diagnostics"]


def test_detect_option_keyword_format():
    msg = (
        "Here are the options:\n"
        "Option 1: Gmail Draft\n"
        "Option 2: Send Immediate\n"
        "Option 3: Cancel"
    )
    prompt = detect_interactive_prompt(msg)
    assert prompt is not None
    assert prompt.kind == "list"
    assert prompt.options == ["Gmail Draft", "Send Immediate", "Cancel"]


def test_extract_user_input_prefers_button_text():
    value = extract_interactive_user_input(
        body="",
        button_text="Yes",
        button_payload="confirm_yes",
        list_title=None,
        list_id=None,
        interactive_data=None,
    )
    assert value == "Yes"


def test_extract_user_input_falls_back_to_body():
    value = extract_interactive_user_input(body="No")
    assert value == "No"


def test_extract_user_input_from_nested_interactive_data():
    payload = '{"list_reply":{"id":"opt_2","title":"City Care Hospital"}}'
    value = extract_interactive_user_input(body="", interactive_data=payload)
    assert value == "City Care Hospital"
