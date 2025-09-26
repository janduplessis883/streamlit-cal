import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from gspread.utils import ValueInputOption # Import ValueInputOption from gspread.utils
from google.oauth2.service_account import Credentials
import time
import os
import resend
import uuid # Import uuid for generating unique IDs
from typing import Any # Import Any for type hinting
import plotly.express as px

# Local Imports
from plots import fair_share_plot, display_plot, display_normalized_sessions_plot
from core import client, get_gspread_client # Import client and get_gspread_client from core.py

# Google Sheet details
from core import SPREADSHEET_ID, SHEET_NAME, SHEET_NAME_COVER_REQUESTS, SHEET_NAME_SURGERIES, SHEET_NAME_PHARMACISTS, get_schedule_data, get_cover_requests_data, add_cover_request_data, get_surgeries_data, add_surgery_data, delete_surgery_data, get_pharmacists_data, add_pharmacist_data, delete_pharmacist_data, generate_ics_file, send_resend_email, cancel_booking, update_booking # Import from core.py


def show_admin_panel(df):
    unbook_mode = False  # Default value
    admin_tab = st.sidebar.radio("Admin Options", ["Manage Availability", "View Future Requests", "Manage Surgeries", "Manage Pharmacists", "Surgery Session Plots"], key="admin_options_radio")

    if admin_tab == "Surgery Session Plots":
        st.session_state.view = 'plot'
    elif admin_tab == "View Future Requests":
        st.session_state.view = 'future_requests'
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
                                            except gspread.exceptions.APIError as e: # Changed to gspread.exceptions.APIError
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
                                            sheet.append_row(ordered_row_values, value_input_option=ValueInputOption.raw)

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
                                                sheet.append_row(ordered_row_values, value_input_option=ValueInputOption.raw)


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
        st.session_state.plot_type = st.sidebar.radio("Select Plot Type", ["Absolute Session Plot", "Normalized Sessions per 1000 pts", "Monthly Sessions"])
    elif admin_tab == "View Future Requests":
        st.header(":material/event_upcoming: Future Cover Requests")
        st.sidebar.subheader("Future Cover Requests")
        cover_requests_df = get_cover_requests_data()

        if not cover_requests_df.empty:
            # Filter for requests from today and the future
            today = datetime.today().date()
            future_requests = cover_requests_df[
                (cover_requests_df['cover_date'].dt.date >= today)
            ].sort_values(by='submission_timestamp')

            if not future_requests.empty:
                st.dataframe(future_requests[['cover_date', 'surgery', 'name', 'session', 'reason', 'desc', 'submission_timestamp']], use_container_width=True)
            else:
                st.info("No future cover requests found.")
        else:
            st.info("No cover requests submitted yet.")

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
                # Removed add_surgery_data call from here as it's meant for admin panel
                # If selected_surgery_option is "Add New Surgery", the user should be directed to admin panel
                # or a separate flow for adding new surgeries.
                if selected_surgery_option == "Add New Surgery":
                    st.error("Please add new surgeries via the Admin Panel before booking.")
                else:
                    update_booking(slot, current_surgery, current_email)
                    st.success("Booking saved successfully!")
                    time.sleep(1.5)
                    st.rerun() # Rerun to close dialog and refresh main app

        if cancel_button:
            st.rerun() # Rerun to close dialog

@st.dialog("Request Cover")
def show_cover_request_dialog(cover_date):
    st.markdown(f"Requesting cover for: **{cover_date.strftime('%A, %d %B %Y')}**")

    surgeries_df = get_surgeries_data()
    surgery_names = sorted(surgeries_df["surgery"].tolist()) if not surgeries_df.empty else []

    with st.form(key=f"form_cover_request_{cover_date.strftime('%Y%m%d')}"):
        selected_surgery = st.selectbox(
            "Select Surgery",
            [""] + surgery_names, # Add an empty option for initial selection
            key=f"cover_surgery_{cover_date.strftime('%Y%m%d')}"
        )
        requested_by_name = st.text_input(
            "Requested by (Your Name)",
            key=f"cover_name_{cover_date.strftime('%Y%m%d')}"
        )

        selected_session = st.selectbox(
            "Session",
            ['AM', 'PM', 'Full-day'],
            key=f"cover_session_{cover_date.strftime('%Y%m%d')}"
        )

        reason_options = ['Annual Leave', 'Study Leave', 'Other']
        selected_reason = st.selectbox(
            "Reason",
            reason_options,
            key=f"cover_reason_{cover_date.strftime('%Y%m%d')}"
        )

        other_reason_text = ""
        if selected_reason == "Other":
            other_reason_text = st.text_input(
                "Please specify other reason",
                key=f"other_reason_text_{cover_date.strftime('%Y%m%d')}"
            )

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("Submit Request")
        cancel_button = col2.form_submit_button("Cancel")

        if submitted:
            final_reason = selected_reason
            final_description = "" # Initialize final_description

            if selected_reason == "Other":
                if not other_reason_text:
                    st.error("Please specify the other reason.")
                    st.stop()
                final_description = other_reason_text
                final_reason = other_reason_text # Store the specific reason if "Other" is selected
            else:
                final_description = selected_reason # Use the selected reason as description if not "Other"

            if not selected_surgery or not requested_by_name or not selected_session or not final_reason:
                st.error("All fields are required.")
            else:
                add_cover_request_data(cover_date, selected_surgery, requested_by_name, selected_session, final_reason, final_description)
                time.sleep(0.2)
                st.rerun() # Rerun to close dialog and refresh main app

        if cancel_button:
            st.rerun() # Rerun to close dialog



st.set_page_config(page_title="Pharma-Cal Brompton Heatlh PCN", layout="centered", page_icon=":material/pill:")


def display_calendar(unbook_mode=False):
    c1, c2, c3 = st.columns([0.25, 0.25, 2], gap="small")
    with c1:
        with st.popover(':material/info:'):
            st.image('images/userguide.png')
    with c3:
        with st.popover(':material/event:'):
            st.markdown(':material/event_available: 2025 **Fair Share**')
            release = pd.read_csv('data/fairshare.csv')
            with st.container(width=700):
                st.dataframe(release, width=800, height=700, hide_index=True)
    with c2:
        with st.popover(':material/bar_chart:'):
            with st.container(width=700):
                display_normalized_sessions_plot(get_schedule_data, get_surgeries_data)





    st.logo('images/logo223.png', size="large")
    # --- Admin Sidebar ---

    password = st.sidebar.text_input("", type="password", placeholder="Admin Login", label_visibility="collapsed", icon=":material/settings:")  # Admin password input
    if password == '':
        st.sidebar.image('images/logo22.png')
    df = get_schedule_data()

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

    # Initialize view state if not already set
    if 'view' not in st.session_state:
        st.session_state.view = 'calendar'
    if 'plot_type' not in st.session_state:
        st.session_state.plot_type = "Absolute Session Plot" # Default plot type

    if password == st.secrets["admin_password"]:
        unbook_mode = show_admin_panel(df)
    elif password != "":
        st.sidebar.error("Incorrect password")

    # Display content based on the selected view
    if st.session_state.view == 'plot':
        display_plot(df, get_surgeries_data) # Pass get_surgeries_data as an argument
        return
    elif st.session_state.view == 'future_requests':
        # The display logic for future requests is handled within show_admin_panel for this view
        # No need to duplicate it here.
        return

    # --- Main Calendar Display ---
    st.html("<div class='status' style='background-color: #334155; color: #fafafa; padding-top: 6px; padding-bottom: 6px; padding-left: 20px; padding-right: 20px; border-radius: 10px; font-family: Arial, sans-serif; font-size: 26px; display: inline-block; text-align: center; box-shadow: 0px 2px 3px rgba(0, 0, 0, 0.5);'>Request a <b>Pharmacist Session</b> - BH PCN</B></div>")
    if df.empty:
        st.info("No pharmacist shifts have been scheduled yet. Contact admin.")
        return

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    upcoming = df[df['Date'] >= datetime.today()].sort_values(['Date', 'am_pm', 'slot_index'])

    if upcoming.empty:
        st.info("No upcoming shifts available.")
        last_advertised_date = datetime.today().date() # If no upcoming, start from today
    else:
        last_advertised_date = upcoming['Date'].max().date()

    # Display existing pharmacist schedule
    for date, daily in upcoming.groupby(df['Date'].dt.date):
        if date.weekday() >= 5: # Skip weekends for advertised dates
            continue

        st.subheader(f"{date.strftime('%A, %d %B %Y')}")

        pharmacist_names_today = sorted(daily['pharmacist_name'].unique())
        # Ensure at least one column is created, even if no pharmacists are available
        pharm_cols = st.columns(max(1, len(pharmacist_names_today)))

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

    # Add functionality for Practice Managers to submit booking requests beyond the advertised date
    st.header("Submit Future Requests", help="Request sessions beyond the advertised schedule")
    start_date_beyond = last_advertised_date + timedelta(days=1)
    end_date_beyond = start_date_beyond + timedelta(weeks=14)

    cover_requests_df = get_cover_requests_data()

    current_date_beyond = start_date_beyond
    while current_date_beyond <= end_date_beyond:
        if current_date_beyond.weekday() < 5: # Only show weekdays
            st.markdown(f"**{current_date_beyond.strftime('%A, %d %B %Y')}**")

            # Display existing cover requests for this date
            daily_cover_requests = cover_requests_df[
                (cover_requests_df['cover_date'].dt.date == current_date_beyond)
            ].sort_values(by='submission_timestamp')

            if not daily_cover_requests.empty:
                for _, req_row in daily_cover_requests.iterrows():
                    submission_time_str = req_row['submission_timestamp'].strftime('%d %b %y %H:%M') if pd.notna(req_row['submission_timestamp']) else "N/A"
                    st.caption(f"**{req_row['surgery']}** requested by {req_row['name']} at {submission_time_str}")
                    if password == st.secrets["admin_password"]: # Check if admin is logged in
                        st.caption(f"Session: {req_row['session']} | Reason: {req_row['reason']} | Description: {req_row['desc']}")
                    # Removed the description caption as per user's implicit feedback (it was removed from the example)

            if st.button("Request Cover", key=f"interest_{current_date_beyond.strftime('%Y%m%d')}", icon=":material/event_upcoming:"):
                show_cover_request_dialog(current_date_beyond)
            st.divider()
        current_date_beyond += timedelta(days=1)

if __name__ == "__main__":
    display_calendar()

    st.sidebar.html("""<BR><BR><BR><BR><BR><BR><center><img alt="Static Badge" src="https://img.shields.io/badge/GitHub-janduplessis883-%23316576"></center>""")
