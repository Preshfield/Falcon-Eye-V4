import streamlit as st
import PyPDF2
import google.generativeai as genai
import os
import io
import pandas as pd
from gtts import gTTS
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. VISUAL HUD (Falcon Eye Aesthetic)
st.set_page_config(page_title="Falcon Eye V4", layout="wide", page_icon="🦅")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00f2ff; }
    stButton>button { border-radius: 20px; border: 1px solid #00f2ff; background-color: #161b22; color: #00f2ff; }
    div.stTextInput>div>div>input { color: #00f2ff; background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# 2. SESSION CONTROL
if "authorized" not in st.session_state:
    st.session_state.authorized = False

if not st.session_state.authorized:
    st.title("🦅 Falcon Eye V4 | Secure Terminal")
    key = st.text_input("Enter Command Authorization Code:", type="password")
    if st.button("Initialize System"):
        if key == "Gate4Pass2026":
            st.session_state.authorized = True
            st.rerun()
        else:
            st.error("🚫 Access Denied")
else:
    # 3. THE AI ENGINE (SHIELDED)
    def falcon_query(prompt):
        # We only configure the key inside the function to prevent "Ghost Pings"
        if "GOOGLE_API_KEY" not in st.secrets:
            return "❌ API KEY MISSING IN SECRETS"
        
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        try:
            # Using 1.5-flash as the primary engine for speed
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Backup engine if flash is busy
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                return response.text
            except:
                return "⏳ SIGNAL INTERFERENCE: Google is cooling down. Wait 20 seconds and click again."

    # 4. COMMAND HUD
    st.title("🦅 Falcon Eye | Gate 4 Command")
    tab1, tab2, tab3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

    with tab1:
        st.subheader("Field Intelligence & Translation")
        # Use text_input instead of chat_input to stop auto-running
        user_input = st.text_input("Enter command (e.g., Translate to Urdu: 'Stay behind the line')")
        target_lang = st.selectbox("Speech Synthesis Language:", ["None", "Urdu", "Arabic", "Hindi", "Tagalog"])
        
        if st.button("RUN SCAN"):
            if user_input:
                with st.spinner("Falcon Eye Scanning..."):
                    res = falcon_query(user_input)
                    st.info(res)
                    
                    if target_lang != "None":
                        try:
                            v_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
                            tts = gTTS(text=res, lang=v_map[target_lang])
                            rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
                            st.audio(rv)
                        except: pass

    with tab2:
        st.subheader("Standard Operating Procedures")
        if os.path.exists("master_docs/gate_manual.pdf"):
            with open("master_docs/gate_manual.pdf", "rb") as f:
                st.download_button("📂 Open PDF Manual", f, "Gate_Manual.pdf")
        else:
            st.warning("Manual not found. Ensure it is in the master_docs folder on GitHub.")

    with tab3:
        st.subheader("Shift Report Generation")
        raw_notes = st.text_area("Input Shift Observations:")
        if st.button("🚀 Finalize & Log Report"):
            if raw_notes:
                with st.spinner("Logging to Database..."):
                    report = falcon_query(f"Format as professional security log: {raw_notes}")
                    st.code(report)
                    try:
                        # Only connect to sheets when the button is clicked
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        log_data = pd.DataFrame([{
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Operator": "pappi",
                            "Report": report
                        }])
                        conn.create(spreadsheet=st.secrets["gsheets_url"], data=log_data)
                        st.success("✅ Logged to Falcon Eye Database")
                    except Exception as e:
                        st.error(f"Database Error: {str(e)}")

    if st.sidebar.button("System Shutdown"):
        st.session_state.authorized = False
        st.rerun()
