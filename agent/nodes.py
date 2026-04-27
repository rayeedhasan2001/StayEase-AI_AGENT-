from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from agent.state import AgentState
from agent.tools import create_booking, get_listing_details, search_available_properties


def load_context(state: AgentState) -> AgentState:
    """Prepare the current turn before routing through the graph."""
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": state["user_message"]})
    state["messages"] = messages
    state["final_response"] = None
    state["tool_result"] = None
    return state


def parse_request(state: AgentState) -> AgentState:
    """Classify the guest request and extract the fields needed by the next node."""
    text = state["user_message"].lower()
    state["needs_human"] = False

    if "book" in text or "confirm" in text:
        state["intent"] = "book"
        state["booking_request"] = {
            "listing_id": state.get("listing_id") or "cox-101",
            "guest_name": "Guest",
            "check_in": date.today().isoformat(),
            "check_out": (date.today() + timedelta(days=2)).isoformat(),
            "guests": 2,
        }
        return state

    if "details" in text or "tell me about" in text:
        state["intent"] = "details"
        state["listing_id"] = state.get("listing_id") or "cox-101"
        return state

    if "room" in text or "stay" in text or "search" in text:
        state["intent"] = "search"
        location = "Cox's Bazar" if "cox" in text else "Sylhet"
        state["search_params"] = {
            "location": location,
            "check_in": date.today().isoformat(),
            "check_out": (date.today() + timedelta(days=2)).isoformat(),
            "guests": 2,
        }
        return state

    state["intent"] = "escalate"
    state["needs_human"] = True
    return state


def run_tool(state: AgentState) -> AgentState:
    """Execute the tool that matches the current intent."""
    intent = state["intent"]

    if intent == "search" and state.get("search_params"):
        params = state["search_params"]
        state["tool_result"] = search_available_properties.invoke(
            {
                "location": params["location"],
                "check_in": params["check_in"],
                "check_out": params["check_out"],
                "guests": params["guests"],
            }
        )
        return state

    if intent == "details" and state.get("listing_id"):
        state["tool_result"] = get_listing_details.invoke({"listing_id": state["listing_id"]})
        return state

    if intent == "book" and state.get("booking_request"):
        booking = state["booking_request"]
        state["tool_result"] = create_booking.invoke(
            {
                "listing_id": booking["listing_id"],
                "guest_name": booking["guest_name"],
                "check_in": booking["check_in"],
                "check_out": booking["check_out"],
                "guests": booking["guests"],
            }
        )
        return state

    state["tool_result"] = {"error": "Unable to determine which tool to call."}
    state["needs_human"] = True
    return state


def respond(state: AgentState) -> AgentState:
    """Build the final guest-facing reply."""
    if state.get("needs_human"):
        state["final_response"] = (
            "I can help with searching listings, property details, and bookings only. "
            "I am escalating this conversation to a human agent."
        )
        return state

    intent = state["intent"]
    tool_result: dict[str, Any] = state.get("tool_result") or {}

    if intent == "search":
        results = tool_result.get("results", [])
        if not results:
            state["final_response"] = "I could not find any available properties for those dates."
            return state
        lines = [
            f'{item["title"]} in {item["location"]} - BDT {item["price_bdt"]}/night'
            for item in results
        ]
        state["final_response"] = "Available options:\n" + "\n".join(lines)
        return state

    if intent == "details":
        if "error" in tool_result:
            state["final_response"] = tool_result["error"]
            return state
        state["final_response"] = (
            f'{tool_result["title"]} costs BDT {tool_result["price_bdt"]} per night and fits '
            f'{tool_result["max_guests"]} guests.'
        )
        return state

    if intent == "book":
        if "error" in tool_result:
            state["final_response"] = tool_result["error"]
            return state
        state["final_response"] = (
            f'Your booking is confirmed. Booking ID: {tool_result["booking_id"]}. '
            f'Total: BDT {tool_result["total_price_bdt"]}.'
        )
        return state

    state["final_response"] = "I am escalating this conversation to a human agent."
    return state


def save_conversation(state: AgentState) -> AgentState:
    """Append the assistant reply so the API layer can persist the turn."""
    messages = list(state.get("messages", []))
    if state.get("final_response"):
        messages.append({"role": "assistant", "content": state["final_response"]})
    state["messages"] = messages
    return state


def route_after_parse(state: AgentState) -> str:
    """Choose the next node after intent parsing."""
    if state.get("needs_human") or state.get("intent") == "escalate":
        return "respond"
    return "run_tool"
