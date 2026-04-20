from unittest.mock import MagicMock, patch


def test_meeting_scheduling_flow():
    """Calendar event creation should return success with generated link."""
    with patch("app.tools.calendar_tool.get_calendar_service") as mock_service_fn:
        mock_service = MagicMock()
        mock_service_fn.return_value = mock_service
        mock_service.events().list().execute.return_value = {"items": []}
        mock_service.events().insert().execute.return_value = {
            "htmlLink": "http://mock.calendar.link"
        }

        from app.tools.calendar_tool import create_event
        result = create_event.invoke({
            "title": "Meeting with Priya",
            "start_datetime": "2026-05-01T15:00:00Z",
            "end_datetime": "2026-05-01T16:00:00Z"
        })

        assert "Meeting with Priya" in result
        assert "http://mock.calendar.link" in result


def test_conflict_detection():
    """When conflict exists, tool should return a conflict message."""
    with patch("app.tools.calendar_tool.get_calendar_service") as mock_service_fn:
        mock_service = MagicMock()
        mock_service_fn.return_value = mock_service
        mock_service.events().list().execute.return_value = {
            "items": [{"summary": "Existing Meeting"}]
        }

        from app.tools.calendar_tool import create_event
        result = create_event.invoke({
            "title": "Another Meeting",
            "start_datetime": "2026-05-01T15:00:00Z",
            "end_datetime": "2026-05-01T16:00:00Z"
        })

        assert "Scheduling Conflict" in result
        assert "Existing Meeting" in result


def test_safety_guard_roundtrip():
    """Pending action should be stored and cleared in SafetyGuard."""
    from app.agents.safety_guard import SafetyGuard
    guard = SafetyGuard()
    phone = "+1234567890"
    payload = {"intent": "send_email", "entities": {"to": "x@y.com"}}

    guard.set_pending_action(phone, payload, "send this email")
    pending = guard.get_pending_action(phone)
    assert pending is not None
    assert pending["intent"] == "send_email"

    guard.clear_pending_action(phone)
    assert guard.get_pending_action(phone) is None
