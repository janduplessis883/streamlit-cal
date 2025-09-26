import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd # Added for get_schedule_data
from datetime import datetime # Added for get_cover_requests_data
import uuid # Added for add_cover_request_data
from gspread.utils import ValueInputOption # Added for add_cover_request_data
import os # Added for generate_ics_file
import resend # Added for send_resend_email
from typing import Any # Added for send_resend_email
import time # Added for cancel_booking

# Google Sheet details
SPREADSHEET_ID = "1m6fJqggnvRJ9u-Hk5keUaPZ_gJHrd4GZmowE3j3nH-c"
SHEET_NAME = "Sheet1"
SHEET_NAME_COVER_REQUESTS = "cover_request" # New sheet for cover requests
SHEET_NAME_SURGERIES = "Sheet2" # New sheet for surgeries
SHEET_NAME_PHARMACISTS = "Sheet3" # New sheet for pharmacists

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
def get_cover_requests_data():
    """Fetch cover request data from Google Sheet (cover_request)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_COVER_REQUESTS)
        with st.spinner("Fetching cover requests..."):
            data = sheet.get_all_records()

        # If data is empty, create an empty DataFrame with expected columns
        if not data:
            df = pd.DataFrame(columns=["uuid", "cover_date", "surgery", "name", "desc", "submission_timestamp"])
        else:
            df = pd.DataFrame(data)

        # Ensure cover_date and submission_timestamp are datetime objects
        if 'cover_date' in df.columns:
            df['cover_date'] = pd.to_datetime(df['cover_date'], errors='coerce')
        if 'submission_timestamp' in df.columns:
            df['submission_timestamp'] = pd.to_datetime(df['submission_timestamp'], errors='coerce')

        # Ensure the DataFrame always has the expected columns, even if empty
        expected_columns = ["uuid", "cover_date", "surgery", "name", "session", "reason", "desc", "submission_timestamp"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None # Add missing columns

        return df
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"Worksheet '{SHEET_NAME_COVER_REQUESTS}' not found. Creating it...")
        sheet = client.open_by_key(SPREADSHEET_ID).add_worksheet(SHEET_NAME_COVER_REQUESTS, rows=1, cols=8)
        sheet.update([["uuid", "cover_date", "surgery", "name", "session", "reason", "desc", "submission_timestamp"]])
        # Return a DataFrame with expected columns after creating the sheet
        return pd.DataFrame(columns=["uuid", "cover_date", "surgery", "name", "session", "reason", "desc", "submission_timestamp"])
    except Exception as e:
        st.error(f"An error occurred while reading cover requests data from Google Sheet: {e}")
        return pd.DataFrame(columns=["uuid", "cover_date", "surgery", "name", "session", "reason", "desc", "submission_timestamp"]) # Ensure columns are always returned

def add_cover_request_data(cover_date, surgery, name, session, reason, desc):
    """Add a new cover request to Google Sheet (cover_request)"""
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME_COVER_REQUESTS)
        new_uuid = str(uuid.uuid4())
        submission_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([new_uuid, cover_date.strftime('%Y-%m-%d'), surgery, name, session, reason, desc, submission_timestamp])
        st.success("Cover request submitted successfully!")
        get_cover_requests_data.clear() # Clear cache to refresh data
    except Exception as e:
        st.error(f"An error occurred while adding cover request data to Google Sheet: {e}")

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
    resend.api_key = st.secrets["RESEND_API_KEY"]

    if attachment_path:
        with open(attachment_path, "rb") as f:
            attachment_content = f.read()
        attachment = {"filename": os.path.basename(attachment_path), "content": list(attachment_content)}
    else:
        attachment = None

    params: dict[str, Any] = { # Explicitly type params as dict[str, Any]
        "from": "Brompton Health PCN - Pharma-cal <hello@attribut.me>",
        "to": to_email,
        "subject": subject,
        "html": html_content,
        "attachments": [attachment] if attachment else [],
    }

    try:
        resend.Emails.send(params) # Pylance might still complain, but this is a common workaround
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
