"""
CDS FastAPI endpoint — POST /assess

Thin wrapper around phase5/rag.py. No auth, no persistence.
Returns the RAG pipeline's validated JSON output directly.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))

from phase5 import rag

app = FastAPI(title="CDS — Clinical Decision Support", version="0.1.0")


class AssessRequest(BaseModel):
    presentation: str
    patient_location: Optional[str] = None
    patient_exposures: Optional[list[str]] = None
    encounter_date: Optional[datetime] = None
    onset_date: Optional[datetime] = None
    patient_latitude: Optional[float] = None
    patient_longitude: Optional[float] = None


@app.post("/assess")
def assess(req: AssessRequest) -> dict:
    try:
        result = rag.run(
            presentation=req.presentation,
            patient_location=req.patient_location,
            patient_exposures=req.patient_exposures,
            encounter_date=req.encounter_date,
            onset_date=req.onset_date,
            patient_latitude=req.patient_latitude,
            patient_longitude=req.patient_longitude,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
