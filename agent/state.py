from __future__ import annotations

from typing import Any, Literal, TypedDict


Intent = Literal["search", "details", "book", "escalate"]


class SearchParams(TypedDict):
    location: str
    check_in: str
    check_out: str
    guests: int


class BookingRequest(TypedDict):
    listing_id: str
    guest_name: str
    check_in: str
    check_out: str
    guests: int


class AgentState(TypedDict):
    conversation_id: str
    messages: list[dict[str, str]]
    user_message: str
    intent: Intent | None
    search_params: SearchParams | None
    listing_id: str | None
    booking_request: BookingRequest | None
    tool_result: dict[str, Any] | None
    final_response: str | None
    needs_human: bool
