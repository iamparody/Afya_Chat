"""
CDS theme — palette, CSS, and UI helpers.
Extracted from the LREB dashboard theme; Ortho-specific components removed.
"""
import streamlit as st

COLORS = {
    "primary": "#0072CE",
    "success": "#0BB99F",
    "warning": "#D97706",
    "danger":  "#E11D48",
    "muted":   "#6B8CAE",
    "dark":    "#003467",
    "purple":  "#7F77DD",
    "coral":   "#D85A30",
    "green":   "#1D9E75",
}

CHART_LAYOUT = dict(
    paper_bgcolor="#fff",
    plot_bgcolor="#fff",
    font=dict(family="Montserrat", color="#003467"),
    margin=dict(l=0, r=0, t=10, b=30),
    xaxis=dict(gridcolor="#EBF3FB", tickfont=dict(size=10, color="#6B8CAE")),
    yaxis=dict(gridcolor="#EBF3FB", tickfont=dict(size=10, color="#6B8CAE")),
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
    background: #F0F5FA !important;
    border-right: 1px solid #D6E4F0 !important;
}
[data-testid="stSidebar"] * {
    font-family: 'Montserrat', sans-serif !important;
}
[data-testid="stSidebarNav"] { display: none !important; }

.sh {
    font-size: 10px;
    font-weight: 800;
    color: #0072CE;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    padding: 8px 0;
    border-bottom: 2px solid #EBF3FB;
    margin-bottom: 16px;
}
.sb-label {
    font-size: 9px;
    font-weight: 700;
    color: #8BAAC5;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    margin-bottom: 4px;
}
.stButton button {
    background: #0072CE !important;
    color: #fff !important;
    border: none !important;
    font-family: 'Montserrat', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    padding: 8px 18px !important;
    border-radius: 6px !important;
}
.stButton button:hover { background: #003467 !important; }

[data-baseweb="tab"] {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600 !important;
    color: #6B8CAE !important;
    font-size: 12px !important;
}
[aria-selected="true"] {
    color: #0072CE !important;
    border-bottom-color: #0072CE !important;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: #B0C8E0; border-radius: 10px; }
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def cl(**kw):
    return {**CHART_LAYOUT, **kw}


def section_header(text, margin_top=0):
    style = f"margin-top:{margin_top}px" if margin_top else ""
    st.markdown(f'<div class="sh" style="{style}">{text}</div>', unsafe_allow_html=True)


def page_header(title, subtitle=None):
    sub_html = (
        f'<div style="font-size:12px;color:#6B8CAE;margin-top:4px">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        f'<div style="margin-bottom:8px">'
        f'<div style="font-size:24px;font-weight:800;color:#003467">{title}</div>'
        f'{sub_html}'
        f'</div>'
        f'<div style="border-bottom:1px solid #EBF3FB;margin:16px 0 24px"></div>',
        unsafe_allow_html=True,
    )


def info_card(text, border_color="#0072CE"):
    st.markdown(
        f'<div style="padding:10px 14px;background:#F4F8FC;border-left:3px solid {border_color};'
        f'border-radius:4px;font-size:12px;color:#003467;margin-bottom:10px">{text}</div>',
        unsafe_allow_html=True,
    )


def dq_note(text):
    st.markdown(
        f'<div style="background:#F4F8FC;border-left:3px solid #B0C8E0;border-radius:4px;'
        f'padding:8px 12px;margin:10px 0;font-size:12px;color:#003467;line-height:1.5">'
        f'<span style="font-weight:700;color:#6B8CAE">Note · </span>{text}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label, value, sub="", color="#003467", icon=""):
    accent = {COLORS["danger"], COLORS["warning"], COLORS["success"]}
    bl = f"border-left:4px solid {color};" if color in accent else ""
    icon_html = f'<span style="font-size:13px;margin-right:5px">{icon}</span>' if icon else ""
    st.markdown(
        f'<div style="background:#F4F8FC;border:1px solid #D6E4F0;border-radius:8px;'
        f'padding:24px 20px;{bl}">'
        f'<div style="font-size:10px;font-weight:700;color:#6B8CAE;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:10px">{icon_html}{label}</div>'
        f'<div style="font-size:42px;font-weight:800;color:{color};line-height:1">{value}</div>'
        f'<div style="font-size:12px;color:#6B8CAE;margin-top:8px">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
