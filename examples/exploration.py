import os

import requests
from dotenv import load_dotenv

load_dotenv()


def get_token():
    json_data = {
        'user': os.getenv("USERNAME"),
        'password': os.getenv("PASSWORD"),
        'token': {
            'access_token': '',
        },
    }

    response = requests.post('https://server.aquawiz.net/api/v1/KH/auth', json=json_data)
    if response.status_code == 200:
        print("Login successful!")
        print("Response:", response.json())
        return {
            'access_token': response.json()['access_token'],
            'expires_in': response.json()['tokenExp'],
            'email': response.json()['user']['email'],
            'devices': response.json()['user']['devices'],
        }
    else:
        print("Login failed with status code:", response.status_code)
        print("Response:", response.text)
        return None


def get_values(token, device_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'de,en-US;q=0.7,en;q=0.3',
        'Authorization': f'Bearer {token}',
        'Origin': 'https://www.aquawiz.net',
        'Connection': 'keep-alive',
        'Referer': 'https://www.aquawiz.net/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }

    # 2025-07-27T00:00:00.000Z needs to be replaced with the current date in ISO format, seems to return the data for 24h starting from that date.
    response = requests.get(
        f'https://server.aquawiz.net/api/v1/query/device/{device_id}/graph?date=2025-07-27T00:00:00.000Z',
        headers=headers,
    )
    """
    Response format:
    {
        sample_size: int,
        device: str, # The device ID
        results: [
            [
                timestamp: int, # Unix timestamp in milliseconds,
                {
                    field22: int, # Alkalinity in dKH * 1000
                    field23: int, # Unknown field, to be ignored
                    field24: int, # Unknown field, to be ignored 
                    field25: int, # Unknown field, to be ignored
                    field26: int, # Alkalinity dosing in ml * 1000
                    field27: int, # pH * 1000
                    field28: int, # pH(O) * 1000 (pH after saturation with air)
                }
            ],
        ]
    }
    """

    return response.json()


def main():
    token = get_token()
    response = get_values(token['access_token'], os.getenv("DEVICE_ID"))
    print(response)


if __name__ == "__main__":
    main()
