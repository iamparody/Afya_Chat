"""
CDS theme — design tokens, CSS, and icon helpers.
Phosphor icons embedded as inline SVG (zero external dependencies).
"""
import streamlit as st

COLORS = {
    "primary":  "#003467",
    "accent":   "#0072CE",
    "high":     "#1D6FA4",
    "moderate": "#B45309",
    "low":      "#6B7280",
    "support":  "#059669",
    "against":  "#DC2626",
    "urgent":   "#DC2626",
    "muted":    "#9BAEC8",
    "dark":     "#003467",
    # legacy aliases kept for any remaining callers
    "success":  "#059669",
    "warning":  "#B45309",
    "danger":   "#DC2626",
}

# Phosphor Icons — regular weight, 256×256 viewBox
_PH: dict[str, str] = {
    "warning": (
        "M236.8,188.09,149.35,36.22a24.76,24.76,0,0,0-42.7,0L19.2,188.09"
        "a23.51,23.51,0,0,0,0,23.72A24.35,24.35,0,0,0,40.55,224h174.9"
        "a24.35,24.35,0,0,0,21.33-12.19A23.51,23.51,0,0,0,236.8,188.09Z"
        "M222.93,203.8a8.5,8.5,0,0,1-7.48,4.2H40.55a8.5,8.5,0,0,1-7.48-4.2"
        ",7.59,7.59,0,0,1,0-7.72L120.52,44.21a8.75,8.75,0,0,1,15,0l87.45,151.87"
        "A7.59,7.59,0,0,1,222.93,203.8Z"
        "M120,144V104a8,8,0,0,1,16,0v40a8,8,0,0,1-16,0Z"
        "m20,36a12,12,0,1,1-12-12A12,12,0,0,1,140,180Z"
    ),
    "check-circle": (
        "M173.66,98.34a8,8,0,0,1,0,11.32l-56,56a8,8,0,0,1-11.32,0l-24-24"
        "a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35A8,8,0,0,1,173.66,98.34Z"
        "M232,128A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Z"
        "m-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"
    ),
    "check": (
        "M232.49,80.49l-128,128a12,12,0,0,1-17,0l-56-56a12,12,0,1,1,17-17"
        "L96,183,215.51,63.51a12,12,0,0,1,17,17Z"
    ),
    "clock": (
        "M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Z"
        "m0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Z"
        "m64-88a8,8,0,0,1-8,8H128a8,8,0,0,1-8-8V72a8,8,0,0,1,16,0v48h48"
        "A8,8,0,0,1,192,128Z"
    ),
    "arrow-right": (
        "M221.66,133.66l-72,72a8,8,0,0,1-11.32-11.32L196.69,136H40"
        "a8,8,0,0,1,0-16H196.69L138.34,61.66a8,8,0,0,1,11.32-11.32l72,72"
        "A8,8,0,0,1,221.66,133.66Z"
    ),
    "question": (
        "M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,"
        "88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm16-40a8,8,0,0,1-16,0v-8a8,8,"
        "0,0,1,16,0ZM112,96a16,16,0,1,1,32,0c0,9.1-7.06,14.58-13,19.42C125.7,"
        "119.17,120,123.53,120,128a8,8,0,0,0,16,0c0-5.75,5.3-10,10.46-14.05C152,"
        "108.76,160,102.86,160,96a32,32,0,0,0-64,0,8,8,0,0,0,16,0Z"
    ),
}


def ph(name: str, size: int = 14, color: str = "currentColor") -> str:
    """Return an inline Phosphor SVG icon string."""
    path = _PH.get(name, "")
    if not path:
        return ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'fill="{color}" viewBox="0 0 256 256" '
        f'style="vertical-align:-2px;flex-shrink:0;display:inline-block">'
        f'<path d="{path}"/>'
        f'</svg>'
    )


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');

/* ── Design tokens ────────────────────────────────────────────────────────── */
:root {
    --c-primary:       #003467;
    --c-accent:        #0072CE;
    --c-surface:       #FFFFFF;
    --c-surface-2:     #F8FAFC;
    --c-border:        #EBF3FB;
    --c-border-2:      #D6E4F0;
    --c-text-1:        #003467;
    --c-text-2:        #6B8CAE;
    --c-text-3:        #9BAEC8;
    --c-urgent:        #DC2626;
    --c-urgent-bg:     #FEF2F2;
    --c-urgent-border: #FCA5A5;
    --c-high:          #1D6FA4;
    --c-high-bg:       #EFF8FF;
    --c-high-border:   #BFDBFE;
    --c-mod:           #B45309;
    --c-mod-bg:        #FFFBEB;
    --c-mod-border:    #FDE68A;
    --c-low:           #6B7280;
    --c-low-bg:        #F3F4F6;
    --c-low-border:    #E5E7EB;
    --c-support:       #059669;
    --c-support-bg:    #ECFDF5;
    --c-against:       #DC2626;
    --radius:          6px;
    --radius-sm:       3px;
    --font:            'Montserrat', sans-serif;
    --max-w:           860px;
}

/* ── Base ─────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--font);
    background: var(--c-surface);
    color: var(--c-text-1);
}
.stApp { background: var(--c-surface); }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { display: none; }

/* Constrain main content width */
section[data-testid="stMain"] > div > div {
    max-width: var(--max-w);
}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #FAFCFE !important;
    border-right: 1px solid var(--c-border) !important;
}
[data-testid="stSidebar"] * { font-family: var(--font) !important; }
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[data-testid="stBaseButton-headerNoPadding"] { display: none !important; }
.sb-label {
    font-size: 9px;
    font-weight: 700;
    color: var(--c-text-3);
    text-transform: uppercase;
    letter-spacing: 1.5px;
}

/* ── Draft banner ─────────────────────────────────────────────────────────── */
.cds-draft-banner {
    background: #FFFBEB;
    border: 1px solid var(--c-mod-border);
    border-radius: var(--radius);
    padding: 9px 14px;
    font-size: 11px;
    font-weight: 600;
    color: #78350F;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 0.2px;
}

/* ── Page title ───────────────────────────────────────────────────────────── */
.cds-page-title {
    font-size: 20px;
    font-weight: 800;
    color: var(--c-primary);
    line-height: 1.2;
    margin-bottom: 3px;
}
.cds-page-sub {
    font-size: 11px;
    color: var(--c-text-3);
    margin-bottom: 20px;
    letter-spacing: 0.2px;
}
.cds-divider {
    border: none;
    border-top: 1px solid var(--c-border);
    margin: 0 0 24px;
}

/* ── Presentation collapsed ───────────────────────────────────────────────── */
.cds-pres {
    background: var(--c-surface-2);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    padding: 10px 16px;
    margin-bottom: 14px;
    display: flex;
    align-items: baseline;
    gap: 12px;
}
.cds-pres-label {
    font-size: 9px;
    font-weight: 700;
    color: var(--c-text-3);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    flex-shrink: 0;
}
.cds-pres-text {
    font-size: 12px;
    color: var(--c-text-2);
    line-height: 1.5;
}

/* ── Section label ────────────────────────────────────────────────────────── */
.cds-sec {
    font-size: 9px;
    font-weight: 700;
    color: var(--c-text-3);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--c-border);
}
.cds-sec.urgent { color: var(--c-urgent); border-color: var(--c-urgent-border); }

/* ── Red flags ────────────────────────────────────────────────────────────── */
.cds-rf {
    margin-bottom: 20px;
}
.cds-rf-item {
    border-left: 3px solid var(--c-urgent-border);
    background: var(--c-urgent-bg);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 10px 14px;
    margin-bottom: 6px;
    font-size: 12px;
    color: var(--c-text-1);
    line-height: 1.65;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.cds-rf-item.doc {
    border-left-color: var(--c-urgent);
    background: #FEE2E2;
}

/* ── Confidence badges ────────────────────────────────────────────────────── */
.cds-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 11px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    white-space: nowrap;
    flex-shrink: 0;
    border: 1px solid transparent;
}
.cds-badge.high     { background: var(--c-high-bg);    color: var(--c-high);    border-color: var(--c-high-border); }
.cds-badge.moderate { background: var(--c-mod-bg);     color: var(--c-mod);     border-color: var(--c-mod-border); }
.cds-badge.low      { background: var(--c-low-bg);     color: var(--c-low);     border-color: var(--c-low-border); }
.cds-badge.sm       { font-size: 9px; padding: 3px 9px; }

/* ── Leading candidate card ───────────────────────────────────────────────── */
.cds-lc {
    border: 1px solid var(--c-border-2);
    border-radius: var(--radius);
    padding: 22px 24px 18px;
    margin-bottom: 16px;
}
.cds-lc-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 4px;
}
.cds-lc-name {
    font-size: 24px;
    font-weight: 800;
    color: var(--c-primary);
    line-height: 1.15;
}
.cds-lc-icd {
    font-size: 10px;
    color: var(--c-text-3);
    margin-bottom: 18px;
    font-weight: 500;
    letter-spacing: 0.2px;
}
.cds-lc-icd b { color: var(--c-text-2); font-weight: 700; }

/* Evidence two-column grid */
.cds-ev {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 18px;
}
.cds-col-label {
    font-size: 9px;
    font-weight: 700;
    color: var(--c-text-3);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 10px;
}
.cds-col-label.ag { color: var(--c-against); }

.cds-feat {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    color: var(--c-text-1);
    line-height: 1.55;
    margin-bottom: 5px;
}
.cds-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 5px;
}
.cds-dot.sp { background: var(--c-support); }
.cds-dot.ag { background: var(--c-against); }
.cds-feat-none { font-size: 12px; color: var(--c-text-3); font-style: italic; }

/* Missing information chips */
.cds-missing-label {
    font-size: 9px;
    font-weight: 700;
    color: var(--c-text-3);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
    padding-top: 16px;
    border-top: 1px solid var(--c-border);
}
.cds-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.cds-chip {
    background: var(--c-surface-2);
    border: 1px solid var(--c-border-2);
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 11px;
    color: var(--c-text-2);
    font-weight: 500;
}

/* Why considered */
.cds-why {
    font-size: 12px;
    color: var(--c-text-2);
    line-height: 1.75;
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid var(--c-border);
    font-style: italic;
}

/* ── Uncertainty / Disambiguation ─────────────────────────────────────────── */
.cds-unc {
    border: 1px solid var(--c-mod-border);
    background: var(--c-mod-bg);
    border-radius: var(--radius);
    padding: 16px 20px;
    margin-bottom: 20px;
}
.cds-unc-title {
    font-size: 10px;
    font-weight: 700;
    color: var(--c-mod);
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 5px;
}
.cds-unc-body {
    font-size: 13px;
    color: var(--c-text-1);
    line-height: 1.6;
}
.cds-unc-count { font-weight: 700; color: var(--c-primary); }
.cds-unc-round {
    font-size: 10px;
    color: var(--c-text-3);
    margin-top: 8px;
    font-weight: 600;
}

/* Disambiguation question rows */
.cds-disam-intro {
    font-size: 12px;
    color: var(--c-text-2);
    line-height: 1.7;
    margin: 14px 0 20px;
}
.cds-disam-empty {
    font-size: 12px;
    color: var(--c-text-3);
    font-style: italic;
    margin-bottom: 12px;
}

/* Radio chip styling */
div[data-testid="stRadio"] > label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: var(--c-text-1) !important;
    margin-bottom: 6px !important;
    display: block !important;
}
div[data-testid="stRadio"] > div {
    gap: 6px !important;
    flex-wrap: wrap !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] {
    background: var(--c-surface) !important;
    border: 1px solid var(--c-border-2) !important;
    border-radius: 20px !important;
    padding: 5px 14px !important;
    gap: 6px !important;
}
div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: var(--c-text-2) !important;
    margin: 0 !important;
}

/* ── Differential ─────────────────────────────────────────────────────────── */
.cds-diff { margin-bottom: 20px; }
.cds-diff-item {
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    margin-bottom: 5px;
    overflow: hidden;
    transition: border-color 0.1s;
}
.cds-diff-item[open] { border-color: var(--c-border-2); }
.cds-diff-sum {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 16px;
    cursor: pointer;
    list-style: none;
    background: var(--c-surface);
    user-select: none;
}
.cds-diff-sum::-webkit-details-marker { display: none; }
.cds-diff-sum::marker { display: none; }
.cds-diff-rank {
    font-size: 10px;
    font-weight: 700;
    color: var(--c-text-3);
    width: 18px;
    flex-shrink: 0;
}
.cds-diff-name {
    font-size: 13px;
    font-weight: 700;
    color: var(--c-text-1);
    flex: 0 0 auto;
    min-width: 0;
}
.cds-diff-hint {
    font-size: 11px;
    color: var(--c-text-3);
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cds-diff-chev {
    font-size: 16px;
    color: var(--c-text-3);
    flex-shrink: 0;
    transition: transform 0.15s ease;
    line-height: 1;
}
.cds-diff-item[open] .cds-diff-chev { transform: rotate(90deg); }
.cds-diff-detail {
    padding: 16px 20px;
    background: var(--c-surface-2);
    border-top: 1px solid var(--c-border);
}
.cds-diff-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}
.cds-diff-why {
    font-size: 12px;
    color: var(--c-text-2);
    line-height: 1.7;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--c-border);
    font-style: italic;
}

/* ── Relevant context ─────────────────────────────────────────────────────── */
.cds-ctx-item {
    font-size: 12px;
    color: var(--c-text-1);
    padding: 8px 0;
    border-bottom: 1px solid var(--c-border);
    line-height: 1.5;
}

/* ── Approval ─────────────────────────────────────────────────────────────── */
.cds-approval {
    border-top: 2px solid var(--c-border-2);
    padding-top: 24px;
    margin-top: 8px;
}
.cds-approval-sys {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 12px 16px;
    background: var(--c-surface-2);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    margin-bottom: 20px;
}
.cds-approval-sys-label {
    font-size: 9px;
    font-weight: 700;
    color: var(--c-text-3);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    flex-shrink: 0;
}
.cds-approval-sys-diag {
    font-size: 14px;
    font-weight: 700;
    color: var(--c-primary);
}
.cds-approval-sys-conf {
    font-size: 11px;
    color: var(--c-text-2);
}
.cds-field-label {
    font-size: 10px;
    font-weight: 700;
    color: var(--c-text-1);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 6px;
}
.cds-icd-hint {
    font-size: 11px;
    color: var(--c-text-3);
    margin-top: 4px;
    margin-bottom: 16px;
}

/* Approved confirmation */
.cds-confirmed {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 0;
}
.cds-confirmed-name { font-size: 15px; font-weight: 700; color: var(--c-primary); }
.cds-confirmed-meta {
    font-size: 11px;
    color: var(--c-text-3);
    margin-top: 3px;
    display: flex;
    align-items: center;
    gap: 5px;
}

/* ── Widget overrides ─────────────────────────────────────────────────────── */
.stButton > button {
    font-family: var(--font) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    border-radius: var(--radius) !important;
}
.stTextArea textarea {
    font-family: var(--font) !important;
    font-size: 13px !important;
    color: var(--c-text-1) !important;
    border: 1px solid var(--c-border-2) !important;
    border-radius: var(--radius) !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus {
    border-color: var(--c-accent) !important;
    box-shadow: none !important;
}
.stTextInput input {
    font-family: var(--font) !important;
    font-size: 13px !important;
    color: var(--c-text-1) !important;
    border: 1px solid var(--c-border-2) !important;
    border-radius: var(--radius) !important;
}
.stTextInput input:focus {
    border-color: var(--c-accent) !important;
    box-shadow: none !important;
}

/* ── Session history (sidebar) ────────────────────────────────────────────── */
.cds-hist-section {
    border-top: 1px solid var(--c-border);
    margin-top: 20px;
    padding-top: 20px;
}
.cds-hist-entry {
    padding: 9px 0;
    border-bottom: 1px solid var(--c-border);
}
.cds-hist-entry:last-child { border-bottom: none; }
.cds-hist-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 3px;
}
.cds-hist-time {
    font-size: 10px;
    font-weight: 600;
    color: var(--c-text-3);
    letter-spacing: 0.4px;
    font-variant-numeric: tabular-nums;
}
.cds-hist-ind {
    font-size: 11px;
    font-weight: 700;
}
.cds-hist-diag {
    font-size: 12px;
    font-weight: 700;
    color: var(--c-primary);
    line-height: 1.3;
    margin-bottom: 2px;
}
.cds-hist-snip {
    font-size: 10px;
    color: var(--c-text-3);
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ── Scrollbar ────────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-thumb { background: var(--c-border-2); border-radius: 10px; }
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None):
    sub = (
        f'<div class="cds-page-sub">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        f'<div class="cds-page-title">{title}</div>'
        f'{sub}'
        f'<hr class="cds-divider">',
        unsafe_allow_html=True,
    )


def section_header(text: str, margin_top: int = 0, urgent: bool = False):
    cls = "cds-sec urgent" if urgent else "cds-sec"
    style = f"margin-top:{margin_top}px;" if margin_top else ""
    st.markdown(
        f'<div class="{cls}" style="{style}">{text}</div>',
        unsafe_allow_html=True,
    )
