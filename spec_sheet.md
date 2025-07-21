Here’s a spec sheet followed by an enhanced and fixed version of your Streamlit app code.

⸻

✅ Streamlit App Specification: Pharmacist Booking

Purpose

Allow surgeries to book a pharmacist for AM/PM shifts via a modern web interface connected to Google Sheets.

⸻

Features
	•	Two pharmacists available per day
	•	AM and PM shifts
	•	No bookings on weekends
	•	Google Sheet backend
	•	Unique booking codes
	•	Dynamic booking buttons
	•	Pop-up form to enter booking details
	•	Instant visual feedback after booking
	•	Auto-refresh page upon booking

⸻

Spreadsheet Fields (Google Sheets)

Column	Description
unique_code	Unique identifier per slot (e.g. 45859-am-1)
Date	Date of the shift
am_pm	Shift timing (am or pm)
pharm	Pharmacist number (1 or 2)
booked	TRUE if booked
surgery	Surgery name
email	Email of requester


⸻

Booking Flow
	1.	User opens app → sees upcoming days
	2.	For each date:
	•	AM and PM buttons shown per pharmacist
	•	Booked shifts show as disabled buttons
	3.	Clicking a button:
	•	Opens a form in a modal/dialog
	•	Input surgery name and email
	4.	Click Submit
	•	Updates Google Sheet
	•	Shows success message
	•	Refreshes app view

⸻

✅ Updated Code (Enhanced UI + Fixes)

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
from st_pages import hide_pages

# Google Sheets setup
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1qpEiHZCqMp8xXBBpoLV2hiMXgQokgN_vigHEhy0lr9A"
CREDS = Credentials.from_service_account_file("google_sheets_secret.json", scopes=SCOPE)
client = gspread.authorize(CREDS)

def get_schedule_data():
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet.get_all_records()

def update_booking(slot, surgery, email):
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    cell = sheet.find(slot['unique_code'])

    if not cell:
        st.error("Could not find the slot in Google Sheet.")
        return

    header = sheet.row_values(1)
    booked_col = header.index("booked") + 1
    surgery_col = header.index("surgery") + 1
    email_col = header.index("email") + 1

    sheet.update_cell(cell.row, booked_col, "TRUE")
    sheet.update_cell(cell.row, surgery_col, surgery)
    sheet.update_cell(cell.row, email_col, email)

def show_booking_dialog(slot):
    with st.form(key=f"form_{slot['unique_code']}"):
        st.markdown(f"**Booking: Pharmacist {slot['pharm']} — {slot['am_pm'].upper()} on {slot['Date']}**")
        surgery = st.text_input("Surgery Name")
        email = st.text_input("Email Address")

        submitted = st.form_submit_button("Submit Booking")

        if submitted:
            if not surgery or not email:
                st.error("All fields are required.")
            else:
                try:
                    update_booking(slot, surgery, email)
                    st.success("Booking saved successfully!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def display_calendar():
    st.set_page_config(page_title="Pharmacist Booking", layout="wide")
    st.title("📅 Pharmacist Appointment Booking")

    df = pd.DataFrame(get_schedule_data())
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    upcoming = df[df['Date'] >= datetime.today()].sort_values(['Date', 'am_pm', 'pharm'])

    for date, daily in upcoming.groupby(df['Date'].dt.date):
        if date.weekday() >= 5:
            continue  # skip weekends

        st.subheader(f"{date.strftime('%A, %d %B %Y')}")

        slots = daily.sort_values(['am_pm', 'pharm'])
        cols = st.columns(2)

        for i, row in slots.iterrows():
            shift = row['am_pm'].upper()
            pharm = row['pharm']
            booked = str(row['booked']).upper() == "TRUE"
            btn_label = f"{shift} — Pharmacist {pharm}"

            col = cols[0] if shift == "AM" else cols[1]

            if booked:
                col.button(btn_label + " (Booked)", key=f"{row['unique_code']}", disabled=True)
            else:
                if col.button(btn_label, key=f"{row['unique_code']}"):
                    st.session_state['selected_slot'] = row

        st.markdown("---")

    if 'selected_slot' in st.session_state:
        st.sidebar.header("Booking Form")
        show_booking_dialog(st.session_state.pop('selected_slot'))

if __name__ == "__main__":
    display_calendar()


⸻

✅ Key Enhancements
	•	Modern two-column layout using st.columns
	•	Sidebar booking form for cleaner UI
	•	st.experimental_rerun() used to refresh after submit
	•	Proper error handling for missing fields or booking failures
	•	Dates cleaned and parsed with errors='coerce' for robustness
	•	Clear button labels showing shift and pharmacist number
	•	Disabled button for already booked slots

⸻

Want me to package this as a deployable app or generate dummy spreadsheet data for testing?
