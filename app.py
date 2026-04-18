import streamlit as st
import os, io, base64
from datetime import datetime
from groq import Groq
from gtts import gTTS
import PyPDF2
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer

# ====================== ELITE UI CONFIG ======================
st.set_page_config(page_title="FALCON EYE | GATE 4", layout="wide", page_icon="🦅")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #020617 100%); color: #e2e8f0; }
    h1, h2, h3 { color: #22d3ee !important; font-family: 'Orbitron', sans-serif; }
    div[data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(10px);
        border-radius: 15px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stButton>button {
        width: 100%; border-radius: 10px; border: 1px solid #22d3ee;
        background: rgba(34, 211, 238, 0.1); color: #22d3ee;
    }
    </style>
    """, unsafe_allow_html=True)

# ====================== SYSTEM ENGINES ======================
def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([page.extract_text() for page in reader.pages])
        except: return ""
    return ""

def falcon_query(prompt: str, mode: str) -> str:
    manual_context = digest_manual()
    
    # Brain Logic
    if mode == "Gate 4 Protocol":
        system_rules = f"Strictly use this manual: {manual_context}. If not in manual, say so. Expert security tone."
    elif mode == "Driver Instruction":
        system_rules = "You are a professional gate translator. Keep instructions short, loud, and clear for truck drivers."
    else:
        system_rules = "You are a general knowledge expert AI."

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# ====================== AUTHENTICATION & WORKER TRACKING ======================
# List of authorized workers (Add or change names here)
WORKERS = ["Pappi", "Bambi", "Worker 3", "Worker 4"]

if "auth" not in st.session_state: st.session_state.auth = False
if "current_worker" not in st.session_state: st.session_state.current_worker = None

if not st.session_state.auth:
    st.title("🦅 FALCON EYE | GATE 4")
    with st.container():
        # Step 1: Identity Selection
        selected_user = st.selectbox("SELECT YOUR IDENTITY:", WORKERS)
        
        # Step 2: Security Clearance
        code = st.text_input("ENTER SECURITY CLEARANCE:", type="password")
        
        if st.button("INITIALIZE SYSTEM"):
            if code == "Gate4Pass2026":
                st.session_state.auth = True
                st.session_state.current_worker = selected_user # Locks the name for the session
                st.rerun()
            else:
                st.error("ACCESS DENIED: Invalid Clearance Code")
    st.stop()

# ====================== DASHBOARD ======================
st.title("🦅 FALCON EYE COMMAND")
t1, t2, t3 = st.tabs(["📡 INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS"])

with t1:
    # --- SEARCH BAR 1: INTERNAL & GLOBAL KNOWLEDGE ---
    st.subheader("🔍 Knowledge Scan")
    k_mode = st.radio("Search Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    k_query = st.text_input("Search manual or general facts:", placeholder="e.g., What is the out-to-out rule?")
    if k_query:
        with st.spinner("Scanning..."):
            st.info(falcon_query(k_query, k_mode))

    st.divider()

    # --- SEARCH BAR 2: DRIVER INTERCOM ---
    st.subheader("🚛 Driver Intercom")
    
    # Expanded Language List
    full_langs = {
        "Urdu": "ur", "Hindi": "hi", "Arabic": "ar", "Tagalog": "tl", 
        "Bengali": "bn", "Malayalam": "ml", "Pashto": "ps", "Punjabi": "pa",
        "Tamil": "ta", "Telugu": "te", "Sinhala": "si", "Swahili": "sw",
        "Russian": "ru", "Chinese": "zh-cn", "French": "fr", "Spanish": "es",
        "Turkish": "tr", "Persian": "fa", "Vietnamese": "vi"
    }
    
    col_l, col_r = st.columns([1, 2])
    with col_l:
        d_lang = st.selectbox("Driver Language:", list(full_langs.keys()))
    with col_r:
        st.write("🎤 Listen to Driver:")
        driver_voice = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN", key='d_mic')

    if driver_voice:
        analysis = falcon_query(f"Driver said: {driver_voice}. What do they need?", "Driver Instruction")
        st.warning(f"**Driver:** {driver_voice}\n**AI:** {analysis}")

    # Reply to Driver
    st.write("⌨️ **Reply to Driver:**")
    d_reply = st.chat_input("Enter command for driver...")
    if d_reply:
        trans = falcon_query(f"Translate to {d_lang}: {d_reply}", "Driver Instruction")
        st.success(f"**Replied:** {trans}")
        tts = gTTS(text=trans, lang=full_langs[d_lang])
        rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
        st.audio(rv, format="audio/mp3", autoplay=True)

# --- TAB 2: PROTOCOLS (Corrected Audio) ---
with t2:
    st.subheader("Manual & Audio Briefing")
    
    # Audio Lecture Fix: Checks for .wav or .mp3
    audio_files = ["protocol_lecture.wav.mp3", "protocol_lecture.wav.mp3"]
    found_audio = None
    for f in audio_files:
        if os.path.exists(f):
            found_audio = f
            break
            
    if found_audio:
        st.write(f"🎧 **Active Briefing:** `{found_audio}`")
        st.audio(found_audio)
    else:
        st.caption("Upload 'protocol_lecture.wav' or 'protocol_lecture.mp3' to GitHub.")

    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=700)
        
# ====================== TAB 3: LOGS ======================
with t3:
    st.subheader("📋 Security Mission Logs")
    st.info("Enter your shift notes below. The AI will format them into a professional report based on Gate 4 Protocols.")
    
    # Input area for raw observations
    raw_observations = st.text_area("Observations / Incident Details:", placeholder="e.g., Truck with plate 1234 arrived, out-to-out rule applied, cleared for entry at 0900.", key="log_input_area")
    
    if st.button("🚀 GENERATE PROFESSIONAL LOG"):
        if raw_observations:
            with st.spinner("Processing Log..."):
                # Captures the current time in Dubai
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Instruction for the AI to format the report
                log_prompt = f"Convert these raw notes into a formal security report including the timestamp {timestamp}. Use high-level professional security language: {raw_observations}"
                
                # Calls your existing falcon_query function
                formatted_report = falcon_query(log_prompt, "Gate 4 Protocol")
                
                st.divider()
                st.write(f"**Generated Report (Time: {timestamp})**")
                
                # Displays the report in a box that is easy to copy
                st.code(formatted_report, language="text")
                st.success("Log Generated. You can now copy this for your official records.")
        else:
            st.warning("Please enter some observations first.")
