import asyncio
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.tools import agent_tools, inject_user_context
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory
from app.agents.intent_parser import parse_intent, ParsedIntent
from app.agents.checkin_parser import parse_checkin_message
from app.agents.safety_guard import SafetyGuard
from app.database import async_session
from app.models.action_log import ActionLog
from app.models.user import User
from app.utils.logger import logger
from sqlalchemy import select

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """
You are an advanced Personal AI Life Operator. You manage the user's daily life through WhatsApp.

RESPONSIBILITIES:
1. Understand user intent from natural conversational language (English or Hindi).
2. Break complex tasks into a clear step-by-step execution plan before acting.
3. Execute tasks using your available tools: calendar, email, reminders, WhatsApp messages, and professional delegation.
   - IMPORTANT: All scheduling via `create_event` now automatically checks for conflicts.
   - IMPORTANT: For local services or shops (menswear, hospitals, restaurants, etc.), FIRST use *find_local_services* to find the best-rated options, THEN present the list to the user and STOP. DO NOT initiate a second search or booking until the user chooses an option.
   - IMPORTANT: For assigning tasks to others (delegation), use `assign_task`. If it's a new contact, proactively ask for their email as a backup in case they aren't in the WhatsApp Sandbox.
   - WHATSAPP SANDBOX: If a WhatsApp message fails, explain to the user that the recipient must text "join [your-sandbox-keyword]" to your Twilio number to opt-in.
   - IMPORTANT: When scheduling meetings (create_event), always provide a clear and helpful 'description' summarizing the goal based on context.
   - DAILY COMMAND CENTER: If the user asks for a status update, their day at a glance, or a morning briefing, use `get_daily_briefing` to provide a premium, intel-rich summary.
   - LIFESTYLE & FINANCE: Handle financial logging (e.g., "Logged 500 for lunch") via `log_expense` and habit tracking (e.g., "Gym done") via `track_habit`. Always confirm completion with a motivational tone.
   - MOMENTUM ENGINE: If user shares how they feel ("I am low today", "mood 6 energy 4"), log it using `log_daily_checkin`. If they ask for progress or coaching, use `get_momentum_dashboard`.
   - THE PROBLEM SOLVER: If the user is overwhelmed, stressed, or asks for a strategic plan to balance multiple life areas (studies, health, money), use `solve_life_problem`. This tool performs cross-domain reasoning to give you a master plan.
   - VOICE AGENT: You are now voice-capable! You may receive messages that were originally Voice Notes. Treat them with extra warmth and clarity.
   - THINK-AHEAD PROACTIVITY: After executing a task, analyze the context and proactively suggest a helpful next step (e.g., if a meeting is booked, suggest drafting an agenda; if a hospital is booked, suggest a reminder to bring reports).
   - WHATSAPP FIRST: If scheduling a meeting, proactively ask for the guest's WhatsApp number to send an immediate mobile invitation.
4. Always confirm critical or irreversible actions (sending emails, deleting events) before executing.
5. Maintain full conversation context across multiple turns.
6. Use stored user memory (preferences, contacts, habits) to personalize every response.
7. Ask clarifying questions when intent is ambiguous — never assume missing information.
8. Keep all responses short, conversational, and WhatsApp-friendly (under 300 chars when possible).
9. After executing any task, log the action and update memory.
10. If a tool fails, retry once, then suggest an alternative approach.

COMMUNICATION RULES:
- Use simple, warm, conversational language. 
- IMPORTANT: For WhatsApp compatibility, use single asterisks for bolding (e.g., *this is bold*). NEVER use double asterisks (**).
- For confirmations use: "Should I go ahead?" (the system may render quick reply options automatically)
- For multi-step tasks: confirm the plan first, then execute step by step.
- For scheduling: always repeat back the final time and date for confirmation.
- Proactively suggest if you notice a conflict (e.g., two meetings at the same time).

SAFETY RULES:
- Never send an email, delete a calendar event, or make an external booking without explicit YES from user.
- Never share user data with any external service beyond what the specific tool requires.
- If uncertain about user intent, ask — never guess on irreversible actions.

TONE: Proactive, reliable, concise, friendly. Like a highly competent personal assistant.
"""

async def run_orchestrator(user_phone: str, message: str) -> str:
    """Run the orchestrator agent and return the response."""
    # 1. Fetch User from DB
    async with async_session() as session:
        result = await session.execute(select(User).where(User.phone_number == user_phone))
        user = result.scalars().first()
        if not user:
            # First time user setup could happen here
            user = User(phone_number=user_phone)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
    # 2. Check for Pending Saftey Guard Confirmations
    guard = SafetyGuard()
    pending = guard.get_pending_action(user_phone)
    if pending:
        normalized = message.strip().lower()
        yes_tokens = {"yes", "y", "yeah", "sure", "ok", "okay", "go ahead", "confirm", "1"}
        no_tokens = {"no", "n", "nope", "cancel", "stop", "2"}

        if normalized in yes_tokens:
            original_msg = pending.get("original_message", "Proceed with the previous action.")
            guard.clear_pending_action(user_phone)
            # Re-inject the original command that led to the confirmation
            message = f"User has confirmed. {original_msg}"
        elif normalized in no_tokens:
            guard.clear_pending_action(user_phone)
            return "Action cancelled."
            
    # 3. Memory & Intent Analysis
    sm = ShortTermMemory()
    lm = LongTermMemory()

    # 3a. Fast-path for compact daily check-in messages
    checkin_payload = parse_checkin_message(message)
    if checkin_payload:
        from app.tools.momentum_tool import log_daily_checkin, get_momentum_dashboard

        checkin_result = log_daily_checkin.invoke({
            "phone_number": user_phone,
            **checkin_payload
        })
        dashboard_result = get_momentum_dashboard.invoke({"phone_number": user_phone})

        reply = f"{checkin_result}\n\n{dashboard_result}"
        sm.save(str(user.id), message, reply)
        return reply
    
    # Load past N messages
    history = sm.load(str(user.id))
    converted_history = []
    for h in history:
        if h.get("role") == "user":
            converted_history.append(HumanMessage(content=h.get("content", "")))
        elif h.get("role") == "assistant":
            converted_history.append(AIMessage(content=h.get("content", "")))

    # Fetch long term memory
    context = lm.retrieve_context(str(user.id), message)
    
    # Parse Intent
    try:
        intent_info = parse_intent(message, history=converted_history)
        if isinstance(intent_info, dict):
            intent_info = ParsedIntent(**intent_info)
    except Exception as e:
        logger.error(f"Intent parsing failed: {e}")
        intent_info = None

    # Handle Clarification Pre-emption
    # Handle Clarification Pre-emption
    # Only pre-empt if the intent is truly unknown or the user message is very short
    if intent_info and intent_info.clarification_needed and not pending:
        if len(message.split()) < 3 and intent_info.intent == "clarification_needed":
            sm.save(str(user.id), message, intent_info.clarification_question)
            return intent_info.clarification_question
        # Otherwise, let the full Agent (gpt-4o) try to handle it with its tools
        
    # Check if action requires confirmation setup
    if intent_info and intent_info.requires_confirmation and not pending:
        guard.set_pending_action(user_phone, {"intent": intent_info.intent, "entities": intent_info.entities}, message)
        reply = "Should I go ahead?"
        sm.save(str(user.id), message, reply)
        return reply

    # 4. Agent Execution Setup — custom ReAct loop
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm_with_tools = llm.bind_tools(agent_tools)
    tools_by_name = {t.name: t for t in agent_tools}

    prompt = SYSTEM_PROMPT
    # Inject real-time clock and user context
    now = datetime.now()
    prompt += f"\n\nCURRENT SYSTEM TIME:\n- Date: {now.strftime('%A, %B %d, %Y')}\n- Time: {now.strftime('%I:%M %p')}\n- Timezone: Asia/Kolkata"
    
    prompt += f"\n\nCURRENT USER PHONE: {user_phone}"
    if context:
        prompt += f"\n\nUSER MEMORIES/CONTEXT:\n{context}"

    messages_to_pass = [SystemMessage(content=prompt)] + converted_history + [HumanMessage(content=message)]

    def run_agent_loop():
        """Synchronous ReAct loop — safe to run inside asyncio.to_thread."""
        msgs = list(messages_to_pass)
        for _ in range(MAX_TOOL_ITERATIONS):
            response = llm_with_tools.invoke(msgs)
            msgs.append(response)

            # If no tool calls, we have the final answer
            if not response.tool_calls:
                return response.content

            # Execute each requested tool
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = dict(tc["args"])

                tool = tools_by_name.get(tool_name)
                if tool is None:
                    result = f"Tool '{tool_name}' not found."
                else:
                    try:
                        tool_args = inject_user_context(tool, tool_args, user_phone)
                        result = tool.invoke(tool_args)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"
                msgs.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        # Max iterations hit — return last message content
        return msgs[-1].content if msgs else "I could not complete that task."

    try:
        ai_reply = await asyncio.to_thread(run_agent_loop)
        
        # Save exact execution back
        sm.save(str(user.id), message, ai_reply)
        
        # Log action asynchronously
        async with async_session() as session:
            log = ActionLog(
                user_id=user.id,
                intent=intent_info.intent if intent_info else "unknown",
                action_taken="agent run completed",
                success=True
            )
            session.add(log)
            await session.commit()
            
        return ai_reply
    except Exception as e:
        logger.error("Agent execution failed", extra={"error": str(e)})
        return f"I ran into an issue handling that: {str(e)}"
