from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class FlightData:
    """Structured view of a flight offer returned by Amadeus."""

    price: float
    currency: str
    origin_city: str
    origin_airport: str
    destination_city: str
    destination_airport: str
    out_date: str
    return_date: str
    stop_overs: int = 0
    via_city: Optional[str] = None

    @classmethod
    def from_amadeus_offer(cls, offer: Dict[str, Any]) -> "FlightData":
        """Convert a single flight offer entry into a FlightData record."""
        price_data = offer.get("price", {})
        itineraries = offer.get("itineraries", [])
        outbound = itineraries[0]
        inbound = itineraries[-1] if len(itineraries) > 1 else outbound

        outbound_segments = outbound.get("segments", [])
        inbound_segments = inbound.get("segments", [])
        outbound_first = outbound_segments[0]
        inbound_last = inbound_segments[-1] if inbound_segments else outbound_segments[-1]

        stop_overs = max(len(outbound_segments) - 1, 0)
        via_city: Optional[str] = None
        if stop_overs:
            via_city = outbound_segments[0]["arrival"].get("iataCode")

        origin_airport = outbound_first["departure"].get("iataCode", "")
        destination_airport = outbound_first["arrival"].get("iataCode", "")
        origin_city = outbound_first["departure"].get("cityCode") or origin_airport
        destination_city = outbound_first["arrival"].get("cityCode") or destination_airport
        out_date = outbound_first["departure"].get("at", "").split("T")[0]
        return_date = inbound_last["arrival"].get("at", "").split("T")[0]

        return cls(
            price=float(price_data.get("total", 0)),
            currency=price_data.get("currency", ""),
            origin_city=origin_city,
            origin_airport=origin_airport,
            destination_city=destination_city,
            destination_airport=destination_airport,
            out_date=out_date,
            return_date=return_date,
            stop_overs=stop_overs,
            via_city=via_city,
        )
