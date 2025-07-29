"""Test configuration for AquaWiz integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.aquawiz.const import CONF_DEVICE_ID, DOMAIN


@pytest.fixture
def mock_config_entry():
    """Mock config entry fixture."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test AquaWiz",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "testpass",
            CONF_DEVICE_ID: "test_device_123",
        },
        options={},
        source="user",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_api_auth_response():
    """Mock API authentication response."""
    return {
        "access_token": "test_token_123",
        "tokenExp": 3600,
        "user": {
            "email": "test@example.com",
            "devices": [
                {
                    "id": "test_device_123",
                    "name": "Test Device",
                    "device_id": "test_device_123",
                    "device_name": "Test Device"
                }
            ]
        }
    }


@pytest.fixture
def mock_api_data_response():
    """Mock API data response."""
    return {
        "sample_size": 1,
        "device": "test_device_123",
        "results": [
            [
                1706745600000,  # 2024-02-01 00:00:00 UTC in milliseconds
                {
                    "field22": 8500,    # Alkalinity in dKH * 1000 (8.5 dKH)
                    "field23": 0,       # Unknown field
                    "field24": 0,       # Unknown field
                    "field25": 0,       # Unknown field
                    "field26": 2500,    # Dosing in ml * 1000 (2.5 ml)
                    "field27": 8200,    # pH * 1000 (8.2 pH)
                    "field28": 8100,    # pH(O) * 1000 (8.1 pH)
                }
            ]
        ]
    }


@pytest.fixture
def mock_parsed_sensor_data():
    """Mock parsed sensor data."""
    from datetime import datetime
    return {
        "timestamp": datetime.fromtimestamp(1706745600),
        "alkalinity": 8.5,
        "dosing": 2.5,
        "ph": 8.2,
        "ph_o": 8.1,
        "delta_ph": 0.1,
    }