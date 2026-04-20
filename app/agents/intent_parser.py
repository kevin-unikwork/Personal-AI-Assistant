from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

class ParsedIntent(BaseModel):
    intent: Literal[
        "schedule_meeting", "set_reminder", "send_email",
        "send_whatsapp", "plan_day", "book_service",
        "query_calendar", "list_tasks", "general_chat",
        "confirm_action", "cancel_action", "clarification_needed"
    ] = Field(description="The primary intent of the user message")
    entities: dict = Field(default_factory=dict, description="Extracted entities like person, time, subject")
    urgency: Literal["low", "medium", "high"] = Field(default="medium", description="Assessed urgency")
    requires_confirmation: bool = Field(default=False, description="True if the action modifies state or contacts others")
    clarification_needed: bool = Field(default=False, description="True if crucial information is missing")
    clarification_question: str | None = Field(default=None, description="Question to ask if clarification is needed")

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert intent extraction system. 
    Analyze the user's message and history to extract intent and entities.
    
    CLARIFICATION LOGIC:
    - clarification_needed = True ONLY IF the user's intent is STILL completely un-executable after combining the new message with conversation history.
    - IMPORTANT: If the assistant asked a question in the last turn and the user's current message answers it (even with one word), set `clarification_needed = False` and update the `entities` dict.
    - NEVER ask the same clarification question twice in a row if the user provided new information.
    
    CONFIRMATION LOGIC:
    - requires_confirmation = True ONLY IF:
        a) The action is IRREVERSIBLE (deleting, canceling).
        b) The action involves CONTACTING OTHERS (external emails/whatsapp) with ambiguous content.
        c) The request is VAGUE or missing critical entities.
    - requires_confirmation = False IF:
        a) The user provides ALL specific details (Who, When, What).
        b) The action is a simple addition (adding a calendar event, setting a reminder).
        c) The user explicitly says "just do it" or "no need to ask" (check history)."""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{message}")
])

def parse_intent(message: str, history: list = []) -> ParsedIntent:
    """Parse the user intent using the current message and conversation history."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    parser = llm.with_structured_output(ParsedIntent)
    chain = prompt | parser
    return chain.invoke({
        "message": message,
        "history": history
    })
