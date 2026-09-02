"""
CDS Streamlit MVP — Phase 6.
Run from cds/ root: streamlit run phase6/app.py
"""

import sys
import logging
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

apply_theme()


# ── ICD lookup ────────────────────────────────────────────────────────────────

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


def _get_icd(name):
    return _ICD.get(name.lower(), (None, None))


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

    # 1 — Red flags (above candidate cards — safety first)
    _render_red_flags(red_flags)

    # 2 — Leading candidate
    section_header("Assessment")
    if leading:
        icd11, icd10 = _get_icd(leading_name)
        st.markdown(
            _candidate_html(leading, is_leading=True, icd11=icd11, icd10=icd10),
            unsafe_allow_html=True,
        )

    # 3 — Alternatives (collapsed)
    if alternatives:
        section_header("Differential", margin_top=16)
        for alt in alternatives:
            with st.expander(f"{alt['diagnosis']}  ·  {alt['confidence_level']}"):
                st.markdown(_candidate_html(alt), unsafe_allow_html=True)

    # 4 — Comorbidities / context
    if comorbidities:
        section_header("Relevant Context", margin_top=16)
        for item in comorbidities:
            st.markdown(
                f'<div style="font-size:12px;color:#003467;padding:8px 0;'
                f'border-bottom:1px solid #EBF3FB;line-height:1.5">{item}</div>',
                unsafe_allow_html=True,
            )


# ── Sidebar ───────────────────────────────────────────────────────────────────

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
    st.divider()
    st.markdown(
        '<div style="font-size:10px;color:#9BAEC8;line-height:1.75">'
        "Embedding · Cohere multilingual v3<br>"
        "Graph · Neo4j AuraDB<br>"
        "LLM · Gemini flash-lite"
        "</div>",
        unsafe_allow_html=True,
    )


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
)

col_btn, _ = st.columns([1, 5])
with col_btn:
    analyse = st.button("Analyse", use_container_width=True)

st.markdown('<div style="margin-bottom:8px"></div>', unsafe_allow_html=True)

if analyse:
    if not presentation.strip():
        st.warning("Enter a patient presentation before analysing.")
        st.stop()

    with st.spinner("Analysing presentation..."):
        try:
            result = rag.run(presentation.strip())
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

    _render_result(result)
