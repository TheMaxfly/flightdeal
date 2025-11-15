import os
from typing import Any, Dict, List, Optional

import requests


class DataManager:
    """Talk to a Sheety-powered Google Sheet for destination data."""

    def __init__(
        self,
        sheety_endpoint: Optional[str] = None,
        data_key: str = "prices",
        auth_token: Optional[str] = None,
    ):
        self.sheety_endpoint = sheety_endpoint or os.getenv("SHEETY_ENDPOINT")
        if not self.sheety_endpoint:
            raise ValueError("SHEETY_ENDPOINT must be provided to use DataManager.")
        self.data_key = data_key
        self.auth_token = auth_token or os.getenv("SHEETY_TOKEN")

    @property
    def _headers(self) -> Dict[str, str]:
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    def get_data(self) -> List[Dict[str, Any]]:
        """Return the full payload stored under the configured data key."""
        response = requests.get(self.sheety_endpoint, headers=self._headers)
        response.raise_for_status()
        payload = response.json()
        return payload.get(self.data_key, payload)

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
            self.sheety_endpoint,
            json={key: row_data},
            headers=self._headers,
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
            f"{self.sheety_endpoint}/{row_id}",
            json={key: row_data},
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()
