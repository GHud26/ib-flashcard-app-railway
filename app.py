import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit.components.v1 import html
import base64
import os
import html as ihtml

# --- Page config ---
st.set_page_config(page_title="BBA CMC Finance Flashcards", layout="wide", initial_sidebar_state="auto")

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gsheet_client():
    # Define scope
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # Try Streamlit secrets first (local)
    if "gcp_service_account" in st.secrets:
        service_account_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    # Otherwise try environment variable (Railway)
    elif os.getenv("GOOGLE_CREDENTIALS"):
        import json
        creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        raise Exception(
            "No Google service account credentials found! "
            "Add them to .streamlit/secrets.toml locally or as GOOGLE_CREDENTIALS env variable on Railway."
        )

    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_and_clean_data(_client):  # Added leading underscore
    sheet = _client.open("IB_QA_Bank").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.astype(str).str.strip().str.lower()
    return df

@st.cache_data
def add_flashcard_to_sheet(_client, new_category, new_difficulty, new_question, new_answer): # Added leading underscore
    sheet = _client.open("IB_QA_Bank").sheet1
    col_b = sheet.col_values(2)  # Column B = Category
    next_row = len(col_b) + 1
    new_row = ["", new_category, new_difficulty, new_question, new_answer]
    sheet.insert_row(new_row, next_row)
    return True

# --- Initialize Google Sheets Client ---
client = get_gsheet_client()

# --- Load Data ---
df = load_and_clean_data(client)

# --- Session state setup ---
if "card_index" not in st.session_state:
    st.session_state.card_index = 0
if "shown_answers" not in st.session_state:
    st.session_state.shown_answers = {}
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "admin_just_logged_in" not in st.session_state:
    st.session_state.admin_just_logged_in = False
if "filtered_df" not in st.session_state:
    st.session_state.filtered_df = pd.DataFrame()
if "prev_filters" not in st.session_state:
    st.session_state.prev_filters = (tuple(), tuple(), False)

# --- Admin Login Sidebar ---
def admin_login_sidebar():
    st.sidebar.markdown("### 🔐 Admin Login")
    if not st.session_state.is_admin:
        admin_code = st.sidebar.text_input("Enter admin code:", type="password", key="admin_code_input")
        if st.sidebar.button("Submit", key="admin_submit_button"):
            if admin_code == "320320":
                st.session_state.is_admin = True
                st.session_state.admin_just_logged_in = True
                st.rerun()
            else:
                st.sidebar.error("Incorrect code.")
    if st.session_state.admin_just_logged_in:
        st.sidebar.success("✅ Admin access granted!")
        st.session_state.admin_just_logged_in = False

admin_login_sidebar()

# --- Callback functions ---
def toggle_answer():
    st.session_state.shown_answers[st.session_state.card_index] = not st.session_state.shown_answers.get(st.session_state.card_index, False)

def go_next():
    if st.session_state.filtered_df is not None and not st.session_state.filtered_df.empty:
        st.session_state.card_index = min(len(st.session_state.filtered_df) - 1, st.session_state.card_index + 1)

def go_previous():
    st.session_state.card_index = max(0, st.session_state.card_index - 1)

# --- Custom styles ---
st.markdown("""
    <style>
        .flashcard {
            border: 1px solid #1976d2;
            border-radius: 8px;
            padding: 1.5rem;
            background-color: white;
            margin-bottom: 2rem;
        }
        .category-label {
            display: inline-block;
            background-color: #f0f4ff;
            color: #1976d2;
            border-radius: 4px;
            padding: 0.2rem 0.6rem;
            font-size: 0.8rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        .question {
            font-weight: 600;
            font-size: 1rem;
            color: #000;
            margin-bottom: 0.8rem;
        }
        .answer {
            font-size: 1rem;
            color: #333;
            margin-top: 1rem;
        }
        .top-right-logo {
            position: absolute;
            top: 10px;
            right: 15px;
            z-index: 999;
        }
    </style>
""", unsafe_allow_html=True)

# --- Logo ---
logo_path = "GWS_Blue_Text_Transparent Logo.png"

@st.cache_data
def get_image_base64_cached(image_path):
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

logo_base64 = get_image_base64_cached(logo_path)
if logo_base64:
    st.markdown(f"""
        <div class="top-right-logo">
            <img src="data:image/png;base64,{logo_base64}" width="200">
        </div>
    """, unsafe_allow_html=True)

# --- Title & Intro ---
st.title("BBA CMC Finance Interview Flashcards")
st.markdown("Hi Coaches! Enjoy this resource for you to help students with technical interviews. Use the filters below to customize your study session.")

# --- Filters ---
categories = sorted(df['category'].dropna().unique())
difficulties = sorted(df['difficulty'].dropna().unique())

col1, col2 = st.columns(2)
with col1:
    selected_categories = st.multiselect("Filter by Category:", options=categories, default=categories)
with col2:
    selected_difficulties = st.multiselect("Filter by Difficulty:", options=difficulties, default=difficulties)

# --- Filtered Data ---
def filter_dataframe(df, selected_categories, selected_difficulties, shuffle):
    filtered_df = df[
        df['category'].isin(selected_categories) &
        df['difficulty'].isin(selected_difficulties)
    ].reset_index(drop=True)
    if shuffle:
        filtered_df = filtered_df.sample(frac=1).reset_index(drop=True)
    return filtered_df

shuffle = st.checkbox("Randomize Card Order", key="shuffle_toggle", value=st.session_state.get("shuffle_toggle", False), on_change=lambda: st.session_state.pop("card_index", None))

if (tuple(selected_categories), tuple(selected_difficulties), shuffle) != st.session_state.get("prev_filters"):
    st.session_state.filtered_df = filter_dataframe(df, selected_categories, selected_difficulties, shuffle)
    st.session_state.card_index = 0
    st.session_state.shown_answers = {}
    st.session_state.prev_filters = (tuple(selected_categories), tuple(selected_difficulties), shuffle)

filtered_df = st.session_state.filtered_df

if filtered_df.empty:
    st.warning("No flashcards match the selected filters.")
    st.stop()

st.markdown(f"### Showing {len(filtered_df)} Flashcards")

# --- Add New Flashcard UI (Admins Only) ---
if st.session_state.is_admin:
    with st.expander("➕ Add a New Flashcard"):
        with st.form("new_flashcard_form"):
            new_question = st.text_area("Question")
            new_answer = st.text_area("Answer")
            new_category = st.selectbox("Select Category", categories)
            new_difficulty = st.selectbox("Select Difficulty", difficulties)
            submitted = st.form_submit_button("Add Flashcard")

            if submitted:
                if new_question and new_answer and new_category and new_difficulty:
                    success = add_flashcard_to_sheet(client, new_category, new_difficulty, new_question, new_answer)
                    if success:
                        st.success("Flashcard added successfully! Please refresh to view.")
                        # Consider clearing the form or reloading data
                    else:
                        st.error("Failed to add flashcard.")
                else:
                    st.error("Please complete all fields before submitting.")

# --- View Mode ---
view_mode = st.radio("Select View Mode:", ["List View", "Individual Card View"], index=1, horizontal=True)

if view_mode == "List View":
    for idx, row in filtered_df.iterrows():
        escaped_answer = ihtml.escape(row['answer']).replace('\n', '<br>')
        st.markdown(f"""
            <div class="flashcard">
                <div class="category-label">{row['category']}</div>
                <div class="question">{row['question']}</div>
                <div class='answer'><strong>Answer</strong><br>{escaped_answer}</div>
            </div>
        """, unsafe_allow_html=True)

else:
    if not filtered_df.empty:
        st.session_state.card_index = min(max(0, st.session_state.card_index), len(filtered_df) - 1)
        card_id = st.session_state.card_index
        row = filtered_df.iloc[card_id]

        if card_id not in st.session_state.shown_answers:
            st.session_state.shown_answers[card_id] = False

        st.markdown("#### Navigate Cards:")
        with st.container():
            escaped_answer = ihtml.escape(row['answer']).replace('\n', '<br>')
            st.markdown(f"""
                <div class="flashcard">
                    <div class="category-label">{row['category']}</div>
                    <div class="question">{row['question']}</div>
                    {f"<div class='answer'><strong>Answer</strong><br>{escaped_answer}</div>" if st.session_state.shown_answers[card_id] else ""}
                </div>
            """, unsafe_allow_html=True)

            st.button(
                "Hide Answer" if st.session_state.shown_answers[card_id] else "Show Answer",
                key="toggle_btn",
                on_click=toggle_answer
            )

        nav_col1, nav_spacer, nav_col2 = st.columns([1, 5, 1])
        with nav_col1:
            st.button("« Previous Question", on_click=go_previous, key="prev_btn", disabled=st.session_state.card_index == 0)
        with nav_col2:
            st.button("Next Question »", on_click=go_next, key="next_btn", disabled=st.session_state.card_index == len(filtered_df) - 1 if not filtered_df.empty else True)
    else:
        st.info("No cards to display in Individual Card View based on current filters.")

# --- Footer ---
st.markdown("""
<br><hr style="margin-top: 50px; margin-bottom: 10px;">
<div style='text-align: center; color: gray; font-size: 14px;'>
    Created by <a href=\"https://www.linkedin.com/in/granthuddleston\" target=\"_blank\">Grant Huddleston</a> BBA '26
</div>
""", unsafe_allow_html=True)