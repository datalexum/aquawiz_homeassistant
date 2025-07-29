"""API client for AquaWiz."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import API_AUTH_ENDPOINT, API_QUERY_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class AquaWizAPIError(Exception):
    """Exception to indicate a general API error."""


class AquaWizAuthError(AquaWizAPIError):
    """Exception to indicate an authentication error."""


class AquaWizAPI:
    """API client for AquaWiz."""

    def __init__(self) -> None:
        """Initialize the API client."""
        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the API client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def authenticate(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate with the AquaWiz API."""
        session = await self._get_session()
        
        json_data = {
            "user": username,
            "password": password,
            "token": {
                "access_token": "",
            },
        }

        try:
            async with session.post(API_AUTH_ENDPOINT, json=json_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self._access_token = data["access_token"]
                    # Token expires in seconds, convert to datetime
                    expires_in = data.get("tokenExp", 3600)
                    self._token_expires = datetime.now() + timedelta(seconds=expires_in)
                    return data
                elif response.status == 401:
                    raise AquaWizAuthError("Invalid credentials")
                else:
                    text = await response.text()
                    raise AquaWizAPIError(f"Authentication failed: {response.status} - {text}")
        except aiohttp.ClientError as exc:
            raise AquaWizAPIError(f"Connection error: {exc}")

    async def _ensure_authenticated(self, username: str, password: str) -> None:
        """Ensure we have a valid authentication token."""
        if (
            self._access_token is None
            or self._token_expires is None
            or datetime.now() >= self._token_expires - timedelta(minutes=5)
        ):
            await self.authenticate(username, password)

    async def get_device_data(
        self, 
        username: str, 
        password: str, 
        device_id: str, 
        date: datetime | None = None
    ) -> dict[str, Any]:
        """Get device data from the AquaWiz API."""
        await self._ensure_authenticated(username, password)
        
        if date is None:
            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        date_str = date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + "Z"
        
        session = await self._get_session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": f"Bearer {self._access_token}",
            "Origin": "https://www.aquawiz.net",
            "Connection": "keep-alive",
            "Referer": "https://www.aquawiz.net/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

        url = f"{API_QUERY_ENDPOINT}/{device_id}/graph?date={date_str}"
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    # Token might be expired, try to re-authenticate once
                    await self.authenticate(username, password)
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with session.get(url, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            return await retry_response.json()
                        else:
                            text = await retry_response.text()
                            raise AquaWizAPIError(f"API request failed after retry: {retry_response.status} - {text}")
                else:
                    text = await response.text()
                    raise AquaWizAPIError(f"API request failed: {response.status} - {text}")
        except aiohttp.ClientError as exc:
            raise AquaWizAPIError(f"Connection error: {exc}")

    async def get_historical_data(
        self,
        username: str,
        password: str,
        device_id: str,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get historical data for a date range."""
        if end_date is None:
            end_date = datetime.now()
        
        all_data = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_date <= end_date:
            try:
                data = await self.get_device_data(username, password, device_id, current_date)
                all_data.append(data)
                
                # Rate limiting - wait between requests
                await asyncio.sleep(0.5)
                
            except AquaWizAPIError as exc:
                _LOGGER.warning("Failed to get data for %s: %s", current_date.date(), exc)
            
            current_date += timedelta(days=1)
        
        return all_data

    def parse_sensor_data(self, api_response: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse API response into sensor data points."""
        results = api_response.get("results", [])
        parsed_data = []
        
        for result in results:
            if len(result) >= 2:
                timestamp_ms = result[0]
                data_fields = result[1]
                
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
                
                # Parse the fields based on the API documentation
                alkalinity = data_fields.get("field22", 0) / 1000  # dKH
                dosing = data_fields.get("field26", 0) / 1000  # ml
                ph = data_fields.get("field27", 0) / 1000
                ph_o = data_fields.get("field28", 0) / 1000
                
                # Calculate delta pH
                delta_ph = ph - ph_o if ph > 0 and ph_o > 0 else 0
                
                parsed_data.append({
                    "timestamp": timestamp,
                    "alkalinity": alkalinity,
                    "dosing": dosing,
                    "ph": ph,
                    "ph_o": ph_o,
                    "delta_ph": delta_ph,
                })
        
        return parsed_data