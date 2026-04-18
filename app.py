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

# Falcon Eye Dark Theme
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
    """Improved query with retry logic for rate limits"""
    for attempt in range(max_retries):
        try:
            # Prefer flash model (faster + better free tier limits)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Detect rate limit / cooling down
            if any(keyword in error_msg for keyword in ["429", "quota", "rate", "cooling", "resource exhausted"]):
                wait_time = (2 ** attempt) * 10  # 10s, 20s, 40s
                if attempt < max_retries - 1:
                    st.warning(f"⚠️ SIGNAL INTERFERENCE: Google is cooling down. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            else:
                # Non-rate-limit error → don't retry
                return f"❌ Error: {str(e)[:150]}"
    
    return "⏳ SIGNAL INTERFERENCE: Still getting rate limits. Please wait 1-2 minutes and try again."

# ====================== AUTHORIZATION ======================
if "authorized" not in st.session_state:
    st.session_state.authorized = False

if not st.session_state.authorized:
    st.title("🦅 Falcon Eye V4 | Secure Terminal")
    key = st.text_input("Enter Command Authorization Code:", type="password")
    
    if st.button("Initialize System"):
        if key == "Gate4Pass2026":
            st.session_state.authorized = True
            st.success("✅ System Initialized Successfully")
            st.rerun()
        else:
            st.error("🚫 Access Denied")
    st.stop()

# ====================== MAIN INTERFACE ======================
st.title("🦅 Falcon Eye | Gate 4 Command")

tab1, tab2, tab3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

# ------------------- TAB 1: Intelligence & Translation -------------------
with tab1:
    st.subheader("Field Intelligence & Translation")

    # Session state for history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    user_input = st.text_input(
        "Enter command (e.g., Translate to Urdu: 'Stay behind the line')",
        key="user_input"
    )
    
    target_lang = st.selectbox(
        "Speech Synthesis Language:",
        ["None", "Urdu", "Arabic", "Hindi", "Tagalog"]
    )

    if st.button("🚀 RUN SCAN", type="primary"):
        if user_input.strip():
            with st.spinner("Falcon Eye Scanning..."):
                time.sleep(1.2)  # Prevent rapid clicks
                result = falcon_query(user_input)
                
                st.info(result)
                
                # Save to history
                st.session_state.messages.append({"query": user_input, "response": result})
                
                # Text-to-Speech
                if target_lang != "None":
                    try:
                        lang_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
                        tts = gTTS(text=result, lang=lang_map[target_lang], slow=False)
                        audio_buffer = io.BytesIO()
                        tts.write_to_fp(audio_buffer)
                        audio_buffer.seek(0)
                        st.audio(audio_buffer, format="audio/mp3")
                        st.success(f"🔊 Speaking in {target_lang}")
                    except Exception as tts_err:
                        st.warning(f"Speech synthesis failed: {tts_err}")
        else:
            st.warning("Please enter a command.")

    # Show recent history
    if st.session_state.messages:
        with st.expander("📜 Recent Intelligence Scans", expanded=False):
            for i, msg in enumerate(reversed(st.session_state.messages[-5:])):
                st.markdown(f"**Query {i+1}:** {msg['query']}")
                st.markdown(f"**Response:** {msg['response'][:600]}{'...' if len(msg['response']) > 600 else ''}")
                st.divider()

# ------------------- TAB 2: Protocols -------------------
with tab2:
    st.subheader("Standard Operating Procedures")
    try:
        with open("master_docs/gate_manual.pdf", "rb") as f:
            st.download_button(
                label="📂 Open PDF Manual",
                data=f,
                file_name="Gate_Manual.pdf",
                mime="application/pdf"
            )
    except FileNotFoundError:
        st.warning("Manual not found. Place `gate_manual.pdf` in `master_docs/` folder.")

# ------------------- TAB 3: Mission Log -------------------
with tab3:
    st.subheader("Shift Report Generation")
    raw_notes = st.text_area("Input Shift Observations:", height=150)

    if st.button("🚀 Finalize & Log Report"):
        if raw_notes.strip():
            with st.spinner("Generating professional report and logging..."):
                report = falcon_query(f"Format this as a professional security log entry. Be concise, formal, and clear:\n\n{raw_notes}")

                st.code(report, language="markdown")

                # Log to Google Sheets
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    try:
                        existing = conn.read(spreadsheet=st.secrets["gsheets_url"])
                    except:
                        existing = pd.DataFrame()

                    new_row = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Operator": "pappi",
                        "Report": report
                    }])

                    updated = pd.concat([existing, new_row], ignore_index=True)
                    conn.update(spreadsheet=st.secrets["gsheets_url"], data=updated)

                    st.success("✅ Report successfully logged to Falcon Eye Database")
                except Exception as e:
                    st.error(f"Database Error: {str(e)}")
        else:
            st.warning("Please enter observations.")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.success("🟢 System Online")
    if st.button("🔌 System Shutdown"):
        st.session_state.authorized = False
        st.rerun()
    
    st.caption("Falcon Eye V4 • Secure Terminal • 2026")
