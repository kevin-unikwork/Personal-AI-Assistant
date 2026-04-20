from app.agents.checkin_parser import parse_checkin_message


def test_parse_checkin_message_compact():
    msg = "mood 7 energy 5 sleep 6.5 win finished project blocker phone distractions note felt better after walk"
    parsed = parse_checkin_message(msg)

    assert parsed is not None
    assert parsed["mood"] == 7
    assert parsed["energy"] == 5
    assert parsed["sleep_hours"] == 6.5
    assert "finished project" in parsed["daily_win"]


def test_parse_checkin_message_non_checkin():
    msg = "Please schedule a meeting tomorrow at 3 pm"
    parsed = parse_checkin_message(msg)
    assert parsed is None
