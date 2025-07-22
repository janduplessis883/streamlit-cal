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

@st.cache_data(ttl=3600) # Cache for 1 hour
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
        sheet = client.open_by_key(SPREADSHEET_ID).add_worksheet(SHEET_NAME_PHARMACISTS, rows=1, cols=2)
        sheet.update([["Name", "Email"]]) # Add headers
        return pd.DataFrame(columns=["Name"])
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

def delete_pharmacist_data(pharmacist_name, pharmacist_email):
    """Delete a pharmacist entry from Google Sheet (Sheet3)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_PHARMACISTS)
        # Find the row index of the pharmacist to delete
        # gspread's find method returns the Cell object, which has a 'row' attribute
        cell = sheet.find(pharmacist_name)
        if cell:
            # Verify email matches to prevent accidental deletion if pharmacist names are not unique
            row_values = sheet.row_values(cell.row)
            # Assuming 'Name' is in column 1 and 'Email' in column 2
            if len(row_values) >= 2 and row_values[1] == pharmacist_email:
                sheet.delete_rows(cell.row)
                st.success(f"Pharmacist '{pharmacist_name}' deleted successfully!")
                get_pharmacists_data.clear() # Clear cache to refresh data
            else:
                st.error(f"Could not delete pharmacist: Email mismatch for '{pharmacist_name}'.")
        else:
            st.error(f"Pharmacist '{pharmacist_name}' not found.")
    except Exception as e:
        st.error(f"An error occurred while deleting pharmacist data from Google Sheet: {e}")

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
    st.sidebar.header("Admin Panel")

    admin_tab = st.sidebar.radio("Admin Options", ["Manage Availability", "Manage Surgeries", "Manage Pharmacists"])

    if admin_tab == "Manage Availability":
        st.sidebar.subheader("Manage Availability")
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

            # Create a dictionary to store current availability and booked status for each slot
            current_availability = {}
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date']).dt.date # Ensure date comparison works
                for _, row in df.iterrows():
                    # Store full row data for each unique slot (date, pharm, am_pm)
                    current_availability[(row['Date'], row['pharm'], row['am_pm'])] = {
                        'booked': str(row['booked']).upper() == "TRUE",
                        'surgery': row['surgery'],
                        'email': row['email'],
                        'unique_code': row['unique_code']
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
                for pharm in [1, 2]:
                    for shift_type in ['am', 'pm']: # Iterate through AM/PM shifts
                        checkbox_key = f"avail_{date.strftime('%Y%m%d')}_{pharm}_{shift_type}"

                        # Get slot info, default to unbooked if not found
                        slot_info = current_availability.get((date.date(), pharm, shift_type), {'booked': False})
                        is_booked = slot_info['booked']

                        # Pre-fill checkbox based on current availability
                        # A slot is initially checked if it exists in current_availability
                        initial_value = (date.date(), pharm, shift_type) in current_availability

                        checked = cols[pharm-1].checkbox(
                            f"Pharmacist {pharm} ({shift_type.upper()})",
                            value=initial_value,
                            key=checkbox_key,
                            disabled=is_weekend or is_booked # Disable if weekend OR booked
                        )

                        # If not a weekend and checked (or was booked and thus disabled but implicitly selected), add to selected_slots
                        if not is_weekend and (checked or is_booked): # Keep booked slots selected
                            selected_slots.append({
                                "date": date,
                                "pharm": pharm,
                                "am_pm": shift_type,
                                "booked_info": slot_info # Pass along the existing booked info
                            })

            submitted = st.form_submit_button("Update Availability")
            if submitted:
                # Create a completely new DataFrame based on selected_slots
                new_df_data = []
                for slot in selected_slots:
                    # Check if this slot was previously booked
                    was_booked = slot['booked_info']['booked'] if 'booked_info' in slot else False
                    booked_surgery = slot['booked_info']['surgery'] if was_booked else ""
                    booked_email = slot['booked_info']['email'] if was_booked else ""
                    booked_unique_code = slot['booked_info']['unique_code'] if was_booked else f"{int(slot['date'].timestamp())}-{slot['am_pm']}-{slot['pharm']}"

                    new_df_data.append({
                        "unique_code": booked_unique_code,
                        "Date": slot['date'].strftime('%Y-%m-%d'),
                        "am_pm": slot['am_pm'],
                        "pharm": slot['pharm'],
                        "booked": "TRUE" if was_booked else "FALSE",
                        "surgery": booked_surgery,
                        "email": booked_email
                    })

                # Overwrite the Google Sheet with the new availability
                try:
                    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
                    with st.spinner("Updating availability..."):
                        sheet.clear()
                        # Convert DataFrame to list of lists, handling potential NaN values
                        # Ensure all values are strings for gspread
                        data_to_write = [list(new_df_data[0].keys())] + [[str(val) for val in row.values()] for row in new_df_data]
                        sheet.update(data_to_write)
                    st.success("Availability updated in Google Sheet!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating availability in Google Sheet: {e}")

    elif admin_tab == "Manage Surgeries":
        st.sidebar.subheader("Add New Surgery")
        with st.sidebar.form("add_surgery_form"):
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
        with st.sidebar.form("add_pharmacist_form"):
            # Initialize session state for input fields if not already present
            if 'new_pharmacist_name_input' not in st.session_state:
                st.session_state.new_pharmacist_name_input = ""
            if 'new_pharmacist_email_input' not in st.session_state:
                st.session_state.new_pharmacist_email_input = ""

            st.text_input("Pharmacist Name (e.g., John Doe)", key="new_pharmacist_name_input", value=st.session_state.new_pharmacist_name_input)
            st.text_input("Pharmacist Email", key="new_pharmacist_email_input", value=st.session_state.new_pharmacist_email_input)

            def _submit_add_pharmacist():
                if st.session_state.new_pharmacist_name_input and st.session_state.new_pharmacist_email_input:
                    add_pharmacist_data(st.session_state.new_pharmacist_name_input, st.session_state.new_pharmacist_email_input)
                    st.session_state.new_pharmacist_name_input = "" # Clear after successful add
                    st.session_state.new_pharmacist_email_input = "" # Clear after successful add
                else:
                    st.error("Pharmacist name and email are required.")

            st.form_submit_button("Add Pharmacist", on_click=_submit_add_pharmacist)

        st.sidebar.subheader("Existing Pharmacists")
        pharmacists_df = get_pharmacists_data()
        if not pharmacists_df.empty:
            for idx, row in pharmacists_df.iterrows():
                col1, col2 = st.sidebar.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"{idx + 1}. **{row['Name']}**: {row['Email']}")
                with col2:
                    if st.button(":material/delete:", key=f"delete_pharmacist_{idx}"):
                        delete_pharmacist_data(row['Name'], row['Email'])
                        st.rerun()
        else:
            st.sidebar.info("No pharmacists saved yet.")

@st.dialog("Booking Details")
def show_booking_dialog(slot):
    shift = slot['am_pm'].upper()
    pharm = slot['pharm']

    st.markdown(f"**Booking: Pharmacist {pharm} — {shift} on {pd.to_datetime(slot['Date']).strftime('%Y-%m-%d')}**")

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
    st.title(":material/pill: Request a Pharmacist Session")
    st.logo('noname.png', size="large")
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

        # Create two columns for Pharmacist 1 and Pharmacist 2
        pharm_cols = st.columns(2)

        # Filter and display sessions for Pharmacist 1 in the first column
        pharm1_slots = daily[daily['pharm'] == 1].sort_values(['am_pm'])
        with pharm_cols[0]:
            st.markdown("**Pharmacist 1**")
            if pharm1_slots.empty:
                st.info("No sessions available for Pharmacist 1.")
            for i, row in pharm1_slots.iterrows():
                shift = row['am_pm'].upper()
                pharm = row['pharm']
                booked = str(row['booked']).upper() == "TRUE"

                if shift == "AM":
                    btn_label = f"Pharmacist {pharm}: 09:00 - 12:30"
                elif shift == "PM":
                    btn_label = f"Pharmacist {pharm}: 14:00 - 17:30"
                else:
                    btn_label = f"Pharmacist {pharm} {shift}"

                unique_key = f"{row['unique_code']}_{i}"

                if booked:
                    st.button(btn_label + " (Booked)", key=unique_key, disabled=True)
                    if row['surgery']:
                        st.caption(row['surgery'])
                else:
                    if st.button(btn_label, key=unique_key):
                        show_booking_dialog(row.to_dict())

        # Filter and display sessions for Pharmacist 2 in the second column
        pharm2_slots = daily[daily['pharm'] == 2].sort_values(['am_pm'])
        with pharm_cols[1]:
            st.markdown("**Pharmacist 2**")
            if pharm2_slots.empty:
                st.info("No sessions available for Pharmacist 2.")
            for i, row in pharm2_slots.iterrows():
                shift = row['am_pm'].upper()
                pharm = row['pharm']
                booked = str(row['booked']).upper() == "TRUE"

                if shift == "AM":
                    btn_label = f"Pharmacist {pharm}: 09:00 - 12:30"
                elif shift == "PM":
                    btn_label = f"Pharmacist {pharm}: 14:00 - 17:30"
                else:
                    btn_label = f"Pharmacist {pharm} {shift}"

                unique_key = f"{row['unique_code']}_{i}"

                if booked:
                    st.button(btn_label + " (Booked)", key=unique_key, disabled=True)
                    if row['surgery']:
                        st.caption(row['surgery'])
                else:
                    if st.button(btn_label, key=unique_key):
                        show_booking_dialog(row.to_dict())

        st.markdown("---")

if __name__ == "__main__":
    display_calendar()
