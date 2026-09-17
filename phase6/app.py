"""
CDS Streamlit MVP — Phase 6.
Run from cds/ root: streamlit run phase6/app.py
"""

import re
import sys
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))
sys.path.insert(0, str(ROOT / "phase8"))

import streamlit as st

st.set_page_config(
    page_title="CDS — Clinical Decision Support",
    layout="wide",
    page_icon="🩺",
)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from cds_theme import apply_theme, page_header, COLORS, ph
import rag
import db
from disambiguate import MAX_ROUNDS, is_ambiguous, get_discriminating_questions, enrich_presentation
from phase7.kenya_locations import normalize_county, DISPLAY_LOCATIONS

apply_theme()
db.init_db()


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_CONFIDENCE = {"high", "moderate", "low"}

_EXPOSURE_LABELS: dict[str, str] = {
    "Floodwater contact":             "floodwater_contact",
    "Livestock contact":              "livestock_contact",
    "Occupational dust exposure":     "occupational_dust",
    "Unsafe water source":            "unsafe_water",
    "High mosquito exposure":         "mosquito_exposure_high",
    "Pastoralist / mobile community": "pastoralist_mobility",
    "Fishing / lakeshore activity":   "fishing_lakeshore",
}
_EXPOSURE_OPTIONS = list(_EXPOSURE_LABELS.keys())

_ICD = {
    "type 2 diabetes mellitus":           ("5A11",  "E11"),
    "essential hypertension":             ("BA00",  "I10"),
    "obesity":                            ("5B81",  "E66"),
    "malaria (unspecified)":              ("1F40",  "B54"),
    "pulmonary tuberculosis":             ("1B10",  "A15"),
    "community-acquired pneumonia":       ("CA40",  "J18"),
    "urinary tract infection":            ("GC08",  "N39.0"),
    "iron deficiency anaemia":            ("3A00",  "D50"),
    "peptic ulcer disease":               ("DA62",  "K27"),
    "acute gastroenteritis (infectious)": ("1A09",  "A09"),
    "typhoid fever":                      ("1A07",  "A01.0"),
    "functional dyspepsia":               ("DA94",  "K30"),
    "gastro-oesophageal reflux disease":  ("DA22",  "K21"),
    "asthma":                             ("CA23",  "J45"),
    "dengue fever":                       ("1D2Z",  "A90"),
}


# ── Session state ─────────────────────────────────────────────────────────────

def _init_session_state():
    defaults = {
        "session_id":           str(uuid.uuid4()),
        "result":               None,
        "analysed_at":          None,
        "presentation_text":    "",
        "approval_state":       None,
        "approved_at":          None,
        "encounter_id":         None,
        "clinician_diag":       "",
        "history":              [],
        "input_key":            0,
        "disam_round":          0,
        "disam_questions":      [],
        "disam_skip_to_result": False,
        "base_presentation":    "",
        "location_norm":        None,
        "patient_exposures":    [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _clear_all():
    st.session_state.input_key          += 1
    st.session_state.result              = None
    st.session_state.analysed_at         = None
    st.session_state.presentation_text   = ""
    st.session_state.approval_state      = None
    st.session_state.approved_at         = None
    st.session_state.encounter_id        = None
    st.session_state.clinician_diag      = ""
    st.session_state.disam_round          = 0
    st.session_state.disam_questions      = []
    st.session_state.disam_skip_to_result = False
    st.session_state.base_presentation    = ""
    st.session_state.location_norm        = None
    st.session_state.patient_exposures    = []


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


# ── HTML primitives ───────────────────────────────────────────────────────────

def _badge(confidence: str, small: bool = False) -> str:
    cls  = {"high": "high", "moderate": "moderate", "low": "low"}.get(confidence, "low")
    text = {"high": "High confidence", "moderate": "Moderate confidence", "low": "Low confidence"}.get(confidence, confidence.capitalize())
    sm   = " sm" if small else ""
    return f'<span class="cds-badge {cls}{sm}">{text if not small else cls.capitalize()}</span>'


def _feature_list(items: list, kind: str) -> str:
    if not items:
        return '<span class="cds-feat-none">None documented</span>'
    rows = ""
    for item in items:
        rows += (
            f'<div class="cds-feat">'
            f'<span class="cds-dot {kind}"></span>'
            f'<span>{item}</span>'
            f'</div>'
        )
    return rows


def _missing_chips(items: list) -> str:
    if not items:
        return ""
    chips = "".join(f'<span class="cds-chip">{m}</span>' for m in items)
    return (
        f'<div class="cds-missing-label">Missing information</div>'
        f'<div class="cds-chips">{chips}</div>'
    )


# ── Display renderers ─────────────────────────────────────────────────────────

def _render_draft_banner():
    st.markdown(
        f'<div class="cds-draft-banner">'
        f'{ph("warning", 13, "#B45309")}'
        f'Development / Clinical Review &nbsp;·&nbsp; '
        f'Corpus not clinician-verified &nbsp;·&nbsp; Not for clinical use'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_presentation_collapsed(text: str):
    short = text[:140] + ("…" if len(text) > 140 else "")
    st.markdown(
        f'<div class="cds-pres">'
        f'<span class="cds-pres-label">Presentation</span>'
        f'<span class="cds-pres-text">{short}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


_MALFORMED_FLAG_RE = re.compile(
    r"^(documented|check\s+for)\s*[—\-]+\s*(none|n/a|not\s+applicable|unknown)[\s.]*$",
    re.IGNORECASE,
)


def _render_red_flags(result: dict):
    flags = result.get("red_flags", [])
    flags = [f for f in flags if f and not _MALFORMED_FLAG_RE.match(f.strip())]
    if not flags:
        return
    items_html = ""
    for flag in flags:
        documented = flag.lower().startswith("documented")
        cls        = "cds-rf-item doc" if documented else "cds-rf-item"
        icon_color = COLORS["urgent"] if documented else "#F87171"
        items_html += (
            f'<div class="{cls}">'
            f'{ph("warning", 14, icon_color)}'
            f'<span>{flag}</span>'
            f'</div>'
        )
    st.markdown(
        f'<div class="cds-rf">'
        f'<div class="cds-sec urgent">'
        f'{ph("warning", 10, COLORS["urgent"])} &nbsp;Red Flags'
        f'</div>'
        f'{items_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_leading_candidate(result: dict):
    leading_name = result.get("leading_candidate", "")
    candidates   = result.get("candidates", [])
    leading      = next((c for c in candidates if c["diagnosis"] == leading_name), None)
    if not leading:
        return

    confidence = leading.get("confidence_level", "")
    supporting = leading.get("supporting_features", [])
    arguing    = leading.get("arguing_against", [])
    missing    = leading.get("missing_information", [])
    why        = leading.get("why_considered", "")
    icd11, icd10 = _get_icd(leading_name)

    icd_html = ""
    if icd11 or icd10:
        parts = []
        if icd11: parts.append(f'<b>ICD-11</b> {icd11}')
        if icd10: parts.append(f'<b>ICD-10</b> {icd10}')
        icd_html = f'<div class="cds-lc-icd">{" &nbsp;·&nbsp; ".join(parts)}</div>'

    why_html     = f'<div class="cds-why">{why}</div>' if why else ""
    missing_html = _missing_chips(missing)

    st.markdown(
        f'<div class="cds-sec" style="margin-bottom:10px">Assessment</div>'
        f'<div class="cds-lc">'
        f'  <div class="cds-lc-header">'
        f'    <div class="cds-lc-name">{leading_name}</div>'
        f'    {_badge(confidence)}'
        f'  </div>'
        f'  {icd_html}'
        f'  <div class="cds-ev">'
        f'    <div>'
        f'      <div class="cds-col-label">Supporting evidence</div>'
        f'      {_feature_list(supporting, "sp")}'
        f'    </div>'
        f'    <div>'
        f'      <div class="cds-col-label ag">Arguing against</div>'
        f'      {_feature_list(arguing, "ag")}'
        f'    </div>'
        f'  </div>'
        f'  {missing_html}'
        f'  {why_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _diff_detail(candidate: dict) -> str:
    supporting = candidate.get("supporting_features", [])
    arguing    = candidate.get("arguing_against", [])
    missing    = candidate.get("missing_information", [])
    why        = candidate.get("why_considered", "")

    missing_html = ""
    if missing:
        chips = "".join(f'<span class="cds-chip">{m}</span>' for m in missing)
        missing_html = (
            f'<div style="margin-top:14px">'
            f'<div class="cds-col-label" style="margin-bottom:8px">Missing information</div>'
            f'<div class="cds-chips">{chips}</div>'
            f'</div>'
        )
    why_html = f'<div class="cds-diff-why">{why}</div>' if why else ""

    return (
        f'<div class="cds-diff-grid">'
        f'  <div>'
        f'    <div class="cds-col-label">Supporting</div>'
        f'    {_feature_list(supporting, "sp")}'
        f'  </div>'
        f'  <div>'
        f'    <div class="cds-col-label ag">Arguing against</div>'
        f'    {_feature_list(arguing, "ag")}'
        f'  </div>'
        f'</div>'
        f'{missing_html}'
        f'{why_html}'
    )


def _render_differential(result: dict):
    leading_name = result.get("leading_candidate", "")
    alternatives = [
        c for c in result.get("candidates", [])
        if c["diagnosis"] != leading_name
        and c.get("supporting_features")
        and c.get("confidence_level") in ("high", "moderate")
    ]
    if not alternatives:
        return

    rows = ""
    for i, cand in enumerate(alternatives, 2):
        diag = cand["diagnosis"]
        conf = cand.get("confidence_level", "low")
        why  = cand.get("why_considered", "")
        hint = (why[:72] + "…") if len(why) > 72 else why
        rows += (
            f'<details class="cds-diff-item">'
            f'  <summary class="cds-diff-sum">'
            f'    <span class="cds-diff-rank">#{i}</span>'
            f'    <span class="cds-diff-name">{diag}</span>'
            f'    {_badge(conf, small=True)}'
            f'    <span class="cds-diff-hint">{hint}</span>'
            f'    <span class="cds-diff-chev">›</span>'
            f'  </summary>'
            f'  <div class="cds-diff-detail">{_diff_detail(cand)}</div>'
            f'</details>'
        )

    st.markdown(
        f'<div class="cds-sec" style="margin-top:8px;margin-bottom:10px">Differential</div>'
        f'<div class="cds-diff">{rows}</div>',
        unsafe_allow_html=True,
    )


def _render_relevant_context(result: dict):
    items = result.get("relevant_comorbidities_or_context", [])
    if not items:
        return
    rows = "".join(f'<div class="cds-ctx-item">{item}</div>' for item in items)
    st.markdown(
        f'<div class="cds-sec" style="margin-top:8px;margin-bottom:10px">Clinical Context</div>'
        f'{rows}'
        f'<div style="margin-bottom:16px"></div>',
        unsafe_allow_html=True,
    )


# ── Disambiguation ────────────────────────────────────────────────────────────

def _render_disambiguation():
    round_num = st.session_state.disam_round
    questions = st.session_state.disam_questions
    result    = st.session_state.result

    # Build uncertainty context card
    candidates   = result.get("candidates", []) if result else []
    leading_name = result.get("leading_candidate", "") if result else ""
    leading_conf = next(
        (c.get("confidence_level") for c in candidates if c["diagnosis"] == leading_name),
        ""
    )
    tied = [
        c["diagnosis"] for c in candidates
        if c.get("confidence_level") == leading_conf and c["diagnosis"] != leading_name
    ]
    tied_str  = " and ".join(tied[:2]) if tied else "other candidates"
    q_count   = len(questions)
    count_str = f"{q_count} question{'s' if q_count != 1 else ''}" if q_count else "clarifying questions"

    st.markdown(
        f'<div class="cds-unc">'
        f'  <div class="cds-unc-title">Assessment uncertain</div>'
        f'  <div class="cds-unc-body">'
        f'    <strong>{leading_name}</strong> and <strong>{tied_str}</strong> '
        f'    remain plausible at the same confidence tier. '
        f'    <span class="cds-unc-count">{count_str}</span> could help distinguish them.'
        f'  </div>'
        f'  <div class="cds-unc-round">Round {round_num} of {MAX_ROUNDS}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Questions
    answers = {}
    if questions:
        st.markdown(
            '<div class="cds-disam-intro">'
            'Tap one answer per question — leave unanswered to skip (not assessed).'
            '</div>',
            unsafe_allow_html=True,
        )
        for i, question in enumerate(questions):
            selection = st.radio(
                question,
                options=["Present", "Absent", "Unknown"],
                index=None,
                horizontal=True,
                key=f"disam_q_{round_num}_{i}",
            )
            if selection is not None:
                answers[question] = selection
            st.markdown('<div style="margin-bottom:4px"></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="cds-disam-empty">'
            'No discriminating questions could be generated — '
            'proceed with the current assessment.'
            '</div>',
            unsafe_allow_html=True,
        )

    col_refine, col_stop, _ = st.columns([2, 2, 4])
    with col_refine:
        refine_clicked = st.button(
            "Refine assessment",
            use_container_width=True,
            type="primary",
            disabled=not questions,
        )
    with col_stop:
        stop_clicked = st.button(
            "Stop — use current assessment",
            use_container_width=True,
        )

    return refine_clicked, stop_clicked, answers


# ── Approval ──────────────────────────────────────────────────────────────────

def _do_approval(result: dict, clinician_diag: str, clinician_icd10: str | None):
    system_diag            = result.get("leading_candidate", "")
    system_icd11, system_icd10 = _get_icd(system_diag)
    clinician_icd11, _     = _get_icd(clinician_diag)

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
    st.markdown('<div class="cds-approval">', unsafe_allow_html=True)

    if st.session_state.approval_state == "approved":
        _render_approval_confirmed()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    system_diag = result.get("leading_candidate", "")
    system_conf = next(
        (c["confidence_level"] for c in result.get("candidates", [])
         if c["diagnosis"] == system_diag),
        "",
    )

    st.markdown(
        f'<div class="cds-sec" style="margin-bottom:14px">Clinical Decision</div>'
        f'<div class="cds-approval-sys">'
        f'  <span class="cds-approval-sys-label">System assessment</span>'
        f'  <span class="cds-approval-sys-diag">{system_diag}</span>'
        f'  <span class="cds-approval-sys-conf">· {system_conf}</span>'
        f'</div>'
        f'<div class="cds-field-label">Approved diagnosis</div>',
        unsafe_allow_html=True,
    )

    clinician_input = st.text_input(
        "Approved diagnosis",
        value=st.session_state.clinician_diag,
        label_visibility="collapsed",
    )

    _, icd10_preview = _get_icd(clinician_input)
    if icd10_preview:
        st.markdown(
            f'<div class="cds-icd-hint">ICD-10 &nbsp; {icd10_preview}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div style="margin-bottom:16px"></div>', unsafe_allow_html=True)

    col_approve, _ = st.columns([2, 4])
    with col_approve:
        if st.button("Approve assessment", use_container_width=True, type="primary"):
            if not clinician_input.strip():
                st.warning("Enter a diagnosis before approving.")
            else:
                _, icd10_final = _get_icd(clinician_input)
                _do_approval(result, clinician_input.strip(), icd10_final)

    st.markdown('</div>', unsafe_allow_html=True)


def _render_approval_confirmed():
    try:
        dt       = datetime.fromisoformat(st.session_state.approved_at)
        time_str = dt.strftime("%H:%M")
    except Exception:
        time_str = ""

    clinician_diag = st.session_state.clinician_diag

    st.markdown(
        f'<div class="cds-confirmed">'
        f'{ph("check-circle", 22, COLORS["support"])}'
        f'  <div>'
        f'    <div class="cds-confirmed-name">{clinician_diag}</div>'
        f'    <div class="cds-confirmed-meta">'
        f'      {ph("clock", 12, COLORS["muted"])}'
        f'      Clinician approved &middot; {time_str}'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("New assessment →"):
        _clear_all()
        st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_history_sidebar():
    history = st.session_state.get("history", [])

    if not history:
        st.markdown(
            '<div class="cds-hist-section">'
            '<div class="sb-label" style="margin-bottom:10px">This session</div>'
            '<div style="font-size:11px;color:#9BAEC8;font-style:italic">'
            'No approved assessments this session.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    entries_html = ""
    for entry in history:
        try:
            dt = datetime.fromisoformat(entry["approved_at"])
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = ""

        agreed = (
            entry["system_diagnosis"].lower().strip()
            == entry["clinician_diagnosis"].lower().strip()
        )
        indicator = "✓" if agreed else "△"
        ind_color = COLORS["support"] if agreed else COLORS["moderate"]

        entries_html += (
            f'<div class="cds-hist-entry">'
            f'  <div class="cds-hist-meta">'
            f'    <span class="cds-hist-time">{time_str}</span>'
            f'    <span class="cds-hist-ind" style="color:{ind_color}">{indicator}</span>'
            f'  </div>'
            f'  <div class="cds-hist-diag">{entry["system_diagnosis"]}</div>'
            f'  <div class="cds-hist-snip">{entry["snippet"]}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="cds-hist-section">'
        f'<div class="sb-label" style="margin-bottom:12px">This session</div>'
        f'{entries_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


_init_session_state()

with st.sidebar:
    st.markdown(
        '<div style="font-size:16px;font-weight:800;color:#003467;letter-spacing:-0.3px">'
        'CDS</div>'
        '<div style="font-size:10px;color:#9BAEC8;margin-top:2px;margin-bottom:20px;'
        'text-transform:uppercase;letter-spacing:1.5px">Clinical Decision Support</div>'
        '<div style="border-top:1px solid #EBF3FB;margin-bottom:20px"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sb-label" style="margin-bottom:10px">Corpus</div>'
        '<div style="font-size:12px;color:#003467;line-height:1.8">'
        '15 conditions<br>'
        '<span style="color:#9BAEC8">East Africa / Kenya primary care</span>'
        '</div>'
        f'<div style="font-size:11px;color:{COLORS["moderate"]};font-weight:600;'
        f'margin-top:8px">'
        'Draft — not clinician-verified</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="border-top:1px solid #EBF3FB;margin:20px 0"></div>',
                unsafe_allow_html=True)

    _render_history_sidebar()


# ── Main ──────────────────────────────────────────────────────────────────────

_render_draft_banner()

page_header(
    "Clinical Decision Support",
    subtitle="Symptom-driven differential assessment · East Africa / Kenya primary care",
)

# Input — shows full textarea when empty, collapses to caption after analysis
if st.session_state.result is not None:
    _render_presentation_collapsed(st.session_state.presentation_text)
    presentation = ""
else:
    presentation = st.text_area(
        "Patient presentation",
        height=100,
        label_visibility="collapsed",
        placeholder="Enter patient presentation in clinical shorthand…",
        key=f"presentation_{st.session_state.input_key}",
    )

    with st.expander("Patient context (optional)"):
        st.markdown(
            '<div class="cds-field-label" style="margin-bottom:6px">Where</div>',
            unsafe_allow_html=True,
        )
        loc_choice = st.selectbox(
            "Patient location",
            options=["Not specified"] + DISPLAY_LOCATIONS + ["Other location…"],
            index=0,
            key=f"location_{st.session_state.input_key}",
            label_visibility="collapsed",
            help="Select a Kenyan county or town to activate seasonal environmental context.",
        )
        if loc_choice == "Not specified":
            st.session_state.location_norm = None
        elif loc_choice == "Other location…":
            other_text = st.text_input(
                "Specify location",
                placeholder="Town, facility, or area name…",
                key=f"other_location_{st.session_state.input_key}",
                label_visibility="collapsed",
            )
            # Explicitly set to None when field is blank — never inherits a prior selection
            st.session_state.location_norm = (
                normalize_county(other_text.strip()) if other_text.strip() else None
            )
        else:
            _norm = normalize_county(loc_choice)
            if _norm.resolution_status == "cross_county_ambiguous":
                chosen_county = st.selectbox(
                    f"{loc_choice} straddles a county boundary. Select county:",
                    options=list(_norm.candidate_counties),
                    key=f"county_disamb_{st.session_state.input_key}_{loc_choice}",
                )
                st.session_state.location_norm = normalize_county(chosen_county)
            else:
                st.session_state.location_norm = _norm

        st.markdown(
            '<div class="cds-field-label" style="margin-top:14px;margin-bottom:6px">Exposures</div>',
            unsafe_allow_html=True,
        )
        exp_labels = st.multiselect(
            "Documented exposures",
            options=_EXPOSURE_OPTIONS,
            default=[],
            key=f"exposures_{st.session_state.input_key}",
            label_visibility="collapsed",
            help="Select any exposures explicitly documented in the patient history.",
        )
        st.session_state.patient_exposures = [_EXPOSURE_LABELS[lbl] for lbl in exp_labels]

col_btn, col_clear, _ = st.columns([1, 1, 4])
with col_btn:
    analyse = st.button(
        "Analyse",
        use_container_width=True,
        disabled=(st.session_state.result is not None),
    )
with col_clear:
    if st.session_state.result is not None:
        if st.button("Clear", use_container_width=True):
            _clear_all()
            st.rerun()

st.markdown('<div style="margin-bottom:16px"></div>', unsafe_allow_html=True)

if analyse:
    if not presentation.strip():
        st.warning("Enter a patient presentation before analysing.")
        st.stop()

    with st.spinner("Analysing presentation…"):
        try:
            _loc = st.session_state.location_norm
            result = rag.run(
                presentation.strip(),
                patient_location=_loc.ecological_region if _loc else None,
                patient_exposures=st.session_state.patient_exposures,
                encounter_date=datetime.now(),
                patient_latitude=_loc.latitude if _loc else None,
                patient_longitude=_loc.longitude if _loc else None,
            )
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

    st.session_state.result              = result
    st.session_state.analysed_at         = datetime.now(timezone.utc).isoformat()
    st.session_state.presentation_text   = presentation.strip()
    st.session_state.approval_state      = None
    st.session_state.approved_at         = None
    st.session_state.encounter_id        = None
    st.session_state.clinician_diag      = result.get("leading_candidate", "")
    st.session_state.disam_skip_to_result = False

    if is_ambiguous(result):
        st.session_state.disam_round       = 1
        st.session_state.disam_questions   = get_discriminating_questions(result)
        st.session_state.base_presentation = presentation.strip()
    else:
        st.session_state.disam_round     = 0
        st.session_state.disam_questions = []

    st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────

_disam_active = (
    st.session_state.disam_round > 0
    and not st.session_state.disam_skip_to_result
    and st.session_state.result is not None
)

if _disam_active:
    result = st.session_state.result
    _render_red_flags(result)
    _render_leading_candidate(result)
    refine_clicked, stop_clicked, answers = _render_disambiguation()

    if stop_clicked:
        st.session_state.disam_round          = 0
        st.session_state.disam_skip_to_result = True
        st.rerun()

    if refine_clicked:
        enriched = enrich_presentation(st.session_state.base_presentation, answers)
        st.session_state.presentation_text = enriched

        with st.spinner("Refining assessment…"):
            try:
                _loc = st.session_state.location_norm
                result = rag.run(
                    enriched,
                    patient_location=_loc.ecological_region if _loc else None,
                    patient_exposures=st.session_state.patient_exposures,
                    encounter_date=datetime.now(),
                    patient_latitude=_loc.latitude if _loc else None,
                    patient_longitude=_loc.longitude if _loc else None,
                )
                _assert_confidence(result)
            except ValueError as e:
                logging.error("CDS disambiguation validation error: %s", e)
                st.error(
                    "Refinement could not be completed — unexpected model response. "
                    "Please try again."
                )
                st.stop()
            except Exception as e:
                logging.error("CDS disambiguation error: %s", e)
                st.error("Service temporarily unavailable. Please try again in a moment.")
                st.stop()

        st.session_state.result         = result
        st.session_state.analysed_at    = datetime.now(timezone.utc).isoformat()
        st.session_state.clinician_diag = result.get("leading_candidate", "")

        next_round    = st.session_state.disam_round + 1
        new_questions = get_discriminating_questions(result) if is_ambiguous(result) else []
        if new_questions and next_round <= MAX_ROUNDS:
            st.session_state.disam_round     = next_round
            st.session_state.disam_questions = new_questions
        else:
            st.session_state.disam_round = 0

        st.rerun()

elif st.session_state.result is not None:
    result = st.session_state.result
    _render_red_flags(result)
    _render_leading_candidate(result)
    _render_differential(result)
    _render_relevant_context(result)
    _render_approval(result)
