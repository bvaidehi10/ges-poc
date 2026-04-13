import os

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ges-poc-490514")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ges-poc-capgemini-001")
BQ_DATASET = os.getenv("BQ_DATASET", "ges_demo")
AGENT_TABLE = os.getenv("BQ_AGENT_TABLE", "call_transcripts_agent")
ANALYTICS_TABLE = os.getenv("BQ_ANALYTICS_TABLE", "call_transcripts_analytics")
SPEECH_LOCATION = os.getenv("SPEECH_LOCATION", "global")

SUPPORTED_EXTENSIONS = ["wav", "mp3", "flac"]
MAX_WAIT_SECONDS = int(os.getenv("MAX_WAIT_SECONDS", "600"))

RAW_PREFIX = "raw-audio"
TRANSCRIPT_PREFIX = "transcripts"
