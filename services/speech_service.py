import time
import requests

from services.auth import get_access_token
from services.config import PROJECT_ID, SPEECH_LOCATION, MAX_WAIT_SECONDS
from services.http_utils import make_session


def run_speech_to_text(gcs_audio_uri: str, transcript_output_prefix: str) -> dict:
    token = get_access_token()
    session = make_session()

    url = (
        f"https://speech.googleapis.com/v2/projects/{PROJECT_ID}/locations/"
        f"{SPEECH_LOCATION}/recognizers/_:batchRecognize"
    )

    payload = {
        "files": [{"uri": gcs_audio_uri}],
        "recognitionOutputConfig": {"gcsOutputConfig": {"uri": transcript_output_prefix}},
        "config": {
            "autoDecodingConfig": {},
            "languageCodes": ["en-US"],
            "model": "long",
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
            return resp.json()
        except Exception as e:
            last_error = e
            time.sleep(min(2 ** attempt, 15))

    raise RuntimeError(f"Speech-to-Text submit failed after retries: {last_error}")


def poll_operation(operation_name: str, status_placeholder) -> dict:
    token = get_access_token()
    session = make_session()
    url = f"https://speech.googleapis.com/v2/{operation_name}"
    start = time.time()
    attempt = 0

    while time.time() - start < MAX_WAIT_SECONDS:
        attempt += 1
        elapsed = int(time.time() - start)
        status_placeholder.info(
            f"DEBUG: polling Speech-to-Text... attempt {attempt}, elapsed {elapsed}s"
        )

        try:
            resp = session.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("done"):
                status_placeholder.success(f"DEBUG: transcription complete after {elapsed}s")
                return data

        except Exception as e:
            status_placeholder.warning(f"DEBUG: poll retry due to network issue: {e}")

        time.sleep(5)

    raise TimeoutError(f"Speech-to-Text operation timed out after {MAX_WAIT_SECONDS} seconds.")
