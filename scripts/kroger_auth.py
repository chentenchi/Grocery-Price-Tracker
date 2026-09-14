import os
from pathlib import Path

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

CLIENT_ID = os.getenv("KROGER_CLIENT_ID")
CLIENT_SECRET = os.getenv("KROGER_CLIENT_SECRET")

TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"


def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError(
            "Kroger credentials were not found. Check your .env file."
        )

    response = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "client_credentials",
            "scope": "product.compact",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["access_token"]


if __name__ == "__main__":
    token = get_access_token()

    print("Kroger authentication successful!")
    print(f"Token preview: {token[:10]}...")