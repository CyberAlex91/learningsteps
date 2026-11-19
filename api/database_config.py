"""Read database configuration without exposing credential values in errors."""

import os
from pathlib import Path
from dotenv import load_dotenv


def get_database_url(environ=None):
    source = os.environ if environ is None else environ
    filename = source.get("DATABASE_URL_FILE")
    value = source.get("DATABASE_URL")
    if filename and value:
        raise ValueError("Set only one database configuration source")
    if filename:
        try:
            value = Path(filename).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            raise ValueError("Database credential file cannot be read") from None
    if not value or not value.strip():
        raise ValueError("Database configuration is missing or empty")
    return value.strip()


load_dotenv()
