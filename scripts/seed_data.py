"""Idempotently ingest the committed sanitized derivative into Neo4j."""

from app.config import Settings
from app.database import Database, load_payload

if __name__ == "__main__":
    settings = Settings()
    db = Database(settings)
    try:
        db.seed(load_payload(settings.data_path))
        print("DataCo derivative and explicit scenario lanes imported.")
    finally:
        db.close()
