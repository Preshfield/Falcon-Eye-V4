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

# ====================== ELITE UI & BRANDING ======================
st.set_page_config(page_title="Falcon Eye Elite", layout="wide", page_icon="🦅")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #020617 100%); color: #e2e8f0; }
    h1, h2, h3 { color: #22d3ee !important; font-family: 'Orbitron', sans-serif; text-shadow: 0px 0px 10px rgba(34, 211, 238, 0.3); }
    [data-testid="stMetricValue"] { color: #22d3ee !important; }
    div[data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(10px);
        border-radius: 15px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stButton>button {
        width: 100%; border-radius: 10px; border: 1px solid #22d3ee;
        background: rgba(34, 211, 238, 0.1); color: #22d3ee; transition: 0.3s;
    }
    .stButton>button:hover { background: #22d3ee; color: #0f172a; box-shadow: 0px 0px 15px #22d3ee; }
    </style>
    """, unsafe_allow_html=True)

# ====================== SYSTEM ENGINES ======================
def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([page.extract_text() for page in reader.pages])
        except: return "Manual read error."
    return "No manual found."

def falcon_query(prompt: str, brain_mode: str) -> str:
    # Brain 1: Gate 4 (Strict Manual) | Brain 2: Global (Open Knowledge)
    manual_context = digest_manual() if brain_mode == "Gate 4 Protocol" else ""
    
    if brain_mode == "Gate 4 Protocol":
        system_rules = f"You are the Gate 4 Supervisor. Use ONLY this manual: {manual_context}. If not in manual, say so. Interpret pappi's messy typing with intelligence."
    else:
        system_rules = "You are a general-purpose Elite AI assistant."

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Connection Error: {str(e)}"

# ====================== AUTHENTICATION ======================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🦅 FALCON EYE ELITE | SECURE ACCESS")
    with st.container():
        code = st.text_input("SECURITY CLEARANCE CODE:", type="password")
        if st.button("INITIALIZE SYSTEM"):
            if code == "Gate4Pass2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("ACCESS DENIED")
    st.stop()

# ====================== DASHBOARD HEADER ======================
col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h1: st.title("🦅 FALCON EYE | GATE 4")
with col_h2: st.metric("System", "OPTIMAL", "🟢 Active")
with col_h3: st.metric("Operator", "pappi")

st.divider()

# ====================== MAIN COMMAND TABS ======================
t1, t2, t3 = st.tabs(["📡 GLOBAL INTERCOM", "📖 PROTOCOL LIBRARY", "📝 MISSION LOGS"])

# --- TAB 1: THE INTERCOM LOOP ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

with t1:
    col_ctrl, col_feed = st.columns([1, 2])
    
    with col_ctrl:
        st.subheader("Control Center")
        brain = st.radio("Active Brain:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
        
        # Global Language Support
        langs = {
            "Urdu": "ur", "Hindi": "hi", "Arabic": "ar", "Tagalog": "tl", 
            "Bengali": "bn", "Malayalam": "ml", "Pashto": "ps", "Punjabi": "pa"
        }
        target_lang = st.selectbox("Driver Language:", list(langs.keys()))
        
        st.write("🎤 **Listen to Driver:**")
        driver_voice = speech_to_text(language=langs[target_lang], start_prompt="👂 START LISTENING", stop_prompt="✅ STOP", just_once=True, key='mic_input')
        
        if st.button("🗑️ CLEAR SESSION"):
            st.session_state.chat_history = []
            st.rerun()

    with col_feed:
        st.subheader("Intelligence Feed")
        if driver_voice:
            st.session_state.chat_history.append({"role": "driver", "text": driver_voice})
            analysis = falcon_query(f"The driver said this in {target_lang}: '{driver_voice}'. Explain what they need in English.", brain)
            st.info(f"**Driver:** {driver_voice}\n\n**AI Context:** {analysis}")

        # Your Reply Section
        my_reply = st.chat_input("Enter instructions for the driver...")
        if my_reply:
            st.session_state.chat_history.append({"role": "pappi", "text": my_reply})
            translation = falcon_query(f"Translate this to {target_lang} clearly: {my_reply}", "Global Knowledge")
            st.success(f"**Replied ({target_lang}):** {translation}")
            
            # Voice Output
            tts = gTTS(text=translation, lang=langs[target_lang])
            rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
            st.audio(rv, format="audio/mp3", autoplay=True)

        for chat in reversed(st.session_state.chat_history):
            avatar = "🚚" if chat["role"] == "driver" else "🦅"
            st.chat_message("user" if chat["role"]=="driver" else "assistant", avatar=avatar).write(chat["text"])

# --- TAB 2: PROTOCOLS & AUDIO ---
with t2:
    st.subheader("Operational Manuals")
    if os.path.exists("gate_manual.pdf"):
        col_pdf, col_audio = st.columns([2, 1])
        with col_audio:
            st.download_button("📥 DOWNLOAD PDF", open("gate_manual.pdf", "rb"), "gate_manual.pdf")
            st.write("---")
            st.write("🎧 **Audio Briefing**")
            if os.path.exists("protocol_lecture.wav"):
                st.audio("protocol_lecture.wav")
            else: st.caption("No audio lecture found.")
        with col_pdf:
            pdf_viewer("gate_manual.pdf", height=700)
    else: st.error("Manual not found.")

# --- TAB 3: MISSION LOGS ---
with t3:
    st.subheader("Shift Reporting")
    raw_notes = st.text_area("Enter shift observations:")
    if st.button("🚀 SUBMIT TO DATABASE"):
        report = falcon_query(f"Format this as a professional security log: {raw_notes}", "Gate 4 Protocol")
        st.code(report)
        # Add G-Sheets Sync here...
