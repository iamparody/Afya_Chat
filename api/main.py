"""
CDS FastAPI endpoint — POST /assess

Thin wrapper around phase5/rag.py. No auth, no persistence.
Returns the RAG pipeline's validated JSON output directly, plus two additive
keys for the HMIS integration:

  extraction — structured vitals / complaints / duration read from the text
               (api/intake_extractor.py; deterministic, span-cited)
  hmis       — the same, shaped for HMIS POST /vitals, with a reviewable note

POST /extract returns only those two keys, without the LLM — fast enough to
prefill a form while /assess is still reasoning, and still available when the
LLM or Neo4j is down.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))

from api.intake_extractor import (
    enriched_presentation,
    extract_intake,
    hmis_block,
    onset_from_duration,
    reconcile_red_flags,
)
from phase5 import rag

app = FastAPI(title="CDS — Clinical Decision Support", version="0.2.0")


class AssessRequest(BaseModel):
    presentation: str
    patient_location: Optional[str] = None
    patient_exposures: Optional[list[str]] = None
    encounter_date: Optional[datetime] = None
    onset_date: Optional[datetime] = None
    patient_latitude: Optional[float] = None
    patient_longitude: Optional[float] = None
    # Reason over the transcript plus its structured reading (normalised
    # numbers, a "Recorded vital signs" line) and derive onset_date from a
    # spoken duration when none is given. Off by default so existing callers
    # get exactly the pipeline they had.
    enrich_presentation: bool = False


class ExtractRequest(BaseModel):
    presentation: str = Field(min_length=1)


@app.post("/assess")
def assess(req: AssessRequest) -> dict:
    extraction = extract_intake(req.presentation)
    presentation, onset_date = req.presentation, req.onset_date
    if req.enrich_presentation:
        presentation = enriched_presentation(extraction)
        onset_date = onset_date or onset_from_duration(extraction, req.encounter_date)
    try:
        result = rag.run(
            presentation=presentation,
            patient_location=req.patient_location,
            patient_exposures=req.patient_exposures,
            encounter_date=req.encounter_date,
            onset_date=onset_date,
            patient_latitude=req.patient_latitude,
            patient_longitude=req.patient_longitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    corrected = 0
    if req.enrich_presentation:
        # HMIS writes documented red flags into the patient record, so a
        # "Documented" claim the transcript does not support is downgraded.
        result["red_flags"], corrected = reconcile_red_flags(
            result.get("red_flags", []), extraction["normalized_transcript"])
    result["extraction"] = extraction
    result["hmis"] = {
        **hmis_block(extraction, result),
        "presentation_sent": presentation,
        "red_flags_downgraded": corrected,
    }
    return result


@app.post("/extract")
def extract(req: ExtractRequest) -> dict:
    extraction = extract_intake(req.presentation)
    return {"extraction": extraction, "hmis": hmis_block(extraction, None)}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
