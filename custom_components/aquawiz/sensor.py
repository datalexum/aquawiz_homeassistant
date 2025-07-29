"""Sensor platform for AquaWiz integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AquaWizConfigEntry
from .const import (
    ATTR_ALKALINITY,
    ATTR_DELTA_PH,
    ATTR_DOSING,
    ATTR_PH,
    ATTR_PH_O,
    CONF_DEVICE_ID,
    DOMAIN,
)
from .coordinator import AquaWizDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AquaWizConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AquaWiz sensor entities."""
    coordinator = entry.runtime_data

    sensors = [
        AquaWizAlkalinitySensor(coordinator, entry),
        AquaWizPhSensor(coordinator, entry),
        AquaWizPhOSensor(coordinator, entry),
        AquaWizDosingSensor(coordinator, entry),
        AquaWizDeltaPhSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


class AquaWizSensorEntity(CoordinatorEntity[AquaWizDataUpdateCoordinator], SensorEntity):
    """Base class for AquaWiz sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AquaWizDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._sensor_type = sensor_type
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._username = entry.data[CONF_USERNAME]
        
        self._attr_unique_id = f"{self._device_id}_{sensor_type}"
        self._attr_name = name
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"AquaWiz {self._device_id}",
            manufacturer="AquaWiz",
            model="Alkalinity Monitor",
            sw_version="1.0",
            configuration_url="https://www.aquawiz.net",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        if self.coordinator.data:
            data = self.coordinator.data.get("data", {})
            if "timestamp" in data:
                attrs["last_measurement"] = data["timestamp"].isoformat()
        return attrs


class AquaWizAlkalinitySensor(AquaWizSensorEntity):
    """Alkalinity sensor for AquaWiz."""

    def __init__(
        self, coordinator: AquaWizDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the alkalinity sensor."""
        super().__init__(coordinator, entry, ATTR_ALKALINITY, "Alkalinity")
        
        self._attr_native_unit_of_measurement = "dKH"
        self._attr_device_class = SensorDeviceClass.PH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:test-tube"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        return data.get(ATTR_ALKALINITY)


class AquaWizPhSensor(AquaWizSensorEntity):
    """pH sensor for AquaWiz."""

    def __init__(
        self, coordinator: AquaWizDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the pH sensor."""
        super().__init__(coordinator, entry, ATTR_PH, "pH")
        
        self._attr_native_unit_of_measurement = "pH"
        self._attr_device_class = SensorDeviceClass.PH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:ph"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        return data.get(ATTR_PH)


class AquaWizPhOSensor(AquaWizSensorEntity):
    """pH(O) sensor for AquaWiz."""

    def __init__(
        self, coordinator: AquaWizDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the pH(O) sensor."""
        super().__init__(coordinator, entry, ATTR_PH_O, "pH(O)")
        
        self._attr_native_unit_of_measurement = "pH"
        self._attr_device_class = SensorDeviceClass.PH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:ph"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        return data.get(ATTR_PH_O)


class AquaWizDosingSensor(AquaWizSensorEntity):
    """Dosing sensor for AquaWiz."""

    def __init__(
        self, coordinator: AquaWizDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the dosing sensor."""
        super().__init__(coordinator, entry, ATTR_DOSING, "Dosing")
        
        self._attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:eyedropper-variant"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        return data.get(ATTR_DOSING)


class AquaWizDeltaPhSensor(AquaWizSensorEntity):
    """Delta pH sensor for AquaWiz."""

    def __init__(
        self, coordinator: AquaWizDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the delta pH sensor."""
        super().__init__(coordinator, entry, ATTR_DELTA_PH, "ΔpH")
        
        self._attr_native_unit_of_measurement = "pH"
        self._attr_device_class = SensorDeviceClass.PH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:delta"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        return data.get(ATTR_DELTA_PH)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes
        if self.coordinator.data:
            data = self.coordinator.data.get("data", {})
            ph = data.get(ATTR_PH)
            ph_o = data.get(ATTR_PH_O)
            if ph is not None and ph_o is not None:
                attrs["ph"] = ph
                attrs["ph_o"] = ph_o
                attrs["calculation"] = "pH - pH(O)"
        return attrs