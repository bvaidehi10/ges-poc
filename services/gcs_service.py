import json

from google.cloud import storage

from services.config import PROJECT_ID, BUCKET_NAME


def upload_to_gcs(local_path: str, dest_blob_name: str) -> str:
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(dest_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{BUCKET_NAME}/{dest_blob_name}"


def list_transcript_files(prefix: str) -> list[str]:
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    return [f"gs://{BUCKET_NAME}/{blob.name}" for blob in client.list_blobs(bucket, prefix=prefix)]


def download_gcs_json(gcs_uri: str) -> dict:
    bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return json.loads(blob.download_as_text())
