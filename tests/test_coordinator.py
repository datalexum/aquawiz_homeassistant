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
            return coordinator

    @pytest.mark.asyncio
    async def test_update_data_success(self, coordinator, mock_api_data_response, mock_parsed_sensor_data):
        """Test successful data update."""
        coordinator.api.get_device_data.return_value = mock_api_data_response
        coordinator.api.parse_sensor_data.return_value = [mock_parsed_sensor_data]
        coordinator._historical_backfill_done = True  # Skip backfill for this test

        result = await coordinator._async_update_data()

        assert result["data"] == mock_parsed_sensor_data
        assert result["device_id"] == "test_device_123"
        assert "last_update" in result
        coordinator.api.get_device_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_data_api_error(self, coordinator):
        """Test data update with API error."""
        coordinator.api.get_device_data.side_effect = AquaWizAPIError("API Error")

        with pytest.raises(UpdateFailed, match="Error communicating with API"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_update_data_empty_response(self, coordinator):
        """Test data update with empty response."""
        coordinator.api.get_device_data.return_value = {"results": []}
        coordinator.api.parse_sensor_data.return_value = []
        coordinator._historical_backfill_done = True

        result = await coordinator._async_update_data()

        assert result["data"] == {}
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
        with patch('custom_components.aquawiz.coordinator.get_instance', return_value=None):
            # Should not raise exception
            await coordinator._store_historical_data([mock_parsed_sensor_data])

    @pytest.mark.asyncio 
    async def test_store_historical_data_success(self, coordinator, mock_parsed_sensor_data):
        """Test successful historical data storage."""
        mock_recorder = MagicMock()
        
        with patch('custom_components.aquawiz.coordinator.get_instance', return_value=mock_recorder), \
             patch('custom_components.aquawiz.coordinator.async_add_external_statistics') as mock_add_stats:
            
            await coordinator._store_historical_data([mock_parsed_sensor_data])
            
            # Should call async_add_external_statistics for each sensor type
            assert mock_add_stats.call_count == 5  # 5 sensors

    @pytest.mark.asyncio
    async def test_update_options(self, coordinator):
        """Test updating coordinator options."""
        coordinator.entry.options = {"update_interval": 300}  # 5 minutes
        
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
        coordinator.api.get_device_data.return_value = mock_api_data_response
        coordinator.api.parse_sensor_data.return_value = [mock_parsed_sensor_data]
        
        with patch.object(coordinator, '_backfill_historical_data') as mock_backfill:
            await coordinator._async_update_data()
            
            mock_backfill.assert_not_called()