from __future__ import annotations

import re
from datetime import date

from langchain.tools import tool
from pydantic import BaseModel, Field


SAMPLE_LISTINGS = [
    {
        "listing_id": "cox-101",
        "title": "Sea Breeze Studio",
        "description": "Private studio near Kolatoli beach.",
        "location": "Cox's Bazar",
        "price_bdt": 4800,
        "max_guests": 2,
        "amenities": ["wifi", "ac", "breakfast"],
    },
    {
        "listing_id": "cox-205",
        "title": "Kolatoli Family Suite",
        "description": "Family suite with balcony and beach access.",
        "location": "Cox's Bazar",
        "price_bdt": 6200,
        "max_guests": 4,
        "amenities": ["wifi", "ac", "parking"],
    },
    {
        "listing_id": "syl-110",
        "title": "Tea Garden Retreat",
        "description": "Quiet apartment close to tea estates.",
        "location": "Sylhet",
        "price_bdt": 4300,
        "max_guests": 3,
        "amenities": ["wifi", "kitchen"],
    },
]

LOCATION_ALIASES = {
    "cox's bazar": "Cox's Bazar",
    "coxs bazar": "Cox's Bazar",
    "cox bazar": "Cox's Bazar",
    "sylhet": "Sylhet",
    "dhaka": "Dhaka",
    "bandarban": "Bandarban",
}


class DetectIntentAndRouteInput(BaseModel):
    message: str = Field(..., description="Latest user message.")
    messages: list[dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation history.",
    )


class ExtractQueryParamsInput(BaseModel):
    intent: str = Field(..., description="Detected intent from the routing tool.")
    message: str = Field(..., description="Latest user message.")
    messages: list[dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation history.",
    )


class SearchAvailablePropertiesInput(BaseModel):
    location: str = Field(..., description="Bangladeshi destination provided by the guest.")
    check_in: date = Field(..., description="Requested arrival date.")
    check_out: date = Field(..., description="Requested departure date.")
    guests: int = Field(..., ge=1, description="Number of guests staying.")


class GetListingDetailsInput(BaseModel):
    listing_id: str = Field(..., description="Unique listing identifier.")


class CreateBookingInput(BaseModel):
    listing_id: str = Field(..., description="Listing to reserve.")
    guest_name: str = Field(..., description="Guest full name.")
    check_in: date = Field(..., description="Requested arrival date.")
    check_out: date = Field(..., description="Requested departure date.")
    guests: int = Field(..., ge=1, description="Number of guests staying.")


def _history_text(messages: list[dict[str, str]]) -> str:
    return "\n".join(message.get("content", "") for message in messages)


def _find_location(text: str) -> str | None:
    lowered = text.lower()
    for alias, value in LOCATION_ALIASES.items():
        if alias in lowered:
            return value
    return None


def _find_dates(text: str) -> tuple[str | None, str | None]:
    range_match = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|-)\s*(\d{4}-\d{2}-\d{2})", text)
    if range_match:
        return range_match.group(1), range_match.group(2)

    all_dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    if len(all_dates) >= 2:
        return all_dates[0], all_dates[1]
    return None, None


def _find_guests(text: str) -> int | None:
    match = re.search(r"(\d+)\s+(?:guest|guests|people|persons)", text.lower())
    if match:
        return int(match.group(1))
    return None


def _find_listing_id(text: str) -> str | None:
    lowered = text.lower()
    for listing in SAMPLE_LISTINGS:
        if listing["listing_id"].lower() in lowered:
            return listing["listing_id"]
    return None


def _find_guest_name(text: str) -> str | None:
    patterns = [
        r"my name is ([a-zA-Z ]+)",
        r"this is ([a-zA-Z ]+)",
        r"book for ([a-zA-Z ]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return None


def _follow_up_question(intent: str, missing_fields: list[str]) -> str:
    if intent == "search":
        if missing_fields == ["location"]:
            return "Which location in Bangladesh would you like to search in?"
        if missing_fields == ["check_in", "check_out"]:
            return "What check-in and check-out dates would you like to search for?"
        if missing_fields == ["guests"]:
            return "How many guests will be staying?"
        return "I need the location, dates, and number of guests before I can search. Could you share those?"

    if intent == "details":
        return "Which listing would you like details for? Please share the listing ID."

    return (
        "Before I create the booking, please share the listing ID, guest name, stay dates, "
        "and number of guests."
    )


def _detect_from_history(messages: list[dict[str, str]]) -> str:
    recent_text = _history_text(messages[-3:]).lower()
    if (
        "search" in recent_text
        or "available options" in recent_text
        or "check-in and check-out dates" in recent_text
        or "number of guests before i can search" in recent_text
    ):
        return "search"
    if "details" in recent_text or "which listing would you like details" in recent_text:
        return "details"
    if "booking" in recent_text or "reserve" in recent_text or "before i create the booking" in recent_text:
        return "book"
    return "escalate"


@tool("detect_intent_and_route", args_schema=DetectIntentAndRouteInput)
def detect_intent_and_route(message: str, messages: list[dict[str, str]]) -> dict:
    """Classify the request and decide which executor node should handle it."""
    text = message.lower()
    intent = "escalate"

    if any(keyword in text for keyword in ["book", "reserve", "confirm", "take it"]):
        intent = "book"
    elif any(keyword in text for keyword in ["details", "tell me about", "amenities", "more about"]):
        intent = "details"
    elif any(keyword in text for keyword in ["search", "find", "room", "stay", "available"]):
        intent = "search"
    elif re.search(r"\d{4}-\d{2}-\d{2}", text) or re.search(r"\d+\s+(?:guest|guests)", text):
        intent = _detect_from_history(messages)
    elif _find_listing_id(text):
        intent = _detect_from_history(messages)
    elif messages:
        intent = _detect_from_history(messages)

    executor_map = {
        "search": "search_node",
        "details": "details_node",
        "book": "book_node",
    }
    return {
        "intent": intent,
        "executor_target": executor_map.get(intent),
        "needs_human": intent == "escalate",
    }


@tool("extract_query_params", args_schema=ExtractQueryParamsInput)
def extract_query_params(intent: str, message: str, messages: list[dict[str, str]]) -> dict:
    """Extract clean tool input and identify missing fields before execution."""
    recent_history = _history_text(messages[-3:])
    tool_input: dict = {}
    missing_fields: list[str] = []

    if intent == "search":
        location = _find_location(message) or _find_location(recent_history)
        check_in, check_out = _find_dates(message)
        if not (check_in and check_out):
            check_in, check_out = _find_dates(recent_history)
        guests = _find_guests(message)
        if guests is None:
            guests = _find_guests(recent_history)

        if location:
            tool_input["location"] = location
        else:
            missing_fields.append("location")

        if check_in and check_out:
            tool_input["check_in"] = check_in
            tool_input["check_out"] = check_out
        else:
            missing_fields.extend(["check_in", "check_out"])

        if guests is not None:
            tool_input["guests"] = guests
        else:
            missing_fields.append("guests")

    elif intent == "details":
        listing_id = _find_listing_id(message) or _find_listing_id(recent_history)
        if listing_id:
            tool_input["listing_id"] = listing_id
        else:
            missing_fields.append("listing_id")

    elif intent == "book":
        listing_id = _find_listing_id(message) or _find_listing_id(recent_history)
        check_in, check_out = _find_dates(message)
        if not (check_in and check_out):
            check_in, check_out = _find_dates(recent_history)
        guests = _find_guests(message)
        if guests is None:
            guests = _find_guests(recent_history)
        guest_name = _find_guest_name(message) or _find_guest_name(recent_history)

        if listing_id:
            tool_input["listing_id"] = listing_id
        else:
            missing_fields.append("listing_id")

        if guest_name:
            tool_input["guest_name"] = guest_name
        else:
            missing_fields.append("guest_name")

        if check_in and check_out:
            tool_input["check_in"] = check_in
            tool_input["check_out"] = check_out
        else:
            missing_fields.extend(["check_in", "check_out"])

        if guests is not None:
            tool_input["guests"] = guests
        else:
            missing_fields.append("guests")

    unique_missing_fields = list(dict.fromkeys(missing_fields))
    return {
        "tool_input": tool_input,
        "missing_fields": unique_missing_fields,
        "follow_up_question": _follow_up_question(intent, unique_missing_fields)
        if unique_missing_fields
        else None,
    }


@tool("search_available_properties", args_schema=SearchAvailablePropertiesInput)
def search_available_properties(
    location: str,
    check_in: date,
    check_out: date,
    guests: int,
) -> dict:
    """Return matching listings for the requested stay."""
    matches = [
        listing
        for listing in SAMPLE_LISTINGS
        if listing["location"].lower() == location.lower() and listing["max_guests"] >= guests
    ]
    return {
        "results": matches,
        "count": len(matches),
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
    }


@tool("get_listing_details", args_schema=GetListingDetailsInput)
def get_listing_details(listing_id: str) -> dict:
    """Return full details for one listing."""
    listing = next(
        (item for item in SAMPLE_LISTINGS if item["listing_id"] == listing_id),
        None,
    )
    if listing is None:
        return {"error": f"Listing {listing_id} was not found."}
    return listing


@tool("create_booking", args_schema=CreateBookingInput)
def create_booking(
    listing_id: str,
    guest_name: str,
    check_in: date,
    check_out: date,
    guests: int,
) -> dict:
    """Create a booking confirmation payload."""
    listing = next(
        (item for item in SAMPLE_LISTINGS if item["listing_id"] == listing_id),
        None,
    )
    if listing is None:
        return {"error": f"Listing {listing_id} was not found."}

    nights = (check_out - check_in).days
    if nights <= 0:
        return {"error": "Check-out must be after check-in."}

    total_price_bdt = nights * listing["price_bdt"]
    return {
        "booking_id": "bk-demo-001",
        "listing_id": listing_id,
        "guest_name": guest_name,
        "guests": guests,
        "status": "confirmed",
        "total_price_bdt": total_price_bdt,
    }
