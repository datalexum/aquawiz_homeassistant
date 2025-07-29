"""Config flow for AquaWiz integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .api import AquaWizAPI, AquaWizAPIError, AquaWizAuthError
from .const import CONF_DEVICE_ID, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = AquaWizAPI()
    
    try:
        auth_data = await api.authenticate(data[CONF_USERNAME], data[CONF_PASSWORD])
        devices = auth_data.get("devices", [])
        
        if not devices:
            raise AquaWizAPIError("No devices found for this account")
            
        return {
            "title": f"AquaWiz ({data[CONF_USERNAME]})",
            "devices": devices,
        }
    except AquaWizAuthError:
        raise AquaWizAuthError("Invalid credentials")
    except Exception as exc:
        _LOGGER.exception("Unexpected exception")
        raise AquaWizAPIError(f"Unknown error: {exc}")
    finally:
        # Always close the API session after validation
        await api.close()


class AquaWizConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AquaWiz."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self._data = {}
        self._devices = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self._data = user_input
                self._devices = info["devices"]
                return await self.async_step_device()
            except AquaWizAuthError:
                errors["base"] = "invalid_auth"
            except AquaWizAPIError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection step."""
        if user_input is not None:
            self._data[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID]
            
            await self.async_set_unique_id(f"{self._data[CONF_USERNAME]}_{user_input[CONF_DEVICE_ID]}")
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"AquaWiz ({self._data[CONF_USERNAME]})",
                data=self._data,
            )

        device_options = {}
        for device in self._devices:
            device_id = device.get("id", device.get("device_id", "unknown"))
            device_name = device.get("name", device.get("device_name", f"Device {device_id}"))
            device_options[device_id] = device_name

        if not device_options:
            return self.async_abort(reason="no_devices")

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(device_options)
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return AquaWizOptionsFlowHandler(config_entry)


class AquaWizOptionsFlowHandler(config_entries.OptionsFlow):
    """AquaWiz config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                }
            ),
        )