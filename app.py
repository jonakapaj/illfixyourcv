# pyrefly: ignore [missing-import]
import streamlit as st
import sys
import os
from importlib import import_module

# Make local modules importable
sys.path.insert(0, os.path.dirname(__file__))

from ai_agents import score_skills, audit_and_rewrite, structure_cv
from pdf_templates import build_corporate, build_tech_modern, build_minimal_slate


def _load(module_name):
    """Lazy-import a heavy module (fitz, plotly) only when needed."""
    return import_module(module_name)


# ─── Session State Init ───────────────────────────────────────────────────────
for key, default in {
    "upload_key": 0,
    "scores": None,
    "audit": None,
    "rewrite": None,
    "cv_data": None,
    "selected_template": "corporate",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─── Page Config & CSS ────────────────────────────────────────────────────────
st.set_page_config(page_title="AI CV Optimizer Pro", layout="wide", page_icon="🎯")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base ─────────────────────────────────────────────── */
html, body, .stApp {
    background: #09070f;
    color: #ede9fe;
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #110d1f 0%, #0b0814 100%) !important;
    border-right: 1px solid rgba(139,92,246,0.18) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #a78bfa !important; }
[data-testid="stSidebar"] label {
    color: #7c6faa !important; font-size:12px !important;
    letter-spacing:.05em; text-transform:uppercase;
}

/* ── Inputs ───────────────────────────────────────────── */
.stTextArea textarea {
    background: rgba(139,92,246,0.06) !important;
    border: 1px solid rgba(139,92,246,0.2) !important;
    border-radius: 12px !important;
    color: #ede9fe !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextArea textarea:focus {
    border-color: #8b5cf6 !important;
    box-shadow: 0 0 0 3px rgba(139,92,246,0.2) !important;
}
[data-testid="stFileUploader"] {
    background: rgba(139,92,246,0.05) !important;
    border: 2px dashed rgba(139,92,246,0.3) !important;
    border-radius: 12px !important;
}

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%) !important;
    color: #fff !important; border: none !important;
    border-radius: 10px !important; font-weight: 700 !important;
    letter-spacing: .03em !important; transition: all .2s !important;
    padding: .55rem 1.6rem !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(139,92,246,0.45) !important;
    filter: brightness(1.1) !important;
}

/* ── Cards ────────────────────────────────────────────── */
.card {
    background: rgba(139,92,246,0.05);
    border: 1px solid rgba(139,92,246,0.15);
    border-radius: 20px; padding: 28px;
    margin-bottom: 20px;
    box-shadow: 0 4px 40px rgba(0,0,0,0.5);
    transition: border-color .2s;
}
.card:hover { border-color: rgba(139,92,246,0.35); }

.card-title {
    font-size: 12px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #a78bfa;
    margin-bottom: 18px;
}

/* ── Score pills ──────────────────────────────────────── */
.score-pill {
    display:inline-flex; align-items:center; gap:6px;
    background: rgba(139,92,246,0.1); border:1px solid rgba(139,92,246,0.25);
    border-radius:30px; padding:5px 13px; font-size:12px; font-weight:600;
    color:#c4b5fd; margin:3px;
}

/* ── Divider ──────────────────────────────────────────── */
.sect-div {
    height:1px;
    background:linear-gradient(90deg,transparent,rgba(139,92,246,0.4),transparent);
    margin: 36px 0;
}

/* ── Template cards ───────────────────────────────────── */
.tpl-card {
    border-radius: 16px; padding: 20px 20px 14px;
    border: 2px solid rgba(255,255,255,0.07);
    transition: all .25s; position: relative;
    cursor: pointer; margin-bottom: 10px;
}
.tpl-card::before {
    content:''; position:absolute; inset:0; border-radius:14px;
    background: linear-gradient(135deg, rgba(255,255,255,0.04), transparent);
    pointer-events:none;
}
.tpl-card:hover {
    transform: translateY(-3px);
    border-color: rgba(139,92,246,0.5);
    box-shadow: 0 10px 32px rgba(0,0,0,0.5);
}
.tpl-card.selected {
    border-color: #8b5cf6;
    box-shadow: 0 0 0 1px #8b5cf6, 0 10px 32px rgba(139,92,246,0.25);
}
.tpl-corporate { background: linear-gradient(145deg, #1a1035 0%, #0e0920 100%); }
.tpl-tech      { background: linear-gradient(145deg, #0f1f35 0%, #071020 100%); }
.tpl-minimal   { background: linear-gradient(145deg, #1a0f2e 0%, #100a20 100%); }

.tpl-badge {
    display:inline-block; padding:3px 12px; border-radius:20px;
    font-size:11px; font-weight:700; letter-spacing:.06em; margin-bottom:10px;
}
.badge-corp { background:#f59e0b22; color:#fbbf24; border:1px solid #f59e0b44; }
.badge-tech { background:#6366f122; color:#818cf8; border:1px solid #6366f144; }
.badge-min  { background:#ec489922; color:#f472b6; border:1px solid #ec489944; }
.tpl-title { font-size:16px; font-weight:700; color:#f5f3ff; margin:6px 0 4px; }
.tpl-desc  { font-size:12px; color:#6b5fa0; line-height:1.5; }
.tpl-check { position:absolute; top:14px; right:16px; font-size:18px; }

/* ── Headings ─────────────────────────────────────────── */
h1,h2,h3 { color:#a78bfa !important; }

/* ── Hero ─────────────────────────────────────────────── */
.hero-title {
    font-size: 2.8rem; font-weight: 800; line-height:1.15;
    background: linear-gradient(135deg, #f5f3ff 0%, #a78bfa 45%, #f472b6 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 8px;
}
.hero-sub { font-size: 1rem; color: #6b5fa0; font-weight: 400; }
.hero-chip {
    display:inline-flex; align-items:center; gap:6px;
    background:rgba(139,92,246,0.1); border:1px solid rgba(139,92,246,0.25);
    border-radius:20px; padding:4px 13px; font-size:12px; color:#c4b5fd;
    font-weight:600; margin-right:8px;
}

/* ── Sidebar steps ────────────────────────────────────── */
.step-badge {
    display:inline-flex; align-items:center; justify-content:center;
    width:26px; height:26px; border-radius:50%;
    background:linear-gradient(135deg,#7c3aed,#a855f7);
    color:#fff; font-size:12px; font-weight:700; flex-shrink:0;
}
.step-row  { display:flex; align-items:center; gap:10px; margin-bottom:14px; }
.step-label{ font-size:13px; font-weight:600; color:#ddd6fe; }

/* ── Tabs ─────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { background:transparent !important; gap:4px; }
.stTabs [data-baseweb="tab"] {
    background: rgba(139,92,246,0.06) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(139,92,246,0.15) !important;
    color: #7c6faa !important; font-size: 13px !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(139,92,246,0.18) !important;
    color: #c4b5fd !important;
    border-color: rgba(139,92,246,0.4) !important;
}

/* ── Info box ─────────────────────────────────────────── */
.stAlert { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ─── UI ───────────────────────────────────────────────────────────────────────

# Hero
st.markdown("""
<div style='padding:2rem 0 1.5rem;'>
  <div class='hero-title'>AI Career Sentinel</div>
  <p class='hero-sub'>Multi-agent CV optimisation powered by local AI</p>
  <div style='margin-top:14px;'>
    <span class='hero-chip'>&#x26A1; Llama 3</span>
    <span class='hero-chip'>&#x1F4C4; PDF Templates</span>
    <span class='hero-chip'>&#x1F4CA; Skill Radar</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Setup")
    st.markdown('<div class="step-row"><span class="step-badge">1</span><span class="step-label">Paste Job Description</span></div>', unsafe_allow_html=True)
    job_desc = st.text_area("Job Description", height=200, placeholder="Paste the full job description here…", label_visibility="collapsed")
    st.markdown('<div class="step-row" style="margin-top:12px"><span class="step-badge">2</span><span class="step-label">Upload Your CV</span></div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload CV PDF", type="pdf", key=f"cv_upload_{st.session_state.upload_key}", label_visibility="collapsed")
    st.markdown('<div class="step-row" style="margin-top:12px"><span class="step-badge">3</span><span class="step-label">Extra Instructions (optional)</span></div>', unsafe_allow_html=True)
    user_request = st.text_area("Extra Instructions", height=70, placeholder="e.g. Emphasise leadership, add more Python projects…", label_visibility="collapsed")
    st.markdown("---")
    st.caption("🔒 Everything runs locally via Ollama. Your data never leaves your machine.")


# ── Main layout ────────────────────────────────────────────────────────────────
analysis_ready = bool(uploaded_file and job_desc)
show_results = bool(st.session_state.scores or st.session_state.rewrite)

if not analysis_ready and not show_results and not st.session_state.cv_data:
    st.info("👈 Upload your CV and paste a job description in the sidebar to get started.")
    st.stop()

col1, col2 = st.columns([1, 1], gap="large")

# ── Left: Skill radar + Run button ────────────────────────────────────────────
with col1:
    st.markdown('<div class="card"><div class="card-title">📊 &nbsp;Skill Alignment Radar</div>', unsafe_allow_html=True)

    if analysis_ready:
        if st.button("🚀 Run Full Analysis", use_container_width=True):
            fitz = _load("fitz")
            with st.spinner("🤖 Agent 1: Scoring skills…"):
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                raw_text = "".join([page.get_text() for page in doc])
                st.session_state.scores = score_skills(raw_text, job_desc)
            with st.spinner("🤖 Agent 2: Auditing & rewriting CV…"):
                st.session_state.audit, st.session_state.rewrite = audit_and_rewrite(
                    raw_text, job_desc, user_request
                )
            with st.spinner("🤖 Agent 3: Structuring output for PDF…"):
                st.session_state.cv_data = structure_cv(
                    raw_text, st.session_state.rewrite
                )
            st.session_state.upload_key += 1
            st.rerun()
    else:
        st.caption("Upload a new CV in the sidebar to run another analysis.")

    if st.session_state.scores:
        go = _load("plotly.graph_objects")
        cats = list(st.session_state.scores.keys())
        vals = list(st.session_state.scores.values())
        fig = go.Figure(data=go.Scatterpolar(
            r=vals, theta=cats, fill="toself", line_color="#00d2ff",
            fillcolor="rgba(0,210,255,0.08)"
        ))
        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 100],
                               gridcolor="rgba(255,255,255,0.08)",
                               tickfont=dict(color="#64748b", size=9)),
                angularaxis=dict(tickfont=dict(color="#94a3b8", size=11)),
            ),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="white", showlegend=False, margin=dict(t=20,b=20,l=20,r=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        pills = "".join(
            f'<span class="score-pill">{k}&nbsp;<b>{v}</b>/100</span>'
            for k, v in st.session_state.scores.items()
        )
        st.markdown(pills, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ── Right: Audit / Suggested Edits ────────────────────────────────────────────
with col2:
    if st.session_state.rewrite and st.session_state.audit:
        st.markdown('<div class="card"><div class="card-title">📝 &nbsp;AI Optimised Content</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["💡 Suggested Edits", "🚩 Audit Report"])
        with tab1:
            st.markdown(st.session_state.rewrite)
        with tab2:
            st.markdown(st.session_state.audit)
        st.markdown('</div>', unsafe_allow_html=True)




# ── Template Selector + PDF Generator ────────────────────────────────────────
if st.session_state.cv_data:
    st.markdown('<div class="sect-div"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🎨 &nbsp;Choose Your CV Template</div>', unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b;font-size:13px;margin-bottom:20px'>Pick a style then click Generate. The AI-optimised content will be applied to your chosen layout.</p>", unsafe_allow_html=True)

    TEMPLATES = {
        "corporate": {
            "label": "Corporate Classic",
            "badge": '<span class="tpl-badge badge-corp">Formal</span>',
            "desc": "Navy header, gold accent bar — perfect for banking, consulting & enterprise roles.",
            "cls": "tpl-corporate",
            "build": build_corporate,
        },
        "tech": {
            "label": "Tech Modern",
            "badge": '<span class="tpl-badge badge-tech">Modern</span>',
            "desc": "Teal/blue gradient header, colored sections — ideal for startups & tech companies.",
            "cls": "tpl-tech",
            "build": build_tech_modern,
        },
        "minimal": {
            "label": "Minimal Slate",
            "badge": '<span class="tpl-badge badge-min">Creative</span>',
            "desc": "Dark slate sidebar with contact & skills — great for product, design & creative-tech roles.",
            "cls": "tpl-minimal",
            "build": build_minimal_slate,
        },
    }

    t1, t2, t3 = st.columns(3)
    for col, (tid, meta) in zip([t1, t2, t3], TEMPLATES.items()):
        selected = st.session_state.selected_template == tid
        check = "✅" if selected else ""
        with col:
            st.markdown(
                f'<div class="tpl-card {meta["cls"]} {"selected" if selected else ""}">'
                f'<span class="tpl-check">{check}</span>'
                f'{meta["badge"]}'
                f'<div class="tpl-title">{meta["label"]}</div>'
                f'<div class="tpl-desc">{meta["desc"]}</div>'
                f'{meta["mini"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Select {meta['label']}", key=f"sel_{tid}"):
                st.session_state.selected_template = tid
                st.rerun()

    # ── Generate PDF ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    chosen = TEMPLATES[st.session_state.selected_template]
    gcol1, gcol2, gcol3 = st.columns([2, 1, 1])
    with gcol1:
        if st.button(f"📥 Generate CV — {chosen['label']}", use_container_width=True, type="primary"):
            with st.spinner("Rendering your CV PDF…"):
                pdf_bytes = chosen["build"](st.session_state.cv_data)
            st.download_button(
                label="⬇️  Download Now",
                data=pdf_bytes,
                file_name=f"optimised_cv_{st.session_state.selected_template}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.success("✅ Your CV is ready!")