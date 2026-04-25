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
        
        if sheet_name == "MANUAL PASS":
            # SL NO, DATE, BOOK NO, GP NO...
            row_data = [payload[0], date_s, payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], worker, payload[8], payload[9]]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [worker]
            
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

@st.cache_data(ttl=3600)
def falcon_query(prompt: str, mode: str, chat_history=None) -> str:
    import openai  # Ensure openai is imported
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    
    # FIX: Changed 'NewOpenAI' back to 'OpenAI'
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # BRAIN 1: GATE 4 PROTOCOL (SECURITY FIREWALL)
    if mode == "Gate 4 Protocol":
        manual_context = get_protocol_context()
        sys_rules = f"""
        You are the Falcon Eye Gate 4 Security Firewall. 
        
        STRICT OPERATING PROCEDURES:
        1. Access ONLY the Gate 4 Protocol Manual below.
        2. If the user's question is NOT directly related to Gate 4 procedures, logistics, or security mentioned in the manual, you MUST respond with:
           "ACCESS DENIED: This query is outside Gate 4 Protocol scope. Please toggle to 'Global Knowledge' for non-operational inquiries."
        3. Do NOT answer general questions (weather, history, math, etc.) in this mode.
        4. Synthesize the manual's logic—do not just copy and paste.

        MANUAL CONTEXT:
        {manual_context}
        """
    
    # BRAIN 2: GLOBAL KNOWLEDGE (UNRESTRICTED)
    elif mode == "Global Knowledge":
        sys_rules = "You are a Global Intelligence AI. You have access to all world information."
    
    # BRAIN 3: LOGISTICS AGENT (DOCUMENTATION SPECIALIST)
    elif mode == "Logistics Agent":
        sys_rules = """
        You are the Falcon Eye Logistics Clerk. Your job is to extract data for the Gate 4 Manual Pass Google Sheet.
        Listen to the user's input and extract these 5 specific fields:
        1. BOOK (The book number)
        2. PASS (The gate pass number)
        3. CONSIGNEE (Company name/Receiver)
        4. BILL (Customs bill number)
        5. AMOUNT (The value/charge)

        Return the data in this EXACT format:
        BOOK: [value] | PASS: [value] | CONSIGNEE: [value] | BILL: [value] | AMOUNT: [value]
        
        Use 'N/A' for any missing fields. Do not add any conversational text.
        """
    
    # FALLBACK: TRANSLATOR
    else:
        sys_rules = "Short & clear translator for truck drivers."

    conversation = [{"role": "system", "content": sys_rules}]
    if chat_history: conversation.extend(chat_history[-10:])
    conversation.append({"role": "user", "content": prompt})
    
    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation)
        return completion.choices[0].message.content
    except Exception as e: return f"AI ERROR: {str(e)}"



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
t1, t2, t3, t4, t5, t6 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "📟 LOGISTIC DOCUMENTATION", "🕵️ AUDIT", "🌐 TRANSLATOR"])

with t1:
    st.subheader(f"🔍 {st.session_state.current_chat_id}")
    
    # 1. SCOPE TOGGLE (Logistics Agent Added)
    k_mode = st.radio("Intelligence Scope:", ["Gate 4 Protocol", "Global Knowledge", "Logistics Agent"], horizontal=True)
    
    # 2. CHAT CONTAINER (With height for auto-scroll)
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): 
                st.markdown(message["content"])

    # 3. 🛰️ FALCON LIVE INTERFACE 
    st.divider()
    
    # Custom CSS for the "Glow" effect
    st.markdown("""
        <style>
        .stMicButton > button {
            background-color: #1e293b !important;
            border: 2px solid #ADFF2F !important;
            border-radius: 50% !important;
            width: 80px !important;
            height: 80px !important;
            box-shadow: 0 0 20px rgba(173, 255, 47, 0.2) !important;
            transition: all 0.3s ease !important;
        }
        .stMicButton > button:hover {
            box-shadow: 0 0 40px rgba(173, 255, 47, 0.6) !important;
            transform: scale(1.05);
        }
        </style>
    """, unsafe_allow_html=True)

    col_vibe, col_status = st.columns([0.2, 0.8])
    
    with col_vibe:
        # This is our "Orb" button
        voice_captured = speech_to_text(
            language='en-US', 
            start_prompt="⭕", 
            stop_prompt="⏺️", 
            key='main_chat_mic'
        )
    
    with col_status:
        if voice_captured:
            st.markdown(f"**Live Feed:** *{voice_captured}...*")
        else:
            st.markdown("<p style='color:#ADFF2F; opacity:0.6; margin-top:15px;'>FALCON LIVE: WAITING FOR VOICE...</p>", unsafe_allow_html=True)

    # 4. CHAT INPUT LOGIC (Cleaned & Loop-Fixed)
    query = st.chat_input("Ask Falcon...", key="falcon_main_input")
    final_query = voice_captured if voice_captured else query

    # Only process if we have a new query
    if final_query and st.session_state.get("last_processed_query") != final_query:
        st.session_state.messages.append({"role": "user", "content": final_query})
        st.session_state.last_processed_query = final_query
        
        with st.spinner("Falcon Analyzing..."):
            ans = falcon_query(final_query, k_mode, st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": ans})
        
        # Audio Engine
        try:
            clean_audio_text = ans.replace("*", "").replace("#", "").replace("-", " ")
            tts = gTTS(text=clean_audio_text, lang='en')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.session_state.pending_audio = audio_fp.getvalue()
        except: 
            pass

        st.session_state.all_sessions[st.session_state.current_chat_id] = st.session_state.messages
        save_all_sessions(st.session_state.current_worker, st.session_state.all_sessions)
        st.rerun()

    # 5. AUDIO AUTOPLAY (Must be outside the 'if final_query' block)
    if "pending_audio" in st.session_state:
        st.audio(st.session_state.pending_audio, format="audio/mpeg", autoplay=True)
        # CRITICAL: Delete it immediately so it doesn't trigger on next interaction
        del st.session_state.pending_audio
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
with t3:
    notes = st.text_area("Observations:")
    if st.button("🚀 SAVE LOG") and notes:
        if save_to_google_sheets(st.session_state.current_worker, notes, "LOG"): st.success("✅ Logged.")


with t4:
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

    # 4. THE MAIN FORM
    with st.form("logistics_form", clear_on_submit=True):
        f_date = st.date_input("SELECT DATE:", value=datetime.now(timezone(timedelta(hours=4))))
        formatted_date = f_date.strftime("%d-%m-%Y")
        
        if doc_type == "Manual Gate Pass":
            c1, c2, c3 = st.columns(3)
            f_sl = c1.text_input("SL NO", value=next_sl).upper()
            f_bk = c2.text_input("BOOK NO").upper()
            f_gp = c3.text_input("GATE PASS NO", value=next_gp).upper()
            f_con = st.text_input("CONSIGNEE", value=smart_con).upper()
            f_bill = st.text_input("CUSTOMS BILL NO").upper()
            f_desc = st.text_area("DESCRIPTION").upper()
            c4, c5, c6 = st.columns(3)
            f_unit = c4.text_input("UNIT").upper()
            f_cash = c5.text_input("CASH RECEIPT NO").upper()
            f_amt = c6.number_input("AMOUNT", min_value=0.0, format="%.2f")
            f_rem = st.text_input("REMARKS").upper()
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

        # --- DYNAMIC ACTION BUTTONS ---
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
                    st.rerun()

    # 5. RECALL SECTION
    with st.expander("🛠️ SEARCH & RECALL FOR CORRECTION"):
        recall_id = st.text_input("Enter ID to edit:")
        if st.button("🔍 FETCH DATA"):
            record, row_idx = search_logs(recall_id, "MANUAL PASS")
            if record:
                st.session_state.edit_row_idx = row_idx
                st.success(f"Loaded Row {row_idx}. Form updated above.")
                st.json(record)
                st.rerun()
            else:
                st.error("❌ Not found.")

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

    # 1. TACTICAL LANGUAGES
    languages = {
        "Arabic": "ar", "Bengali": "bn", "Chinese": "zh-CN", "English": "en", 
        "Hindi": "hi", "Malayalam": "ml", "Pashto": "ps", "Punjabi": "pa", 
        "Russian": "ru", "Spanish": "es", "Tagalog": "tl", "Tamil": "ta", "Urdu": "ur"
    }

    # 2. INTERFACE MODE TOGGLE
    # This switches the "Brain" direction
    mode = st.radio("Direction:", ["Driver ➡️ Operator", "Operator ➡️ Driver"], horizontal=True)
    
    target_lang = st.selectbox("Guest Language:", sorted(languages.keys()), index=sorted(languages.keys()).index("Arabic"))
    guest_code = languages[target_lang]

    st.divider()

    # 3. DYNAMIC CAPTURE BASED ON MODE
    if mode == "Driver ➡️ Operator":
        st.info(f"Falcon is listening for {target_lang}...")
        voice_in = speech_to_text(language=guest_code, start_prompt=f"🎤 DRIVER SPEAK ({target_lang})", key="driver_mic")
        src_label = target_lang
        trg_label = "English (Operator)"
        system_instruction = f"The user is speaking {target_lang} with a heavy accent in a noisy logistics environment. Repair the grammar and translate it into clear, tactical English for a customs officer."
    else:
        st.success("Falcon is listening for your Command...")
        voice_in = speech_to_text(language='en-US', start_prompt="🎤 OPERATOR SPEAK (English)", key="op_mic")
        src_label = "English (Operator)"
        trg_label = target_lang
        system_instruction = f"Translate my English command into perfect {target_lang}. Ensure the tone is professional and clear for a driver. Output ONLY the translation."

    text_in = st.text_input("OR TYPE MESSAGE:", key="two_way_text")
    raw_input = voice_in if voice_in else text_in

    # 4. TWO-WAY EXECUTION
    if raw_input:
        with st.spinner("Falcon Interpreting..."):
            # The "Brain" Layer: Repair + Translate
            repair_prompt = f"{system_instruction}\n\nINPUT: {raw_input}"
            result = falcon_query(repair_prompt, "Global Knowledge")
            
            # --- DISPLAY BOX ---
            st.markdown(f"""
                <div style="background: #1e293b; padding: 25px; border-radius: 15px; border-left: 5px solid #ADFF2F; margin-top: 20px;">
                    <p style="color: #888; font-size: 12px; margin-bottom: 5px;">FROM: {src_label} | TO: {trg_label}</p>
                    <h1 style="color: #ADFF2F; margin: 0; font-size: 38px; line-height: 1.2;">{result}</h1>
                </div>
            """, unsafe_allow_html=True)

            # --- AUDIO OUTPUT (Only for the Driver) ---
            if mode == "Operator ➡️ Driver":
                try:
                    tts = gTTS(text=result, lang=guest_code)
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp.getvalue(), format="audio/mpeg", autoplay=True)
                except:
                    pass
            else:
                # For the operator (you), we just show the text clearly so you can read it fast
                st.toast("Translation Ready")

    if st.button("CLEAR CONSOLE 🔄", use_container_width=True):
        st.rerun()








