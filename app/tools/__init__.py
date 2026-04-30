from __future__ import annotations

from typing import Any
from langchain_core.tools import BaseTool

from app.tools.calendar_tool import create_event, list_events
from app.tools.email_tool import send_email, draft_email
from app.tools.whatsapp_tool import send_whatsapp
from app.tools.task_tool import create_reminder, list_tasks, complete_task, assign_task
from app.tools.search_tool import web_search
from app.tools.service_discovery_tool import find_local_services
from app.tools.briefing_tool import get_daily_briefing
from app.tools.intel_tool import get_morning_intel
from app.tools.expense_tool import log_expense, get_expense_summary
from app.tools.habit_tool import track_habit, get_habit_status
from app.tools.solver_tool import solve_life_problem
from app.tools.momentum_tool import log_daily_checkin, get_momentum_dashboard
from app.tools.profile_tool import update_user_location

# Grouped catalog makes extensions easier and keeps registrations organized.
AGENT_TOOL_GROUPS: dict[str, list[BaseTool]] = {
    "calendar": [create_event, list_events],
    "messaging": [send_whatsapp],
    "email": [send_email, draft_email],
    "tasks": [create_reminder, list_tasks, complete_task, assign_task],
    "discovery": [find_local_services, web_search],
    "briefing": [get_daily_briefing, get_morning_intel],
    "finance": [log_expense, get_expense_summary],
    "habits": [track_habit, get_habit_status],
    "momentum": [log_daily_checkin, get_momentum_dashboard],
    "strategy": [solve_life_problem],
    "profile": [update_user_location],
}

# Flat list consumed by the orchestrator.
agent_tools: list[BaseTool] = [
    tool for group_tools in AGENT_TOOL_GROUPS.values() for tool in group_tools
]


def inject_user_context(tool: BaseTool, tool_args: dict[str, Any], user_phone: str) -> dict[str, Any]:
    """Auto-fill common identity fields expected by tools."""
    tool_arg_names = set((tool.args or {}).keys())

    if "phone_number" in tool_arg_names and not tool_args.get("phone_number"):
        tool_args["phone_number"] = user_phone
    if "user_phone" in tool_arg_names and not tool_args.get("user_phone"):
        tool_args["user_phone"] = user_phone

    return tool_args
