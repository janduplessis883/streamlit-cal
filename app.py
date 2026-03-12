import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from gspread.utils import ValueInputOption
from html import escape
import time

# Local Imports
from plots import display_plot, display_normalized_sessions_plot
from core import client

# Google Sheet details
from core import SPREADSHEET_ID, SHEET_NAME, get_schedule_data, get_cover_requests_data, add_cover_request_data, get_surgeries_data, add_surgery_data, delete_surgery_data, get_pharmacists_data, add_pharmacist_data, delete_pharmacist_data, cancel_booking, update_booking, reject_cover_request


def _clean_string_values(df: pd.DataFrame, column: str) -> list[str]:
    if df.empty or column not in df.columns:
        return []

    cleaned = df[column].dropna().astype(str).str.strip()
    return sorted(value for value in cleaned.unique().tolist() if value)


def _normalize_schedule_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    normalized = df.copy()
    if "Date" not in normalized.columns:
        return pd.DataFrame()

    normalized["Date"] = pd.to_datetime(normalized["Date"], errors="coerce")
    normalized = normalized.dropna(subset=["Date"]).copy()

    if normalized.empty:
        return normalized

    if "am_pm" not in normalized.columns:
        normalized["am_pm"] = ""
    normalized["am_pm"] = normalized["am_pm"].fillna("").astype(str).str.strip().str.lower()

    fallback_slot_index = normalized.groupby(
        [normalized["Date"].dt.date, normalized["am_pm"]]
    ).cumcount()

    slot_index = pd.Series(float("nan"), index=normalized.index, dtype="float64")
    if "slot_index" in normalized.columns:
        slot_index = pd.to_numeric(normalized["slot_index"], errors="coerce")
    elif "pharm" in normalized.columns:
        slot_index = pd.to_numeric(normalized["pharm"], errors="coerce") - 1

    normalized["slot_index"] = slot_index.where(slot_index.notna(), fallback_slot_index).astype(int)

    pharmacist_names = pd.Series("", index=normalized.index, dtype="object")
    if "pharmacist_name" in normalized.columns:
        pharmacist_names = normalized["pharmacist_name"].fillna("").astype(str)
    elif "pharm" in normalized.columns:
        pharmacist_names = normalized["pharm"].fillna("").astype(str)

    pharmacist_names = pharmacist_names.str.strip()
    normalized["pharmacist_name"] = pharmacist_names.where(pharmacist_names != "", "None")

    return normalized


def _apply_app_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --app-ink: #1f2937;
            --app-muted: #64748b;
            --app-border: #dbe4ee;
            --app-surface: #f8fafc;
            --app-accent: #0f766e;
            --app-accent-soft: #e6fffb;
        }

        .stApp .block-container {
            padding-top: 3rem;
            padding-bottom: 2.75rem;
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
            padding-bottom: 1.75rem;
        }

        [data-testid="stForm"] {
            border: 1px solid var(--app-border);
            background: #ffffff;
            border-radius: 16px;
            padding: 0.85rem 0.9rem 1rem;
        }

        .stButton > button,
        .stForm button {
            border-radius: 12px;
            font-weight: 600;
        }

        .app-section {
            margin: 0.35rem 0 0.9rem;
        }

        .app-section-kicker {
            color: var(--app-accent);
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.15rem;
        }

        .app-section-title {
            color: var(--app-ink);
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .app-section-copy {
            color: var(--app-muted);
            font-size: 0.92rem;
            margin-top: 0.2rem;
        }

        .app-hero {
            background: linear-gradient(135deg, #eefaf8 0%, #f8fbfc 100%);
            border: 1px solid #cfe3e0;
            border-radius: 18px;
            color: var(--app-ink);
            margin: 0.25rem 0 1.25rem;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
        }

        .app-hero-kicker {
            color: var(--app-accent);
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .app-hero-title {
            font-size: 1.65rem;
            font-weight: 800;
            line-height: 1.15;
            margin-top: 0.25rem;
            color: var(--app-ink);
        }

        .app-hero-copy {
            color: var(--app-muted);
            font-size: 0.95rem;
            margin-top: 0.3rem;
        }

        .app-band {
            background: linear-gradient(135deg, #ecfeff 0%, #f8fafc 100%);
            border: 1px solid #cfe8e8;
            border-radius: 16px;
            margin: 1.15rem 0 1rem;
            padding: 0.85rem 1rem 0.9rem;
        }

        .app-band-kicker {
            color: var(--app-accent);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .app-band-title {
            color: var(--app-ink);
            font-size: 1.3rem;
            font-weight: 800;
            line-height: 1.15;
            margin-top: 0.18rem;
        }

        .app-band-copy {
            color: var(--app-muted);
            font-size: 0.94rem;
            margin-top: 0.22rem;
        }

        .slot-header {
            min-height: 2.9rem;
            display: flex;
            align-items: flex-end;
            margin-bottom: 0.5rem;
            font-size: 0.98rem;
            line-height: 1.2;
        }

        .slot-header--name {
            color: #b86200;
            font-size: 1.05rem;
            font-weight: 700;
        }

        .slot-header--available {
            color: var(--app-ink);
            font-weight: 700;
        }

        .slot-header--empty {
            color: transparent;
        }

        .slot-footer {
            min-height: 1.75rem;
            margin-top: 0.55rem;
            font-size: 0.92rem;
            line-height: 1.25;
        }

        .slot-footer--filled {
            color: #7c8699;
        }

        .slot-footer--empty {
            color: transparent;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_section_header(title: str, eyebrow: str | None = None, copy: str | None = None, *, sidebar: bool = False) -> None:
    target = st.sidebar if sidebar else st
    eyebrow_html = f"<div class='app-section-kicker'>{eyebrow}</div>" if eyebrow else ""
    copy_html = f"<div class='app-section-copy'>{copy}</div>" if copy else ""
    target.markdown(
        f"<div class='app-section'>{eyebrow_html}<div class='app-section-title'>{title}</div>{copy_html}</div>",
        unsafe_allow_html=True,
    )


def _render_section_band(title: str, eyebrow: str | None = None, copy: str | None = None) -> None:
    eyebrow_html = f"<div class='app-band-kicker'>{eyebrow}</div>" if eyebrow else ""
    copy_html = f"<div class='app-band-copy'>{copy}</div>" if copy else ""
    st.markdown(
        f"<div class='app-band'>{eyebrow_html}<div class='app-band-title'>{title}</div>{copy_html}</div>",
        unsafe_allow_html=True,
    )


def _render_slot_header(pharmacist_name: str | None, *, available_slot: bool) -> None:
    if pharmacist_name and pharmacist_name != "None":
        content = escape(str(pharmacist_name))
        css_class = "slot-header slot-header--name"
    elif available_slot:
        content = "Available"
        css_class = "slot-header slot-header--available"
    else:
        content = "&nbsp;"
        css_class = "slot-header slot-header--empty"

    st.markdown(f"<div class='{css_class}'>{content}</div>", unsafe_allow_html=True)


def _render_slot_footer(details: str | None = None) -> None:
    if details and str(details).strip():
        content = escape(str(details).strip())
        css_class = "slot-footer slot-footer--filled"
    else:
        content = "&nbsp;"
        css_class = "slot-footer slot-footer--empty"

    st.markdown(f"<div class='{css_class}'>{content}</div>", unsafe_allow_html=True)


def show_admin_panel(df):
    df = _normalize_schedule_data(df)
    unbook_mode = False  # Default value
    _render_section_header("Admin Options", eyebrow="Workspace", copy="Manage scheduling, directory data, and analytics.", sidebar=True)
    admin_tab = st.sidebar.radio("Admin Options", ["Manage Availability", "View Future Requests", "Manage Surgeries", "Manage Pharmacists", "Surgery Session Plots"], key="admin_options_radio", width="stretch")

    if admin_tab == "Surgery Session Plots":
        st.session_state.view = 'plot'
    elif admin_tab == "View Future Requests":
        st.session_state.view = 'future_requests'
    else:
        st.session_state.view = 'calendar'

    if admin_tab == "Manage Availability":
        _render_section_header("Manage Availability", eyebrow="Scheduling", copy="Assign pharmacist availability and protect booked slots.", sidebar=True)
        unbook_mode = st.sidebar.toggle("Unbook Mode", value=False, width="stretch")

        today = datetime.today().date()
        three_months_later = today + timedelta(days=90)

        availability_range = st.sidebar.slider(
            "Select date range for availability",
            min_value=today,
            max_value=three_months_later,
            value=(today, today + timedelta(weeks=4)),
            format="ddd, D MMM YYYY",
            width="stretch"
        )

        pharmacists_df = get_pharmacists_data()
        pharmacist_names = ["None", *_clean_string_values(pharmacists_df, "Name")]

        with st.sidebar.form("availability_form"):
            st.caption("Select the dates and pharmacist slots you want to publish.")

            start_date, end_date = availability_range
            dates_to_show = []
            current_date = start_date
            while current_date <= end_date:
                # convert to datetime before appending
                dates_to_show.append(datetime.combine(current_date, datetime.min.time()))
                current_date += timedelta(days=1)

            current_availability = {}
            if not df.empty:
                df_copy = df.copy()
                df_copy['Date'] = df_copy['Date'].dt.date
                for _, row in df_copy.iterrows():
                    key = (row['Date'], int(row['slot_index']), row['am_pm'])
                    current_availability[key] = {
                        'booked': str(row.get('booked', 'FALSE')).upper() == "TRUE",
                        'surgery': row.get('surgery', ''),
                        'email': row.get('email', ''),
                        'unique_code': row.get('unique_code', ''),
                        'pharmacist_name': row.get('pharmacist_name', 'None')
                    }

            get_cover_requests_data.clear()
            cover_requests_df = get_cover_requests_data()

            for date in dates_to_show:
                is_weekend = date.weekday() >= 5
                date_str = date.strftime('%A, %d %B')

                if is_weekend:
                    st.markdown(f":orange[{date_str} (Weekend)]")
                else:
                    st.markdown(f"**{date_str}**")

                    st.markdown("AM")
                    cols_am = st.columns(3)
                    for i, col in enumerate(cols_am):
                        with col:
                            shift_type = 'am'
                            slot_key = f"avail_{date.strftime('%Y%m%d')}_{shift_type}_{i}"

                            lookup_key = (date.date(), i, shift_type)
                            slot_info = current_availability.get(lookup_key, {'booked': False, 'pharmacist_name': 'None'})
                            is_booked = slot_info['booked']

                            default_pharmacist = slot_info.get('pharmacist_name', 'None')

                            current_options = list(pharmacist_names)
                            if is_booked and default_pharmacist not in current_options:
                                current_options.append(default_pharmacist)

                            if default_pharmacist not in current_options:
                                default_pharmacist = "None"

                            selected_pharmacist = st.selectbox(
                                "Pharmacist",
                                current_options,
                                index=current_options.index(default_pharmacist),
                                key=slot_key,
                                label_visibility="collapsed",
                                disabled=is_weekend or is_booked
                            )

                    st.markdown("PM")
                    cols_pm = st.columns(3)
                    for i, col in enumerate(cols_pm):
                        with col:
                            shift_type = 'pm'
                            slot_key = f"avail_{date.strftime('%Y%m%d')}_{shift_type}_{i}"

                            lookup_key = (date.date(), i, shift_type)
                            slot_info = current_availability.get(lookup_key, {'booked': False, 'pharmacist_name': 'None'})
                            is_booked = slot_info['booked']

                            default_pharmacist = slot_info.get('pharmacist_name', 'None')

                            current_options = list(pharmacist_names)
                            if is_booked and default_pharmacist not in current_options:
                                current_options.append(default_pharmacist)

                            if default_pharmacist not in current_options:
                                default_pharmacist = "None"

                            selected_pharmacist = st.selectbox(
                                "Pharmacist",
                                current_options,
                                index=current_options.index(default_pharmacist),
                                key=slot_key,
                                label_visibility="collapsed",
                                disabled=is_weekend or is_booked
                            )

                # Display existing cover requests for this date
                if 'cover_date' in cover_requests_df.columns and 'submission_timestamp' in cover_requests_df.columns:
                    daily_cover_requests = cover_requests_df[
                        cover_requests_df['cover_date'].dt.date == date.date()
                    ].sort_values(by='submission_timestamp')
                else:
                    daily_cover_requests = pd.DataFrame()

                if not daily_cover_requests.empty:
                    st.markdown("**Cover Requests:**")
                    for _, req_row in daily_cover_requests.iterrows():
                        request_uuid = str(req_row.get('uuid', '')).strip()
                        request_status = str(req_row.get('status', '') or 'Pending').strip()
                        requester_email = str(req_row.get('requester_email', '') or '').strip()
                        action_disabled = request_status.casefold() == 'rejected' or not requester_email or not request_uuid

                        info_col, action_col = st.columns([0.72, 0.28])
                        with info_col:
                            st.caption(f"- **{req_row['surgery']}** ({req_row['session']}) requested by {req_row['name']}")
                        with action_col:
                            if request_status.casefold() == 'rejected':
                                st.caption("Rejected")
                                reject_clicked = False
                            elif not requester_email:
                                st.caption("Email missing")
                                reject_clicked = False
                            else:
                                st.caption("Reject request")
                                reject_clicked = st.form_submit_button(
                                    "Reject",
                                    key=f"reject_cover_request_{request_uuid or req_row.name}",
                                    type="tertiary",
                                    disabled=action_disabled,
                                    use_container_width=True,
                                )

                        if reject_clicked and request_uuid:
                            if reject_cover_request(request_uuid):
                                time.sleep(0.3)
                                st.rerun()


            submitted = st.form_submit_button("Update Availability", type="primary", icon=":material/save:", use_container_width=True)
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

                            for i in range(3): # Number of pharmacist columns
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
        _render_section_header("Manage Surgeries", eyebrow="Directory", copy="Keep the surgery directory and list sizes up to date.", sidebar=True)
        with st.sidebar.form("add_surgery_form", clear_on_submit=True):
            new_surgery_name = st.text_input("Surgery Name")
            new_surgery_email = st.text_input("Email Address")
            new_list_size = st.number_input("List Size", min_value=0, step=1)
            add_surgery_submitted = st.form_submit_button("Add Surgery", type="primary", icon=":material/add:", use_container_width=True)

            if add_surgery_submitted:
                if new_surgery_name and new_surgery_email:
                    add_surgery_data(new_surgery_name, new_surgery_email, new_list_size)
                else:
                    st.error("Both surgery name and email are required.")

        st.sidebar.caption("Existing surgeries")
        surgeries_df = get_surgeries_data()
        if not surgeries_df.empty and {'surgery', 'email'}.issubset(surgeries_df.columns):
            surgeries_df = surgeries_df.assign(
                surgery_sort=surgeries_df["surgery"].fillna("").astype(str).str.strip().str.casefold()
            ).sort_values("surgery_sort", kind="stable")
            for idx, row in surgeries_df.iterrows():
                col1, col2 = st.sidebar.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**{row['surgery']}**<br>{row['email']}", unsafe_allow_html=True)
                with col2:
                    if st.button(":material/delete:", key=f"delete_surgery_{idx}", type="tertiary", use_container_width=True):
                        delete_surgery_data(row['surgery'], row['email'])
                        st.rerun()
        else:
            st.sidebar.info("No surgeries saved yet.")

    elif admin_tab == "Manage Pharmacists":
        _render_section_header("Manage Pharmacists", eyebrow="Directory", copy="Maintain the pharmacist list used across bookings and emails.", sidebar=True)
        with st.sidebar.form("add_pharmacist_form", clear_on_submit=True):
            new_pharmacist_name = st.text_input("Pharmacist Name")
            new_pharmacist_email = st.text_input("Pharmacist Email")
            add_pharmacist_submitted = st.form_submit_button("Add Pharmacist", type="primary", icon=":material/add:", use_container_width=True)

            if add_pharmacist_submitted:
                if new_pharmacist_name and new_pharmacist_email:
                    add_pharmacist_data(new_pharmacist_name, new_pharmacist_email)
                else:
                    st.error("Pharmacist name is required.")

        st.sidebar.caption("Existing pharmacists")
        pharmacists_df = get_pharmacists_data()
        if not pharmacists_df.empty and {'Name', 'Email'}.issubset(pharmacists_df.columns):
            pharmacists_df = pharmacists_df.assign(
                pharmacist_sort=pharmacists_df["Name"].fillna("").astype(str).str.strip().str.casefold()
            ).sort_values("pharmacist_sort", kind="stable")
            for idx, row in pharmacists_df.iterrows():
                col1, col2 = st.sidebar.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**{row['Name']}**<br>{row['Email']}", unsafe_allow_html=True)
                with col2:
                    if st.button(":material/delete:", key=f"delete_pharmacist_{idx}", type="tertiary", use_container_width=True):
                        delete_pharmacist_data(row['Name'], row['Email'])
                        st.rerun()
        else:
            st.sidebar.info("No pharmacists saved yet.")
    elif admin_tab == "Surgery Session Plots":
        _render_section_header("Surgery Session Plots", eyebrow="Analytics", copy="Switch between activity views using a single control.", sidebar=True)
        st.session_state.plot_type = st.sidebar.radio("Select Plot Type", ["Absolute Session Plot", "Normalized Sessions per 1000 pts", "Monthly Sessions"], width="stretch")
    elif admin_tab == "View Future Requests":
        _render_section_header("Future Cover Requests", eyebrow="Admin Review", copy="Requests from today onward ordered by submission time.")
        _render_section_header("Future Cover Requests", eyebrow="Requests", copy="Review upcoming requests from the sidebar workspace.", sidebar=True)
        get_cover_requests_data.clear()
        cover_requests_df = get_cover_requests_data()

        required_columns = {'cover_date', 'surgery', 'name', 'session', 'reason', 'desc', 'submission_timestamp', 'status'}
        if not cover_requests_df.empty and required_columns.issubset(cover_requests_df.columns):
            # Filter for requests from today and the future
            today = datetime.today().date()
            future_requests = cover_requests_df[
                (cover_requests_df['cover_date'].dt.date >= today)
            ].sort_values(by='submission_timestamp')

            if not future_requests.empty:
                st.dataframe(future_requests[['cover_date', 'surgery', 'name', 'session', 'reason', 'desc', 'status', 'submission_timestamp']], use_container_width=True)
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
    surgery_names = _clean_string_values(surgeries_df, "surgery")
    if not surgery_names:
        st.warning("No surgeries are configured yet. Add a surgery in the Admin Panel before booking.")
        return
    selected_surgery_option = st.selectbox(
        "Select Surgery",
        surgery_names,
        key=f"select_surgery_{slot['unique_code']}"
    )

    if "surgery" in surgeries_df.columns:
        selected_surgery_row = surgeries_df[surgeries_df["surgery"] == selected_surgery_option]
    else:
        selected_surgery_row = pd.DataFrame()

    prefilled_email = ""
    if "email" in surgeries_df.columns and not selected_surgery_row.empty:
        prefilled_email = str(selected_surgery_row["email"].iloc[0]).strip()

    st.text_input("Surgery Name", value=selected_surgery_option, disabled=True, key=f"display_surgery_{slot['unique_code']}_{selected_surgery_option}")
    st.text_input("Email Address", value=prefilled_email, disabled=True, key=f"display_email_{slot['unique_code']}_{selected_surgery_option}")

    current_surgery = selected_surgery_option
    current_email = prefilled_email

    action_left, action_right = st.columns(2)
    cancel_button = action_left.button("Cancel", type="secondary", use_container_width=True, key=f"cancel_booking_dialog_{slot['unique_code']}")
    submitted = action_right.button("Submit Booking", type="primary", icon=":material/check_circle:", use_container_width=True, key=f"submit_booking_dialog_{slot['unique_code']}")

    if submitted:
        if not current_surgery or not current_email:
            st.error("All fields are required.")
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
    surgery_names = _clean_string_values(surgeries_df, "surgery")
    if not surgery_names:
        st.warning("No surgeries are configured yet. Add one in the Admin Panel before submitting a cover request.")
        return

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
        requested_by_email = st.text_input(
            "Requester Email",
            key=f"cover_email_{cover_date.strftime('%Y%m%d')}"
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

        action_left, action_right = st.columns(2)
        cancel_button = action_left.form_submit_button("Cancel", type="secondary", use_container_width=True)
        submitted = action_right.form_submit_button("Submit Request", type="primary", icon=":material/send:", use_container_width=True)

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

            if not selected_surgery or not requested_by_name or not requested_by_email or not selected_session or not final_reason:
                st.error("All fields are required.")
            else:
                add_cover_request_data(cover_date, selected_surgery, requested_by_name, requested_by_email, selected_session, final_reason, final_description)
                time.sleep(0.2)
                st.rerun() # Rerun to close dialog and refresh main app

        if cancel_button:
            st.rerun() # Rerun to close dialog



st.set_page_config(page_title="Pharma-Cal Brompton Heatlh PCN", layout="centered", page_icon=":material/pill:")


def display_calendar(unbook_mode=False):
    _apply_app_theme()
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
                schedule_data = get_schedule_data()
                if 'surgery' in schedule_data.columns:
                    display_normalized_sessions_plot(lambda: schedule_data, get_surgeries_data)
                else:
                    st.warning("No surgery data to display.")





    st.logo('images/logo223.png', size="large")
    # --- Admin Sidebar ---

    password = st.sidebar.text_input("", type="password", placeholder="Admin Login", label_visibility="collapsed", icon=":material/settings:")  # Admin password input
    if password == '':
        st.sidebar.image('images/logo22.png')
    df = _normalize_schedule_data(get_schedule_data())

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
    st.markdown(
        """
        <div class="app-hero">
            <div class="app-hero-kicker">Brompton Health PCN</div>
            <div class="app-hero-title">Request a Pharmacist Session</div>
            <div class="app-hero-copy">Browse advertised sessions, book available slots, and submit requests beyond the current schedule.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if df.empty:
        st.info("No pharmacist shifts have been scheduled yet. Contact admin.")
        return

    # All data, sorted, will be the base for filtering
    df_sorted = df.sort_values(['Date', 'am_pm', 'slot_index'])

    # For 'future requests', we still need to know the last advertised date from today onwards.
    upcoming = df[df['Date'] >= datetime.today()].sort_values(['Date', 'am_pm', 'slot_index'])

    if upcoming.empty:
        st.info("No upcoming shifts available.")
        last_advertised_date = datetime.today().date() # If no upcoming, start from today
    else:
        last_advertised_date = upcoming['Date'].max().date()

    # Date range slider for timeframe visualization
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    min_data_date = df['Date'].min().date() if not df.empty else yesterday

    # The slider's start date can be the earlier of the first data point or yesterday.
    slider_min_date = min(min_data_date, yesterday)
    # The slider's max date is 3 months from today.
    slider_max_date = today + timedelta(days=90)

    default_start_date = max(slider_min_date, yesterday)
    default_date_range = (default_start_date, slider_max_date)
    current_day_key = today.isoformat()

    # Reset the default range once per day so stale session state does not keep an old start date.
    if st.session_state.get('date_range_initialized_for_day') != current_day_key:
        st.session_state.date_range = default_date_range
        st.session_state.date_range_initialized_for_day = current_day_key

    _render_section_header("Available Sessions", eyebrow="Schedule", copy="Filter the live rota and book an available pharmacist slot.")
    selected_range = st.slider(
        "Select a date range to view",
        min_value=slider_min_date,
        max_value=slider_max_date,
        value=st.session_state.date_range,
        format="ddd, D MMM YYYY",
        width="stretch"
    )
    st.session_state.date_range = selected_range

    # Filter schedule based on the selected date range
    schedule_filtered = df_sorted[
        (df_sorted['Date'].dt.date >= selected_range[0]) &
        (df_sorted['Date'].dt.date <= selected_range[1])
    ]

    # Display existing pharmacist schedule
    if schedule_filtered.empty:
        st.info("No shifts available in the selected date range.")

    for date, daily in schedule_filtered.groupby(schedule_filtered['Date'].dt.date):
        if date.weekday() >= 5: # Skip weekends for advertised dates
            continue

        st.subheader(f"{date.strftime('%A, %d %B %Y')}")

        # AM Shift
        st.markdown("**AM**")
        am_slots = daily[daily['am_pm'] == 'am']
        am_cols = st.columns(3)
        for i in range(3):
            with am_cols[i]:
                slot_data = am_slots[am_slots['slot_index'] == i]
                if not slot_data.empty:
                    row = slot_data.iloc[0]
                    pharmacist_name = row['pharmacist_name']
                    _render_slot_header(pharmacist_name, available_slot=True)

                    booked = str(row['booked']).upper() == "TRUE"
                    footer_details = row['surgery'] if booked else None
                    btn_label = "09:00 - 12:45"
                    unique_key = f"{row['unique_code']}_{pharmacist_name}_{i}_am"

                    if unbook_mode:
                        if booked:
                            if st.button(btn_label + " (Cancel)", key=unique_key, type="secondary", use_container_width=True):
                                cancel_booking(row.to_dict())
                        else:
                            st.button(btn_label, key=unique_key, disabled=True, use_container_width=True)
                    else:
                        if booked:
                            st.button(btn_label + " (Booked)", key=unique_key, disabled=True, use_container_width=True)
                        else:
                            if st.button(btn_label, key=unique_key, type="primary", use_container_width=True):
                                show_booking_dialog(row.to_dict())
                    _render_slot_footer(footer_details)
                else:
                    _render_slot_header(None, available_slot=False)
                    st.button("Not Available", disabled=True, key=f"empty_{date.strftime('%Y%m%d')}_am_{i}", use_container_width=True)
                    _render_slot_footer()

        # PM Shift
        st.markdown("**PM**")
        pm_slots = daily[daily['am_pm'] == 'pm']
        pm_cols = st.columns(3)
        for i in range(3):
            with pm_cols[i]:
                slot_data = pm_slots[pm_slots['slot_index'] == i]
                if not slot_data.empty:
                    row = slot_data.iloc[0]
                    pharmacist_name = row['pharmacist_name']
                    _render_slot_header(pharmacist_name, available_slot=True)

                    booked = str(row['booked']).upper() == "TRUE"
                    footer_details = row['surgery'] if booked else None
                    btn_label = "13:15 - 17:00"
                    unique_key = f"{row['unique_code']}_{pharmacist_name}_{i}_pm"

                    if unbook_mode:
                        if booked:
                            if st.button(btn_label + " (Cancel)", key=unique_key, type="secondary", use_container_width=True):
                                cancel_booking(row.to_dict())
                        else:
                            st.button(btn_label, key=unique_key, disabled=True, use_container_width=True)
                    else:
                        if booked:
                            st.button(btn_label + " (Booked)", key=unique_key, disabled=True, use_container_width=True)
                        else:
                            if st.button(btn_label, key=unique_key, type="primary", use_container_width=True):
                                show_booking_dialog(row.to_dict())
                    _render_slot_footer(footer_details)
                else:
                    _render_slot_header(None, available_slot=False)
                    st.button("Not Available", disabled=True, key=f"empty_{date.strftime('%Y%m%d')}_pm_{i}", use_container_width=True)
                    _render_slot_footer()

        st.divider()

    # Add functionality for Practice Managers to submit booking requests beyond the advertised date
    _render_section_band("Submit Future Requests", eyebrow="Beyond Advertised Dates", copy="Request support for sessions that are not yet on the rota.")
    start_date_beyond = last_advertised_date + timedelta(days=1)
    end_date_beyond = selected_range[1]

    get_cover_requests_data.clear()
    cover_requests_df = get_cover_requests_data()

    current_date_beyond = start_date_beyond
    while current_date_beyond <= end_date_beyond:
        if current_date_beyond.weekday() < 5: # Only show weekdays
            st.markdown(f"**{current_date_beyond.strftime('%A, %d %B %Y')}**")

            # Display existing cover requests for this date
            if 'cover_date' in cover_requests_df.columns and 'submission_timestamp' in cover_requests_df.columns:
                daily_cover_requests = cover_requests_df[
                    cover_requests_df['cover_date'].dt.date == current_date_beyond
                ].sort_values(by='submission_timestamp')
            else:
                daily_cover_requests = pd.DataFrame()

            if not daily_cover_requests.empty:
                for _, req_row in daily_cover_requests.iterrows():
                    submission_time_str = req_row['submission_timestamp'].strftime('%d %b %y %H:%M') if pd.notna(req_row['submission_timestamp']) else "N/A"
                    st.caption(f"**{req_row['surgery']}** requested by {req_row['name']} at {submission_time_str}")
                    if password == st.secrets["admin_password"]: # Check if admin is logged in
                        st.caption(f"Session: {req_row['session']} | Reason: {req_row['reason']} | Description: {req_row['desc']}")
                    # Removed the description caption as per user's implicit feedback (it was removed from the example)

            if st.button("Request Cover", key=f"interest_{current_date_beyond.strftime('%Y%m%d')}", icon=":material/event_upcoming:", type="primary", use_container_width=True):
                show_cover_request_dialog(current_date_beyond)
            st.divider()
        current_date_beyond += timedelta(days=1)

if __name__ == "__main__":
    display_calendar()

    st.sidebar.html("""<BR><BR><BR><BR><BR><BR><center><img alt="Static Badge" src="https://img.shields.io/badge/GitHub-janduplessis883-%23316576"></center>""")
