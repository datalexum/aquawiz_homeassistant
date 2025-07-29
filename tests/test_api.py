"""Tests for AquaWiz API client."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import aiohttp

from custom_components.aquawiz.api import (
    AquaWizAPI,
    AquaWizAPIError,
    AquaWizAuthError,
)


class TestAquaWizAPI:
    """Test the AquaWiz API client."""

    @pytest.fixture
    def api_client(self):
        """Create API client fixture."""
        return AquaWizAPI()

    @pytest.mark.asyncio
    async def test_authenticate_success(self, api_client, mock_api_auth_response):
        """Test successful authentication."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_api_auth_response
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await api_client.authenticate("test@example.com", "testpass")

            assert result == mock_api_auth_response
            assert api_client._access_token == "test_token_123"
            assert api_client._token_expires is not None

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self, api_client):
        """Test authentication with invalid credentials."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(AquaWizAuthError, match="Invalid credentials"):
                await api_client.authenticate("test@example.com", "wrongpass")

    @pytest.mark.asyncio
    async def test_authenticate_api_error(self, api_client):
        """Test authentication with API error."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(AquaWizAPIError, match="Authentication failed: 500"):
                await api_client.authenticate("test@example.com", "testpass")

    @pytest.mark.asyncio
    async def test_authenticate_connection_error(self, api_client):
        """Test authentication with connection error."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Connection failed")

            with pytest.raises(AquaWizAPIError, match="Connection error"):
                await api_client.authenticate("test@example.com", "testpass")

    @pytest.mark.asyncio
    async def test_get_device_data_success(self, api_client, mock_api_data_response):
        """Test successful device data retrieval."""
        # Set up authenticated state
        api_client._access_token = "test_token_123"
        api_client._token_expires = datetime.now() + timedelta(hours=1)

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_api_data_response
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await api_client.get_device_data(
                "test@example.com", "testpass", "test_device_123"
            )

            assert result == mock_api_data_response

    @pytest.mark.asyncio
    async def test_get_device_data_token_refresh(self, api_client, mock_api_auth_response, mock_api_data_response):
        """Test device data retrieval with token refresh."""
        # Set up expired token
        api_client._access_token = "old_token"
        api_client._token_expires = datetime.now() - timedelta(hours=1)

        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Mock authentication response
            mock_auth_response = AsyncMock()
            mock_auth_response.status = 200
            mock_auth_response.json.return_value = mock_api_auth_response
            mock_post.return_value.__aenter__.return_value = mock_auth_response

            # Mock data response
            mock_data_response = AsyncMock()
            mock_data_response.status = 200
            mock_data_response.json.return_value = mock_api_data_response
            mock_get.return_value.__aenter__.return_value = mock_data_response

            result = await api_client.get_device_data(
                "test@example.com", "testpass", "test_device_123"
            )

            assert result == mock_api_data_response
            assert api_client._access_token == "test_token_123"

    @pytest.mark.asyncio
    async def test_parse_sensor_data(self, api_client, mock_api_data_response):
        """Test parsing of sensor data."""
        parsed_data = api_client.parse_sensor_data(mock_api_data_response)

        assert len(parsed_data) == 1
        data_point = parsed_data[0]
        
        assert data_point["alkalinity"] == 8.5
        assert data_point["dosing"] == 2.5
        assert data_point["ph"] == 8.2
        assert data_point["ph_o"] == 8.1
        assert data_point["delta_ph"] == 0.1
        assert isinstance(data_point["timestamp"], datetime)

    @pytest.mark.asyncio
    async def test_parse_sensor_data_empty(self, api_client):
        """Test parsing of empty sensor data."""
        empty_response = {"results": []}
        parsed_data = api_client.parse_sensor_data(empty_response)
        
        assert parsed_data == []

    @pytest.mark.asyncio
    async def test_get_historical_data(self, api_client, mock_api_data_response):
        """Test historical data retrieval."""
        api_client._access_token = "test_token_123"
        api_client._token_expires = datetime.now() + timedelta(hours=1)

        start_date = datetime(2024, 2, 1)
        end_date = datetime(2024, 2, 2)

        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('asyncio.sleep', new_callable=AsyncMock):
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_api_data_response
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await api_client.get_historical_data(
                "test@example.com", "testpass", "test_device_123", start_date, end_date
            )

            # Should make 2 requests (one for each day)
            assert len(result) == 2
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_close_session(self, api_client):
        """Test session closure."""
        # Mock session
        mock_session = AsyncMock()
        mock_session.closed = False
        api_client._session = mock_session

        await api_client.close()
        
        mock_session.close.assert_called_once()