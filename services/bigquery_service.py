from google.cloud import bigquery

from services.config import PROJECT_ID, BQ_DATASET, AGENT_TABLE, ANALYTICS_TABLE


def ensure_tables_exist() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    dataset_id = f"{PROJECT_ID}.{BQ_DATASET}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)

    agent_schema = [
        bigquery.SchemaField("call_id", "STRING"),
        bigquery.SchemaField("audio_uri", "STRING"),
        bigquery.SchemaField("transcript_uri", "STRING"),
        bigquery.SchemaField("customer_name", "STRING"),
        bigquery.SchemaField("phone_number", "STRING"),
        bigquery.SchemaField("email", "STRING"),
        bigquery.SchemaField("transcript_raw", "STRING"),
        bigquery.SchemaField("language_code", "STRING"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ]
    analytics_schema = [
        bigquery.SchemaField("call_id", "STRING"),
        bigquery.SchemaField("audio_uri", "STRING"),
        bigquery.SchemaField("transcript_uri", "STRING"),
        bigquery.SchemaField("transcript_masked", "STRING"),
        bigquery.SchemaField("language_code", "STRING"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ]

    client.create_table(
        bigquery.Table(f"{PROJECT_ID}.{BQ_DATASET}.{AGENT_TABLE}", schema=agent_schema),
        exists_ok=True,
    )
    client.create_table(
        bigquery.Table(f"{PROJECT_ID}.{BQ_DATASET}.{ANALYTICS_TABLE}", schema=analytics_schema),
        exists_ok=True,
    )


def insert_rows(agent_row: dict, analytics_row: dict) -> None:
    client = bigquery.Client(project=PROJECT_ID)
    agent_ref = f"{PROJECT_ID}.{BQ_DATASET}.{AGENT_TABLE}"
    analytics_ref = f"{PROJECT_ID}.{BQ_DATASET}.{ANALYTICS_TABLE}"

    errors1 = client.insert_rows_json(agent_ref, [agent_row])
    errors2 = client.insert_rows_json(analytics_ref, [analytics_row])

    if errors1:
        raise RuntimeError(f"BigQuery insert failed for agent table: {errors1}")
    if errors2:
        raise RuntimeError(f"BigQuery insert failed for analytics table: {errors2}")
