import streamlit as st
import openai
import os
import PyPDF2
from datetime import datetime

# --- 1. THE TACTICAL INTERFACE (CSS) ---
st.set_page_config(page_title="FALCON EYE | GATE 4", page_icon="🦅", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #e0e6ed; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #1a2a6c; color: white; border: 1px solid #4facfe; }
    .tactical-header { 
        padding: 20px; border-bottom: 2px solid #4facfe; margin-bottom: 25px;
        background: linear-gradient(90deg, rgba(26,42,108,1) 0%, rgba(0,242,254,0.1) 100%);
    }
    .station-status { color: #00f2fe; font-family: monospace; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE MEMORY & SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. THE PROTOCOL ENGINE (PDF SCAN) ---
def digest_manual():
    target_file = "gate_4_protocol.pdf" # Ensure your manual is named this
    if os.path.exists(target_file):
        try:
            with open(target_file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([page.extract_text() for page in reader.pages])
        except: return "ERROR: Manual unreadable."
    return "WARNING: No Manual Loaded. Operating on Global Knowledge."

@st.cache_data(ttl=3600)
def falcon_query(user_prompt: str, mode: str):
    manual_context = digest_manual()
    current_time = datetime.now().strftime("%H:%M")
    
    # SYSTEM RULES: PRESERVING TACTICAL DISCIPLINE
    if mode == "Gate 4 Protocol":
        sys_rules = f"You are FALCON EYE GATE 4. USE ONLY THIS MANUAL: {manual_context}. Be precise and authoritative."
    else:
        sys_rules = "You are FALCON EYE TACTICAL INTEL. Use Global Security Knowledge. Current Time: " + current_time

    # CONVERSATION LOOP
    conversation = [{"role": "system", "content": sys_rules}]
    for msg in st.session_state.messages:
        conversation.append({"role": msg["role"], "content": msg["content"]})
    conversation.append({"role": "user", "content": user_prompt})

    client = openai.OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    
    try:
        response = client.chat.completions.create(model="deepseek-chat", messages=conversation)
        return response.choices[0].message.content
    except Exception as e:
        return f"CRITICAL SYSTEM ERROR: {str(e)}"

# --- 4. THE UI LAYOUT (PRESERVING YOUR DESIGN) ---
with st.container():
    st.markdown(f"""
    <div class="tactical-header">
        <h1>🦅 FALCON EYE: GATE 4</h1>
        <div class="station-status">STATION ACTIVE: PRECIOUS AKPEZI OJAH | GST: {datetime.now().strftime("%H:%M")}</div>
        <p style="color: #4facfe; margin-top: 5px;">Tactical AI Intelligence & Protocol Management</p>
    </div>
    """, unsafe_allow_html=True)

# SIDEBAR CONTROLS
st.sidebar.header("🕹️ COMMAND CONSOLE")
k_mode = st.sidebar.selectbox("Knowledge Scan Scope", ["Gate 4 Protocol", "Global Knowledge"])
if st.sidebar.button("Clear Mission Logs"):
    st.session_state.messages = []
    st.rerun()

# CHAT INTERFACE
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Enter Protocol Query or Driver Command..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        response = falcon_query(prompt, k_mode)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
