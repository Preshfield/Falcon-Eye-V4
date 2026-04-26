import streamlit as st
import os, io, json, base64
from datetime import datetime, timedelta, timezone
from gtts import gTTS
import PyPDF2
import openai
import gspread
from google.oauth2.service_account import Credentials
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer
from fpdf import FPDF
import pandas as pd
import random

# ====================== 1. CRITICAL INITIALIZATION ======================
st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")

if "auth" not in st.session_state:
    st.session_state.auth = False
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"New Conversation": []}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "New Conversation"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_worker" not in st.session_state:
    st.session_state.current_worker = "Guest"

# ====================== 2. FULL RESTORED CSS ======================
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    st.markdown('''
        <style>
        .stApp { background: radial-gradient(circle at top right, #0f172a, #020617); color: #f8fafc; }
        .hero-container {
            background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px);
            padding: 60px 40px; border-radius: 20px; margin-bottom: 30px;
            border: 1px solid rgba(173, 255, 47, 0.3); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        .hero-title { color: #ffffff !important; font-size: 72px !important; font-weight: 900 !important; letter-spacing: -3px !important; }
        .status-dot { color: #ADFF2F; font-weight: 800; text-shadow: 0 0 15px #ADFF2F; animation: pulse 2s infinite; }
        .hero-divider { height: 3px; width: 80px; background: linear-gradient(90deg, #ADFF2F, transparent); margin: 20px 0; }
        .hero-tagline { color: #ADFF2F !important; font-size: 14px !important; letter-spacing: 5px !important; font-weight: 700 !important; text-transform: uppercase; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .stTabs [data-baseweb="tab-list"] { background-color: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 12px; }
        .stTabs [aria-selected="true"] { color: #ADFF2F !important; background-color: rgba(173, 255, 47, 0.1) !important; }
        .driver-msg { background: rgba(173, 255, 47, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #ADFF2F; margin: 10px 0; }
        .intercom-box { background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); }
        .custom-header { background: rgba(15, 23, 42, 0.9); padding: 10px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ADFF2F; }
        </style>
    ''', unsafe_allow_html=True)

local_css("css/style.css")

# ====================== 3. UTILITY ENGINES ======================
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def save_to_google_sheets(worker, payload, sheet_name="LOG", custom_date=None):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        
        # Use custom_date if provided, otherwise use Dubai current date
        if custom_date:
            date_s = custom_date
        else:
            now = datetime.now(timezone(timedelta(hours=4)))
            date_s = now.strftime("%d-%m-%Y")
        
        # --- THE SMART "IF" LOGIC ---
        if sheet_name == "REPORT":
            # Keeps the Professor's professional casing (Lower + Upper)
            row_data = [date_s] + [str(i) for i in payload] + [worker]
            
        elif sheet_name == "MANUAL PASS":
            # Structured transfer for Gate passes - forced to UPPER
            row_data = [
                str(payload[0]).upper(), date_s, str(payload[1]).upper(), 
                str(payload[2]).upper(), str(payload[3]).upper(), str(payload[4]).upper(), 
                str(payload[5]).upper(), str(payload[6]).upper(), str(payload[7]).upper(), 
                worker.upper(), str(payload[8]).upper(), str(payload[9]).upper()
            ]
            
        else:
            # Default logic: Forces ALL CAPS for LOG and other logistics data
            row_data = [date_s] + [str(i).upper() for i in payload] + [worker.upper()]
            
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"❌ SYNC ERROR: {str(e)}"); return False

def update_google_sheet(row_index, payload, sheet_name, custom_date=None):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        if custom_date:
            date_s = custom_date
        else:
            now = datetime.now(timezone(timedelta(hours=4)))
            date_s = now.strftime("%d-%m-%Y")

        if sheet_name == "MANUAL PASS":
            row_data = [payload[0], date_s, payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], st.session_state.current_worker, payload[8], payload[9]]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [st.session_state.current_worker]
        sheet.update(f"A{row_index}", [row_data])
        return True
    except Exception as e:
        st.error(f"Update Failed: {e}"); return False

def search_logs(query, sheet_name="LOG"):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        all_rows = sheet.get_all_values()
        if not all_rows: return None, None
        header = all_rows[0]
        for idx, row in enumerate(all_rows[1:][-50:], start=max(2, len(all_rows)-49)): 
            if any(query.upper() in str(c).upper() for c in row):
                return dict(zip(header, row)), idx
        return None, None
    except: return None, None

def get_last_ids(sheet_name):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        vals = sheet.get_all_values()
        if len(vals) < 2: return "1", "1"
        last_row = vals[-1]
        return last_row[0], last_row[3]
    except: return "1", "1"

def load_all_sessions(username):
    file_path = f"memory_{username.replace(' ', '_').lower()}.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f: return json.load(f)
    return {"New Conversation": []}

def save_all_sessions(username, sessions):
    file_path = f"memory_{username.replace(' ', '_').lower()}.json"
    with open(file_path, "w") as f: json.dump(sessions, f)


# ====================== 4. AI ENGINES (FIREWALLED ANALYST) ======================

import requests

def get_protocol_context():
    """Extracts text from the gate manual to give the AI 'vision'."""
    try:
        if os.path.exists("gate_manual.pdf"):
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        text += content
                return text
        return "Manual not found."
    except Exception as e:
        return f"Error reading manual: {e}"

def generate_human_voice(text):
    """ElevenLabs high-fidelity voice engine."""
    try:
        api_key = st.secrets["ELEVENLABS_API_KEY"]
        # 'pNInz6obpgDQGcFmaJgB' is the ID for Adam (Professional/Deep)
        voice_id = "pNInz6obpgDQGcFmaJgB" 
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg", 
            "Content-Type": "application/json", 
            "xi-api-key": api_key
        }
        data = {
            "text": text[:1000], # Stability limit
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        response = requests.post(url, json=data, headers=headers)
        return response.content if response.status_code == 200 else None
    except:
        return None
def falcon_query(prompt: str, mode: str, chat_history=None):
    """Hardened logic to force Gate 4 Protocol compliance and clean Global switching."""
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # 1. SET THE BRAIN RULES
    if mode == "Gate 4 Protocol":
        manual_context = get_protocol_context()
        sys_rules = (
            "### ROLE: GATE 4 PROTOCOL PROFESSOR\n"
            f"### PRIMARY SOURCE MATERIAL: {manual_context}\n"
            "### STRICT OPERATING RULES:\n"
            "1. You are a specialist professor for Gate 4 Dubai DWC Customs. You ONLY know what is in the manual.\n"
            "2. If a question is NOT in the manual, respond: 'Access Denied. Outside sanctioned protocol.'\n"
            "3. NO SMALL TALK."
        )
    else:
        # GLOBAL MODE: We ignore the manual entirely to prevent the "Access Denied" bug
        sys_rules = (
            "You are the Global Intelligence AI. You are an omniscient genius. "
            "You have full access to all world knowledge. Solve any problem. "
            "You are NOT restricted by the gate manual in this mode."
        )

    # 2. THE BRAIN CLEANSER
    # If switching to Global, we ignore past "Gate 4" history to avoid conflicts
    conversation = [{"role": "system", "content": sys_rules}]
    
    if chat_history and mode == "Gate 4 Protocol": 
        # Only carry history if staying within the protocol mode
        conversation.extend(chat_history[-6:])
    elif chat_history and mode == "Global Knowledge":
        # Filter history: only keep messages that don't mention "Manual" or "Protocol"
        # This stops the AI from thinking it is still the 'Gate 4 Professor'
        clean_history = [m for m in chat_history[-4:] if "protocol" not in m["content"].lower()]
        conversation.extend(clean_history)
    
    # 3. FINAL INSTRUCTION PACKAGING
    if mode == "Gate 4 Protocol":
        prompt = f"[STRICT PROTOCOL MODE] {prompt}"
    else:
        prompt = f"[GLOBAL INTELLIGENCE MODE] {prompt}"
        
    conversation.append({"role": "user", "content": prompt})
    
    return client.chat.completions.create(
        model="deepseek-chat",
        messages=conversation,
        stream=True,
        temperature=0.1, # Slightly higher for global fluidity, still low for protocol
        timeout=15.0
    )
# ====================== 5. AUTHENTICATION ======================
WORKER_DB = {"Precious Akpezi Ojah": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}

if not st.session_state.auth:
    st.title("🦅 FALCON EYE | LOGIN")
    user_identity = st.selectbox("USER:", list(WORKER_DB.keys()))
    user_password = st.text_input("PASSWORD:", type="password")
    if st.button("SIGN IN") and user_password == WORKER_DB[user_identity]:
        st.session_state.auth = True
        st.session_state.current_worker = user_identity
        st.session_state.all_sessions = load_all_sessions(user_identity)
        st.rerun()
    st.stop()


# ====================== 6. DASHBOARD UI (SIDEBAR RESTORED) ======================
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")

with st.sidebar:
    st.title("🦅 MISSION LOGS")
    chat_list = list(st.session_state.all_sessions.keys())
    if st.button("➕ START NEW CHAT", use_container_width=True):
        new_id = f"Session {len(chat_list) + 1} ({dubai_time})"
        st.session_state.all_sessions[new_id] = []
        st.session_state.current_chat_id = new_id
        st.rerun()
    st.divider()
    selected_chat = st.radio("History:", chat_list)
    st.session_state.current_chat_id = selected_chat
    st.session_state.messages = st.session_state.all_sessions.get(selected_chat, [])
    if st.button("🔒 LOGOUT", use_container_width=True):
        save_all_sessions(st.session_state.current_worker, st.session_state.all_sessions)
        st.session_state.auth = False
        st.rerun()

st.markdown(f'<div class="custom-header"><b>Station:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-container"><h1 class="hero-title">FALCON EYE</h1><h2>GATE 4 <span class="status-dot">● ONLINE</span></h2><div class="hero-divider"></div><p class="hero-tagline">Tactical AI & Protocol Management</p></div>', unsafe_allow_html=True)

# TABS
t1, t2, t3, t4, t5, t6, t7 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "📟 LOGISTIC DOCUMENTATION", "🕵️ AUDIT", "🌐 TRANSLATOR", "💳 FAST-PAY"])

with t1:
    st.subheader(f"🔍 {st.session_state.current_chat_id}")
    
    # --- NEW: VOICE PLAYER MOVED TO TOP OF TAB (STAYS HIDDEN UNTIL NEEDED) ---
    voice_placeholder = st.container() 
    with voice_placeholder:
        falcon_responses = [m["content"] for m in st.session_state.messages if m["role"] == "assistant"]
        if falcon_responses:
            last_msg = falcon_responses[-1]
            
            # Check if we need to generate new audio
            if st.session_state.get("last_voiced_msg") != last_msg:
                audio_bytes = generate_human_voice(last_msg) 
                if audio_bytes:
                    st.session_state["falcon_audio_cache"] = audio_bytes
                    st.session_state["last_voiced_msg"] = last_msg
            
            # Display the player if cache exists
            if "falcon_audio_cache" in st.session_state:
                c1, c2 = st.columns([0.1, 0.9])
                c1.markdown("### 🔊")
                c2.audio(st.session_state["falcon_audio_cache"], format="audio/mpeg", autoplay=True)
                st.divider() # Separates player from the chat history

    # 1. SCOPE TOGGLE
    k_mode = st.radio("Intelligence Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    
    # 2. CHAT CONTAINER
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): 
                st.markdown(message["content"])

    st.divider()
    
    # 3. 🛰️ FALCON LIVE INTERFACE
    col_vibe, col_status = st.columns([0.2, 0.8])
    with col_vibe:
        voice_captured = speech_to_text(language='en-US', start_prompt="⭕", stop_prompt="⏺️", key='main_chat_mic')
    
    with col_status:
        st.markdown(f"**Live Feed:** *{voice_captured if voice_captured else 'WAITING...'}*")

    # 4. INPUT BOX
    query = st.chat_input("Ask Falcon...", key="falcon_universal_input")
    final_query = voice_captured if voice_captured else query

    # 5. EXECUTION ENGINE
    if final_query and st.session_state.get("last_processed_query") != final_query:
        st.session_state.last_processed_query = final_query
        st.session_state.messages.append({"role": "user", "content": final_query})
        
        with st.chat_message("assistant"):
            res_placeholder = st.empty()
            full_res = ""
            for chunk in falcon_query(final_query, k_mode, st.session_state.messages[:-1]):
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    res_placeholder.markdown(full_res + "▌")
            res_placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
        # Save and trigger rerun - The player at the top will catch the new message now
        st.rerun()


   # protocol manual)

with t2:
    if os.path.exists("gate_manual.pdf"):
        # Create a layout for the title and the audio player
        col_p1, col_p2 = st.columns([0.6, 0.4])
        
        with col_p1:
            st.subheader("📖 Gate 4 Protocol Manual")
            
        with col_p2:
            # --- PRE-RECORDED LECTURE PLAYER ---
            lecture_path = "protocol_lecture.wav.mp3"
            if os.path.exists(lecture_path):
                st.write("🎵 **Protocol Audio Lecture**")
                st.audio(lecture_path, format="audio/mpeg")
            else:
                st.info("Audio file 'protocol_lecture.wav.mp3' not found.")

        # Display the PDF below
        pdf_viewer("gate_manual.pdf", height=800)
    else:
        st.error("Manual not found. Please ensure 'gate_manual.pdf' is in the repository.")

 # ======================LOG AND REPORT ======================
with t3:
    st.markdown("<h3 style='text-align: center; color: #ADFF2F;'>OFFICIAL INCIDENT REPORTING 📋</h3>", unsafe_allow_html=True)
    
    # 1. INPUT AREA
    raw_notes = st.text_area("Enter Rough Observations / Agent Notes:", height=150, key="report_input")
    
    # 2. THE REWRITE ENGINE
    if st.button("🪄 GENERATE PROFESSIONAL REPORT") and raw_notes:
        with st.spinner("Falcon Intelligence rewriting to Standard Security Protocol..."):
            report_instruction = (
                "You are a Senior Security Supervisor. Rewrite the following rough notes into a "
                "formal, detailed, and objective Incident Report. Use standard security terminology. "
                "Output ONLY the polished report text without any markdown stars or formatting."
            )
            
            # Using the Global Brain for maximum intelligence
            polished_report = "".join([
                chunk.choices[0].delta.content 
                for chunk in falcon_query(f"{report_instruction}\n\nNOTES: {raw_notes}", "Global Knowledge") 
                if chunk.choices[0].delta.content
            ])
            
            st.session_state["active_report_text"] = polished_report

    # 3. DISPLAY & SAVE AREA
    if "active_report_text" in st.session_state:
        st.markdown("---")
        st.subheader("Standardized Security Report")
        
        # Display the report in an easy-to-read box
        st.success(st.session_state["active_report_text"])
        
        # 4. GOOGLE SHEETS TRANSFER (Locked to 'REPORT' Tab)
        if st.button("🚀 AUTHORIZE & SEND TO REPORT STORAGE"):
            final_report = st.session_state["active_report_text"]
            
            # Formatting as a list to match your existing save_to_google_sheets(worker, payload, sheet_name)
            # This creates: [Date, "OFFICIAL_INCIDENT", Report_Body, Worker_Name] in your sheet
            report_payload = ["OFFICIAL_INCIDENT", final_report] 
            
            # TARGETING THE NEW 'REPORT' WORKSHEET
            if save_to_google_sheets(st.session_state.current_worker, report_payload, sheet_name="REPORT"):
                st.balloons() # Visual confirmation it worked
                st.success("✅ Successfully archived in REPORT worksheet.")
                del st.session_state["active_report_text"]
            else:
                st.error("FAILED. Ensure you created a tab named 'REPORT' in your Google Sheet.")

    if st.button("CLEAR LOG 🔄"):
        if "active_report_text" in st.session_state:
            del st.session_state["active_report_text"]
        st.rerun()

 # ====================== 1. STAFF AGENT: AUTO-FILL VOICE COMMANDS ======================


with t4:
    
    with st.expander("👨‍💼 STAFF AGENT (VOICE-TO-FORM)", expanded=True):
        st.markdown("<p style='color: #ADFF2F;'>Tell the agent what to write, and he will fill the form below.</p>", unsafe_allow_html=True)
        
        col_mic, col_txt = st.columns([0.2, 0.8])
        with col_mic:
            agent_voice = speech_to_text(language='en-US', start_prompt="⭕", stop_prompt="⏺️", key='staff_agent_mic')
        with col_txt:
            agent_input = st.chat_input("Instruct your staff agent...", key="staff_agent_input")
        
        final_agent_query = agent_voice if agent_voice else agent_input

        if final_agent_query:
            with st.spinner("Staff Agent typing..."):
                staff_resp = falcon_query(final_agent_query, "Logistics Agent")
                
                # --- PUSH DATA TO SESSION STATE ---
                if "|" in staff_resp:
                    data_pairs = staff_resp.split("|")
                    for pair in data_pairs:
                        if ":" in pair:
                            k, v = pair.split(":", 1)
                            key_clean = k.strip().upper()
                            val_clean = v.strip().replace("N/A", "")
                            
                            # Map extracted data to form variables
                            if "BOOK" in key_clean: st.session_state["f_bk_val"] = val_clean
                            if "PASS" in key_clean: st.session_state["f_gp_val"] = val_clean
                            if "CONSIGNEE" in key_clean: st.session_state["f_con_val"] = val_clean
                            if "BILL" in key_clean: st.session_state["f_bill_val"] = val_clean
                            if "AMOUNT" in key_clean: st.session_state["f_amt_val"] = float(val_clean) if val_clean.replace('.','',1).isdigit() else 0.0
                            if "REMARKS" in key_clean: st.session_state["f_rem_val"] = val_clean
                    st.success("✅ Form updated! Review below.")

    st.divider()

    # ====================== 2.  COMMAND CENTER  ======================
    st.subheader("📟 Logistics Command Center")
    
    # 1. EXPRESS ENTRY LOGIC
    quick_code = st.text_input("⚡ EXPRESS ENTRY (e.g. PASS 1234):").upper()
    st.write("📌 Quick Fill:")
    col_q1, col_q2, col_q3 = st.columns(3)
    smart_con = ""
    if col_q1.button("DHL"): smart_con = "DHL EXPRESS"
    if col_q2.button("FEDEX"): smart_con = "FEDEX LOGISTICS"
    if col_q3.button("ARAMEX"): smart_con = "ARAMEX DUBAI"

    # 2. AUTO-ID GENERATION
    last_sl, last_gp = get_last_ids("MANUAL PASS")
    try: next_sl = str(int(last_sl) + 1); next_gp = str(int(last_gp) + 1)
    except: next_sl = ""; next_gp = ""
    if "PASS" in quick_code: next_gp = quick_code.replace("PASS", "").strip()

    # 3. MODE STATUS
    is_editing = "edit_row_idx" in st.session_state
    doc_type = st.radio("Form Type:", ["Manual Gate Pass", "Labour Charge", "Official Report"], horizontal=True)

    # 4. THE MAIN FORM (NOW CONNECTED TO STAFF AGENT)
    with st.form("logistics_form", clear_on_submit=True):
        f_date = st.date_input("SELECT DATE:", value=datetime.now(timezone(timedelta(hours=4))))
        formatted_date = f_date.strftime("%d-%m-%Y")
        
        if doc_type == "Manual Gate Pass":
            c1, c2, c3 = st.columns(3)
            # LOGIC: If agent provides data, use it; otherwise use the original QuickFill/AutoID logic
            f_sl = c1.text_input("SL NO", value=next_sl).upper()
            f_bk = c2.text_input("BOOK NO", value=st.session_state.get("f_bk_val", "")).upper()
            f_gp = c3.text_input("GATE PASS NO", value=st.session_state.get("f_gp_val", next_gp)).upper()
            
            f_con = st.text_input("CONSIGNEE", value=st.session_state.get("f_con_val", smart_con)).upper()
            f_bill = st.text_input("CUSTOMS BILL NO", value=st.session_state.get("f_bill_val", "")).upper()
            f_desc = st.text_area("DESCRIPTION").upper()
            
            c4, c5, c6 = st.columns(3)
            f_unit = c4.text_input("UNIT").upper()
            f_cash = c5.text_input("CASH RECEIPT NO").upper()
            f_amt = c6.number_input("AMOUNT", min_value=0.0, value=st.session_state.get("f_amt_val", 0.0), format="%.2f")
            
            f_rem = st.text_input("REMARKS", value=st.session_state.get("f_rem_val", "")).upper()
            payload = [f_sl, f_bk, f_gp, f_con, f_bill, f_desc, f_unit, f_cash, f_rem, str(f_amt)]
            sheet_target, check_id = "MANUAL PASS", f_gp
        
        elif doc_type == "Labour Charge":
            t_start = st.time_input("START TIME")
            t_end = st.time_input("FINISH TIME")
            payload = [t_start.strftime("%H:%M"), t_end.strftime("%H:%M"), st.text_input("RECEIPT BOOK").upper(),
                       st.text_input("VOUCHER").upper(), st.text_input("HOURS").upper(), st.text_input("LABOURS").upper(),
                       st.selectbox("FORKLIFT", ["YES", "NO"]), st.number_input("AMOUNT", min_value=0.0), st.text_input("FROM").upper(), st.text_input("REMARKS").upper()]
            sheet_target, check_id = "LABOUR CHARGE", payload[3]
        else:
            payload = [st.text_input("BOOK NO").upper(), st.text_input("GATE PASS NO").upper(), st.text_input("CONSIGNEE").upper(),
                       st.text_input("BILL NO").upper(), st.text_input("REMARKS").upper(), st.number_input("AMOUNT", min_value=0.0), st.text_area("REASON").upper()]
            sheet_target, check_id = "OFFICIAL REPORT", payload[1]

        # --- DYNAMIC ACTION BUTTONS (PRESERVED) ---
        st.divider()
        if is_editing:
            st.warning(f"🛠️ EDITING MODE: ROW {st.session_state.edit_row_idx}")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.form_submit_button("✅ SUBMIT EDIT", use_container_width=True):
                    if update_google_sheet(st.session_state.edit_row_idx, payload, sheet_target, custom_date=formatted_date):
                        st.success("✅ UPDATED")
                        del st.session_state.edit_row_idx
                        st.rerun()
            with btn_col2:
                if st.form_submit_button("❌ CANCEL", use_container_width=True):
                    del st.session_state.edit_row_idx
                    st.rerun()
        else:
            if st.form_submit_button("🚀 SYNC TO DATABASE", use_container_width=True):
                dup, _ = search_logs(check_id, sheet_target)
                if dup: st.error(f"⚠️ DUPLICATE! {check_id} exists."); st.stop()
                if save_to_google_sheets(st.session_state.current_worker, payload, sheet_target, custom_date=formatted_date):
                    st.success(f"✅ SYNCED FOR {formatted_date}")
                    # Clear temporary agent values after a successful sync
                    for key in ["f_bk_val", "f_gp_val", "f_con_val", "f_bill_val", "f_amt_val", "f_rem_val"]:
                        if key in st.session_state: del st.session_state[key]
                    st.rerun()

   # 5. UNIVERSAL SEARCH & RECALL (MANUAL, LABOUR, & OFFICIAL)
  
    with st.expander("🛠️ SEARCH & RECALL FOR CORRECTION"):
        recall_id = st.text_input("Enter ID to edit (Gate Pass / Voucher / Bill No):")
        
        if st.button("🔍 FETCH DATA"):
            # Use the sheet_target determined by your radio button choice
            record, row_idx = search_logs(recall_id, sheet_target)
            
            if record:
                st.session_state.edit_row_idx = row_idx
                
                # --- AUTO-MAPPER WITH KEYERROR PROTECTION ---
                if sheet_target == "MANUAL PASS":
                    # Columns: [SL, BOOK, PASS, CONSIGNEE, BILL, DESC, UNIT, CASH, REMARKS, AMT]
                    if len(record) > 1: st.session_state["f_bk_val"] = str(record[1])
                    if len(record) > 2: st.session_state["f_gp_val"] = str(record[2])
                    if len(record) > 3: st.session_state["f_con_val"] = str(record[3])
                    if len(record) > 4: st.session_state["f_bill_val"] = str(record[4])
                    if len(record) > 8: st.session_state["f_rem_val"] = str(record[8])
                    if len(record) > 9:
                        val = str(record[9]).replace(',','').strip()
                        st.session_state["f_amt_val"] = float(val) if val.replace('.','',1).isdigit() else 0.0

                elif sheet_target == "LABOUR CHARGE":
                    # Columns: [START, END, BOOK, VOUCHER, HOURS, LABOURS, FORK, AMT, FROM, REMARKS]
                    if len(record) > 2: st.session_state["f_bk_val"] = str(record[2])
                    if len(record) > 3: st.session_state["f_bill_val"] = str(record[3])
                    if len(record) > 7: 
                        val = str(record[7]).replace(',','').strip()
                        st.session_state["f_amt_val"] = float(val) if val.replace('.','',1).isdigit() else 0.0
                    if len(record) > 9: st.session_state["f_rem_val"] = str(record[9])

                elif sheet_target == "OFFICIAL REPORT":
                    # Columns: [BOOK, PASS, CONSIGNEE, BILL, REMARKS, AMT, REASON]
                    if len(record) > 0: st.session_state["f_bk_val"] = str(record[0])
                    if len(record) > 1: st.session_state["f_gp_val"] = str(record[1])
                    if len(record) > 2: st.session_state["f_con_val"] = str(record[2])
                    if len(record) > 3: st.session_state["f_bill_val"] = str(record[3])
                    if len(record) > 4: st.session_state["f_rem_val"] = str(record[4])
                    if len(record) > 5:
                        val = str(record[5]).replace(',','').strip()
                        st.session_state["f_amt_val"] = float(val) if val.replace('.','',1).isdigit() else 0.0
                
                st.success(f"✅ {sheet_target} Row {row_idx} Loaded. Edit above!")
                st.rerun()
            else:
                st.error(f"❌ ID '{recall_id}' not found in {sheet_target}.")
with t5:
    st.markdown("### 🕵️‍♂️ CIA Universal Intelligence Search")
    
    # 1. SELECT THE DOCUMENTATION SOURCE
    # The manager can now choose which "corridor" of the warehouse to audit
    doc_source = st.selectbox(
        "Select Documentation Category:", 
        ["LOG", "MANUAL PASS", "LABOUR CHARGE", "OFFICIAL REPORT"]
    )
    
    # 2. FETCH DATA FROM SELECTED SOURCE
    try:
        client_audit = get_gsheet_client()
        audit_sheet = client_audit.open("Falcon_Eye_Database").worksheet(doc_source)
        
        raw_data = audit_sheet.get_all_values()
        
        if raw_data:
            header_row = raw_data[0]
            body_data = raw_data[1:]
            audit_df = pd.DataFrame(body_data, columns=header_row)
            # Remove empty columns
            audit_df = audit_df.loc[:, audit_df.columns != '']
        else:
            audit_df = None
            st.warning(f"The {doc_source} category is currently empty.")
            
    except Exception as e:
        st.error(f"CIA Access Error for {doc_source}: {e}")
        audit_df = None

    # 3. MANAGER COMMAND INTERFACE
    st.divider()
    audit_query = st.text_input(f"Interrogate {doc_source} (Plate, ID, or Details):", placeholder="Search archives...")

    if audit_query and audit_df is not None:
        # Search across all columns
        mask = audit_df.apply(lambda row: row.astype(str).str.contains(audit_query, case=False).any(), axis=1)
        found = audit_df[mask]

        if not found.empty:
            st.success(f"Audit Result: {len(found)} records found in {doc_source}.")
            st.dataframe(found, use_container_width=True)
            
            # Export for the Manager
            csv = found.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📂 Export {doc_source} Audit",
                data=csv,
                file_name=f"FalconEye_{doc_source}_{audit_query}.csv",
                mime='text/csv',
            )
        else:
            st.info(f"No records found in {doc_source} for '{audit_query}'.")
    
    elif audit_df is not None:
        st.write(f"Latest {doc_source} Entries:")
        st.table(audit_df.tail(10))
with t6:
    st.markdown("<h3 style='text-align: center; color: #ADFF2F;'>COMMAND INTERPRETER ⚡</h3>", unsafe_allow_html=True)

    # 1. THE COMPLETE LOGISTICS LANGUAGE LIBRARY (Now correctly indented)
    languages = {
        "Arabic": "ar", "Urdu": "ur", "Hindi": "hi", "Mandarin": "zh-CN",
        "Russian": "ru", "Tagalog": "tl", "Farsi": "fa", "Bengali": "bn",
        "Pashto": "ps", "Malayalam": "ml", "Punjabi": "pa", "Turkish": "tr",
        "French": "fr", "Spanish": "es", "German": "de", "Italian": "it"
    }

    # 2. INTERFACE MODE TOGGLE
    mode = st.radio("Direction:", ["Driver ➡️ Operator", "Operator ➡️ Driver"], horizontal=True)

    target_lang = st.selectbox("Guest Language:", sorted(languages.keys()), index=sorted(languages.keys()).index("Arabic"))
    guest_code = languages[target_lang]

    st.divider()

    # 3. DYNAMIC CAPTURE BASED ON MODE
    if mode == "Driver ➡️ Operator":
        st.info(f"Falcon is listening for {target_lang}...")
        voice_in = speech_to_text(language=guest_code, start_prompt=f"🎤 DRIVER SPEAK ({target_lang})", key="driver_mic")
        src_label, trg_label = target_lang, "English (Operator)"
        system_instruction = (
            f"You are a translation bridge. The user is a driver speaking {target_lang}. "
            "Translate their words into clear, tactical English for a Customs Officer. "
            "Fix grammar and noise artifacts. Output ONLY the English translation."
        )
    else:
        st.success("Falcon is listening for your Command...")
        voice_in = speech_to_text(language='en-US', start_prompt="🎤 OPERATOR SPEAK (English)", key="op_mic")
        src_label, trg_label = "English (Operator)", target_lang
        system_instruction = (
            f"Translate the following English command into {target_lang}. "
            "Tone: Professional and clear. Context: Logistics/Customs. Output ONLY the translation."
        )

    text_in = st.text_input("OR TYPE MESSAGE:", key="two_way_text")
    raw_input = voice_in if voice_in else text_in

    # 4. TWO-WAY EXECUTION
    if raw_input:
        try:
            full_res = "".join([
                chunk.choices[0].delta.content 
                for chunk in falcon_query(f"{system_instruction}\n\nINPUT: {raw_input}", "Global Knowledge") 
                if chunk.choices[0].delta.content
            ])
            
            # --- DISPLAY BOX ---
            st.markdown(f"""
                <div style="background: #1e293b; padding: 25px; border-radius: 15px; border-left: 5px solid #ADFF2F; margin-top: 20px;">
                    <p style="color: #888; font-size: 12px; margin-bottom: 5px;">FROM: {src_label} | TO: {trg_label}</p>
                    <h1 style="color: #ADFF2F; margin: 0; font-size: 32px; font-weight: bold;">{full_res}</h1>
                </div>
            """, unsafe_allow_html=True)

            # --- AUDIO OUTPUT ---
            if mode == "Operator ➡️ Driver":
                from gtts import gTTS
                import io
                tts = gTTS(text=full_res, lang=guest_code)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp.getvalue(), format="audio/mpeg", autoplay=True)
            else:
                st.toast("Direct Translation Received")

        except Exception as e:
            st.error(f"Translation Error: {e}")

    if st.button("CLEAR CONSOLE 🔄", use_container_width=True):
        st.rerun()


#    Digital Toll Gate

with t7:
    st.markdown("<h3 style='text-align: center; color: #ADFF2F;'>FAST-PAY DIGITAL GATEWAY 💳</h3>", unsafe_allow_html=True)
    
    # 1. THE PAYMENT INTERFACE
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            amount_aed = st.number_input("Transaction Amount (AED):", min_value=0, step=10, key="pay_amt")
            v_plate = st.text_input("Vehicle Plate Number:", placeholder="e.g. DXB 12345").upper()
        
        with col2:
            p_type = st.selectbox("Payment Category:", ["Gate Entry Fee", "Overtime Parking", "Customs Fine", "Documentation Fee"])
            method = st.radio("Method:", ["QR Code / Online", "Cash at Desk"], horizontal=True)

    st.divider()

    # 2. GENERATION & LOGGING
    if st.button("🚀 EXECUTE PAYMENT & GENERATE RECEIPT", use_container_width=True):
        if v_plate and amount_aed > 0:
            with st.spinner("Falcon Secure Processing..."):
                # Unique Transaction ID
                tx_id = f"FAL-{datetime.now().strftime('%y%m%d')}-{random.randint(100, 999)}"
                
                # Payload for Google Sheets
                # Format: [Date, TX_ID, Plate, Category, Amount, Method, Status]
                pay_payload = [tx_id, v_plate, p_type, f"AED {amount_aed}", method, "SUCCESS"]
                
                if save_to_google_sheets(st.session_state.current_worker, pay_payload, sheet_name="PAYMENTS"):
                    st.balloons()
                    
                    # 3. THE DIGITAL RECEIPT DISPLAY
                    st.success(f"PAYMENT VERIFIED: {tx_id}")
                    
                    res_col1, res_col2 = st.columns([0.4, 0.6])
                    with res_col1:
                        # Generate a QR for the driver to show or keep
                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=VERIFIED_{tx_id}_{v_plate}"
                        st.image(qr_url, caption="Driver's Digital Pass")
                    
                    with res_col2:
                        st.markdown(f"""
                        **OFFICIAL RECEIPT**
                        - **ID:** {tx_id}
                        - **PLATE:** {v_plate}
                        - **TOTAL:** AED {amount_aed}
                        - **STATUS:** COMPLETED
                        - **AGENT:** {st.session_state.current_worker}
                        """)
                else:
                    st.error("Sheet Error: Ensure a worksheet named 'PAYMENTS' exists in your database.")
        else:
            st.warning("Please enter a valid Plate Number and Amount.")

    # 4. QUICK SEARCH FOR GUARD VERIFICATION
    with st.expander("🔍 VERIFY PREVIOUS PAYMENTS"):
        v_query = st.text_input("Search Plate or TX ID:")
        if v_query:
            found_pay, _ = search_logs(v_query, "PAYMENTS")
            if found_pay:
                st.info(f"Payment Found: {found_pay}")
            else:
                st.error("No record found for this vehicle.")








