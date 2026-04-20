from app.tools import inject_user_context
from app.tools.task_tool import create_reminder
from app.agents.checkin_parser import parse_checkin_message


def test_inject_user_context_for_phone_number():
    args = {"title": "Task"}
    updated = inject_user_context(create_reminder, args, "+911234567890")
    assert updated["phone_number"] == "+911234567890"


def test_checkin_parser_extracts_mood_and_energy():
    parsed = parse_checkin_message("mood 8 energy 6 sleep 7 win finished report")
    assert parsed is not None
    assert parsed["mood"] == 8
    assert parsed["energy"] == 6
