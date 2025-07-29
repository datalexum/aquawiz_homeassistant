"""DataUpdateCoordinator for AquaWiz."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AquaWizAPI, AquaWizAPIError
from .const import CONF_DEVICE_ID, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class AquaWizDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching AquaWiz data from the API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api = AquaWizAPI()
        self.entry = entry
        self._username = entry.data[CONF_USERNAME]
        self._password = entry.data[CONF_PASSWORD]
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._last_successful_update: datetime | None = None
        self._historical_backfill_done = False

        update_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Get current day's data
            current_data = await self.api.get_device_data(
                self._username, self._password, self._device_id
            )
            
            parsed_data = self.api.parse_sensor_data(current_data)
            
            # If this is the first successful update, try to backfill historical data
            if not self._historical_backfill_done:
                await self._backfill_historical_data()
                self._historical_backfill_done = True
            
            self._last_successful_update = datetime.now()
            
            # Return the latest data point or empty dict if no data
            if parsed_data:
                latest_data = max(parsed_data, key=lambda x: x["timestamp"])
                return {
                    "data": latest_data,
                    "device_id": self._device_id,
                    "last_update": self._last_successful_update,
                }
            else:
                return {
                    "data": {},
                    "device_id": self._device_id,
                    "last_update": self._last_successful_update,
                }
                
        except AquaWizAPIError as exc:
            raise UpdateFailed(f"Error communicating with API: {exc}")

    async def _backfill_historical_data(self) -> None:
        """Backfill historical data if Home Assistant was offline."""
        try:
            # Look back up to 7 days for historical data
            start_date = datetime.now() - timedelta(days=7)
            
            _LOGGER.info("Starting historical data backfill for device %s", self._device_id)
            
            historical_data = await self.api.get_historical_data(
                self._username,
                self._password,
                self._device_id,
                start_date,
            )
            
            all_parsed_data = []
            for daily_data in historical_data:
                parsed_data = self.api.parse_sensor_data(daily_data)
                all_parsed_data.extend(parsed_data)
            
            if all_parsed_data:
                # Store historical data points in Home Assistant's recorder
                await self._store_historical_data(all_parsed_data)
                _LOGGER.info(
                    "Backfilled %d historical data points for device %s",
                    len(all_parsed_data),
                    self._device_id,
                )
            
        except Exception as exc:
            _LOGGER.warning("Failed to backfill historical data: %s", exc)

    async def _store_historical_data(self, data_points: list[dict[str, Any]]) -> None:
        """Store historical data points in Home Assistant."""
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
        from homeassistant.components.recorder.statistics import (
            async_add_external_statistics,
        )
        
        if not data_points:
            return
            
        recorder_instance = get_instance(self.hass)
        if not recorder_instance:
            _LOGGER.warning("Recorder not available for historical data storage")
            return

        # Create statistics metadata for each sensor
        statistics_meta = [
            StatisticMetaData(
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{self._device_id}_alkalinity",
                name="Alkalinity",
                unit_of_measurement="dKH",
                has_mean=True,
                has_sum=False,
            ),
            StatisticMetaData(
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{self._device_id}_ph",
                name="pH",
                unit_of_measurement="pH",
                has_mean=True,
                has_sum=False,
            ),
            StatisticMetaData(
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{self._device_id}_ph_o",
                name="pH(O)",
                unit_of_measurement="pH",
                has_mean=True,
                has_sum=False,
            ),
            StatisticMetaData(
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{self._device_id}_dosing",
                name="Dosing",
                unit_of_measurement="ml",
                has_mean=True,
                has_sum=True,
            ),
            StatisticMetaData(
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{self._device_id}_delta_ph",
                name="ΔpH",
                unit_of_measurement="pH",
                has_mean=True,
                has_sum=False,
            ),
        ]

        # Create statistics data for each sensor
        for meta in statistics_meta:
            sensor_key = meta.statistic_id.split("_")[-1]
            if sensor_key == "delta":
                sensor_key = "delta_ph"
                
            statistics_data = []
            for point in data_points:
                if sensor_key in point and point[sensor_key] is not None:
                    stat_data = StatisticData(
                        start=point["timestamp"],
                        mean=point[sensor_key],
                    )
                    if meta.has_sum and sensor_key == "dosing":
                        stat_data.sum = point[sensor_key]
                    statistics_data.append(stat_data)
            
            if statistics_data:
                async_add_external_statistics(
                    self.hass, meta, statistics_data
                )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.close()

    def update_options(self) -> None:
        """Update coordinator options."""
        update_interval = timedelta(
            seconds=self.entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        self.update_interval = update_interval