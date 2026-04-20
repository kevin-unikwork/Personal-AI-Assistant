from app.utils.whatsapp_interactive import InteractivePrompt
from app.utils.twilio_client import (
    _build_list_picker_variables,
    _build_quick_reply_variables,
    _build_list_picker_variable_candidates,
)


def test_build_quick_reply_variables_trims_lengths():
    prompt = InteractivePrompt(
        prompt="Should I go ahead with this very long action details " * 50,
        options=["Absolutely Yes Please Confirm", "No Cancel This"],
        kind="yes_no",
    )
    variables = _build_quick_reply_variables(prompt)
    assert set(variables.keys()) == {"1", "2", "3"}
    assert len(variables["1"]) <= 1024
    assert len(variables["2"]) <= 20
    assert len(variables["3"]) <= 20


def test_build_list_picker_variables_uses_fixed_slots(monkeypatch):
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_option_slots", 3)
    prompt = InteractivePrompt(
        prompt="Please choose a hospital near your location",
        options=["Apollo Super Specialty Hospital", "Fortis Memorial Research Institute"],
        kind="list",
    )
    variables = _build_list_picker_variables(prompt)
    assert set(variables.keys()) == {"1", "2", "3", "4"}
    assert len(variables["2"]) <= 24
    assert len(variables["3"]) <= 24
    assert variables["4"].startswith("Option")


def test_build_list_picker_variable_candidates_descending_slots(monkeypatch):
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_option_slots", 4)
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_button_variable_key", "")
    prompt = InteractivePrompt(
        prompt="Choose one",
        options=["One", "Two", "Three"],
        kind="list",
    )
    candidates = _build_list_picker_variable_candidates(prompt)
    assert len(candidates) >= 3
    assert list(candidates[0].keys()) == ["1", "2", "3", "4", "5"]
    assert list(candidates[1].keys()) == ["1", "2", "3", "4"]


def test_build_list_picker_variable_candidates_named_keys(monkeypatch):
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_option_slots", 3)
    monkeypatch.setattr(
        "app.utils.twilio_client.settings.twilio_whatsapp_list_picker_variable_keys",
        "prompt,opt1,opt2,opt3",
    )
    prompt = InteractivePrompt(prompt="Choose one", options=["One", "Two"], kind="list")
    candidates = _build_list_picker_variable_candidates(prompt)
    assert "prompt" in candidates[0]
    assert "opt1" in candidates[0]


def test_build_list_picker_candidates_with_button_variable_key(monkeypatch):
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_option_slots", 4)
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_button_variable_key", "11")
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_button_text", "Choose")
    prompt = InteractivePrompt(prompt="Select a hospital", options=["A", "B", "C"], kind="list")
    candidates = _build_list_picker_variable_candidates(prompt)
    assert "11" in candidates[0]
    assert candidates[0]["11"] == "Choose"


def test_build_list_picker_candidates_with_named_keys_and_button_slot(monkeypatch):
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_option_slots", 4)
    monkeypatch.setattr(
        "app.utils.twilio_client.settings.twilio_whatsapp_list_picker_variable_keys",
        "1,11,2,3,4,5",
    )
    monkeypatch.setattr("app.utils.twilio_client.settings.twilio_whatsapp_list_picker_button_variable_key", "11")
    prompt = InteractivePrompt(prompt="Select", options=["A", "B", "C", "D"], kind="list")
    candidates = _build_list_picker_variable_candidates(prompt)
    assert set(candidates[0].keys()) == {"1", "11", "2", "3", "4", "5"}
