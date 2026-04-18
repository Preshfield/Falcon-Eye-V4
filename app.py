import streamlit as st
import google.generativeai as genai
import pandas as pd
from gtts import gTTS
import io
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# ====================== PAGE CONFIG ======================
st.set_page_config(
    page_title="Falcon Eye V4",
    layout="wide",
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# Falcon Eye Dark Aesthetic
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00f2ff; }
    .stButton>button {
        border-radius: 20px;
        border: 1px solid #00f2ff;
        background-color: #161b22;
        color: #00f2ff;
    }
    div.stTextInput>div>div>input, 
    div.stTextArea>div>div>textarea {
        color: #00f2ff;
        background-color: #161b22;
    }
    </style>
    """, unsafe_allow_html=True)

# ====================== GEMINI SETUP ======================
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ GOOGLE_API_KEY is missing from secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def falcon_query(prompt: str, max_retries: int = 3) -> str:
    """Improved query function with retry for rate limits"""
    for attempt in range(max_retries):
        try:
            # Since you paid for billing, 1.5-flash will be incredibly fast
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e).lower()
            # If billing is active, you shouldn't see these, but we keep the safety net
            if any(k in error_str for k in ["429", "quota", "rate", "cooling", "resource exhausted"]):
                wait_time = (2 ** attempt) * 5 
                if attempt < max_retries - 1:
                    st.warning(f"⚠️ SIGNAL INTERFERENCE: Re-routing via backup... ({wait_time}s)")
                    time.sleep(wait_time)
                    continue
            else:
                return f"❌ API Error: {str(e)[:120]}"
    
    return "⏳ Connection Timeout. Please check your internet or API billing status."

# ====================== SESSION STATE ======================
if "authorized" not in st.session_state:
    st.session_state.authorized = False
if "last_response" not in st.session_state:
    st.session_state.last_response = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# ====================== AUTHORIZATION ======================
if not st.session_state.authorized:
    st.title("🦅 Falcon Eye V4 | Secure Terminal")
    key = st.text_input("Enter Command Authorization Code:", type="password")
    
    if st.button("Initialize System"):
        if key == "Gate4Pass2026":
            st.session_state.authorized = True
            st.success("✅ System Initialized")
            st.rerun()
        else:
            st.error("🚫 Access Denied")
    st.stop()

# ====================== MAIN APP ======================
st.title("🦅 Falcon Eye | Gate 4 Command")

tab1, tab2, tab3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

# ------------------- TAB 1: Intelligence & Speech -------------------
with tab1:
    st.subheader("Field Intelligence & Translation")
    user_input = st.text_input("Enter command:", key="user_input")
    target_lang = st.selectbox("Speech Synthesis Language:", ["None", "Urdu", "Arabic", "Hindi", "Tagalog"])

    if st.button("🚀 RUN SCAN", type="primary"):
        if user_input.strip():
            with st.spinner("Falcon Eye Scanning..."):
                result = falcon_query(user_input)
                st.info(result)
                st.session_state.last_response = result
                st.session_state.messages.append({"query": user_input, "response": result})
                
                if target_lang != "None":
                    try:
                        lang_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
                        tts = gTTS(text=result, lang=lang_map[target_lang], slow=False)
                        audio_buffer = io.BytesIO()
                        tts.write_to_fp(audio_buffer)
                        audio_buffer.seek(0)
                        st.audio(audio_buffer, format="audio/mp3")
                    except: st.warning("Audio processing failed.")

# ------------------- TAB 3: Mission Log -------------------
with tab3:
    st.subheader("Shift Report Generation")
    raw_notes = st.text_area("Input Shift Observations:", height=150)

    if st.button("🚀 Finalize & Log Report"):
        if raw_notes.strip():
            with st.spinner("Generating & Logging Report..."):
                report = falcon_query(f"Format as a concise security log: {raw_notes}")
                st.code(report, language="markdown")
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    new_row = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Operator": "pappi",
                        "Report": report
                    }])
                    # Using the simpler 'create' method for reliability
                    conn.create(spreadsheet=st.secrets["gsheets_url"], data=new_row)
                    st.success("✅ Report logged to Falcon Eye Database")
                except Exception as e:
                    st.error(f"Database Error: {str(e)}")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.success("🟢 System Online")
    st.caption("Operator: pappi")
    if st.button("🔌 System Shutdown"):
        st.session_state.authorized = False
        st.rerun()
