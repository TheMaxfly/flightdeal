from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from flight_data import FlightData


class FlightSearch:
    """Query Amadeus for flight offers and return structured FlightData."""

    TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
    FLIGHT_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    LOCATIONS_URL = "https://test.api.amadeus.com/v1/reference-data/locations"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        origin_iata: Optional[str] = None,
        currency: str = "EUR",
    ):
        if not api_key or not api_secret:
            raise ValueError("Both Amadeus API key and secret are required.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.origin_iata = origin_iata
        self.currency = currency
        self._token: Optional[str] = None
        self._token_expires_at = 0.0

    def _ensure_token(self) -> None:
        if self._token and time.time() < self._token_expires_at:
            return
        token, expires_in = self._get_new_token()
        self._token = token
        self._token_expires_at = time.time() + expires_in - 10  # refresh before expiry

    def _headers(self) -> Dict[str, str]:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._token}"}

    def _get_new_token(self) -> tuple[str, int]:
        """Request a new OAuth token from Amadeus."""
        response = requests.post(
            self.TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 0))
        return access_token, expires_in

    def search_cheapest_flight(
        self,
        destination_iata: str,
        departure_date: str,
        return_date: str,
        max_price: Optional[float] = None,
        adults: int = 1,
    ) -> Optional[FlightData]:
        """Return the cheapest flight offer for the given destination and dates."""
        if not self.origin_iata:
            raise ValueError("FlightSearch requires origin_iata to search for flights.")
        params: Dict[str, Any] = {
            "originLocationCode": self.origin_iata,
            "destinationLocationCode": destination_iata,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": adults,
            "currencyCode": self.currency,
            "max": 1,
        }
        if max_price is not None:
            params["maxPrice"] = str(max_price)

        response = requests.get(self.FLIGHT_OFFERS_URL, headers=self._headers(), params=params)
        response.raise_for_status()
        payload = response.json()
        offers = payload.get("data", [])
        if not offers:
            return None
        return FlightData.from_amadeus_offer(offers[0])

    def find_city_code(self, city_name: str) -> Optional[str]:
        """Look up the IATA city code for the provided city name."""
        params = {
            "keyword": city_name,
            "subType": "CITY",
            "page[limit]": 1,
        }
        response = requests.get(self.LOCATIONS_URL, headers=self._headers(), params=params)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        if not data:
            return None
        return data[0].get("iataCode")
