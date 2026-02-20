"""Tests for AquaWiz coordinator."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.aquawiz.coordinator import AquaWizDataUpdateCoordinator
from custom_components.aquawiz.api import AquaWizAPIError


class TestAquaWizDataUpdateCoordinator:
    """Test the AquaWiz data update coordinator."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant."""
        hass = MagicMock(spec=HomeAssistant)
        return hass

    @pytest.fixture
    def coordinator(self, mock_hass, mock_config_entry):
        """Create coordinator fixture."""
        with patch('custom_components.aquawiz.coordinator.AquaWizAPI'):
            coordinator = AquaWizDataUpdateCoordinator(mock_hass, mock_config_entry)
            coordinator.api = AsyncMock()
            # Sync methods must use MagicMock, not AsyncMock
            coordinator.api.parse_sensor_data = MagicMock()
            coordinator.api.parse_device_config = MagicMock()
            return coordinator

    @pytest.mark.asyncio
    async def test_update_data_success(self, coordinator, mock_api_data_response, mock_parsed_sensor_data, mock_api_config_response):
        """Test successful data update."""
        coordinator.api.get_device_config.return_value = mock_api_config_response
        coordinator.api.parse_device_config.return_value = {
            "ml_per_dkh": 582,
            "dosing_container_remaining": 671,
            "max_dosing_per_hour": 41,
            "target_kh": 7.2,
        }
        coordinator.api.get_device_data.return_value = mock_api_data_response
        coordinator.api.parse_sensor_data.return_value = [mock_parsed_sensor_data]
        coordinator._historical_backfill_done = True  # Skip backfill for this test

        result = await coordinator._async_update_data()

        assert result["data"]["alkalinity"] == mock_parsed_sensor_data["alkalinity"]
        assert result["data"]["dosing_today"] == mock_parsed_sensor_data["dosing"]
        assert result["data"]["dosing_container_remaining"] == 671
        assert result["data"]["max_dosing_per_hour"] == 41
        assert result["data"]["target_kh"] == 7.2
        assert result["device_id"] == "test_device_123"
        assert "last_update" in result
        coordinator.api.get_device_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_data_api_error(self, coordinator):
        """Test data update with API error."""
        coordinator.api.get_device_config.return_value = {}
        coordinator.api.parse_device_config.return_value = {"ml_per_dkh": 0}
        coordinator.api.get_device_data.side_effect = AquaWizAPIError("API Error")

        with pytest.raises(UpdateFailed, match="Error communicating with API"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_update_data_empty_response(self, coordinator):
        """Test data update with empty response."""
        coordinator.api.get_device_config.return_value = {}
        coordinator.api.parse_device_config.return_value = {
            "ml_per_dkh": 582,
            "dosing_container_remaining": 671,
            "max_dosing_per_hour": 41,
            "target_kh": 7.2,
        }
        coordinator.api.get_device_data.return_value = {"results": []}
        coordinator.api.parse_sensor_data.return_value = []
        coordinator._historical_backfill_done = True

        result = await coordinator._async_update_data()

        # Config data should still be present even with no sensor data
        assert result["data"]["dosing_container_remaining"] == 671
        assert result["device_id"] == "test_device_123"

    @pytest.mark.asyncio
    async def test_historical_backfill_success(self, coordinator, mock_api_data_response, mock_parsed_sensor_data):
        """Test successful historical data backfill."""
        coordinator.api.get_historical_data.return_value = [mock_api_data_response]
        coordinator.api.parse_sensor_data.return_value = [mock_parsed_sensor_data]
        
        with patch.object(coordinator, '_store_historical_data') as mock_store:
            await coordinator._backfill_historical_data()
            
            coordinator.api.get_historical_data.assert_called_once()
            mock_store.assert_called_once_with([mock_parsed_sensor_data])

    @pytest.mark.asyncio
    async def test_historical_backfill_error(self, coordinator):
        """Test historical data backfill with error."""
        coordinator.api.get_historical_data.side_effect = AquaWizAPIError("API Error")
        
        # Should not raise exception, just log warning
        await coordinator._backfill_historical_data()
        
        coordinator.api.get_historical_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_historical_data_no_recorder(self, coordinator, mock_parsed_sensor_data):
        """Test historical data storage when recorder is not available."""
        with patch('homeassistant.components.recorder.get_instance', return_value=None):
            # Should not raise exception
            await coordinator._store_historical_data([mock_parsed_sensor_data])

    @pytest.mark.asyncio
    async def test_store_historical_data_success(self, coordinator, mock_parsed_sensor_data):
        """Test successful historical data storage."""
        mock_recorder = MagicMock()

        with patch('homeassistant.components.recorder.get_instance', return_value=mock_recorder), \
             patch('homeassistant.components.recorder.statistics.async_add_external_statistics') as mock_add_stats:

            await coordinator._store_historical_data([mock_parsed_sensor_data])

            # Should call async_add_external_statistics for each sensor type
            assert mock_add_stats.call_count == 6  # 6 sensors

    @pytest.mark.asyncio
    async def test_update_options(self, coordinator):
        """Test updating coordinator options."""
        object.__setattr__(coordinator.entry, 'options', {"update_interval": 300})

        coordinator.update_options()

        assert coordinator.update_interval == timedelta(seconds=300)

    @pytest.mark.asyncio
    async def test_async_shutdown(self, coordinator):
        """Test coordinator shutdown."""
        await coordinator.async_shutdown()
        
        coordinator.api.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_first_update_triggers_backfill(self, coordinator, mock_api_data_response, mock_parsed_sensor_data):
        """Test that first update triggers historical backfill."""
        coordinator.api.get_device_config.return_value = {}
        coordinator.api.parse_device_config.return_value = {"ml_per_dkh": 582}
        coordinator.api.get_device_data.return_value = mock_api_data_response
        coordinator.api.parse_sensor_data.return_value = [mock_parsed_sensor_data]
        coordinator.api.get_historical_data.return_value = []

        with patch.object(coordinator, '_backfill_historical_data') as mock_backfill:
            await coordinator._async_update_data()

            mock_backfill.assert_called_once()
            assert coordinator._historical_backfill_done is True

    @pytest.mark.asyncio
    async def test_subsequent_updates_skip_backfill(self, coordinator, mock_api_data_response, mock_parsed_sensor_data):
        """Test that subsequent updates don't trigger backfill."""
        coordinator._historical_backfill_done = True
        coordinator.api.get_device_config.return_value = {}
        coordinator.api.parse_device_config.return_value = {"ml_per_dkh": 582}
        coordinator.api.get_device_data.return_value = mock_api_data_response
        coordinator.api.parse_sensor_data.return_value = [mock_parsed_sensor_data]

        with patch.object(coordinator, '_backfill_historical_data') as mock_backfill:
            await coordinator._async_update_data()

            mock_backfill.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_data_config_fetch_failure(self, coordinator, mock_api_data_response, mock_parsed_sensor_data):
        """Test that data update continues when config fetch fails."""
        coordinator.api.get_device_config.side_effect = AquaWizAPIError("Config fetch failed")
        coordinator.api.get_device_data.return_value = mock_api_data_response
        coordinator.api.parse_sensor_data.return_value = [mock_parsed_sensor_data]
        coordinator._historical_backfill_done = True

        result = await coordinator._async_update_data()

        # Should still return measurement data
        assert result["data"]["alkalinity"] == mock_parsed_sensor_data["alkalinity"]
        assert result["device_id"] == "test_device_123"
        # _ml_per_dkh defaults to 0, so parse_sensor_data is called with 0
        coordinator.api.parse_sensor_data.assert_called_once_with(mock_api_data_response, 0)