from __future__ import annotations

from agent.state import AgentState
from agent.tools import create_booking, get_listing_details, search_available_properties


def search_node(state: AgentState) -> AgentState:
    """Handle search intent from tool call to guest reply."""
    state["tool_result"] = search_available_properties.invoke(state["tool_input"])
    results = state["tool_result"].get("results", [])

    if not results:
        state["final_response"] = "I could not find any available properties for those dates."
        state["needs_human"] = False
        return state

    lines = []
    for index, listing in enumerate(results, start=1):
        lines.append(
            f'{index}. {listing["listing_id"]} - {listing["title"]}, '
            f'{listing["location"]} - BDT {listing["price_bdt"]}/night'
        )

    state["final_response"] = "I found these available options:\n" + "\n".join(lines)
    state["needs_human"] = False
    return state


def details_node(state: AgentState) -> AgentState:
    """Handle details intent from tool call to guest reply."""
    state["tool_result"] = get_listing_details.invoke(state["tool_input"])

    if "error" in state["tool_result"]:
        state["final_response"] = (
            "I could not find that listing from the information I have, so I am handing this to a human agent."
        )
        state["needs_human"] = True
        return state

    details = state["tool_result"]
    amenities = ", ".join(details["amenities"])
    state["final_response"] = (
        f'{details["listing_id"]} - {details["title"]} is in {details["location"]}. '
        f'It costs BDT {details["price_bdt"]} per night, fits {details["max_guests"]} guests, '
        f'and includes {amenities}.'
    )
    state["needs_human"] = False
    return state


def book_node(state: AgentState) -> AgentState:
    """Handle booking intent from tool call to guest reply."""
    state["tool_result"] = create_booking.invoke(state["tool_input"])

    if "error" in state["tool_result"]:
        state["final_response"] = (
            "I could not complete that booking safely, so I am handing this to a human agent."
        )
        state["needs_human"] = True
        return state

    booking = state["tool_result"]
    state["final_response"] = (
        f'Your booking is confirmed. Booking ID: {booking["booking_id"]}. '
        f'Total price: BDT {booking["total_price_bdt"]}.'
    )
    state["needs_human"] = False
    return state
