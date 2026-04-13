import os
from datetime import datetime, timezone
import uuid
import tempfile

import streamlit as st

from services.config import (
    PROJECT_ID,
    BUCKET_NAME,
    BQ_DATASET,
    AGENT_TABLE,
    ANALYTICS_TABLE,
    SUPPORTED_EXTENSIONS,
    RAW_PREFIX,
    TRANSCRIPT_PREFIX,
)
from services.gcs_service import upload_to_gcs, list_transcript_files, download_gcs_json
from services.speech_service import run_speech_to_text, poll_operation
from services.dlp_service import mask_sensitive_with_dlp
from services.bigquery_service import ensure_tables_exist, insert_rows
from services.parsers import extract_transcript_text, normalize_email_words, extract_name_phone_email


st.set_page_config(page_title="GES Audio Processor", page_icon="🎧", layout="wide")

st.title("🎧 GES Audio Upload and Processing")
st.caption(
    "Upload call audio, transcribe it, mask sensitive data, and push both agent and analytics rows into BigQuery."
)

with st.expander("Configuration", expanded=False):
    st.write(
        {
            "PROJECT_ID": PROJECT_ID,
            "BUCKET_NAME": BUCKET_NAME,
            "BQ_DATASET": BQ_DATASET,
            "AGENT_TABLE": AGENT_TABLE,
            "ANALYTICS_TABLE": ANALYTICS_TABLE,
        }
    )

uploaded = st.file_uploader(
    "Upload a .wav, .mp3, or .flac file",
    type=SUPPORTED_EXTENSIONS,
)
col1, col2 = st.columns(2)
auto_create = col1.checkbox("Create dataset/tables if missing", value=False)
process_btn = col2.button("Process audio", type="primary", use_container_width=True)

debug_box = st.empty()

if process_btn:
    if not uploaded:
        st.error("Please upload an audio file first.")
        st.stop()

    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        st.error(f"Unsupported file type: .{ext}. Use one of: {', '.join(SUPPORTED_EXTENSIONS)}")
        st.stop()

    if auto_create:
        with st.spinner("Ensuring BigQuery dataset and tables exist..."):
            ensure_tables_exist()
        debug_box.info("DEBUG: table check complete")

    run_id = uuid.uuid4().hex[:8]
    base_name = os.path.splitext(uploaded.name)[0]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    object_name = f"{RAW_PREFIX}/{base_name}_{timestamp}_{run_id}.{ext}"
    transcript_prefix = f"{TRANSCRIPT_PREFIX}/{base_name}_{run_id}/"

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded.getbuffer())
        local_path = tmp.name

    try:
        with st.spinner("Uploading audio to Cloud Storage..."):
            gcs_audio_uri = upload_to_gcs(local_path, object_name)
        debug_box.success(f"DEBUG: upload complete → {gcs_audio_uri}")

        with st.spinner("Submitting Speech-to-Text job..."):
            op = run_speech_to_text(gcs_audio_uri, f"gs://{BUCKET_NAME}/{transcript_prefix}")
            operation_name = op["name"]
        st.info(f"DEBUG: speech job submitted → {operation_name}")

        with st.spinner("Waiting for transcription to complete..."):
            poll_operation(operation_name, debug_box)

        st.success("DEBUG: transcription DONE")

        files = list_transcript_files(transcript_prefix)
        if not files:
            st.error("Transcription finished but no transcript file was found.")
            st.stop()

        transcript_uri = files[0]
        st.success(f"Transcript saved to {transcript_uri}")
        st.info("DEBUG: transcript file found")

        transcript_json = download_gcs_json(transcript_uri)
        raw_transcript = extract_transcript_text(transcript_json)
        normalized_transcript = normalize_email_words(raw_transcript)

        customer_name, phone_number, email = extract_name_phone_email(normalized_transcript)
        masked_transcript = mask_sensitive_with_dlp(normalized_transcript)

        processed_at = datetime.now(timezone.utc).isoformat()
        call_id = f"call-{timestamp}-{run_id}"

        agent_row = {
            "call_id": call_id,
            "audio_uri": gcs_audio_uri,
            "transcript_uri": transcript_uri,
            "customer_name": customer_name,
            "phone_number": phone_number,
            "email": email,
            "transcript_raw": normalized_transcript,
            "language_code": "en-US",
            "processed_at": processed_at,
        }

        analytics_row = {
            "call_id": call_id,
            "audio_uri": gcs_audio_uri,
            "transcript_uri": transcript_uri,
            "transcript_masked": masked_transcript,
            "language_code": "en-US",
            "processed_at": processed_at,
        }

        with st.spinner("Writing rows to BigQuery..."):
            insert_rows(agent_row, analytics_row)
        st.success("DEBUG: BigQuery insert complete")

        st.success("Done. Rows inserted into both BigQuery tables.")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Agent View")
            st.json(agent_row)
        with c2:
            st.subheader("Analytics View")
            st.json(analytics_row)

        st.subheader("Transcript Preview")
        st.text_area("Raw transcript", normalized_transcript, height=140)
        st.text_area("Masked transcript", masked_transcript, height=140)

        st.info(
            "Connect Looker Studio to the analytics table: "
            f"{PROJECT_ID}.{BQ_DATASET}.{ANALYTICS_TABLE}"
        )

    except Exception as e:
        st.exception(e)
    finally:
        try:
            os.remove(local_path)
        except Exception:
            pass
