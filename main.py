# Helper script for manually exercising the Sheety GET/POST calls prior to wiring the rest of the flow.
import argparse
import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional

import requests

from config import Settings, load_settings
from data_manager import DataManager
from flight_search import FlightSearch
from notification_manager import NotificationManager


@dataclass
class Destination:
    city: str
    iata_code: str
    lowest_price: float


# Name of the column in the users sheet that stores email addresses.
CUSTOMER_EMAIL_FIELD = "email"


def build_data_manager(settings: Settings) -> DataManager:
    """Constructs a manager from the pre-validated project settings."""
    return DataManager(
        prices_endpoint=settings.sheety_endpoint,
        data_key=settings.sheety_data_key,
        auth_token=settings.sheety_token,
    )


def print_data_dump(data: Any) -> None:
    """Show the retrieved rows to confirm the GET result."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def post_demo_row(manager: DataManager, payload: Dict[str, Any], row_key: Optional[str]) -> None:
    """Send a POST to Sheety using the provided row payload."""
    result = manager.add_row(payload, row_key=row_key)
    print("Sheety returned:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def valid_date(value: str) -> str:
    """Ensure the provided date is ISO-8601 compatible (`YYYY-MM-DD`)."""
    try:
        date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Dates must use YYYY-MM-DD format.")
    return value


def default_trip_dates() -> tuple[str, str]:
    """Generate a default departure/return window (6 months from today, 7-day trip)."""
    departure = date.today() + timedelta(days=182)
    return departure.isoformat(), (departure + timedelta(days=7)).isoformat()


def build_destinations(sheet_rows: Iterable[Dict[str, Any]]) -> List[Destination]:
    """Normalize the Sheety payload into our simplified destination list."""
    destinations: List[Destination] = []
    for row in sheet_rows:
        city = (row.get("city") or row.get("destination") or "").strip()
        if not city:
            continue
        iata_code = (row.get("iataCode") or row.get("iata_code") or "").strip().upper()
        if not iata_code:
            continue
        lowest_price_raw = row.get("lowestPrice") or row.get("lowest_price") or 0
        try:
            lowest_price = float(lowest_price_raw)
        except (TypeError, ValueError):
            lowest_price = 0.0

        destinations.append(
            Destination(city=city, iata_code=iata_code, lowest_price=lowest_price)
        )
    return destinations


def load_customer_emails(manager: DataManager, email_field: str) -> List[str]:
    """Load all customer email addresses from the users sheet."""
    customer_rows = manager.get_customer_emails()
    emails: List[str] = []
    for row in customer_rows:
        email_value = (row.get(email_field) or "").strip()
        if email_value:
            emails.append(email_value)
    return emails


def search_destinations(
    destinations: Iterable[Destination],
    searcher: FlightSearch,
    departure_date: str,
    return_date: str,
    notifier: Optional[NotificationManager] = None,
) -> None:
    """Query Amadeus for each destination and print the cheapest offer."""
    print(f"Trip window: {departure_date} → {return_date}")
    for destination in destinations:
        print(f"Checking {destination.city} ({destination.iata_code})...")
        try:
            offer = searcher.search_cheapest_flight(
                destination.iata_code, departure_date, return_date
            )
        except requests.RequestException as exc:
            print(f"  · error contacting Amadeus: {exc}")
            continue

        if not offer:
            print("  · aucun vol trouvé pour cette période.")
            continue

        in_target = offer.price <= destination.lowest_price
        status = "✅ sous le prix cible" if in_target else "⚠️ au-dessus du prix cible"
        print(
            f"  · prix Amadeus: {offer.currency} {offer.price:.2f} ({status}, cible {destination.lowest_price:.2f})"
        )
        if in_target and notifier:
            try:
                sms_sid = notifier.send_deal_alert(offer, destination.lowest_price)
                print(f"    SMS envoyé (Twilio SID: {sms_sid}).")
            except requests.RequestException as exc:
                print(f"    ⚠️ impossible d'envoyer le SMS: {exc}")


def sync_missing_iata_codes(
    rows: Iterable[Dict[str, Any]],
    manager: DataManager,
    searcher: FlightSearch,
) -> int:
    """Use Amadeus to fill missing IATA codes and persist them to Sheety."""
    updated = 0
    for row in rows:
        iata = (row.get("iataCode") or row.get("iata_code") or "").strip()
        if iata:
            continue
        city = (row.get("city") or row.get("destination") or "").strip()
        row_id = row.get("id")
        if not city or not row_id:
            continue
        print(f"Recherche du code IATA pour {city}...")
        try:
            city_code = searcher.find_city_code(city)
        except requests.RequestException as exc:
            print(f"  · échec de l'appel Amadeus pour {city}: {exc}")
            continue
        if not city_code:
            print("  · aucun code trouvé.")
            continue
        city_code = city_code.upper()
        try:
            manager.update_row(int(row_id), {"iataCode": city_code})
        except requests.RequestException as exc:
            print(f"  · impossible de mettre à jour la feuille: {exc}")
            continue
        row["iataCode"] = city_code
        updated += 1
        print(f"  · code rempli: {city_code}")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Helper for Sheety + Amadeus interactions before adding notifications."
    )
    parser.add_argument("--fetch", action="store_true", help="Run GET to list the cached destination data.")
    parser.add_argument(
        "--push",
        type=str,
        help="JSON string describing a single row; the helper wraps it with the configured key before POSTing.",
    )
    parser.add_argument("--row-key", type=str, help="Override the record key used when POSTing.")
    parser.add_argument("--sync-iata", action="store_true", help="Fill missing IATA codes via Amadeus and update Sheety.")
    parser.add_argument("--search", action="store_true", help="Call Amadeus for every destination to retrieve current prices.")
    parser.add_argument("--notify", action="store_true", help="Send a Twilio SMS when a deal beats the lowest price.")
    parser.add_argument("--origin", type=str, help="IATA code to use as the flight origin (overrides ORIGIN_IATA).")
    parser.add_argument(
        "--departure",
        type=valid_date,
        help="Departure date (YYYY-MM-DD); defaults to ~6 months from today or DEFAULT_DEPARTURE_DATE.",
    )
    parser.add_argument(
        "--return",
        dest="return_date",
        type=valid_date,
        help="Return date (YYYY-MM-DD); defaults to 7 days after the computed departure date or DEFAULT_RETURN_DATE.",
    )

    args = parser.parse_args()

    try:
        settings = load_settings()
    except EnvironmentError as exc:
        parser.error(str(exc))
        return

    manager = build_data_manager(settings)
    rows = manager.get_data()
    customer_emails = load_customer_emails(manager, CUSTOMER_EMAIL_FIELD)

    performed_action = False
    if args.fetch:
        performed_action = True
        print_data_dump(rows)

    if args.push:
        performed_action = True
        try:
            row_payload = json.loads(args.push)
        except json.JSONDecodeError as exc:
            parser.error(f"Invalid JSON for --push: {exc}")
        post_demo_row(manager, row_payload, args.row_key)

    needs_amadeus = args.sync_iata or args.search
    flight_search: Optional[FlightSearch] = None
    notifier: Optional[NotificationManager] = None
    if needs_amadeus:
        if not settings.amadeus_api_key or not settings.amadeus_api_secret:
            parser.error(
                "Amadeus credentials (AMADEUS_API_KEY/AMADEUS_API_SECRET) are required for this action."
            )
            return
        origin_candidate = (args.origin or settings.default_origin_iata or "").strip().upper() or None
        flight_search = FlightSearch(
            api_key=settings.amadeus_api_key,
            api_secret=settings.amadeus_api_secret,
            origin_iata=origin_candidate,
        )
        if args.notify:
            if not all([settings.twilio_sid, settings.twilio_auth_token, settings.twilio_from, settings.twilio_to]):
                parser.error("Twilio configuration is incomplete; set TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM, TWILIO_TO.")
                return
            notifier = NotificationManager(
                account_sid=settings.twilio_sid,
                auth_token=settings.twilio_auth_token,
                from_number=settings.twilio_from,
                to_number=settings.twilio_to,
            )

    if args.sync_iata and flight_search:
        performed_action = True
        updated = sync_missing_iata_codes(rows, manager, flight_search)
        if updated:
            print(f"{updated} code(s) IATA complétés.")
        else:
            print("Tous les codes IATA étaient déjà présents ou aucune mise à jour possible.")

    if args.search:
        performed_action = True
        if not flight_search:
            parser.error("FlightSearch non disponible.")
            return

        origin = flight_search.origin_iata
        if not origin:
            parser.error("Provide an origin IATA code via --origin or ORIGIN_IATA.")
            return

        departure = args.departure or settings.default_departure_date
        return_date = args.return_date or settings.default_return_date
        if not departure or not return_date:
            departure, return_date = default_trip_dates()

        try:
            departure_date_obj = date.fromisoformat(departure)
            return_date_obj = date.fromisoformat(return_date)
        except ValueError:
            parser.error("Configured departure/return dates must use YYYY-MM-DD.")
            return

        if return_date_obj <= departure_date_obj:
            parser.error("Return date must be after departure date.")
            return

        destinations = build_destinations(rows)
        if not destinations:
            print("Aucune destination valide trouvée dans la feuille.")
        else:
            search_destinations(destinations, flight_search, departure, return_date, notifier)

    if not performed_action:
        parser.print_help()


if __name__ == "__main__":
    main()
