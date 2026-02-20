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
ATTR_DKH_DOSED = "dkh_dosed"
ATTR_DOSING_TODAY = "dosing_today"
ATTR_DELTA_PH = "delta_ph"
ATTR_ML_PER_DKH = "ml_per_dkh"
ATTR_DOSING_CONTAINER_REMAINING = "dosing_container_remaining"
ATTR_MAX_DOSING_PER_HOUR = "max_dosing_per_hour"
ATTR_TARGET_KH = "target_kh"