import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit.components.v1 import html
import base64
import os
import html as ihtml

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gspread_key.json", scope)
client = gspread.authorize(creds)
sheet = client.open("IB_QA_Bank").sheet1

# --- Load Data ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- Clean column names ---
df.columns = df.columns.astype(str).str.strip().str.lower()

# --- Page config ---
st.set_page_config(page_title="BBA CMC Finance Flashcards", layout="wide", initial_sidebar_state="auto")

# --- Session state setup ---
if "card_index" not in st.session_state:
    st.session_state.card_index = 0
if "shown_answers" not in st.session_state:
    st.session_state.shown_answers = {}
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "admin_just_logged_in" not in st.session_state:
    st.session_state.admin_just_logged_in = False

# --- Admin Login Sidebar ---
def admin_login_sidebar():
    st.sidebar.markdown("### 🔐 Admin Login")
    if not st.session_state.is_admin:
        admin_code = st.sidebar.text_input("Enter admin code:", type="password")
        if st.sidebar.button("Submit"):
            if admin_code == "320320":
                st.session_state.is_admin = True
                st.session_state.admin_just_logged_in = True
            else:
                st.sidebar.error("Incorrect code.")
    if st.session_state.admin_just_logged_in:
        st.sidebar.success("✅ Admin access granted!")
        st.session_state.admin_just_logged_in = False

admin_login_sidebar()

# --- Callback functions ---
def toggle_answer():
    card_id = st.session_state.card_index
    st.session_state.shown_answers[card_id] = not st.session_state.shown_answers.get(card_id, False)

def go_next():
    st.session_state.card_index = min(len(filtered_df) - 1, st.session_state.card_index + 1)

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
logo_path = os.path.expanduser("~/Flashcard_/GWS_Blue_Text_Transparent Logo.png")

def get_image_base64(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

if os.path.exists(logo_path):
    logo_base64 = get_image_base64(logo_path)
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
filtered_df = df[
    df['category'].isin(selected_categories) &
    df['difficulty'].isin(selected_difficulties)
].reset_index(drop=True)

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
                    sheet.append_row([new_question, new_answer, new_category, new_difficulty])
                    st.success("Flashcard added successfully! Please refresh to view.")
                else:
                    st.error("Please complete all fields before submitting.")

# --- Shuffle ---
shuffle = st.checkbox("Randomize Card Order", key="shuffle_toggle", value=False)

# --- Update filtered data on changes ---
if "filtered_df" not in st.session_state or st.session_state.get("prev_filters") != (tuple(selected_categories), tuple(selected_difficulties), shuffle):
    filtered = df[
        df['category'].isin(selected_categories) &
        df['difficulty'].isin(selected_difficulties)
    ].reset_index(drop=True)

    if shuffle:
        filtered = filtered.sample(frac=1).reset_index(drop=True)

    st.session_state.filtered_df = filtered
    st.session_state.card_index = 0
    st.session_state.shown_answers = {}
    st.session_state.prev_filters = (tuple(selected_categories), tuple(selected_difficulties), shuffle)

filtered_df = st.session_state.filtered_df

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
        st.button("« Previous Question", on_click=go_previous, key="prev_btn")
    with nav_col2:
        st.button("Next Question »", on_click=go_next, key="next_btn")

# --- Footer ---
st.markdown("""
<br><hr style="margin-top: 50px; margin-bottom: 10px;">
<div style='text-align: center; color: gray; font-size: 14px;'>
    Created by <a href=\"https://www.linkedin.com/in/granthuddleston\" target=\"_blank\">Grant Huddleston</a> BBA '26
</div>
""", unsafe_allow_html=True)
