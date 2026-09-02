"""
CDS theme — palette, CSS, and UI component helpers.
Phosphor icons embedded as inline SVG (zero external dependencies).
"""
import streamlit as st

COLORS = {
    "primary": "#0072CE",
    "success": "#0BB99F",
    "warning": "#D97706",
    "danger":  "#E11D48",
    "muted":   "#6B8CAE",
    "dark":    "#003467",
}

# Phosphor Icons — regular weight, 256×256 viewBox
# https://phosphoricons.com
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
    "minus-circle": (
        "M168,128a8,8,0,0,1-8,8H96a8,8,0,0,1,0-16h64A8,8,0,0,1,168,128Z"
        "M232,128A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Z"
        "m-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"
    ),
    "check": (
        "M232.49,80.49l-128,128a12,12,0,0,1-17,0l-56-56a12,12,0,1,1,17-17"
        "L96,183,215.51,63.51a12,12,0,0,1,17,17Z"
    ),
    "info": (
        "M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Z"
        "m0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Z"
        "m16-40a8,8,0,0,1-8,8,16,16,0,0,1-16-16V128a8,8,0,0,1,0-16"
        ",16,16,0,0,1,16,16v40A8,8,0,0,1,144,176Z"
        "M112,84a12,12,0,1,1,12,12A12,12,0,0,1,112,84Z"
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

html, body, [class*="css"] {
    font-family: 'Montserrat', sans-serif;
    background: #fff;
    color: #003467;
}
.stApp { background: #fff; }

[data-testid="stSidebar"] {
    background: #FAFCFE !important;
    border-right: 1px solid #EBF3FB !important;
}
[data-testid="stSidebar"] * { font-family: 'Montserrat', sans-serif !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* Section header — quiet label, not dashboard title */
.sh {
    font-size: 9px;
    font-weight: 700;
    color: #9BAEC8;
    text-transform: uppercase;
    letter-spacing: 2px;
    padding: 6px 0;
    border-bottom: 1px solid #F0F5FA;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.sb-label {
    font-size: 9px;
    font-weight: 700;
    color: #9BAEC8;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}

/* Buttons — keep Streamlit primary/secondary distinction */
.stButton > button {
    font-family: 'Montserrat', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    border-radius: 4px !important;
}

/* Text area */
.stTextArea textarea {
    font-family: 'Montserrat', sans-serif !important;
    font-size: 13px !important;
    color: #003467 !important;
    border: 1px solid #D6E4F0 !important;
    border-radius: 4px !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus { border-color: #0072CE !important; box-shadow: none !important; }

/* Text input (approval diagnosis) */
.stTextInput input {
    font-family: 'Montserrat', sans-serif !important;
    font-size: 13px !important;
    color: #003467 !important;
    border: 1px solid #D6E4F0 !important;
    border-radius: 4px !important;
}
.stTextInput input:focus { border-color: #0072CE !important; box-shadow: none !important; }

/* Expanders (differential) */
[data-testid="stExpander"] {
    border: 1px solid #EBF3FB !important;
    border-radius: 4px !important;
    margin-bottom: 6px !important;
    box-shadow: none !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Montserrat', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #003467 !important;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-thumb { background: #D6E4F0; border-radius: 10px; }
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def section_header(text: str, margin_top: int = 0):
    style = f"margin-top:{margin_top}px;" if margin_top else ""
    st.markdown(
        f'<div class="sh" style="{style}">{text}</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str | None = None):
    sub_html = (
        f'<div style="font-size:12px;color:#6B8CAE;margin-top:4px;line-height:1.5">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        f'<div style="margin-bottom:8px">'
        f'<div style="font-size:22px;font-weight:800;color:#003467;line-height:1.2">{title}</div>'
        f'{sub_html}'
        f'</div>'
        f'<div style="border-bottom:1px solid #EBF3FB;margin:14px 0 24px"></div>',
        unsafe_allow_html=True,
    )
