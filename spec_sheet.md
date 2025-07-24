# Project Spec Sheet: Streamlit Pharmacist Booking Calendar

## 1. Overview

This document outlines the specifications for the Streamlit Pharmacist Booking Calendar, a web application designed to facilitate the scheduling of pharmacist sessions for medical surgeries. The application provides a user-friendly interface for viewing available slots and a password-protected admin panel for managing the schedule, pharmacists, and surgeries.

The system uses Google Sheets as its database, making it easy for non-technical users to view and manage data directly if needed.

## 2. Core Features

### 2.1. User-Facing Features

- **Calendar Display**: Users can view upcoming available pharmacist sessions, grouped by date and pharmacist.
- **Real-time Availability**: The calendar shows which slots are available and which are already booked. Booked slots are disabled and display the name of the surgery that made the booking.
- **Booking Process**:
    - Users can click on an available time slot to open a booking dialog.
    - They can select their surgery from a pre-populated list or add a new surgery on the fly.
    - Upon submission, the selected slot is marked as booked in the backend.
- **Email Confirmations**:
    - **To the Surgery**: An email is automatically sent to the surgery's email address, confirming the booking details. This email includes an `.ics` calendar file to easily add the appointment to their calendar.
    - **To the Pharmacist**: An email notification is sent to the booked pharmacist, informing them of the new session, including the surgery's name and contact details.

### 2.2. Admin Panel Features

The admin panel is accessible via a password entered in the sidebar.

- **Manage Availability**:
    - Admins can view and manage the pharmacist schedule for a configurable number of weeks.
    - They can assign a specific pharmacist to an AM or PM slot on any given day, effectively making that slot available for booking.
    - Booked slots are disabled to prevent accidental changes, but they correctly display the name of the assigned pharmacist.
- **Manage Surgeries**:
    - Admins can add new surgeries with their corresponding email addresses.
    - They can view a list of all existing surgeries and delete them as needed.
- **Manage Pharmacists**:
    - Admins can add new pharmacists with their names and email addresses.
    - They can view a list of all existing pharmacists and delete them. The system handles cases where a deleted pharmacist is still assigned to a booked slot, ensuring the schedule display remains accurate.

## 3. Technical Specifications

- **Frontend**: Streamlit
- **Backend Logic**: Python
- **Database**: Google Sheets
    - **Sheet1 (`Sheet1`)**: Stores the main schedule, including dates, shifts (AM/PM), assigned pharmacist, and booking status.
    - **Sheet2 (`Sheet2`)**: A list of all surgeries and their email addresses.
    - **Sheet3 (`Sheet3`)**: A list of all pharmacists and their email addresses.
- **Email Service**: [Resend](https://resend.com/) API for transactional emails.
- **Authentication**:
    - **Google Sheets**: Service Account credentials.
    - **Admin Panel**: A simple password check.

## 4. Data Model (Google Sheets)

### Sheet1: `Sheet1` (Schedule)
| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `unique_code` | String | A unique identifier for the time slot. | `1672531200-am-0` |
| `Date` | String | The date of the slot in `YYYY-MM-DD` format. | `2024-08-15` |
| `am_pm` | String | The shift type, either "am" or "pm". | `am` |
| `booked` | String | "TRUE" or "FALSE" indicating booking status. | `TRUE` |
| `surgery` | String | The name of the surgery that booked the slot. | `The Health Centre` |
| `email` | String | The email of the surgery that booked the slot. | `contact@health.com` |
| `pharmacist_name`| String | The name of the assigned pharmacist. | `John Doe` |
| `slot_index` | Integer| A zero-based index for the slot within the day. | `0` |

### Sheet2: `Sheet2` (Surgeries)
| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `surgery` | String | The name of the surgery. | `The Health Centre` |
| `email` | String | The contact email for the surgery. | `contact@health.com` |

### Sheet3: `Sheet3` (Pharmacists)
| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `Name` | String | The full name of the pharmacist. | `John Doe` |
| `Email` | String | The contact email for the pharmacist. | `j.doe@pharmacist.com`|

## 5. Setup & Configuration

The application requires a `.streamlit/secrets.toml` file with the following structure:

```toml
# Google Sheets API Credentials
[gsheets]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "..."
client_email = "..."
# ... (and other fields from the service account JSON)

# Resend API Key
[resend]
RESEND_API_KEY="re_xxxxxxxxxxxx"

# Admin Panel Password
[password]
ADMIN_PASSWORD="your_secure_password_here"
```