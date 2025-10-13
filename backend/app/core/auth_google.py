import requests
from app.core.config import settings

def verify_google_id_token(id_token: str) -> dict:
    response = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": id_token}
    )
    if response.status_code != 200:
        raise ValueError("Invalid Google ID token")

    payload = response.json()
    if payload.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise ValueError("Invalid audience")

    return payload