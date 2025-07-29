"""Tests for AquaWiz config flow."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.aquawiz.config_flow import AquaWizConfigFlow, validate_input
from custom_components.aquawiz.const import CONF_DEVICE_ID, CONF_UPDATE_INTERVAL, DOMAIN
from custom_components.aquawiz.api import AquaWizAPIError, AquaWizAuthError


class TestAquaWizConfigFlow:
    """Test the AquaWiz config flow."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def config_flow(self, mock_hass):
        """Create config flow fixture."""
        flow = AquaWizConfigFlow()
        flow.hass = mock_hass
        return flow

    @pytest.mark.asyncio
    async def test_validate_input_success(self, mock_hass, mock_api_auth_response):
        """Test successful input validation."""
        with patch('custom_components.aquawiz.config_flow.AquaWizAPI') as mock_api_class:
            mock_api = AsyncMock()
            mock_api.authenticate.return_value = mock_api_auth_response
            mock_api_class.return_value = mock_api

            user_input = {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "testpass",
            }

            result = await validate_input(mock_hass, user_input)

            assert result["title"] == "AquaWiz (test@example.com)"
            assert len(result["devices"]) == 1
            assert result["devices"][0]["id"] == "test_device_123"

    @pytest.mark.asyncio
    async def test_validate_input_auth_error(self, mock_hass):
        """Test input validation with auth error."""
        with patch('custom_components.aquawiz.config_flow.AquaWizAPI') as mock_api_class:
            mock_api = AsyncMock()
            mock_api.authenticate.side_effect = AquaWizAuthError("Invalid credentials")
            mock_api_class.return_value = mock_api

            user_input = {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "wrongpass",
            }

            with pytest.raises(AquaWizAuthError):
                await validate_input(mock_hass, user_input)

    @pytest.mark.asyncio
    async def test_validate_input_no_devices(self, mock_hass):
        """Test input validation with no devices."""
        with patch('custom_components.aquawiz.config_flow.AquaWizAPI') as mock_api_class:
            mock_api = AsyncMock()
            mock_api.authenticate.return_value = {"devices": []}
            mock_api_class.return_value = mock_api

            user_input = {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "testpass",
            }

            with pytest.raises(AquaWizAPIError, match="No devices found"):
                await validate_input(mock_hass, user_input)

    @pytest.mark.asyncio
    async def test_step_user_form(self, config_flow):
        """Test user step shows form."""
        result = await config_flow.async_step_user()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert CONF_USERNAME in result["data_schema"].schema
        assert CONF_PASSWORD in result["data_schema"].schema

    @pytest.mark.asyncio
    async def test_step_user_success(self, config_flow, mock_api_auth_response):
        """Test successful user step."""
        with patch('custom_components.aquawiz.config_flow.validate_input') as mock_validate:
            mock_validate.return_value = {
                "title": "AquaWiz (test@example.com)",
                "devices": mock_api_auth_response["user"]["devices"],
            }

            user_input = {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "testpass",
            }

            result = await config_flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "device"

    @pytest.mark.asyncio
    async def test_step_user_invalid_auth(self, config_flow):
        """Test user step with invalid auth."""
        with patch('custom_components.aquawiz.config_flow.validate_input') as mock_validate:
            mock_validate.side_effect = AquaWizAuthError("Invalid credentials")

            user_input = {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "wrongpass",
            }

            result = await config_flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "invalid_auth"

    @pytest.mark.asyncio
    async def test_step_user_cannot_connect(self, config_flow):
        """Test user step with connection error."""
        with patch('custom_components.aquawiz.config_flow.validate_input') as mock_validate:
            mock_validate.side_effect = AquaWizAPIError("Connection error")

            user_input = {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "testpass",
            }

            result = await config_flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_step_device_success(self, config_flow):
        """Test successful device step."""
        config_flow._data = {
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "testpass",
        }
        config_flow._devices = [{"id": "test_device_123", "name": "Test Device"}]

        with patch.object(config_flow, 'async_set_unique_id'), \
             patch.object(config_flow, '_abort_if_unique_id_configured'), \
             patch.object(config_flow, 'async_create_entry') as mock_create:

            mock_create.return_value = {"type": FlowResultType.CREATE_ENTRY}

            user_input = {CONF_DEVICE_ID: "test_device_123"}
            result = await config_flow.async_step_device(user_input)

            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_step_device_no_devices(self, config_flow):
        """Test device step with no devices."""
        config_flow._devices = []

        with patch.object(config_flow, 'async_abort') as mock_abort:
            mock_abort.return_value = {"type": FlowResultType.ABORT}

            result = await config_flow.async_step_device()

            mock_abort.assert_called_once_with(reason="no_devices")


class TestAquaWizOptionsFlow:
    """Test the AquaWiz options flow."""

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.options = {CONF_UPDATE_INTERVAL: 600}
        return entry

    @pytest.fixture
    def options_flow(self, mock_config_entry):
        """Create options flow fixture."""
        from custom_components.aquawiz.config_flow import AquaWizOptionsFlowHandler
        return AquaWizOptionsFlowHandler(mock_config_entry)

    @pytest.mark.asyncio
    async def test_options_init_form(self, options_flow):
        """Test options flow shows form."""
        result = await options_flow.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"
        assert CONF_UPDATE_INTERVAL in result["data_schema"].schema

    @pytest.mark.asyncio
    async def test_options_init_success(self, options_flow):
        """Test successful options flow."""
        with patch.object(options_flow, 'async_create_entry') as mock_create:
            mock_create.return_value = {"type": FlowResultType.CREATE_ENTRY}

            user_input = {CONF_UPDATE_INTERVAL: 300}
            result = await options_flow.async_step_init(user_input)

            mock_create.assert_called_once_with(title="", data=user_input)