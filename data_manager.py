import os
from typing import Any, Dict, List, Optional, Tuple

import requests


class DataManager:
    """Talk to Sheety-powered Google Sheets for destination and user data."""

    def __init__(
        self,
        prices_endpoint: Optional[str] = None,
        users_endpoint: Optional[str] = None,
        data_key: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.prices_endpoint = (
            prices_endpoint
            or os.getenv("SHEETY_PRICES_ENDPOINT")
            or os.getenv("SHEETY_ENDPOINT")
        )
        if not self.prices_endpoint:
            raise ValueError("A Sheety prices endpoint must be provided to use DataManager.")

        self.users_endpoint = users_endpoint or os.getenv("SHEETY_USERS_ENDPOINT")
        self.data_key = data_key or os.getenv("SHEETY_DATA_KEY", "prices")
        self.auth_token = auth_token or os.getenv("SHEETY_TOKEN")
        self.username = username or os.getenv("SHEETY_USERNAME")
        self.password = password or os.getenv("SHEETY_PASSWORD")
        self.users_key = os.getenv("SHEETY_USERS_KEY", "users")

    @property
    def _headers(self) -> Dict[str, str]:
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    @property
    def _auth(self) -> Optional[Tuple[str, str]]:
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def get_data(self) -> List[Dict[str, Any]]:
        """Return the full payload stored under the configured data key."""
        response = requests.get(
            self.prices_endpoint,
            headers=self._headers,
            auth=self._auth,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get(self.data_key, payload)

    def get_customer_emails(self) -> List[Dict[str, Any]]:
        """Return the records stored on the users sheet."""
        if not self.users_endpoint:
            raise ValueError("SHEETY_USERS_ENDPOINT must be configured to fetch customer emails.")
        response = requests.get(
            self.users_endpoint,
            headers=self._headers,
            auth=self._auth,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get(self.users_key, payload)

    def add_row(
        self,
        row_data: Dict[str, Any],
        row_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST a new row to the sheet; the row_key wraps the provided dict."""
        key = row_key or (
            self.data_key[:-1] if self.data_key.endswith("s") and len(self.data_key) > 1 else self.data_key
        )
        response = requests.post(
            self.prices_endpoint,
            json={key: row_data},
            headers=self._headers,
            auth=self._auth,
        )
        response.raise_for_status()
        return response.json()

    def update_row(
        self,
        row_id: int,
        row_data: Dict[str, Any],
        row_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """PUT updated values into an existing row identified by its id."""
        key = row_key or (
            self.data_key[:-1] if self.data_key.endswith("s") and len(self.data_key) > 1 else self.data_key
        )
        response = requests.put(
            f"{self.prices_endpoint}/{row_id}",
            json={key: row_data},
            headers=self._headers,
            auth=self._auth,
        )
        response.raise_for_status()
        return response.json()
