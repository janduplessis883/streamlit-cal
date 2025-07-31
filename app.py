import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time
import os
import resend

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
        # Ensure list_size is numeric, coercing errors
        if 'list_size' in df.columns:
            df['list_size'] = pd.to_numeric(df['list_size'], errors='coerce').fillna(0)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"Worksheet '{SHEET_NAME_SURGERIES}' not found. Creating it...")
        # Create the worksheet if it doesn't exist
        sheet = client.open_by_key(SPREADSHEET_ID).add_worksheet(SHEET_NAME_SURGERIES, rows=1, cols=3)
        sheet.update([["surgery", "email", "list_size"]]) # Add headers
        return pd.DataFrame(columns=["surgery", "email", "list_size"])
    except Exception as e:
        st.error(f"An error occurred while reading surgeries data from Google Sheet: {e}")
        return pd.DataFrame()

def add_surgery_data(surgery_name, email_address, list_size):
    """Add a new surgery and email to Google Sheet (Sheet2)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_SURGERIES)
        # Check if surgery already exists
        existing_data = sheet.get_all_records()
        for row in existing_data:
            if row.get("surgery") == surgery_name and row.get("email") == email_address:
                st.info(f"Surgery '{surgery_name}' with email '{email_address}' already exists.")
                return

        sheet.append_row([surgery_name, email_address, list_size])
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
            # Assuming 'surgery' is in column A and 'email' in column B
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

def delete_pharmacist_data(pharmacist_name, email_address):
    """Delete a pharmacist entry from Google Sheet (Sheet3)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_PHARMACISTS)
        # Find the row index of the pharmacist to delete
        cell = sheet.find(pharmacist_name)
        if cell:
            # Verify email matches to prevent accidental deletion if names are not unique
            row_values = sheet.row_values(cell.row)
            # Assuming 'Name' is in column A and 'Email' in column B
            if len(row_values) >= 2 and row_values[1] == email_address:
                sheet.delete_rows(cell.row)
                st.success(f"Pharmacist '{pharmacist_name}' deleted successfully!")
                get_pharmacists_data.clear()
            else:
                st.error(f"Could not delete pharmacist: Email mismatch for '{pharmacist_name}'.")
        else:
            st.error(f"Pharmacist '{pharmacist_name}' not found.")
    except Exception as e:
        st.error(f"An error occurred while deleting pharmacist data from Google Sheet: {e}")

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
        return pd.DataFrame(columns=["Name", "Email"])
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
            if row.get("Name") == pharmacist_name:
                st.info(f"Pharmacist '{pharmacist_name}' already exists.")
                return

        sheet.append_row([pharmacist_name, pharmacist_email])
        st.success(f"Pharmacist '{pharmacist_name}' added successfully!")
        get_pharmacists_data.clear() # Clear cache to refresh data
    except Exception as e:
        st.error(f"An error occurred while adding pharmacist data to Google Sheet: {e}")

def generate_ics_file(pharmacist_name, start_time, end_time, location):
    """Generate an Outlook .ics file for the booking"""
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Pharma-Cal//EN
BEGIN:VEVENT
SUMMARY:Pharmacist Booking - {pharmacist_name}
DTSTART:{start_time.strftime('%Y%m%dT%H%M%S')}
DTEND:{end_time.strftime('%Y%m%dT%H%M%S')}
LOCATION:{location} - Remote Session
DESCRIPTION:Pharmacist: {pharmacist_name}
END:VEVENT
END:VCALENDAR"""

    file_path = f"pharmacist_booking_{start_time.strftime('%Y%m%d')}.ics"
    with open(file_path, 'w') as f:
        f.write(ics_content)
    return file_path

def send_resend_email(to_email, subject, html_content, attachment_path=None):
    """Send email via Resend API"""
    resend.api_key = "re_cJjyoNUq_6M1WHM9T76ofbvApaRrUz6eG"

    if attachment_path:
        with open(attachment_path, "rb") as f:
            attachment_content = f.read()
        attachment = {"filename": os.path.basename(attachment_path), "content": list(attachment_content)}
    else:
        attachment = None

    params = {
        "from": "Brompton Health PCN - Pharma-cal <hello@attribut.me>",
        "to": to_email,
        "subject": subject,
        "html": html_content,
        "attachments": [attachment] if attachment else [],
    }

    try:
        resend.Emails.send(params)
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

def cancel_booking(slot):
    """Cancel a booking, update the Google Sheet, and send cancellation emails."""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        cell = sheet.find(slot['unique_code'])

        if cell:
            headers = sheet.row_values(1)
            row_values = sheet.row_values(cell.row)

            try:
                # Get column indices
                booked_col_idx = headers.index('booked') + 1
                surgery_col_idx = headers.index('surgery') + 1
                email_col_idx = headers.index('email') + 1
                pharmacist_name_col_idx = headers.index('pharmacist_name') + 1
                date_col_idx = headers.index('Date') + 1
                am_pm_col_idx = headers.index('am_pm') + 1

                # Get booking details from the sheet
                surgery_name = row_values[surgery_col_idx - 1]
                surgery_email = row_values[email_col_idx - 1]
                pharmacist_name = row_values[pharmacist_name_col_idx - 1]
                booking_date_str = row_values[date_col_idx - 1]
                booking_am_pm = row_values[am_pm_col_idx - 1]

                # Fetch pharmacist's email
                pharmacists_df = get_pharmacists_data()
                pharmacist_row = pharmacists_df[pharmacists_df['Name'] == pharmacist_name]
                if pharmacist_row.empty:
                    st.error(f"Could not find email for pharmacist {pharmacist_name}. Cancellation email to pharmacist not sent.")
                    pharmacist_email = None
                else:
                    pharmacist_email = pharmacist_row['Email'].iloc[0]

            except (ValueError, IndexError) as e:
                st.error(f"Missing or incorrect column in Google Sheet: {e}")
                return

            with st.spinner("Cancelling booking and sending notifications..."):
                # Clear booking info in the sheet
                sheet.update_cell(cell.row, booked_col_idx, "FALSE")
                sheet.update_cell(cell.row, surgery_col_idx, "")
                sheet.update_cell(cell.row, email_col_idx, "")

                # Prepare email content
                booking_date = pd.to_datetime(booking_date_str).strftime('%A, %d %B %Y')
                booking_time = '09:00 - 12:45' if booking_am_pm == 'am' else '13:15 - 17:00'

                # Email to Surgery
                if surgery_email:
                    surgery_html = f"""
                    <h2>Booking Cancellation Notice</h2>
                    <p>The booking for <b>{pharmacist_name}</b> on <b>{booking_date}</b> at <b>{booking_time}</b> has been cancelled.</p>
                    <p>This slot is now available again.</p>
                    """
                    send_resend_email(surgery_email, f"Booking Cancellation - {pharmacist_name} on {booking_date}", surgery_html)

                # Email to Pharmacist
                if pharmacist_email:
                    pharmacist_html = f"""
                    <h2>Booking Cancellation Notice</h2>
                    <p>Your session at <b>{surgery_name}</b> on <b>{booking_date}</b> at <b>{booking_time}</b> has been cancelled.</p>
                    <p>This slot is now available again.</p>
                    """
                    send_resend_email(pharmacist_email, f"Booking Cancellation - {surgery_name} on {booking_date}", pharmacist_html)


            st.success("Booking cancelled successfully and notifications sent!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Could not find the slot to cancel.")
    except Exception as e:
        st.error(f"An error occurred while cancelling the booking: {e}")


def update_booking(slot, surgery, email):
    """Update the Google Sheet with booking details and send confirmation emails"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        # Find the row based on unique_code
        cell = sheet.find(slot['unique_code'])

        if cell:
            # Get all headers to find column indices dynamically
            headers = sheet.row_values(1)
            try:
                booked_col_idx = headers.index('booked') + 1
                surgery_col_idx = headers.index('surgery') + 1
                email_col_idx = headers.index('email') + 1
            except ValueError as e:
                st.error(f"Missing required column in Google Sheet: {e}")
                return

            # Update cells
            with st.spinner("Updating booking..."):
                sheet.update_cell(cell.row, booked_col_idx, "TRUE")
                sheet.update_cell(cell.row, surgery_col_idx, surgery)
                sheet.update_cell(cell.row, email_col_idx, email)

                # Get pharmacist details
                pharmacist_name = slot.get('pharmacist_name', 'Pharmacist')
                pharmacists_df = get_pharmacists_data()
                pharmacist_row = pharmacists_df[pharmacists_df['Name'] == pharmacist_name]

                if pharmacist_row.empty:
                    st.error(f"Could not find email for pharmacist {pharmacist_name}")
                    return
                pharmacist_email = pharmacist_row['Email'].iloc[0]


                # Generate ICS file
                date = pd.to_datetime(slot['Date'])
                start_time = date.replace(hour=9 if slot['am_pm'] == 'am' else 13)
                end_time = date.replace(hour=12, minute=45) if slot['am_pm'] == 'am' else date.replace(hour=17)
                ics_file = generate_ics_file(pharmacist_name, start_time, end_time, surgery)

                # Email to surgery
                surgery_html = f"""
                <h2>Pharmacist Booking Confirmation</h2>
                <p>You have booked <b>{pharmacist_name}</b> for:</p>
                <p><strong>Date:</strong> {date.strftime('%A, %d %B %Y')}</p>
                <p><strong>Time:</strong> {'09:00 - 12:45' if slot['am_pm'] == 'am' else '13:15 - 17:00'}</p>
                <p>Please find attached the calendar invite.</p>
                """
                send_resend_email(email, f"Pharmacist Booking Confirmation - {date.strftime('%d/%m/%Y')}",
                                surgery_html, ics_file)

                # Email to pharmacist
                pharmacist_html = f"""
                <h2>New Surgery Booking Notification</h2>
                <p>You have been booked for a session at:</p>
                <p><strong>Surgery:</strong> {surgery}</p>
                <p><strong>Date:</strong> {date.strftime('%A, %d %B %Y')}</p>
                <p><strong>Time:</strong> {'09:00 - 12:45' if slot['am_pm'] == 'am' else '13:15 - 17:00'}</p>
                <p><strong>Surgery Email:</strong> {email}</p>
                <p>Please find attached the calendar invite.</p>
                """
                send_resend_email(pharmacist_email, f"New Booking - {surgery} on {date.strftime('%d/%m/%Y')}",
                                pharmacist_html, ics_file)

        else:
            st.error("Could not find the slot in the Google Sheet.")
    except Exception as e:
        st.error(f"An error occurred while updating the booking in Google Sheet: {e}")

def show_admin_panel(df):
    unbook_mode = False  # Default value
    admin_tab = st.sidebar.radio("Admin Options", ["Manage Availability", "Manage Surgeries", "Manage Pharmacists", "Surgery Session Plots"])

    if admin_tab == "Surgery Session Plots":
        st.session_state.view = 'plot'
    else:
        st.session_state.view = 'calendar'

    if admin_tab == "Manage Availability":
        st.sidebar.subheader("Manage Availability")
        unbook_mode = st.sidebar.toggle("Unbook Mode", value=False)

        num_weeks = st.sidebar.slider("Number of weeks to show", 1, 12, 4)

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
                    key = (row['Date'], int(row['slot_index']), row['am_pm'])
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
                    st.markdown(f":orange[{date_str} (Weekend)]")
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

                                # Create a temporary list of options for this specific selectbox
                                current_options = list(pharmacist_names)

                                if is_booked and default_pharmacist not in current_options:
                                    # If the booked pharmacist is not in the main list (e.g., deleted),
                                    # add them to the options for this dropdown to display correctly.
                                    current_options.append(default_pharmacist)

                                # If default_pharmacist is still not in the list (e.g. it's None), default to "None"
                                if default_pharmacist not in current_options:
                                    default_pharmacist = "None"

                                selected_pharmacist = st.selectbox(
                                    f"{shift_type.upper()} Slot",
                                    current_options, # Use the potentially modified list
                                    index=current_options.index(default_pharmacist),
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
                EXPECTED_HEADERS = ["unique_code", "Date", "am_pm", "booked", "surgery", "email", "pharmacist_name", "slot_index"]
                try:
                    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

                    try:
                        headers = sheet.row_values(1)
                        if not headers: # Check if the first row is empty
                            sheet.update([EXPECTED_HEADERS])
                            headers = EXPECTED_HEADERS
                    except gspread.exceptions.APIError as e:
                        # This can happen if the sheet is completely empty
                        sheet.update([EXPECTED_HEADERS])
                        headers = EXPECTED_HEADERS

                    # Ensure all expected headers are present
                    if not all(h in headers for h in EXPECTED_HEADERS):
                        st.error("The sheet is missing required headers. Please check the sheet configuration.")
                        st.stop()

                    pharmacist_name_col_idx = headers.index('pharmacist_name') + 1

                    with st.spinner("Updating availability... This may take a moment."):
                        for date in dates_to_show:
                            if date.weekday() >= 5: continue

                            for i in range(2): # Number of pharmacist columns
                                for shift_type in ['am', 'pm']:
                                    slot_key = f"avail_{date.strftime('%Y%m%d')}_{shift_type}_{i}"
                                    lookup_key = (date.date(), i, shift_type)

                                    slot_info = current_availability.get(lookup_key, {})
                                    original_pharmacist = slot_info.get('pharmacist_name', 'None')
                                    new_pharmacist = st.session_state.get(slot_key, 'None')

                                    if slot_info.get('booked', False):
                                        continue

                                    if new_pharmacist != original_pharmacist:
                                        unique_code = slot_info.get('unique_code') or f"{int(date.timestamp())}-{shift_type}-{i}"

                                        # Find cell for existing entries (deletion or modification)
                                        cell_to_modify = None
                                        if original_pharmacist != 'None' and unique_code:
                                            try:
                                                cell_to_modify = sheet.find(unique_code)
                                            except gspread.exceptions.CellNotFound:
                                                # This can happen if data is out of sync. We can proceed as if it wasn't there.
                                                pass

                                        # Case 1: Deletion
                                        if new_pharmacist == 'None':
                                            if cell_to_modify:
                                                sheet.delete_rows(cell_to_modify.row)

                                        # Case 2: Addition
                                        elif original_pharmacist == 'None':
                                            new_row_data = {
                                                "unique_code": unique_code,
                                                "Date": date.strftime('%Y-%m-%d'),
                                                "am_pm": shift_type,
                                                "booked": "FALSE",
                                                "surgery": "",
                                                "email": "",
                                                "pharmacist_name": new_pharmacist,
                                                "slot_index": i
                                            }
                                            # Build the row in the correct order based on sheet headers
                                            ordered_row_values = [new_row_data.get(h, "") for h in headers]
                                            sheet.append_row(ordered_row_values, value_input_option='USER_ENTERED')

                                        # Case 3: Modification
                                        else:
                                            if cell_to_modify:
                                                sheet.update_cell(cell_to_modify.row, pharmacist_name_col_idx, new_pharmacist)
                                            else:
                                                # The original entry was not found, so treat it as an addition
                                                st.warning(f"Could not find slot {unique_code} to modify. Adding it as a new entry.")
                                                new_row_data = {
                                                    "unique_code": unique_code,
                                                    "Date": date.strftime('%Y-%m-%d'),
                                                    "am_pm": shift_type,
                                                    "booked": "FALSE",
                                                    "surgery": "",
                                                    "email": "",
                                                    "pharmacist_name": new_pharmacist,
                                                    "slot_index": i
                                                }
                                                ordered_row_values = [new_row_data.get(h, "") for h in headers]
                                                sheet.append_row(ordered_row_values, value_input_option='USER_ENTERED')


                    st.success("Availability updated successfully!")
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(f"An error occurred while updating availability: {e}")

    elif admin_tab == "Manage Surgeries":
        st.sidebar.subheader("Add New Surgery")
        with st.sidebar.form("add_surgery_form", clear_on_submit=True):
            new_surgery_name = st.text_input("Surgery Name")
            new_surgery_email = st.text_input("Email Address")
            new_list_size = st.number_input("List Size", min_value=0, step=1)
            add_surgery_submitted = st.form_submit_button("Add Surgery")

            if add_surgery_submitted:
                if new_surgery_name and new_surgery_email:
                    add_surgery_data(new_surgery_name, new_surgery_email, new_list_size)
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
            new_pharmacist_name = st.text_input("Pharmacist Name")
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
    elif admin_tab == "Surgery Session Plots":
        st.sidebar.subheader("Surgery Session Plots")
        st.session_state.plot_type = st.sidebar.radio("Select Plot Type", ["Absolute Session Plot", "Normalized Sessions per 1000 pts"])

    return unbook_mode

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

import plotly.express as px

st.set_page_config(page_title="Pharma-Cal Brompton Heatlh PCN", layout="centered")

def display_plot(df):
    st.subheader("Surgery Session Distribution")

    plot_type = st.session_state.get('plot_type', "Absolute Session Plot")

    # Ensure the DataFrame is not empty and contains required columns
    if df.empty or 'surgery' not in df.columns:
        st.info("No data available to display the plot.")
        return

    # Filter out rows where surgery is not specified or empty
    plot_df = df[df['surgery'].notna() & (df['surgery'] != '')].copy()

    if plot_df.empty:
        st.info("No booked sessions with surgery information available.")
        return

    # Count sessions per surgery
    surgery_counts = plot_df['surgery'].value_counts().reset_index()
    surgery_counts.columns = ['Surgery', 'Number of Sessions']

    if plot_type == "Normalized Sessions per 1000 pts":
        surgeries_df = get_surgeries_data()
        if surgeries_df.empty or 'list_size' not in surgeries_df.columns:
            st.warning("List size information is not available. Please add it in the 'Manage Surgeries' section.")
            return

        # Merge dataframes to get list sizes
        merged_df = pd.merge(surgery_counts, surgeries_df, left_on='Surgery', right_on='surgery', how='left')
        merged_df['list_size'] = merged_df['list_size'].replace(0, 1) # Avoid division by zero
        merged_df['Normalized Sessions'] = (merged_df['Number of Sessions'] / merged_df['list_size']) * 1000

        fig = px.bar(
            merged_df,
            x='Surgery',
            y='Normalized Sessions',
            title='Normalized Sessions per 1000 Patients',
            color='Surgery',
            template='plotly_white'
        )
        fig.update_layout(
            xaxis_title="Surgery",
            yaxis_title="Sessions per 1000 Patients",
            showlegend=False,
            xaxis_tickangle=-45
        )
    else: # Absolute Session Plot
        fig = px.bar(
            surgery_counts,
            x='Surgery',
            y='Number of Sessions',
            title='Number of Sessions per Surgery',
            color='Surgery',  # Color bars by surgery name
            template='plotly_white', # Use a clean, modern template
        )
        fig.update_layout(
            xaxis_title="Surgery",
            yaxis_title="Number of Sessions",
            showlegend=False, # Hide legend as colors are self-explanatory
            xaxis_tickangle=-45 # Angle the x-axis labels for better readability
        )

    st.plotly_chart(fig, use_container_width=True)

def display_calendar(unbook_mode=False):
    c1, c2 = st.columns([0.2,2], gap="small")
    with c1:
        with st.popover(':material/info:'):
            st.image('images/userguide.png')
    with c2:
        with st.popover(':material/event:'):
            st.markdown(':material/event_available: 2025 Communal Sessions **Release Schedule**')
            release = pd.read_csv('data/release.csv')
            st.dataframe(release, width=400, height=700, hide_index=True)



    st.html("<div class='status' style='background-color: #3982c2; color: #fafafa; padding-top: 6px; padding-bottom: 6px; padding-left: 20px; padding-right: 20px; border-radius: 10px; font-family: Arial, sans-serif; font-size: 26px; display: inline-block; text-align: center; box-shadow: 0px 1px 2px rgba(0, 0, 0, 0.5);'>Request a <b>Pharmacist Session</b> - BH PCN</B></div>")
    st.logo('images/logo223.png', size="large")
    # --- Admin Sidebar ---

    password = st.sidebar.text_input("", type="password", placeholder="Admin Login", label_visibility="collapsed", icon=":material/settings:")  # Admin password input
    if password == '':
        st.sidebar.image('images/logo22.png')
    df = get_schedule_data()

    if 'view' not in st.session_state:
        st.session_state.view = 'calendar'

    if not df.empty:
        if 'slot_index' not in df.columns:
            if 'pharm' in df.columns and pd.api.types.is_numeric_dtype(df['pharm']):
                df['slot_index'] = df['pharm'].astype(int) - 1
            else:
                df['slot_index'] = df.groupby(['Date', 'am_pm']).cumcount()

        if 'pharmacist_name' not in df.columns:
            if 'pharm' in df.columns:
                if pd.api.types.is_numeric_dtype(df['pharm']):
                    df['pharmacist_name'] = df['pharm'].astype(str)
                else:
                    df['pharmacist_name'] = df['pharm']
            else:
                df['pharmacist_name'] = "Pharmacist"

    if password == "super user":
        unbook_mode = show_admin_panel(df)
    elif password != "":
        st.sidebar.error("Incorrect password")

    if st.session_state.view == 'plot':
        display_plot(df)
        return

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

                    btn_label = "09:00 - 12:45" if shift == "AM" else "13:15 - 17:00"
                    unique_key = f"{row['unique_code']}_{row['pharmacist_name']}"

                    if unbook_mode:
                        if booked:
                            if st.button(btn_label + " (Cancel)", key=unique_key):
                                cancel_booking(row.to_dict())
                        else:
                            st.button(btn_label, key=unique_key, disabled=True)
                    else:
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
