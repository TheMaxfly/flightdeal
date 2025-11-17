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
    stops: int = 0
    is_direct: bool = True
    via_city: Optional[str] = None

    @classmethod
    def from_amadeus_offer(cls, offer: Dict[str, Any]) -> "FlightData":
        """Convert a single flight offer entry into a FlightData record."""
        price_data = offer.get("price", {})
        itineraries = offer.get("itineraries", [])
        outbound = itineraries[0]
        inbound = itineraries[-1] if len(itineraries) > 1 else outbound

        outbound_segments = outbound.get("segments", [])
        if not outbound_segments:
            raise ValueError("Amadeus offer missing outbound segments.")

        inbound_segments = inbound.get("segments", [])
        outbound_first = outbound_segments[0]
        outbound_last = outbound_segments[-1]
        inbound_last = inbound_segments[-1] if inbound_segments else outbound_last

        stops = max(len(outbound_segments) - 1, 0)
        via_city: Optional[str] = None
        if stops:
            first_stop_arrival = outbound_segments[0]["arrival"]
            via_city = first_stop_arrival.get("cityCode") or first_stop_arrival.get("iataCode")

        origin_departure = outbound_first["departure"]
        destination_arrival = outbound_last["arrival"]
        origin_airport = origin_departure.get("iataCode", "")
        destination_airport = destination_arrival.get("iataCode", "")
        origin_city = origin_departure.get("cityCode") or origin_airport
        destination_city = destination_arrival.get("cityCode") or destination_airport
        out_date = origin_departure.get("at", "").split("T")[0]
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
            stops=stops,
            is_direct=(stops == 0),
            via_city=via_city,
        )
