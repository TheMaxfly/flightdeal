from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    sheety_prices_endpoint: str
    sheety_users_endpoint: Optional[str] = None
    sheety_token: Optional[str] = None
    sheety_data_key: str = "prices"
    sheety_users_key: str = "users"
    sheety_username: Optional[str] = None
    sheety_password: Optional[str] = None
    amadeus_api_key: Optional[str] = None
    amadeus_api_secret: Optional[str] = None
    default_origin_iata: Optional[str] = None
    default_departure_date: Optional[str] = None
    default_return_date: Optional[str] = None
    twilio_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from: Optional[str] = None
    twilio_to: Optional[str] = None
    email_sender: Optional[str] = None
    email_password: Optional[str] = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587

    def validate(self) -> None:
        """Assert that the minimal required values are provided."""
        if not self.sheety_prices_endpoint:
            raise EnvironmentError(
                "SHEETY_PRICES_ENDPOINT (or legacy SHEETY_ENDPOINT) must be set (see .env.example)."
            )


def load_settings(dotenv_path: Optional[str] = None) -> Settings:
    """Build project settings from the environment (loads a .env via python-dotenv)."""
    load_dotenv(dotenv_path=Path(dotenv_path) if dotenv_path else Path(".env"))

    smtp_port_raw = os.getenv("SMTP_PORT")
    if smtp_port_raw:
        try:
            smtp_port = int(smtp_port_raw)
        except ValueError as exc:
            raise EnvironmentError("SMTP_PORT must be an integer.") from exc
    else:
        smtp_port = 587

    settings = Settings(
        sheety_prices_endpoint=os.getenv("SHEETY_PRICES_ENDPOINT")
        or os.getenv("SHEETY_ENDPOINT", ""),
        sheety_users_endpoint=os.getenv("SHEETY_USERS_ENDPOINT"),
        sheety_token=os.getenv("SHEETY_TOKEN"),
        sheety_data_key=os.getenv("SHEETY_DATA_KEY", "prices"),
        sheety_users_key=os.getenv("SHEETY_USERS_KEY", "users"),
        sheety_username=os.getenv("SHEETY_USERNAME"),
        sheety_password=os.getenv("SHEETY_PASSWORD"),
        amadeus_api_key=os.getenv("AMADEUS_API_KEY"),
        amadeus_api_secret=os.getenv("AMADEUS_API_SECRET"),
        default_origin_iata=(os.getenv("ORIGIN_IATA") or "CDG").upper(),
        default_departure_date=os.getenv("DEFAULT_DEPARTURE_DATE"),
        default_return_date=os.getenv("DEFAULT_RETURN_DATE"),
        twilio_sid=os.getenv("TWILIO_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        twilio_from=os.getenv("TWILIO_FROM"),
        twilio_to=os.getenv("TWILIO_TO"),
        email_sender=os.getenv("EMAIL_SENDER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=smtp_port,
    )
    settings.validate()
    return settings
