import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# Google Sheet details
SPREADSHEET_ID = "1m6fJqggnvRJ9u-Hk5keUaPZ_gJHrd4GZmowE3j3nH-c"
SHEET_NAME = "Sheet1"

# Authenticate with Google Sheets using st.secrets
@st.cache_resource
def get_gspread_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gsheets"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error authenticating with Google Sheets: {e}")
        st.stop()

client = get_gspread_client()

def get_schedule_data():
    """Fetch pharmacist schedule data from Google Sheet"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"An error occurred while reading data from Google Sheet: {e}")
        return pd.DataFrame()

def update_booking(slot, surgery, email):
    """Update the Google Sheet with booking details"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        # Find the row based on unique_code
        cell = sheet.find(slot['unique_code'])

        if cell:
            # Get all headers to find column indices dynamically
            headers = sheet.row_values(1)
            booked_col_idx = headers.index('booked') + 1
            surgery_col_idx = headers.index('surgery') + 1
            email_col_idx = headers.index('email') + 1

            # Update cells
            sheet.update_cell(cell.row, booked_col_idx, "TRUE")
            sheet.update_cell(cell.row, surgery_col_idx, surgery)
            sheet.update_cell(cell.row, email_col_idx, email)
        else:
            st.error("Could not find the slot in the Google Sheet.")
    except Exception as e:
        st.error(f"An error occurred while updating the booking in Google Sheet: {e}")

def show_admin_panel(df):
    st.sidebar.header("Manage Availability")
    with st.sidebar.form("availability_form"):
        st.write("Select dates and pharmacists to mark as available.")

        today = datetime.today()
        # Calculate two months ahead
        two_months_ahead = today + timedelta(days=60) # Approximately 2 months
        dates_to_show = []
        current_date = today
        while current_date <= two_months_ahead:
            dates_to_show.append(current_date)
            current_date += timedelta(days=1)

        # Create a dictionary to easily check current availability
        current_availability = {}
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date # Ensure date comparison works
            for _, row in df.iterrows():
                current_availability[(row['Date'], row['pharm'])] = True

        selected_slots = []

        for date in dates_to_show:
            is_weekend = date.weekday() >= 5
            date_str = date.strftime('%A, %d %B')

            if is_weekend:
                st.markdown(f"**{date_str} (Weekend)**")
            else:
                st.markdown(f"**{date_str}**")

            cols = st.columns(2)
            for pharm in [1, 2]:
                checkbox_key = f"avail_{date.strftime('%Y%m%d')}_{pharm}"

                # Pre-fill checkbox based on current availability
                initial_value = current_availability.get((date.date(), pharm), False)

                checked = cols[pharm-1].checkbox(
                    f"Pharmacist {pharm}",
                    value=initial_value,
                    key=checkbox_key,
                    disabled=is_weekend # Disable checkboxes for weekends
                )

                # If not a weekend and checked, add to selected_slots
                if not is_weekend and checked:
                    selected_slots.append({
                        "date": date,
                        "pharm": pharm
                    })

        submitted = st.form_submit_button("Update Availability")
        if submitted:
            # Create a completely new DataFrame based on selected_slots
            new_df_data = []
            for slot in selected_slots:
                for shift in ['am', 'pm']:
                    unique_code = f"{int(slot['date'].timestamp())}-{shift}-{slot['pharm']}"
                    new_df_data.append({
                        "unique_code": unique_code,
                        "Date": slot['date'].strftime('%Y-%m-%d'),
                        "am_pm": shift,
                        "pharm": slot['pharm'],
                        "booked": "FALSE", # All newly added slots are unbooked
                        "surgery": "",
                        "email": ""
                    })

            # Overwrite the Google Sheet with the new availability
            try:
                sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
                sheet.clear()
                # Convert DataFrame to list of lists, handling potential NaN values
                # Ensure all values are strings for gspread
                data_to_write = [list(new_df_data[0].keys())] + [[str(val) for val in row.values()] for row in new_df_data]
                sheet.update(data_to_write)
                st.success("Availability updated in Google Sheet!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating availability in Google Sheet: {e}")

@st.dialog("Booking Details")
def show_booking_dialog(slot):
    shift = slot['am_pm'].upper()
    pharm = slot['pharm']
    btn_label = f"09:00 - 12:30 — Pharmacist {pharm}" if shift == "AM" else f"14:00 - 17:30 — Pharmacist {pharm}"

    st.markdown(f"**Booking: Pharmacist {pharm} — {shift} on {pd.to_datetime(slot['Date']).strftime('%Y-%m-%d')}**")
    with st.form(key=f"form_dialog_{slot['unique_code']}"):
        surgery = st.text_input("Surgery Name", key=f"surgery_dialog_{slot['unique_code']}")
        email = st.text_input("Email Address", key=f"email_dialog_{slot['unique_code']}")

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("Submit Booking")
        cancel_button = col2.form_submit_button("Cancel")

        if submitted:
            if not surgery or not email:
                st.error("All fields are required.")
            else:
                update_booking(slot, surgery, email)
                st.success("Booking saved successfully!")
                st.rerun() # Rerun to close dialog and refresh main app

        if cancel_button:
            st.rerun() # Rerun to close dialog

def display_calendar():
    st.set_page_config(page_title="Pharma-Cal Brompton Heatlh PCN", layout="centered")
    st.title(":material/pill: Request a Pharmacist Session")

    # --- Admin Sidebar ---
    st.sidebar.title(":material/settings: Admin Panel")
    password = st.sidebar.text_input("Password", type="password")

    df = get_schedule_data()

    if password == "super user":
        show_admin_panel(df)
    elif password != "":
        st.sidebar.error("Incorrect password")

    # --- Main Calendar Display ---
    if df.empty:
        st.info("No pharmacist shifts have been scheduled yet. Contact admin.")
        return

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    upcoming = df[df['Date'] >= datetime.today()].sort_values(['Date', 'am_pm', 'pharm'])

    if upcoming.empty:
        st.info("No upcoming shifts available.")
        return

    for date, daily in upcoming.groupby(df['Date'].dt.date):
        if date.weekday() >= 5:
            continue

        st.subheader(f"{date.strftime('%A, %d %B %Y')}")
        slots = daily.sort_values(['am_pm', 'pharm'])
        cols = st.columns(2)

        for i, row in slots.iterrows():
            shift = row['am_pm'].upper()
            pharm = row['pharm']
            booked = str(row['booked']).upper() == "TRUE"

            # Modify btn_label based on shift
            if shift == "AM":
                btn_label = f"09:00 - 12:30 — Pharmacist {pharm}"
            elif shift == "PM":
                btn_label = f"14:00 - 17:30 — Pharmacist {pharm}"
            else:
                btn_label = f"{shift} — Pharmacist {pharm}" # Fallback

            unique_key = f"{row['unique_code']}_{i}"

            col = cols[0] if shift == "AM" else cols[1]

            if booked:
                col.button(btn_label + " (Booked)", key=unique_key, disabled=True)
            else:
                if col.button(btn_label, key=unique_key):
                    show_booking_dialog(row.to_dict()) # Call the decorated dialog function

        st.markdown("---")

if __name__ == "__main__":
    display_calendar()
