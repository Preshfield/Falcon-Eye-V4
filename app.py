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
    /* 1. Global Background & Dark Theme */
    .stApp {
        background: linear-gradient(180deg, #020617 0%, #0f172a 100%);
        color: #f1f5f9;
    }

    /* 2. Floating Top Header (Station Status) */
    .custom-header {
        position: fixed; top: 10px; left: 5%; width: 90%;
        background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px);
        border: 1px solid #22d3ee; border-radius: 15px;
        padding: 10px 25px; display: flex; justify-content: space-between;
        align-items: center; z-index: 1000; box-shadow: 0 4px 15px rgba(34, 211, 238, 0.2);
    }

    /* 3. Floating LOGOUT Button (Top Right) */
    div[data-testid="stButton"] > button[kind="secondary"] {
        position: fixed; top: 22px; right: 8%; z-index: 1001;
        background: transparent; border: 1px solid #22d3ee;
        color: #22d3ee; border-radius: 8px; font-weight: bold;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: #22d3ee; color: #020617; box-shadow: 0 0 10px #22d3ee;
    }

    /* 4. Tab Styling (Blue Underline) */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 500; }
    .stTabs [aria-selected="true"] { color: #22d3ee !important; border-bottom-color: #22d3ee !important; }

    /* 5. Glowing Intercom Box */
    .intercom-box {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(34, 211, 238, 0.3);
        border-radius: 20px; padding: 25px; margin-top: 20px;
    }

    /* 6. Driver Response Bubble */
    .driver-bubble {
        background: #1e293b; border-left: 5px solid #22d3ee;
        padding: 15px; border-radius: 10px; margin: 10px 0;
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
# ====================== AUTHENTICATION & WORKER TRACKING ======================
# WORKER DATABASE: "Name": "Password"
# You can add more workers here easily!
WORKER_DB = {
    "Precious": "Falcon01",
    "Bambi": "Nancy",
    "Worker3": "Access2026",
    "Worker4": "Secure789"
}

if "auth" not in st.session_state: st.session_state.auth = False
if "current_worker" not in st.session_state: st.session_state.current_worker = None

if not st.session_state.auth:
    st.title("🦅 FALCON EYE | GATE 4")
    
    with st.container():
        st.subheader("Worker Login")
        
        # Step 1: Select Name
        user_identity = st.selectbox("SELECT YOUR NAME:", list(WORKER_DB.keys()))
        
        # Step 2: Enter Personal Password
        user_password = st.text_input("ENTER YOUR PERSONAL PASSWORD:", type="password")
        
        if st.button("SIGN IN TO STATION"):
            # Check if the password matches the selected worker
            if user_password == WORKER_DB[user_identity]:
                st.session_state.auth = True
                st.session_state.current_worker = user_identity
                st.success(f"Welcome back, {user_identity}. System Initializing...")
                st.rerun()
            else:
                st.error("❌ INVALID PASSWORD. Please check your credentials.")
    st.stop()

# ====================== LOGOUT SYSTEM ======================
# Add this right after your main title
col_title, col_logout = st.columns([3, 1])

with col_logout:
    if st.button("🔒 LOGOUT"):
        # This clears all session data and kicks back to the login screen
        st.session_state.auth = False
        st.session_state.current_worker = None
        st.session_state.chat_history = []
        st.rerun()

with col_title:
    # This keeps your metric looking clean next to the logout button
    st.write(f"**Station Active:** {st.session_state.current_worker} | {datetime.now().strftime('%H:%M')}")

# ====================== DASHBOARD ======================
st.title("🦅 Falcon Eye Gate4")
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

    # --- SEARCH 2: DRIVER INTERCOM (FIXED AUDIO) ---
    st.subheader("🚛 Driver Intercom")
    
    full_langs = {
        "Bengali": "bn", "Urdu": "ur", "Hindi": "hi", "Arabic": "ar", 
        "Tagalog": "tl", "Malayalam": "ml", "Pashto": "ps", "Punjabi": "pa",
        "Tamil": "ta", "Telugu": "te", "Sinhala": "si", "Swahili": "sw"
    }
    
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        d_lang = st.selectbox("Select Language:", list(full_langs.keys()))
    with d_col2:
        st.write("🎤 Driver Speaking:")
        driver_voice = speech_to_text(language=full_langs[d_lang], start_prompt="👂 CLICK TO LISTEN", key='d_mic')

    if driver_voice:
        intent = falcon_query(f"Driver said: {driver_voice}. What do they need?", "Driver Intercom")
        st.warning(f"**Driver ({d_lang}):** {driver_voice}\n\n**AI Context:** {intent}")

    # Reply Logic
    d_reply = st.chat_input("Enter command for driver...")
    if d_reply:
        translation = falcon_query(f"Translate to {d_lang}: {d_reply}", "Driver Intercom")
        st.success(f"**Translation ({d_lang}):** {translation}")
        
        # FIXED AUDIO BLOCK
        tts = gTTS(text=translation, lang=full_langs[d_lang])
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        
        # Using getvalue() to ensure the browser reads the raw data correctly
        st.audio(audio_stream.getvalue(), format="audio/mpeg", autoplay=True)
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
# ====================== TAB 3: LOGS ======================
with t3:
    st.subheader("📋 Security Mission Logs")
    
    # Displays who is currently logged in
    st.info(f"Logged in as: **{st.session_state.current_worker}**")
    
    st.write("Enter your shift notes below. The AI will format them into a professional report digitally signed by you.")
    
    # Input area for raw observations
    raw_observations = st.text_area(
        "Observations / Incident Details:", 
        placeholder="e.g., Truck with plate 1234 arrived, out-to-out rule applied, cleared for entry at 0900.", 
        key="log_input_area"
    )
    
    if st.button("🚀 GENERATE PROFESSIONAL LOG"):
        if raw_observations:
            with st.spinner("Processing Log..."):
                # Captures the current time in Dubai
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Instruction for the AI to format the report and include the specific worker
                log_prompt = (
                    f"Convert these raw notes into a formal security report. "
                    f"OFFICER ON DUTY: {st.session_state.current_worker}. "
                    f"TIMESTAMP: {timestamp}. "
                    f"Use high-level professional security language based on Gate 4 Protocols: {raw_observations}"
                )
                
                # Calls your existing falcon_query function
                formatted_report = falcon_query(log_prompt, "Gate 4 Protocol")
                
                st.divider()
                st.write(f"**Generated Report**")
                st.caption(f"Prepared by {st.session_state.current_worker} at {timestamp}")
                
                # Displays the report in a box that is easy to copy
                st.code(formatted_report, language="text")
                st.success("Log Generated. Copy the text above for your official records.")
        else:
            st.warning("Please enter some observations first.")
