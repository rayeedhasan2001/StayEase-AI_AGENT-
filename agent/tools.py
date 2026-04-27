from __future__ import annotations

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
    """Return full details for a single listing."""
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
    total_price_bdt = max(nights, 1) * listing["price_bdt"]
    return {
        "booking_id": "bk-demo-001",
        "listing_id": listing_id,
        "guest_name": guest_name,
        "guests": guests,
        "status": "confirmed",
        "total_price_bdt": total_price_bdt,
    }
