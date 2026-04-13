import re
from typing import Optional, Tuple


def extract_transcript_text(stt_json: dict) -> str:
    texts = []

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "transcript" and isinstance(v, str):
                    texts.append(v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(stt_json)
    return " ".join(t.strip() for t in texts if t and t.strip()).strip()


def normalize_email_words(text: str) -> str:
    t = re.sub(r"\s+dot\s+", ".", text, flags=re.IGNORECASE)
    t = re.sub(r"\s+at\s+", "@", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_name_phone_email(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    phone = None
    email = None
    name = None

    phone_match = re.search(r"(\+?\d[\d\-\s]{7,}\d)", text)
    if phone_match:
        phone = phone_match.group(1).strip()

    email_match = re.search(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", text)
    if email_match:
        email = email_match.group(1).strip().lower()

    name_match = re.search(r"\bmy name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text)
    if name_match:
        name = name_match.group(1).strip()

    return name, phone, email
