from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import smtplib
from typing import Iterable, List, Optional

import requests

from flight_data import FlightData


class NotificationError(Exception):
    """Raised when sending an email notification fails."""


@dataclass
class NotificationResult:
    sms_sid: Optional[str] = None
    emails_sent: int = 0


class NotificationManager:
    """Send SMS alerts with flight-deal details via the Twilio API and email."""

    API_URL_TEMPLATE = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_number: str,
        *,
        customer_emails: Optional[Iterable[str]] = None,
        email_sender: Optional[str] = None,
        email_password: Optional[str] = None,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ):
        if not all([account_sid, auth_token, from_number, to_number]):
            raise ValueError("Twilio SID, auth token, from, and to numbers are required.")
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_number = to_number
        self.customer_emails: List[str] = [
            email.strip()
            for email in (customer_emails or [])
            if isinstance(email, str) and email.strip()
        ]
        self.email_sender = email_sender
        self.email_password = email_password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

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

    def send_email_alert(
        self,
        subject: str,
        body: str,
        recipients: Optional[Iterable[str]] = None,
    ) -> int:
        """Send the alert email to every customer in the users sheet."""
        if not (self.email_sender and self.email_password):
            return 0

        target_recipients = [
            email.strip()
            for email in (recipients or self.customer_emails)
            if isinstance(email, str) and email.strip()
        ]
        if not target_recipients:
            return 0

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as connection:
                connection.starttls()
                connection.login(self.email_sender, self.email_password)
                for recipient in target_recipients:
                    message = EmailMessage()
                    message["From"] = self.email_sender
                    message["To"] = recipient
                    message["Subject"] = subject
                    message.set_content(body)
                    connection.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise NotificationError(f"Impossible d'envoyer l'e-mail: {exc}") from exc

        return len(target_recipients)

    def send_deal_alert(self, flight: FlightData, threshold_price: float) -> NotificationResult:
        """Compose and send a standard deal alert message via SMS and email."""
        body = (
            f"Bon plan vol ✈️ {flight.origin_city}-{flight.destination_city} "
            f"à {flight.price:.2f} {flight.currency} (cible {threshold_price:.2f}). "
            f"Aller: {flight.out_date}, retour: {flight.return_date}."
        )
        if flight.stops:
            via_info = f" via {flight.via_city}" if flight.via_city else ""
            body += f" {flight.stops} escale(s){via_info}."

        subject = f"Bon plan vol {flight.origin_city} → {flight.destination_city}"
        sms_sid = self.send_sms(body)
        emails_sent = self.send_email_alert(subject, body)
        return NotificationResult(sms_sid=sms_sid, emails_sent=emails_sent)
