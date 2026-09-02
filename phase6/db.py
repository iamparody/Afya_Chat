"""
CDS approval database — SQLite persistence layer.

Single responsibility: write approved encounter records.
Schema is locked — see STATUS.md decisions log.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "cds.db"

VALID_CONFIDENCE = {"high", "moderate", "low"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the encounters table if it does not exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS encounters (
                encounter_id        TEXT PRIMARY KEY,
                session_id          TEXT NOT NULL,
                analysed_at         TEXT NOT NULL,
                presentation        TEXT NOT NULL,

                system_diagnosis    TEXT NOT NULL,
                system_confidence   TEXT NOT NULL
                                    CHECK(system_confidence IN ('high', 'moderate', 'low')),
                system_icd10        TEXT,
                system_icd11        TEXT,
                system_output       TEXT NOT NULL,

                clinician_diagnosis TEXT NOT NULL,
                clinician_icd10     TEXT,

                approved_at         TEXT NOT NULL,
                approved_by         TEXT
            )
        """)


def write_encounter(
    *,
    session_id: str,
    analysed_at: str,
    presentation: str,
    system_output: dict,
    system_icd11: str | None,
    system_icd10: str | None,
    clinician_diagnosis: str,
    clinician_icd10: str | None,
    approved_by: str | None = None,
) -> tuple[str, str]:
    """
    Write one approved encounter record.
    Returns (encounter_id, approved_at) on success.
    Raises ValueError if system_confidence is not a valid value.
    """
    system_diag = system_output["leading_candidate"]
    system_conf = next(
        (c["confidence_level"] for c in system_output.get("candidates", [])
         if c["diagnosis"] == system_diag),
        "",
    )

    if system_conf not in VALID_CONFIDENCE:
        raise ValueError(
            f"system_confidence '{system_conf}' is not valid — "
            f"must be one of {VALID_CONFIDENCE}"
        )

    encounter_id = str(uuid.uuid4())
    approved_at  = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO encounters (
                encounter_id, session_id, analysed_at, presentation,
                system_diagnosis, system_confidence, system_icd10, system_icd11,
                system_output,
                clinician_diagnosis, clinician_icd10,
                approved_at, approved_by
            ) VALUES (
                :encounter_id, :session_id, :analysed_at, :presentation,
                :system_diagnosis, :system_confidence, :system_icd10, :system_icd11,
                :system_output,
                :clinician_diagnosis, :clinician_icd10,
                :approved_at, :approved_by
            )
            """,
            {
                "encounter_id":        encounter_id,
                "session_id":          session_id,
                "analysed_at":         analysed_at,
                "presentation":        presentation,
                "system_diagnosis":    system_diag,
                "system_confidence":   system_conf,
                "system_icd10":        system_icd10,
                "system_icd11":        system_icd11,
                "system_output":       json.dumps(system_output, ensure_ascii=False),
                "clinician_diagnosis": clinician_diagnosis,
                "clinician_icd10":     clinician_icd10,
                "approved_at":         approved_at,
                "approved_by":         approved_by,
            },
        )

    return encounter_id, approved_at
