# Pharma-Cal: Pharmacist Session Booking Application

Pharma-Cal is a Streamlit-based application designed to streamline the booking and management of pharmacist sessions for the Brompton Health PCN. It provides a user-friendly interface for surgeries to book available pharmacist slots and a comprehensive admin panel for managing availability, surgeries, and pharmacists. The application integrates with Google Sheets for data storage and Resend for email notifications, including calendar invites.

## Application Overview

The core purpose of Pharma-Cal is to facilitate the scheduling of pharmacist sessions. It displays a calendar of available slots, allows for new bookings, and provides administrative tools for managing the underlying data.

### Key Features:

1.  **Pharmacist Session Calendar:**
    *   Displays upcoming pharmacist availability by date, showing both AM (09:00 - 12:45) and PM (13:15 - 17:00) slots.
    *   Clearly indicates which pharmacist is assigned to each slot.
    *   Visually distinguishes between available and already booked sessions.
    *   Includes a "Release Schedule" popover to inform users about communal session release dates.
    *   Provides a user guide popover for quick reference.

2.  **Seamless Booking System:**
    *   Allows authorized surgeries to book an available pharmacist slot with a single click.
    *   Presents a booking dialog where users can select from pre-registered surgeries or add new surgery details on the fly.
    *   Requires surgery name and email for each booking.
    *   Automatically sends confirmation emails to both the booking surgery and the assigned pharmacist.
    *   Each confirmation email includes an attached `.ics` calendar file, allowing easy addition of the session to personal calendars (e.g., Outlook).

3.  **Comprehensive Admin Panel:**
    *   A password-protected section (`super user`) accessible from the sidebar, offering robust management capabilities.
    *   **Manage Availability:**
        *   Admins can view and modify pharmacist availability for a specified number of weeks.
        *   Allows assigning specific pharmacists to AM/PM slots on any given day.
        *   Features an "Unbook Mode" to easily cancel existing bookings, which also triggers cancellation emails to relevant parties.
        *   Updates the main schedule data in Google Sheet (Sheet1).
    *   **Manage Surgeries:**
        *   Enables adding new surgery entries, including their name, email address, and list size (number of patients).
        *   Provides a list of all registered surgeries with the option to delete them.
        *   Manages surgery data in Google Sheet (Sheet2).
    *   **Manage Pharmacists:**
        *   Facilitates adding new pharmacist profiles with their name and email.
        *   Displays a list of all registered pharmacists with the option to remove them.
        *   Manages pharmacist data in Google Sheet (Sheet3).
    *   **Surgery Session Plots:**
        *   Generates visual analytics of booked sessions.
        *   Offers two types of plots:
            *   **Absolute Session Plot:** Shows the total number of sessions booked per surgery.
            *   **Normalized Sessions per 1000 pts:** Normalizes session counts by surgery list size, providing insights into session distribution relative to patient population. (Requires list size data to be entered for each surgery).

## How to Use the Application

### For General Users (Surgeries):

1.  **Access the Application:** Open the Pharma-Cal Streamlit application in your web browser.
2.  **View Available Sessions:** The main screen displays a calendar-like view of upcoming dates. For each date, you will see available AM and PM slots, along with the name of the pharmacist assigned to that slot.
3.  **Identify Booked Slots:** Slots marked as "(Booked)" are unavailable.
4.  **Book a Session:** Click on any available slot (not marked as "Booked").
5.  **Complete Booking Details:**
    *   A "Booking Details" dialog will appear.
    *   **Select Surgery:** Choose your surgery from the dropdown list. If your surgery is not listed, select "Add New Surgery".
    *   **Add New Surgery (if applicable):** If you selected "Add New Surgery", enter your "New Surgery Name" and "New Email Address" in the provided fields.
    *   **Submit:** Click the "Submit Booking" button.
6.  **Confirmation:** Upon successful booking, you will see a confirmation message. You will also receive an email with the booking details and a calendar invite.

### For Administrators:

1.  **Access Admin Panel:**
    *   Locate the password input field in the sidebar (labeled "Admin Login").
    *   Enter the password: `super user`
    *   The sidebar will expand to show "Admin Options".
2.  **Navigate Admin Sections:** Use the radio buttons in the sidebar to switch between different admin functionalities:
    *   **Manage Availability:**
        *   **Toggle "Unbook Mode":** If you need to cancel a booking, switch this toggle to "On". When "Unbook Mode" is active, booked slots will appear with a "Cancel" button. Clicking this button will cancel the booking and send cancellation emails.
        *   **Set Number of Weeks:** Use the slider to determine how many weeks of availability are displayed for management.
        *   **Update Slots:** For each date and shift (AM/PM), use the dropdown to assign a pharmacist or set the slot to "None" to make it unavailable.
        *   **Submit Changes:** Click "Update Availability" to save your changes to the Google Sheet.
    *   **Manage Surgeries:**
        *   **Add New Surgery:** Use the "Add New Surgery" form to input the "Surgery Name", "Email Address", and "List Size" (patient count) for a new surgery. Click "Add Surgery".
        *   **View/Delete Existing:** Review the list of existing surgeries. Click the ":material/delete:" button next to a surgery to remove it from the system.
    *   **Manage Pharmacists:**
        *   **Add New Pharmacist:** Use the "Add New Pharmacist" form to input the "Pharmacist Name" and "Pharmacist Email". Click "Add Pharmacist".
        *   **View/Delete Existing:** Review the list of existing pharmacists. Click the ":material/delete:" button next to a pharmacist to remove them from the system.
    *   **Surgery Session Plots:**
        *   Select "Absolute Session Plot" to see the raw count of sessions per surgery.
        *   Select "Normalized Sessions per 1000 pts" to view sessions adjusted by surgery list size. Ensure list size data is accurate in "Manage Surgeries" for this plot type.

## Data Storage and Integrations

*   **Google Sheets:** All application data, including pharmacist schedules, surgery details, and pharmacist information, is securely stored and managed within Google Sheets.
*   **Resend API:** Used for sending all email communications, including booking confirmations and cancellations.
*   **ICS Calendar Files:** Automatically generated and attached to booking confirmation emails, allowing users to easily add sessions to their digital calendars.

This detailed document should provide a comprehensive understanding of the Pharma-Cal application's features and usage.
