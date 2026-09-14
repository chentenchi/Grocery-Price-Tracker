import requests

from kroger_auth import get_access_token


LOCATIONS_URL = "https://api.kroger.com/v1/locations"


def get_locations(zip_code):
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "filter.zipCode.near": zip_code,
        "filter.radiusInMiles": 10,
        "filter.limit": 10,
    }

    response = requests.get(
        LOCATIONS_URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["data"]


if __name__ == "__main__":
    zip_code = "45202"

    locations = get_locations(zip_code)

    print(f"\nKroger locations near {zip_code}:\n")

    for store in locations:
        address = store.get("address", {})

        print(f"Store:       {store.get('name')}")
        print(f"Location ID: {store.get('locationId')}")
        print(
            "Address:     "
            f"{address.get('addressLine1')}, "
            f"{address.get('city')}, "
            f"{address.get('state')} "
            f"{address.get('zipCode')}"
        )
        print("-" * 60)