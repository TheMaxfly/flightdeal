from __future__ import annotations

from typing import Optional

import requests

from flight_data import FlightData


class NotificationManager:
    """Send SMS alerts with flight-deal details via the Twilio API."""

    API_URL_TEMPLATE = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    def __init__(self, account_sid: str, auth_token: str, from_number: str, to_number: str):
        if not all([account_sid, auth_token, from_number, to_number]):
            raise ValueError("Twilio SID, auth token, from, and to numbers are required.")
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_number = to_number

    def send_sms(self, body: str) -> Optional[str]:
        """Send a raw SMS message; returns the Twilio SID if successful."""
        response = requests.post(
            self.API_URL_TEMPLATE.format(sid=self.account_sid),
            data={
                "To": self.to_number,
                "From": self.from_number,
                "Body": body,
            },
            auth=(self.account_sid, self.auth_token),
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("sid")

    def send_deal_alert(self, flight: FlightData, threshold_price: float) -> Optional[str]:
        """Compose and send a standard deal alert message."""
        body = (
            f"Bon plan vol ✈️ {flight.origin_city}-{flight.destination_city} "
            f"à {flight.price:.2f} {flight.currency} (cible {threshold_price:.2f}). "
            f"Aller: {flight.out_date}, retour: {flight.return_date}."
        )
        if flight.stop_overs:
            via_info = f" via {flight.via_city}" if flight.via_city else ""
            body += f" {flight.stop_overs} escale(s){via_info}."
        return self.send_sms(body)
