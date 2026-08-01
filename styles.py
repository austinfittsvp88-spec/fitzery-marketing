import streamlit as st


def apply_styles():
    st.markdown(
"""
<style>
#MainMenu, footer, header {
visibility: hidden;
}

.stApp {
background:
radial-gradient(circle at top left, rgba(34, 197, 94, 0.12), transparent 28%),
linear-gradient(180deg, #07110c 0%, #0b1510 55%, #08110c 100%);
color: #ffffff;
}

body, .stApp, .stApp p, .stApp label {
color: #ffffff;
}

[data-testid="stSidebar"] {
background: #07100b;
border-right: 1px solid rgba(255, 255, 255, 0.10);
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
color: #ffffff !important;
}

.hero {
padding: 30px;
border-radius: 24px;
background: linear-gradient(135deg, rgba(34, 197, 94, 0.33), rgba(10, 30, 18, 0.92));
border: 1px solid rgba(255, 255, 255, 0.12);
box-shadow: 0 18px 50px rgba(0, 0, 0, 0.25);
margin-bottom: 22px;
}

.hero h1 {
margin: 0;
font-size: 2.45rem;
color: #ffffff !important;
}

.hero p {
color: #e6f4eb !important;
font-size: 1.05rem;
margin: 8px 0 0 0;
}

.metric-card {
background: rgba(10, 24, 16, 0.90);
border: 1px solid rgba(255, 255, 255, 0.12);
border-radius: 18px;
padding: 20px;
min-height: 135px;
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
}

.metric-label {
color: #d1fae5 !important;
font-size: 0.88rem;
margin-bottom: 8px;
}

.metric-value {
color: #ffffff !important;
font-size: 1.8rem;
font-weight: 800;
}

.metric-note {
color: #86efac !important;
font-size: 0.86rem;
margin-top: 7px;
}

.lead-card {
background: linear-gradient(145deg, rgba(12, 28, 18, 0.96), rgba(7, 18, 11, 0.96));
border: 1px solid rgba(255, 255, 255, 0.12);
border-radius: 18px;
padding: 18px;
margin-bottom: 12px;
box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
}

.lead-name {
font-size: 1.2rem;
font-weight: 800;
color: #ffffff !important;
}

.lead-meta {
color: #d1fae5 !important;
font-size: 0.92rem;
line-height: 1.7;
}

.badge {
display: inline-block;
padding: 5px 10px;
border-radius: 999px;
background: rgba(34, 197, 94, 0.18);
border: 1px solid rgba(134, 239, 172, 0.35);
color: #bbf7d0 !important;
font-size: 0.78rem;
font-weight: 750;
margin-right: 6px;
}

.output-box {
background: rgba(2, 10, 5, 0.86);
border: 1px solid rgba(255, 255, 255, 0.12);
border-radius: 16px;
padding: 22px;
color: #ffffff !important;
line-height: 1.65;
overflow-wrap: anywhere;
word-break: normal;
}

.output-box * {
color: #ffffff !important;
max-width: 100%;
}

div[data-testid="stMetric"] {
background: rgba(10, 24, 16, 0.88);
border: 1px solid rgba(255, 255, 255, 0.10);
border-radius: 16px;
padding: 16px;
}

div[data-testid="stMetric"] * {
color: #ffffff !important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input {
color: #ffffff !important;
background-color: #0b1a11 !important;
border-color: rgba(255, 255, 255, 0.22) !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
color: #94a3b8 !important;
opacity: 1 !important;
}

div[data-baseweb="select"] > div {
color: #ffffff !important;
background-color: #0b1a11 !important;
border-color: rgba(255, 255, 255, 0.22) !important;
}

div[data-baseweb="select"] span,
div[data-baseweb="select"] div {
color: #ffffff !important;
}

div[data-baseweb="select"] svg {
fill: #ffffff !important;
}

ul[role="listbox"] {
background: #0b1a11 !important;
border: 1px solid rgba(255, 255, 255, 0.18) !important;
box-shadow: 0 18px 50px rgba(0, 0, 0, 0.42) !important;
}

li[role="option"],
li[role="option"] * {
background: #0b1a11 !important;
color: #ffffff !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"],
li[role="option"]:hover *,
li[role="option"][aria-selected="true"] * {
background: #166534 !important;
color: #ffffff !important;
}

details[data-testid="stExpander"] {
background: rgba(10, 24, 16, 0.88) !important;
border: 1px solid rgba(255, 255, 255, 0.12) !important;
border-radius: 16px !important;
overflow: hidden !important;
}

details[data-testid="stExpander"] summary,
details[data-testid="stExpander"][open] summary {
background: #142a1c !important;
color: #ffffff !important;
}

details[data-testid="stExpander"] summary:hover {
background: #166534 !important;
}

details[data-testid="stExpander"] summary *,
details[data-testid="stExpander"] summary svg {
color: #ffffff !important;
fill: #ffffff !important;
}

div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button,
button[data-testid^="stBaseButton"] {
background: #166534 !important;
color: #ffffff !important;
border: 1px solid rgba(255, 255, 255, 0.22) !important;
border-radius: 12px !important;
min-height: 44px !important;
font-weight: 750 !important;
opacity: 1 !important;
}

div[data-testid="stButton"] > button p,
div[data-testid="stButton"] > button span,
div[data-testid="stDownloadButton"] > button p,
div[data-testid="stDownloadButton"] > button span,
button[data-testid^="stBaseButton"] p,
button[data-testid^="stBaseButton"] span {
color: #ffffff !important;
opacity: 1 !important;
}

div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover,
button[data-testid^="stBaseButton"]:hover {
background: #15803d !important;
color: #ffffff !important;
border-color: rgba(255, 255, 255, 0.35) !important;
}

div[data-testid="stButton"] > button:focus,
div[data-testid="stDownloadButton"] > button:focus,
button[data-testid^="stBaseButton"]:focus {
color: #ffffff !important;
box-shadow: 0 0 0 2px rgba(134, 239, 172, 0.35) !important;
}

div[data-testid="stButton"] > button:disabled,
div[data-testid="stDownloadButton"] > button:disabled,
button[data-testid^="stBaseButton"]:disabled {
background: #334155 !important;
color: #ffffff !important;
opacity: 0.75 !important;
}

.stAlert, .stAlert * {
color: #ffffff !important;
}
</style>
""",
unsafe_allow_html=True,
)
