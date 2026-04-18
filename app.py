import streamlit as st
import os, io, base64
from datetime import datetime
import google.generativeai as genai
from groq import Groq
from gtts import gTTS
import PyPDF2
from streamlit_gsheets import GSheetsConnection
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer

# ====================== ELITE UI CONFIG ======================
st.set_page_config(page_title="Falcon Eye Elite", layout="wide", page_icon="🦅")

# Advanced CSS for Investor-Ready Look
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
        color: #e2e8f0;
    }
    /* Glowing Headers */
    h1, h2, h3 {
        color: #22d3ee !important;
        font-family: 'Orbitron', sans-serif;
        text-shadow: 0px 0px 10px rgba(34, 211, 238, 0.3);
    }
    /* Glassmorphism Containers */
    div[data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    /* Custom Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        border: 1px solid #22d3ee;
        background: rgba(34, 211, 238, 0.1);
        color: #22d3ee;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: #22d3ee;
        color: #0f172a;
        box-shadow: 0px 0px 15px #22d3ee;
    }
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(30, 41, 59, 0.7);
        border-radius: 10px 10px 0px 0px;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        color: #22d3ee !important;
        border-bottom-color: #22d3ee !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ====================== CORE ENGINES ======================
def falcon_query(prompt: str, brain_mode: str) -> str:
    # Manual Digestion Logic
    manual_data = ""
    if brain_mode == "Gate 4 Protocol" and os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                manual_data = "".join([page.extract_text() for page in reader.pages])
        except: pass

    system_rules = f"You are Falcon Eye Elite, a security AI. Context: {manual_data}. Mode: {brain_mode}. Be professional."
    
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# ====================== UI LAYOUT ======================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🦅 FALCON EYE ELITE")
    with st.container():
        code = st.text_input("ENTER SECURITY CLEARANCE:", type="password")
        if st.button("AUTHENTICATE SYSTEM"):
            if code == "Gate4Pass2026":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- TOP STATUS BAR ---
col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
with col_s1:
    st.title("🦅 FALCON EYE | GATE 4")
with col_s2:
    st.metric(label="System Status", value="OPTIMAL", delta="🟢 Online")
with col_s3:
    st.metric(label="Active Operator", value="pappi")

st.write("---")

t1, t2, t3 = st.tabs(["📡 INTERCOM", "📖 PROTOCOLS", "📝 LOGS"])

# --- TAB 1: INTERCOM LOOP ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

with t1:
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.subheader("Control")
        brain = st.radio("Brain Mode:", ["Gate 4 Protocol", "Global Knowledge"])
        lang_dict = {"Urdu":"ur", "Hindi":"hi", "Arabic":"ar", "Tagalog":"tl", "Bengali":"bn", "Malayalam":"ml"}
        d_lang = st.selectbox("Driver Language:", list(lang_dict.keys()))
        
        st.write("🎤 **Step 1: Listen**")
        voice = speech_to_text(language=lang_dict[d_lang], start_prompt="👂 EAR ON", stop_prompt="✅ CAPTURED", just_once=True, key='mic')
        
        if st.button("🗑️ Reset Chat"):
            st.session_state.chat_history = []
            st.rerun()

    with col_b:
        st.subheader("Live Feed")
        if voice:
            st.session_state.chat_history.append({"role": "driver", "text": voice})
            analysis = falcon_query(f"Driver said in {d_lang}: '{voice}'. English summary?", brain)
            st.info(f"**Driver:** {voice}\n\n**Analysis:** {analysis}")

        reply = st.chat_input("Type Response...")
        if reply:
            st.session_state.chat_history.append({"role": "pappi", "text": reply})
            trans = falcon_query(f"Translate to {d_lang}: {reply}", "Global Knowledge")
            st.success(f"**Replied:** {trans}")
            tts = gTTS(text=trans, lang=lang_dict[d_lang])
            rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
            st.audio(rv, format="audio/mp3", autoplay=True)

        for chat in reversed(st.session_state.chat_history):
            avatar = "🚚" if chat["role"] == "driver" else "🦅"
            st.chat_message("user" if chat["role"]=="driver" else "assistant", avatar=avatar).write(chat["text"])

# --- TAB 2: PROTOCOLS ---
with t2:
    st.subheader("Manual & Training Station")
    if os.path.exists("gate_manual.pdf"):
        c1, c2 = st.columns([2, 1])
        with c2:
            st.download_button("📥 GET PDF", open("gate_manual.pdf", "rb"), "gate_manual.pdf")
            if os.path.exists("protocol_lecture.wav"):
                st.write("🎧 **Shift Briefing**")
                st.audio("protocol_lecture.wav")
        with c1:
            pdf_viewer("gate_manual.pdf", height=600)

# --- TAB 3: LOGS ---
with t3:
    st.subheader("Shift Intelligence Report")
    raw = st.text_area("Observations:")
    if st.button("🚀 GENERATE OFFICIAL LOG"):
        report = falcon_query(f"Professional Log: {raw}", "Gate 4 Protocol")
        st.code(report)
