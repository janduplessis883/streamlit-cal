# Streamlit Pharmacist Booking Calendar

This is a Streamlit web application that provides a simple and interactive calendar system for booking pharmacist sessions. The application uses Google Sheets as a backend to store and manage availability, bookings, and related data like surgeries and pharmacists.

![Pharm-cal](images/admin.png)

## Features

- **Interactive Calendar View**: Displays available pharmacist sessions for the next two months.
- **Booking System**: Users can click on an available slot to book a session.
- **Dynamic Booking Form**: A dialog appears to enter booking details, including selecting an existing surgery or adding a new one.
- **Admin Panel**: A password-protected admin section to manage the application's data.
- **Availability Management**: Admins can update pharmacist availability for AM/PM shifts.
- **Surgery Management**: Admins can add and delete surgery locations and their contact emails.
- **Pharmacist Management**: Admins can add and delete pharmacists from the system.
- **Google Sheets Backend**: All data is stored and read from a Google Sheet, making it easy to view and manage data outside the app.

## How to Run

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd streamlit-cal
    ```

2.  **Install dependencies:**
    Make sure you have Python installed. Then, install the required packages using the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Google Sheets API credentials:**
    - Follow the instructions [here](https://docs.streamlit.io/knowledge-base/tutorials/databases/gsheets) to get your Google Sheets API credentials JSON file.
    - Create a `.streamlit` directory if it doesn't exist.
    - Create a `secrets.toml` file inside the `.streamlit` directory.
    - Add your Google Sheets credentials to the `secrets.toml` file in the following format:
      ```toml
      # .streamlit/secrets.toml
      [gsheets]
      type = "service_account"
      project_id = "your-project-id"
      private_key_id = "your-private-key-id"
      private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
      client_email = "your-service-account-email@your-project-id.iam.gserviceaccount.com"
      client_id = "your-client-id"
      auth_uri = "https://accounts.google.com/o/oauth2/auth"
      token_uri = "https://oauth2.googleapis.com/token"
      auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
      client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email%40your-project-id.iam.gserviceaccount.com"
      ```

4.  **Set up the Google Sheet:**
    - Create a new Google Sheet.
    - Get the Spreadsheet ID from the URL (`https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`).
    - Update the `SPREADSHEET_ID` constant in `app.py` with your ID.
    - Share the Google Sheet with the `client_email` from your credentials file.
    - The application will automatically create the necessary sheets (`Sheet1`, `Sheet2`, `Sheet3`) and headers if they don't exist.

5.  **Run the Streamlit app:**
    ```bash
    streamlit run app.py
    ```

## Admin Access

To access the admin panel, use the password.

## Dependencies

- `streamlit`
- `pandas`
- `gspread`
- `google-oauth2-service-account`
