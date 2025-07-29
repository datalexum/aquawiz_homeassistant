"""Constants for the AquaWiz integration."""
from typing import Final

DOMAIN: Final = "aquawiz"

CONF_DEVICE_ID: Final = "device_id"
CONF_UPDATE_INTERVAL: Final = "update_interval"

DEFAULT_UPDATE_INTERVAL: Final = 600  # 10 minutes in seconds

API_BASE_URL: Final = "https://server.aquawiz.net/api/v1"
API_AUTH_ENDPOINT: Final = f"{API_BASE_URL}/KH/auth"
API_QUERY_ENDPOINT: Final = f"{API_BASE_URL}/query/device"

ATTR_ALKALINITY = "alkalinity"
ATTR_PH = "ph"
ATTR_PH_O = "ph_o"
ATTR_DOSING = "dosing"
ATTR_DELTA_PH = "delta_ph"