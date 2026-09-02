"""
CDS approval database — SQLite persistence layer.

Single responsibility: write approved encounter records.
Schema decisions locked in STATUS.md.

Structured fields extracted from system_output at write time:
  supporting_symptoms  — corpus-controlled terms, leading candidate supporting_features
  arguing_against      — corpus-controlled terms, leading candidate arguing_against
  red_flags            — top-level red_flags list
  comorbidities        — relevant_comorbidities_or_context list

system_output (full JSON blob) is retained alongside for complete record preservation.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "cds.db"

VALID_CONFIDENCE = {"high", "moderate", "low"}

# Corpus-controlled category lookup — keyed by lowercase condition name.
_CATEGORY: dict[str, str] = {
    "type 2 diabetes mellitus":           "endocrine / metabolic",
    "essential hypertension":             "cardiovascular",
    "obesity":                            "metabolic",
    "malaria (unspecified)":              "infectious",
    "pulmonary tuberculosis":             "infectious / respiratory",
    "community-acquired pneumonia":       "respiratory / infectious",
    "urinary tract infection":            "urogenital / infectious",
    "iron deficiency anaemia":            "haematological",
    "peptic ulcer disease":               "gastroenterological",
    "acute gastroenteritis (infectious)": "gastroenterological / infectious",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # column already exists


def init_db() -> None:
    """
    Create the encounters table and apply any pending column migrations.
    Safe to call on every startup.
    """
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS encounters (
                encounter_id                 TEXT PRIMARY KEY,
                session_id                   TEXT NOT NULL,
                analysed_at                  TEXT NOT NULL,
                presentation                 TEXT NOT NULL,

                system_diagnosis             TEXT NOT NULL,
                system_confidence            TEXT NOT NULL
                                             CHECK(system_confidence IN ('high', 'moderate', 'low')),
                system_icd10                 TEXT,
                system_icd11                 TEXT,
                system_category              TEXT,

                supporting_symptoms          TEXT,
                arguing_against              TEXT,
                red_flags                    TEXT,
                comorbidities                TEXT,

                system_output                TEXT NOT NULL,

                clinician_diagnosis          TEXT NOT NULL,
                clinician_icd10              TEXT,
                clinician_icd11              TEXT,

                system_clinician_agreement   INTEGER NOT NULL DEFAULT 0
                                             CHECK(system_clinician_agreement IN (0, 1)),

                approved_at                  TEXT NOT NULL,
                approved_by                  TEXT
            )
        """)

        # Migration: add columns for installs from prior schema versions
        _add_column_if_missing(conn, "encounters", "supporting_symptoms",        "TEXT")
        _add_column_if_missing(conn, "encounters", "arguing_against",            "TEXT")
        _add_column_if_missing(conn, "encounters", "red_flags",                  "TEXT")
        _add_column_if_missing(conn, "encounters", "comorbidities",              "TEXT")
        _add_column_if_missing(conn, "encounters", "system_category",            "TEXT")
        _add_column_if_missing(conn, "encounters", "clinician_icd11",            "TEXT")
        _add_column_if_missing(conn, "encounters", "system_clinician_agreement", "INTEGER NOT NULL DEFAULT 0")


def _extract_structured(system_output: dict) -> dict:
    """
    Extract corpus-controlled structured fields from the RAG output.
    All values are lists of clean strings sourced from the knowledge base,
    not from free-text parsing.
    """
    leading_name = system_output.get("leading_candidate", "")
    leading = next(
        (c for c in system_output.get("candidates", []) if c["diagnosis"] == leading_name),
        {},
    )
    return {
        "supporting_symptoms": leading.get("supporting_features", []),
        "arguing_against":     leading.get("arguing_against", []),
        "red_flags":           system_output.get("red_flags", []),
        "comorbidities":       system_output.get("relevant_comorbidities_or_context", []),
    }


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
    clinician_icd11: str | None = None,
    approved_by: str | None = None,
) -> tuple[str, str]:
    """
    Write one approved encounter record.
    Returns (encounter_id, approved_at).
    Raises ValueError if system_confidence is not valid.
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

    system_category = _CATEGORY.get(system_diag.lower().strip())
    agreement       = 1 if system_diag.lower().strip() == clinician_diagnosis.lower().strip() else 0
    structured      = _extract_structured(system_output)
    encounter_id    = str(uuid.uuid4())
    approved_at     = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO encounters (
                encounter_id, session_id, analysed_at, presentation,
                system_diagnosis, system_confidence, system_icd10, system_icd11, system_category,
                supporting_symptoms, arguing_against, red_flags, comorbidities,
                system_output,
                clinician_diagnosis, clinician_icd10, clinician_icd11,
                system_clinician_agreement,
                approved_at, approved_by
            ) VALUES (
                :encounter_id, :session_id, :analysed_at, :presentation,
                :system_diagnosis, :system_confidence, :system_icd10, :system_icd11, :system_category,
                :supporting_symptoms, :arguing_against, :red_flags, :comorbidities,
                :system_output,
                :clinician_diagnosis, :clinician_icd10, :clinician_icd11,
                :system_clinician_agreement,
                :approved_at, :approved_by
            )
            """,
            {
                "encounter_id":               encounter_id,
                "session_id":                 session_id,
                "analysed_at":                analysed_at,
                "presentation":               presentation,
                "system_diagnosis":           system_diag,
                "system_confidence":          system_conf,
                "system_icd10":               system_icd10,
                "system_icd11":               system_icd11,
                "system_category":            system_category,
                "supporting_symptoms":        json.dumps(structured["supporting_symptoms"], ensure_ascii=False),
                "arguing_against":            json.dumps(structured["arguing_against"],     ensure_ascii=False),
                "red_flags":                  json.dumps(structured["red_flags"],           ensure_ascii=False),
                "comorbidities":              json.dumps(structured["comorbidities"],       ensure_ascii=False),
                "system_output":              json.dumps(system_output,                     ensure_ascii=False),
                "clinician_diagnosis":        clinician_diagnosis,
                "clinician_icd10":            clinician_icd10,
                "clinician_icd11":            clinician_icd11,
                "system_clinician_agreement": agreement,
                "approved_at":                approved_at,
                "approved_by":                approved_by,
            },
        )

    return encounter_id, approved_at
