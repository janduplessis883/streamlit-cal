import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time

# Google Sheet details
SPREADSHEET_ID = "1m6fJqggnvRJ9u-Hk5keUaPZ_gJHrd4GZmowE3j3nH-c"
SHEET_NAME = "Sheet1"
SHEET_NAME_SURGERIES = "Sheet2"
SHEET_NAME_PHARMACISTS = "Sheet3"


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
        with st.spinner("Fetching schedule..."):
            data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"An error occurred while reading data from Google Sheet: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600) # Cache for 1 hour
def get_surgeries_data():
    """Fetch saved surgeries data from Google Sheet (Sheet2)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_SURGERIES)
        with st.spinner("Fetching surgeries data..."):
            data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"Worksheet '{SHEET_NAME_SURGERIES}' not found. Creating it...")
        # Create the worksheet if it doesn't exist
        sheet = client.open_by_key(SPREADSHEET_ID).add_worksheet(SHEET_NAME_SURGERIES, rows=1, cols=2)
        sheet.update([["surgery", "email"]]) # Add headers
        return pd.DataFrame(columns=["surgery", "email"])
    except Exception as e:
        st.error(f"An error occurred while reading surgeries data from Google Sheet: {e}")
        return pd.DataFrame()

def add_surgery_data(surgery_name, email_address):
    """Add a new surgery and email to Google Sheet (Sheet2)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_SURGERIES)
        # Check if surgery already exists
        existing_data = sheet.get_all_records()
        for row in existing_data:
            if row.get("surgery") == surgery_name and row.get("email") == email_address:
                st.info(f"Surgery '{surgery_name}' with email '{email_address}' already exists.")
                return

        sheet.append_row([surgery_name, email_address])
        st.success(f"Surgery '{surgery_name}' added successfully!")
        get_surgeries_data.clear() # Clear cache to refresh data
    except Exception as e:
        st.error(f"An error occurred while adding surgery data to Google Sheet: {e}")

def delete_surgery_data(surgery_name, email_address):
    """Delete a surgery entry from Google Sheet (Sheet2)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_SURGERIES)
        # Find the row index of the surgery to delete
        # gspread's find method returns the Cell object, which has a 'row' attribute
        cell = sheet.find(surgery_name)
        if cell:
            # Verify email matches to prevent accidental deletion if surgery names are not unique
            row_values = sheet.row_values(cell.row)
            # Assuming 'surgery' is in column 1 and 'email' in column 2
            if len(row_values) >= 2 and row_values[1] == email_address:
                sheet.delete_rows(cell.row)
                st.success(f"Surgery '{surgery_name}' deleted successfully!")
                get_surgeries_data.clear() # Clear cache to refresh data
            else:
                st.error(f"Could not delete surgery: Email mismatch for '{surgery_name}'.")
        else:
            st.error(f"Surgery '{surgery_name}' not found.")
    except Exception as e:
        st.error(f"An error occurred while deleting surgery data from Google Sheet: {e}")

@st.cache_data(ttl=1200) # Cache for 1 hour
def get_pharmacists_data():
    """Fetch saved pharmacists data from Google Sheet (Sheet3)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_PHARMACISTS)
        with st.spinner("Fetching pharmacists data..."):
            data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"Worksheet '{SHEET_NAME_PHARMACISTS}' not found. Creating it...")
        # Create the worksheet if it doesn't exist
        sheet = client.open_by_key(SPREADSHEET_ID).add_worksheet(SHEET_NAME_PHARMACISTS, rows=1, cols=1)
        sheet.update([["Name", "Email"]]) # Add header
        return pd.DataFrame(columns=["Name", "Emnail"])
    except Exception as e:
        st.error(f"An error occurred while reading pharmacists data from Google Sheet: {e}")
        return pd.DataFrame()

def add_pharmacist_data(pharmacist_name, pharmacist_email):
    """Add a new pharmacist to Google Sheet (Sheet3)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_PHARMACISTS)
        # Check if pharmacist already exists
        existing_data = sheet.get_all_records()
        for row in existing_data:
            if row.get("Name") == pharmacist_name and row.get("Email") == pharmacist_email:
                st.info(f"Pharmacist '{pharmacist_name}' with email '{pharmacist_email}' already exists.")
                return

        sheet.append_row([pharmacist_name, pharmacist_email])
        st.success(f"Pharmacist '{pharmacist_name}' added successfully!")
        get_pharmacists_data.clear() # Clear cache to refresh data
    except Exception as e:
        st.error(f"An error occurred while adding pharmacist data to Google Sheet: {e}")

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
            with st.spinner("Updating booking..."):
                sheet.update_cell(cell.row, booked_col_idx, "TRUE")
                sheet.update_cell(cell.row, surgery_col_idx, surgery)
                sheet.update_cell(cell.row, email_col_idx, email)
        else:
            st.error("Could not find the slot in the Google Sheet.")
    except Exception as e:
        st.error(f"An error occurred while updating the booking in Google Sheet: {e}")

def show_admin_panel(df):

    admin_tab = st.sidebar.radio("Admin Options", ["Manage Availability", "Manage Surgeries", "Manage Pharmacists"])

    if admin_tab == "Manage Availability":
        st.sidebar.subheader("Manage Availability")
        num_weeks = st.sidebar.slider("Number of weeks to show", 1, 12, 2)

        pharmacists_df = get_pharmacists_data()
        pharmacist_names = ["None"] + sorted(pharmacists_df["Name"].tolist()) if not pharmacists_df.empty else ["None"]

        with st.sidebar.form("availability_form"):
            st.write("Select dates and pharmacists to mark as available.")

            today = datetime.today()
            end_date = today + timedelta(weeks=num_weeks)
            dates_to_show = []
            current_date = today
            while current_date <= end_date:
                dates_to_show.append(current_date)
                current_date += timedelta(days=1)

            current_availability = {}
            if not df.empty:
                df_copy = df.copy()
                if 'slot_index' not in df_copy.columns:
                    df_copy['slot_index'] = df_copy.groupby(['Date', 'am_pm']).cumcount()
                df_copy['Date'] = pd.to_datetime(df_copy['Date']).dt.date
                for _, row in df_copy.iterrows():
                    key = (row['Date'], row['slot_index'], row['am_pm'])
                    current_availability[key] = {
                        'booked': str(row.get('booked', 'FALSE')).upper() == "TRUE",
                        'surgery': row.get('surgery', ''),
                        'email': row.get('email', ''),
                        'unique_code': row.get('unique_code', ''),
                        'pharmacist_name': row.get('pharmacist_name', 'None')
                    }

            selected_slots = []

            for date in dates_to_show:
                is_weekend = date.weekday() >= 5
                date_str = date.strftime('%A, %d %B')

                if is_weekend:
                    st.markdown(f"**{date_str} (Weekend)**")
                else:
                    st.markdown(f"**{date_str}**")

                    cols = st.columns(2)
                    for i, col in enumerate(cols):
                        with col:
                            for shift_type in ['am', 'pm']:
                                slot_key = f"avail_{date.strftime('%Y%m%d')}_{shift_type}_{i}"

                                lookup_key = (date.date(), i, shift_type)
                                slot_info = current_availability.get(lookup_key, {'booked': False, 'pharmacist_name': 'None'})
                                is_booked = slot_info['booked']

                                default_pharmacist = slot_info.get('pharmacist_name', 'None')
                                if default_pharmacist not in pharmacist_names:
                                    default_pharmacist = "None"

                                selected_pharmacist = st.selectbox(
                                    f"{shift_type.upper()} Slot",
                                    pharmacist_names,
                                    index=pharmacist_names.index(default_pharmacist),
                                    key=slot_key,
                                    disabled=is_weekend or is_booked
                                )

                                if not is_weekend and selected_pharmacist != "None":
                                    selected_slots.append({
                                        "date": date,
                                        "am_pm": shift_type,
                                        "pharmacist_name": selected_pharmacist,
                                        "booked_info": slot_info,
                                        "pharm_id": i
                                    })

            submitted = st.form_submit_button("Update Availability")
            if submitted:
                new_df_data = []
                for slot in selected_slots:
                    was_booked = slot['booked_info']['booked']
                    booked_surgery = slot['booked_info']['surgery'] if was_booked else ""
                    booked_email = slot['booked_info']['email'] if was_booked else ""

                    new_df_data.append({
                        "unique_code": f"{int(slot['date'].timestamp())}-{slot['am_pm']}-{slot['pharm_id']}",
                        "Date": slot['date'].strftime('%Y-%m-%d'),
                        "am_pm": slot['am_pm'],
                        "booked": "TRUE" if was_booked else "FALSE",
                        "surgery": booked_surgery,
                        "email": booked_email,
                        "pharmacist_name": slot['pharmacist_name'],
                        "slot_index": slot['pharm_id']
                    })

                try:
                    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
                    with st.spinner("Updating availability..."):
                        sheet.clear()
                        if new_df_data:
                            headers = list(new_df_data[0].keys())
                            data_to_write = [headers] + [[str(row.get(h, '')) for h in headers] for row in new_df_data]
                            sheet.update(data_to_write)
                    st.success("Availability updated in Google Sheet!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating availability in Google Sheet: {e}")

    elif admin_tab == "Manage Surgeries":
        st.sidebar.subheader("Add New Surgery")
        with st.sidebar.form("add_surgery_form", clear_on_submit=True):
            new_surgery_name = st.text_input("Surgery Name")
            new_surgery_email = st.text_input("Email Address")
            add_surgery_submitted = st.form_submit_button("Add Surgery")

            if add_surgery_submitted:
                if new_surgery_name and new_surgery_email:
                    add_surgery_data(new_surgery_name, new_surgery_email)
                else:
                    st.error("Both surgery name and email are required.")

        st.sidebar.subheader("Existing Surgeries")
        surgeries_df = get_surgeries_data()
        if not surgeries_df.empty:
            for idx, row in surgeries_df.iterrows():
                col1, col2 = st.sidebar.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"{idx + 1}. **{row['surgery']}**: {row['email']}")
                with col2:
                    if st.button(":material/delete:", key=f"delete_surgery_{idx}"):
                        delete_surgery_data(row['surgery'], row['email'])
                        st.rerun()
        else:
            st.sidebar.info("No surgeries saved yet.")

    elif admin_tab == "Manage Pharmacists":
        st.sidebar.subheader("Add New Pharmacist")
        with st.sidebar.form("add_pharmacist_form", clear_on_submit=True):
            new_pharmacist_name = st.text_input("Pharmacist Name (e.g., John Doe)")
            new_pharmacist_email = st.text_input("Pharmacist Email")
            add_pharmacist_submitted = st.form_submit_button("Add Pharmacist")

            if add_pharmacist_submitted:
                if new_pharmacist_name and new_pharmacist_email:
                    add_pharmacist_data(new_pharmacist_name, new_pharmacist_email)
                else:
                    st.error("Pharmacist name is required.")

        st.sidebar.subheader("Existing Pharmacists")
        pharmacists_df = get_pharmacists_data()
        if not pharmacists_df.empty:
            for idx, row in pharmacists_df.iterrows():
                col1, col2 = st.sidebar.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"{idx + 1}. **{row['Name']}**<br>{row['Email']}", unsafe_allow_html=True)
                with col2:
                    if st.button(":material/delete:", key=f"delete_pharmacist_{idx}"):
                        delete_pharmacist_data(row['Name'], row['Email'])
                        st.rerun()
        else:
            st.sidebar.info("No pharmacists saved yet.")

@st.dialog("Booking Details")
def show_booking_dialog(slot):
    shift = slot['am_pm'].upper()
    pharmacist_name = slot.get('pharmacist_name', 'Pharmacist') # Default to 'Pharmacist' if name is not available

    st.markdown(f"**Booking: {pharmacist_name} — {shift} on {pd.to_datetime(slot['Date']).strftime('%Y-%m-%d')}**")

    surgeries_df = get_surgeries_data()
    surgery_names = ["Add New Surgery"] + sorted(surgeries_df["surgery"].tolist()) if not surgeries_df.empty else ["Add New Surgery"]

    with st.form(key=f"form_dialog_{slot['unique_code']}"):
        selected_surgery_option = st.selectbox(
            "Select Surgery",
            surgery_names,
            key=f"select_surgery_{slot['unique_code']}"
        )

        manual_surgery_input = ""
        manual_email_input = ""

        if selected_surgery_option == "Add New Surgery":
            manual_surgery_input = st.text_input("New Surgery Name", key=f"new_surgery_name_{slot['unique_code']}")
            manual_email_input = st.text_input("New Email Address", key=f"new_email_address_{slot['unique_code']}")
            current_surgery = manual_surgery_input
            current_email = manual_email_input
        else:
            # Pre-fill with selected surgery's email
            selected_surgery_row = surgeries_df[surgeries_df["surgery"] == selected_surgery_option]
            prefilled_email = selected_surgery_row["email"].iloc[0] if not selected_surgery_row.empty else ""

            st.text_input("Surgery Name", value=selected_surgery_option, disabled=True, key=f"display_surgery_{slot['unique_code']}")
            st.text_input("Email Address", value=prefilled_email, disabled=True, key=f"display_email_{slot['unique_code']}")
            current_surgery = selected_surgery_option
            current_email = prefilled_email

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("Submit Booking")
        cancel_button = col2.form_submit_button("Cancel")

        if submitted:
            if not current_surgery or not current_email:
                st.error("All fields are required.")
            else:
                # If a new surgery was added, save it to Sheet2
                if selected_surgery_option == "Add New Surgery":
                    add_surgery_data(current_surgery, current_email)

                update_booking(slot, current_surgery, current_email)
                st.success("Booking saved successfully!")
                time.sleep(1.5)
                st.rerun() # Rerun to close dialog and refresh main app

        if cancel_button:
            st.rerun() # Rerun to close dialog

st.set_page_config(page_title="Pharma-Cal Brompton Heatlh PCN", layout="centered")

def display_calendar():
    st.title("Request a Pharmacist Session :material/pill:")
    st.logo('noname.png', size="large")
    # --- Admin Sidebar ---
    st.sidebar.title(":material/settings: Admin Panel")
    password = st.sidebar.text_input("Password", type="password")

    df = get_schedule_data()

    if not df.empty:
        if 'slot_index' not in df.columns:
            if 'pharm' in df.columns and pd.api.types.is_numeric_dtype(df['pharm']):
                df['slot_index'] = df['pharm'].astype(int) - 1
            else:
                df['slot_index'] = df.groupby(['Date', 'am_pm']).cumcount()

        if 'pharmacist_name' not in df.columns and 'pharm' in df.columns:
             df['pharmacist_name'] = df['pharm']

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

    upcoming = df[df['Date'] >= datetime.today()].sort_values(['Date', 'am_pm', 'slot_index'])

    if upcoming.empty:
        st.info("No upcoming shifts available.")
        return

    for date, daily in upcoming.groupby(df['Date'].dt.date):
        if date.weekday() >= 5:
            continue

        st.subheader(f"{date.strftime('%A, %d %B %Y')}")

        pharmacist_names_today = sorted(daily['pharmacist_name'].unique())
        pharm_cols = st.columns(len(pharmacist_names_today))

        for i, pharmacist_name in enumerate(pharmacist_names_today):
            with pharm_cols[i]:
                st.markdown(f":orange[**{pharmacist_name}**]")
                pharmacist_slots = daily[daily['pharmacist_name'] == pharmacist_name].sort_values(['am_pm'])

                if pharmacist_slots.empty:
                    st.info(f"No sessions available for {pharmacist_name}.")

                for _, row in pharmacist_slots.iterrows():
                    shift = row['am_pm'].upper()
                    booked = str(row['booked']).upper() == "TRUE"

                    btn_label = "09:00 - 12:30" if shift == "AM" else "14:00 - 17:30"
                    unique_key = f"{row['unique_code']}_{row['pharmacist_name']}"

                    if booked:
                        st.button(btn_label + " (Booked)", key=unique_key, disabled=True)
                        if row['surgery']:
                            st.caption(row['surgery'])
                    else:
                        if st.button(btn_label, key=unique_key):
                            show_booking_dialog(row.to_dict())

        st.divider()

if __name__ == "__main__":
    display_calendar()
