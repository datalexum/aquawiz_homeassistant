# AquaWiz Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant integration for AquaWiz Alkalinity Monitoring devices. This integration allows you to monitor your reef tank's alkalinity, pH levels, and dosing data directly in Home Assistant.

## Features

- **Real-time monitoring**: Track alkalinity (dKH), pH, pH(O), and dosing volumes
- **Calculated ΔpH**: Automatically calculates the difference between pH and pH(O)
- **Historical data**: Backfills up to 7 days of historical data when first set up
- **Long-term storage**: All sensor data is stored in Home Assistant's recorder for long-term analysis
- **Configurable polling**: Adjustable update interval (default: 10 minutes)
- **Device integration**: Shows up as a single device with all sensors

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/aquawiz` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "AquaWiz"
3. Enter your AquaWiz credentials (username and password)
4. Select your device from the list
5. The integration will automatically start collecting data

### Options

After setup, you can configure the following options:

- **Update Interval**: How often to check for new data (60-3600 seconds, default: 600)

## Sensors

The integration creates the following sensors for your AquaWiz device:

| Sensor | Unit | Description |
|--------|------|-------------|
| Alkalinity | dKH | Current alkalinity level |
| pH | pH | Current pH level |
| pH(O) | pH | pH level after air saturation |
| Dosing | ml | Cumulative dosing volume |
| ΔpH | pH | Calculated difference (pH - pH(O)) |

## Data Storage

- All sensor readings are stored in Home Assistant's recorder database
- Historical data is automatically backfilled when the integration is first set up
- Data is preserved even if Home Assistant is offline for extended periods

## Troubleshooting

### Common Issues

**Invalid credentials**: Ensure your AquaWiz username and password are correct and that you can log in to the AquaWiz web interface.

**No devices found**: Make sure your AquaWiz device is properly registered to your account and visible in the AquaWiz web interface.

**Connection errors**: Check your internet connection and ensure Home Assistant can reach `server.aquawiz.net`.

### Debug Logging

To enable debug logging for troubleshooting:

```yaml
logger:
  logs:
    custom_components.aquawiz: debug
```

## Development

### Project Structure

```
├── custom_components/aquawiz/    # Home Assistant integration
│   ├── __init__.py              # Integration setup
│   ├── api.py                   # API client
│   ├── config_flow.py          # Configuration flow
│   ├── const.py                # Constants
│   ├── coordinator.py          # Data coordinator
│   ├── manifest.json           # Integration metadata
│   ├── sensor.py              # Sensor entities
│   └── translations/          # UI translations
│       ├── en.json
│       └── de.json
├── examples/                   # Example scripts
│   └── exploration.py         # API exploration script
├── tests/                     # Unit tests
│   ├── __init__.py
│   ├── conftest.py           # Test fixtures
│   ├── test_api.py           # API tests
│   ├── test_config_flow.py   # Config flow tests
│   └── test_coordinator.py   # Coordinator tests
├── .gitignore                # Git ignore rules
├── hacs.json                 # HACS metadata
├── pytest.ini               # Pytest configuration
├── requirements-test.txt     # Test dependencies
└── README.md                 # This file
```

### Running Tests

1. Install test dependencies:
   ```bash
   pip install -r requirements-test.txt
   ```

2. Run tests:
   ```bash
   pytest
   ```

3. Run tests with coverage:
   ```bash
   pytest --cov=custom_components.aquawiz
   ```

### API Exploration

The `examples/exploration.py` script demonstrates how to interact with the AquaWiz API directly. Create a `.env` file with your credentials:

```env
USERNAME=your_username
PASSWORD=your_password
DEVICE_ID=your_device_id
```

## Support

If you encounter any issues or have feature requests, please open an issue on GitHub.

## License

This project is licensed under the MIT License.