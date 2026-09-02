"""
CDS Streamlit MVP — Phase 6.
Run from cds/ root: streamlit run phase6/app.py
"""

import sys
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))

import streamlit as st

st.set_page_config(
    page_title="CDS — Clinical Decision Support",
    layout="wide",
    page_icon="🩺",
)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from cds_theme import apply_theme, section_header, page_header, COLORS
import rag
import db

apply_theme()
db.init_db()


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_CONFIDENCE = {"high", "moderate", "low"}

_ICD = {
    "type 2 diabetes mellitus":           ("5A11", "E11"),
    "essential hypertension":             ("BA00", "I10"),
    "obesity":                            ("5B81", "E66"),
    "malaria (unspecified)":              ("1F40", "B54"),
    "pulmonary tuberculosis":             ("1B10", "A15"),
    "community-acquired pneumonia":       ("CA40", "J18"),
    "urinary tract infection":            ("GC08", "N39.0"),
    "iron deficiency anaemia":            ("3A00", "D50"),
    "peptic ulcer disease":               ("DA60", "K27"),
    "acute gastroenteritis (infectious)": ("1A09", "A09"),
}

CONF_COLOR = {
    "high":     COLORS["success"],
    "moderate": COLORS["warning"],
    "low":      COLORS["muted"],
}


# ── Session state ─────────────────────────────────────────────────────────────

def _init_session_state():
    defaults = {
        "session_id":       str(uuid.uuid4()),
        "result":           None,
        "analysed_at":      None,
        "presentation_text": "",
        "approval_state":   None,   # None | "approved"
        "approved_at":      None,
        "encounter_id":     None,
        "clinician_diag":   "",
        "history":          [],
        "input_key":        0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _clear_all():
    st.session_state.input_key        += 1
    st.session_state.result            = None
    st.session_state.analysed_at       = None
    st.session_state.presentation_text = ""
    st.session_state.approval_state    = None
    st.session_state.approved_at       = None
    st.session_state.encounter_id      = None
    st.session_state.clinician_diag    = ""


# ── Validation ────────────────────────────────────────────────────────────────

def _assert_confidence(result: dict):
    for c in result.get("candidates", []):
        conf = c.get("confidence_level", "")
        if conf not in VALID_CONFIDENCE:
            raise ValueError(
                f"Invalid confidence_level '{conf}' — must be one of {VALID_CONFIDENCE}"
            )


# ── ICD lookup ────────────────────────────────────────────────────────────────

def _get_icd(name: str) -> tuple:
    return _ICD.get(name.lower().strip(), (None, None))


# ── Rendering helpers ─────────────────────────────────────────────────────────

def _list_html(items, color="#003467"):
    if not items:
        return (
            '<span style="font-size:12px;color:#9BAEC8;font-style:italic">'
            "None documented</span>"
        )
    rows = "".join(
        f'<li style="margin-bottom:5px;color:{color};font-size:12px;line-height:1.5">'
        f"{item}</li>"
        for item in items
    )
    return f'<ul style="margin:0;padding-left:16px">{rows}</ul>'


def _render_red_flags(red_flags):
    if not red_flags:
        return
    section_header("Red Flags")
    for flag in red_flags:
        documented = flag.lower().startswith("documented")
        border = COLORS["danger"] if documented else COLORS["warning"]
        bg     = "#FFF1F3"      if documented else "#FFFBEB"
        st.markdown(
            f'<div style="background:{bg};border-left:4px solid {border};border-radius:4px;'
            f'padding:10px 14px;margin-bottom:8px;font-size:13px;color:#003467;line-height:1.5">'
            f"{flag}</div>",
            unsafe_allow_html=True,
        )
    st.markdown('<div style="margin-bottom:4px"></div>', unsafe_allow_html=True)


def _candidate_html(candidate, is_leading=False, icd11=None, icd10=None):
    diagnosis  = candidate["diagnosis"]
    confidence = candidate["confidence_level"]
    why        = candidate["why_considered"]
    supporting = candidate["supporting_features"]
    arguing    = candidate["arguing_against"]
    missing    = candidate["missing_information"]

    conf_color   = CONF_COLOR.get(confidence, COLORS["muted"])
    border_color = COLORS["dark"] if is_leading else COLORS["primary"]
    bg           = "#F8FBFE"     if is_leading else "#FAFCFE"

    leading_label = (
        '<div style="font-size:9px;font-weight:700;color:#8BAAC5;text-transform:uppercase;'
        'letter-spacing:2px;margin-bottom:12px">Leading candidate</div>'
    ) if is_leading else ""

    arg_hdr_color = COLORS["danger"] if arguing else "#9BAEC8"

    icd_html = ""
    if is_leading and (icd11 or icd10):
        parts = []
        if icd11:
            parts.append(f'<b style="color:#003467">ICD-11</b> {icd11}')
        if icd10:
            parts.append(f'<b style="color:#003467">ICD-10</b> {icd10}')
        icd_html = (
            '<div style="border-top:1px solid #EBF3FB;margin-top:16px;padding-top:12px;'
            'font-size:11px;color:#6B8CAE;display:flex;gap:24px">'
            + " &nbsp;·&nbsp; ".join(parts)
            + "</div>"
        )

    conf_bg     = conf_color + "18"
    conf_border = conf_color + "40"

    return (
        f'<div style="background:{bg};border:1px solid #D6E4F0;border-left:4px solid {border_color};'
        f'border-radius:8px;padding:24px;margin-bottom:16px">'
        f'{leading_label}'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">'
        f'<div style="font-size:18px;font-weight:800;color:#003467">{diagnosis}</div>'
        f'<span style="background:{conf_bg};color:{conf_color};border:1px solid {conf_border};'
        f'font-size:10px;font-weight:700;letter-spacing:1px;padding:2px 8px;border-radius:4px;'
        f'text-transform:uppercase">{confidence}</span>'
        f'</div>'
        f'<div style="display:flex;gap:24px;margin-bottom:16px">'
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:10px;font-weight:700;color:{COLORS["primary"]};'
        f'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px">Supporting evidence</div>'
        f'{_list_html(supporting)}'
        f'</div>'
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:10px;font-weight:700;color:{arg_hdr_color};'
        f'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px">Arguing against</div>'
        f'{_list_html(arguing, color=COLORS["danger"] if arguing else "#9BAEC8")}'
        f'</div>'
        f'</div>'
        f'<div style="border-top:1px solid #EBF3FB;margin:0 0 16px"></div>'
        f'<div style="display:flex;gap:24px">'
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:10px;font-weight:700;color:#6B8CAE;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:6px">Why considered</div>'
        f'<div style="font-size:12px;color:#6B8CAE;line-height:1.6">{why}</div>'
        f'</div>'
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:10px;font-weight:700;color:#6B8CAE;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:6px">Missing information</div>'
        f'{_list_html(missing, color="#6B8CAE")}'
        f'</div>'
        f'</div>'
        f'{icd_html}'
        f'</div>'
    )


def _render_result(result):
    leading_name  = result.get("leading_candidate", "")
    candidates    = result.get("candidates", [])
    red_flags     = result.get("red_flags", [])
    comorbidities = result.get("relevant_comorbidities_or_context", [])

    leading      = next((c for c in candidates if c["diagnosis"] == leading_name), None)
    alternatives = [c for c in candidates if c["diagnosis"] != leading_name]

    _render_red_flags(red_flags)

    section_header("Assessment")
    if leading:
        icd11, icd10 = _get_icd(leading_name)
        st.markdown(
            _candidate_html(leading, is_leading=True, icd11=icd11, icd10=icd10),
            unsafe_allow_html=True,
        )

    if alternatives:
        section_header("Differential", margin_top=16)
        for alt in alternatives:
            with st.expander(f"{alt['diagnosis']}  ·  {alt['confidence_level']}"):
                st.markdown(_candidate_html(alt), unsafe_allow_html=True)

    if comorbidities:
        section_header("Relevant Context", margin_top=16)
        for item in comorbidities:
            st.markdown(
                f'<div style="font-size:12px;color:#003467;padding:8px 0;'
                f'border-bottom:1px solid #EBF3FB;line-height:1.5">{item}</div>',
                unsafe_allow_html=True,
            )


# ── Approval ──────────────────────────────────────────────────────────────────

def _do_approval(result: dict, clinician_diag: str, clinician_icd10: str | None):
    system_diag       = result.get("leading_candidate", "")
    system_icd11, system_icd10 = _get_icd(system_diag)

    clinician_icd11, _ = _get_icd(clinician_diag)

    try:
        encounter_id, approved_at = db.write_encounter(
            session_id          = st.session_state.session_id,
            analysed_at         = st.session_state.analysed_at,
            presentation        = st.session_state.presentation_text,
            system_output       = result,
            system_icd11        = system_icd11,
            system_icd10        = system_icd10,
            clinician_diagnosis = clinician_diag,
            clinician_icd10     = clinician_icd10,
            clinician_icd11     = clinician_icd11,
        )
    except Exception as e:
        logging.error("Approval write failed: %s", e)
        st.error("Could not save the approval record — please try again.")
        return

    st.session_state.approval_state = "approved"
    st.session_state.approved_at    = approved_at
    st.session_state.encounter_id   = encounter_id
    st.session_state.clinician_diag = clinician_diag

    st.session_state.history.append({
        "snippet":             st.session_state.presentation_text[:60]
                               + ("…" if len(st.session_state.presentation_text) > 60 else ""),
        "system_diagnosis":    system_diag,
        "clinician_diagnosis": clinician_diag,
        "approved_at":         approved_at,
    })

    st.rerun()


def _render_approval(result: dict):
    st.markdown(
        '<div style="border-top:1px solid #EBF3FB;margin:32px 0 24px"></div>',
        unsafe_allow_html=True,
    )

    if st.session_state.approval_state == "approved":
        _render_approval_confirmed()
        return

    section_header("Approval")

    # System assessment — read-only
    system_diag = result.get("leading_candidate", "")
    system_conf = next(
        (c["confidence_level"] for c in result.get("candidates", [])
         if c["diagnosis"] == system_diag),
        "",
    )
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:20px">'
        f'<div style="font-size:10px;font-weight:700;color:#9BAEC8;text-transform:uppercase;'
        f'letter-spacing:1.5px;width:140px;flex-shrink:0">System assessment</div>'
        f'<div style="font-size:13px;color:#6B8CAE">{system_diag}'
        f'<span style="font-size:11px;margin-left:8px">· {system_conf}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Editable diagnosis
    st.markdown(
        '<div style="font-size:10px;font-weight:700;color:#003467;text-transform:uppercase;'
        'letter-spacing:1.5px;margin-bottom:6px">Approved diagnosis</div>',
        unsafe_allow_html=True,
    )
    clinician_input = st.text_input(
        "Approved diagnosis",
        value=st.session_state.clinician_diag,
        label_visibility="collapsed",
    )

    # ICD-10 preview — resolves live from input
    _, icd10_preview = _get_icd(clinician_input)
    if icd10_preview:
        st.markdown(
            f'<div style="font-size:11px;color:#9BAEC8;margin-top:4px;margin-bottom:20px">'
            f'ICD-10 &nbsp; {icd10_preview}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div style="margin-bottom:20px"></div>', unsafe_allow_html=True)

    col_approve, _ = st.columns([2, 4])
    with col_approve:
        if st.button("Approve assessment", use_container_width=True, type="primary"):
            if not clinician_input.strip():
                st.warning("Enter a diagnosis before approving.")
            else:
                _, icd10_final = _get_icd(clinician_input)
                _do_approval(result, clinician_input.strip(), icd10_final)


def _render_approval_confirmed():
    try:
        dt       = datetime.fromisoformat(st.session_state.approved_at)
        time_str = dt.strftime("%H:%M")
    except Exception:
        time_str = ""

    clinician_diag = st.session_state.clinician_diag

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:14px;padding:20px 0">'
        f'<span style="color:{COLORS["success"]};font-size:18px;font-weight:700">✓</span>'
        f'<div>'
        f'<div style="font-size:14px;font-weight:700;color:#003467">{clinician_diag}</div>'
        f'<div style="font-size:11px;color:#9BAEC8;margin-top:2px">'
        f'Clinician approved · {time_str}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("New assessment →"):
        _clear_all()
        st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────

_init_session_state()

with st.sidebar:
    st.markdown(
        '<div style="font-size:20px;font-weight:800;color:#003467;margin-bottom:2px">CDS</div>'
        '<div style="font-size:11px;color:#6B8CAE;margin-bottom:20px">'
        "Clinical Decision Support</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sb-label" style="margin-bottom:8px">About</div>'
        '<div style="font-size:12px;color:#003467;line-height:1.75">'
        "Enter a free-text patient presentation. The system retrieves candidate diagnoses "
        "from the clinical knowledge base and returns a ranked differential with supporting "
        "evidence, arguing-against features, and red flags."
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        '<div class="sb-label" style="margin-bottom:8px">Corpus</div>'
        '<div style="font-size:12px;color:#003467;line-height:1.75">'
        "10 conditions · East Africa / Kenya primary care<br>"
        f'<span style="color:{COLORS["warning"]};font-weight:600">'
        "All cards: draft — not clinician-verified</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    # Session history rendered here in step 5


# ── GOVERNANCE BANNER ─────────────────────────────────────────────────────────
# Uncomment when tool goes to clinical review or testing.
# st.warning(
#     "All condition cards are draft and have not been clinician-verified. "
#     "This tool is a clinical reasoning aid, not a substitute for clinical judgment."
# )


# ── Main ──────────────────────────────────────────────────────────────────────

page_header(
    "Clinical Decision Support",
    subtitle="Symptom-driven differential assessment · East Africa / Kenya primary care",
)

presentation = st.text_area(
    "Patient presentation",
    placeholder=(
        "e.g. 29M, 4 days fever, chills, headache. Productive cough started yesterday. "
        "Weakness, not eating well. No known illness. Came from Kisumu 10 days ago."
    ),
    height=100,
    label_visibility="collapsed",
    key=f"presentation_{st.session_state.input_key}",
)

col_btn, col_clear, _ = st.columns([1, 1, 4])
with col_btn:
    analyse = st.button("Analyse", use_container_width=True)
with col_clear:
    if st.session_state.result is not None:
        if st.button("Clear", use_container_width=True):
            _clear_all()
            st.rerun()

st.markdown('<div style="margin-bottom:8px"></div>', unsafe_allow_html=True)

if analyse:
    if not presentation.strip():
        st.warning("Enter a patient presentation before analysing.")
        st.stop()

    with st.spinner("Analysing presentation..."):
        try:
            result = rag.run(presentation.strip())
            _assert_confidence(result)
        except ValueError as e:
            logging.error("CDS validation error: %s", e)
            st.error(
                "The analysis could not be completed — the model returned an unexpected response. "
                "Please try again."
            )
            st.stop()
        except Exception as e:
            logging.error("CDS pipeline error: %s", e)
            st.error("Service temporarily unavailable. Please try again in a moment.")
            st.stop()

    st.session_state.result           = result
    st.session_state.analysed_at      = datetime.now(timezone.utc).isoformat()
    st.session_state.presentation_text = presentation.strip()
    st.session_state.approval_state   = None
    st.session_state.approved_at      = None
    st.session_state.encounter_id     = None
    st.session_state.clinician_diag   = result.get("leading_candidate", "")
    st.rerun()

if st.session_state.result is not None:
    _render_result(st.session_state.result)
    _render_approval(st.session_state.result)
