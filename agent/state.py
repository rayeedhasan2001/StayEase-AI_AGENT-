from __future__ import annotations

from typing import Any, Literal, TypedDict


Intent = Literal["search", "details", "book", "escalate"]
ExecutorNode = Literal["search_node", "details_node", "book_node"]


class ToolInput(TypedDict, total=False):
    location: str
    check_in: str
    check_out: str
    guests: int
    listing_id: str
    guest_name: str


class AgentState(TypedDict):
    conversation_id: str
    messages: list[dict[str, str]]
    user_message: str
    intent: Intent
    executor_target: ExecutorNode
    tool_input: ToolInput
    tool_result: dict[str, Any] | None
    final_response: str | None
    needs_human: bool
