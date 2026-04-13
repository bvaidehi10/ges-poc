import time

from services.auth import get_access_token
from services.config import PROJECT_ID
from services.http_utils import make_session


def mask_sensitive_with_dlp(text: str) -> str:
    token = get_access_token()
    session = make_session()
    url = f"https://dlp.googleapis.com/v2/projects/{PROJECT_ID}/content:deidentify"

    payload = {
        "item": {"value": text},
        "deidentifyConfig": {
            "infoTypeTransformations": {
                "transformations": [
                    {"primitiveTransformation": {"replaceWithInfoTypeConfig": {}}}
                ]
            }
        },
        "inspectConfig": {
            "infoTypes": [
                {"name": "PHONE_NUMBER"},
                {"name": "EMAIL_ADDRESS"},
            ]
        },
    }

    last_error = None
    for attempt in range(1, 6):
        try:
            resp = session.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )
            resp.raise_for_status()
            return resp.json().get("item", {}).get("value", text)
        except Exception as e:
            last_error = e
            time.sleep(min(2 ** attempt, 15))

    raise RuntimeError(f"DLP failed after retries: {last_error}")
