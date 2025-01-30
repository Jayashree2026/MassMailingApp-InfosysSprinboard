import streamlit as st
import pandas as pd
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pymysql
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
from google.auth.transport.requests import Request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import logging
from streamlit_option_menu import option_menu

# APScheduler Scheduler
scheduler = BackgroundScheduler()

if not scheduler.running:
    scheduler.start()

# SCOPES for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

#Database connection
def get_db_connection():
    """Establish a connection to the database."""
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='602696',
            database='mail_app'
        )
        return conn
    except pymysql.MySQLError as e:
        st.error(f"Database connection error: {e}")
        return None
#Function to get user details    
def fetch_user_details(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, is_enabled FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                # Return user details as a dictionary, including the user_id
                user_details = {"user_id": result[0], "username": result[1], "is_enabled": result[2]}
                return user_details
            else:
                return None  # Return None if no record is found
        except Exception as e:
            st.error(f"Database connection error: {e}")
            return None

        
# Function to authenticate Gmail API
def authenticate_gmail_api():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)  # Path to your credentials file
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def log_email_stats(user_id, to_emails,cc,bcc):
    """Logs email statistics for each user, ensuring that only unique recipients are counted."""
    conn = get_db_connection()
    if conn:
        try:
            # Ensure unique email addresses (normalize by stripping spaces and making lowercase)
            unique_emails = list(set(email.strip().lower() for email in to_emails.split(',')))
            uniqcc_emails = list(set(email.strip().lower() for email in cc.split(',')))
            uniqbcc_emails = list(set(email.strip().lower() for email in bcc.split(',')))
            num_sent_emails = len(unique_emails)+len(uniqbcc_emails)+len(uniqcc_emails)
            st.write(f"Unique Recipients: {unique_emails}, Count: {num_sent_emails}")

            # Insert into email_stats table (if it's the first time, create a new entry)
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO email_stats (user_id, sent, delivered, inbox) 
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        sent = sent + %s, delivered = delivered + %s, inbox = inbox + %s
                """, (user_id, num_sent_emails, num_sent_emails, num_sent_emails, 
                      num_sent_emails, num_sent_emails, num_sent_emails))
                conn.commit()

        except Exception as e:
            st.error(f"Error logging email stats: {e}")
        finally:
            conn.close()

# Function to send email using Gmail API
def send_email(service, from_email, to_emails, subject, body, user_id, cc=None, bcc=None):
    if not user_id or user_id == '':
        st.error("Invalid user ID provided. Cannot send email.")
        return None  # Prevent further processing if user_id is invalid

    try:
        message = MIMEMultipart()
        message["From"] = from_email
        message["To"] = to_emails
        message["Subject"] = subject
        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc

        message.attach(MIMEText(body, "plain"))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send email via Gmail API
        send_message = service.users().messages().send(
            userId="me", body={'raw': raw_message}
        ).execute()

        # Log email statistics after sending the email
        log_email_stats(user_id, to_emails,cc,bcc)

        return send_message
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


# Configure logging for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_scheduled_email(email_id):
    """
    This function runs as a scheduled job to send emails.
    """
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to the database.")
        return

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Fetch email details
        cursor.execute("SELECT * FROM scheduled_emails WHERE id = %s AND status = 'Pending'", (email_id,))
        email = cursor.fetchone()

        if not email:
            logger.warning(f"No pending email found for ID: {email_id}.")
            return

        # Fetch sender's email details
        user_details = fetch_user_details(email['user_id'])
        if not user_details or not user_details.get('username'):
            logger.error("Failed to fetch sender details.")
            return

        from_address = user_details['username']

        # Authenticate and send the email
        service = authenticate_gmail_api()
        result = send_email(
            service,
            from_address,
            email['to_emails'],
            email['subject'],
            email['body'],
            email['user_id'],
            email['cc'],
            email['bcc']
        )

        # Update status to 'Sent' if email was successfully sent
        if result:
            cursor.execute("UPDATE scheduled_emails SET status = 'Sent' WHERE id = %s",
                           (email_id,))
            conn.commit()
            logger.info(f"Email ID {email_id} sent successfully.")
        else:
            logger.error(f"Failed to send email ID {email_id}.")
    except Exception as e:
        logger.error(f"Error sending scheduled email: {e}")
    finally:
        cursor.close()
        conn.close()



# Schedule an email
def schedule_email_with_apscheduler(user_id,to_emails, subject, body, schedule_time, cc=None, bcc=None):
    conn = get_db_connection()
    if conn:
        try:

            if cc and isinstance(cc, list):
                cc = ",".join(cc)
            if bcc and isinstance(bcc, list):
                bcc = ",".join(bcc)
            # Save the email to the database with status 'Pending'
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO scheduled_emails (user_id,to_emails, subject, body, cc, bcc, schedule_time, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id,(to_emails), subject, body, cc, bcc, schedule_time, 'Pending'))
                conn.commit()
                email_id = cursor.lastrowid

            # Schedule the job using APScheduler
            trigger = DateTrigger(run_date=schedule_time)
            scheduler.add_job(
                send_scheduled_email,
                trigger,
                args=[email_id],
                id=f"email_{email_id}",
                misfire_grace_time=3600  # Allow 1-hour grace period for missed jobs
            )

            st.success("Email scheduled successfully!")
        except Exception as e:
            st.error(f"Error scheduling email: {e}")
        finally:
            conn.close()

def generate_scheduled_email_reports():
    schcss = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Delius+Unicase:wght@400;700&family=DynaPuff:wght@400..700&family=Funnel+Sans:ital,wght@0,300..800;1,300..800&display=swap');
                
        [data-testid="stApp"]{
        background-color:white;
        color:black;}
        h1{
        font-family: 'Delius Unicase', cursive;}
        h3{
        font-family: 'DanPuff', sans-serif;}
        [data-testid="stSidebarContent"]{
        background-color:#4f6367;}

        [data-testid="stHeader"]{
        background-color:black;
        }
        [data-testid="stBaseButton-secondary"]{
        border:2px solid black;
        }
        [data-testid="stSidebarUserContent"]{
        border-radius:5px;}

        [class="st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7"]{
        border:2px solid black;
        border-radius:5px;}
        
        [data-testid="stDataFrame"]{
        width:700px;
         border:2px solid black;
        border-radius:5px;}
        text-align:center;
        }
        [class="marks"]{
        border:2px solid black;
        border-radius:5px;}
        .st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7{
        background-color:white;
        }
        [data-testid="stTextInputRootElement"]{
        border:2px solid black;
        background-color:white;}
        [class="st-ah"]{
        border:2px solid black;
        background-color:white;}
       
        </style>
        """
    st.markdown(schcss,unsafe_allow_html=True)
    st.title("Scheduled Email Reports")
    st.markdown("Manage your scheduled emails below.")
    
    # Database connection
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM scheduled_emails")
            emails = cursor.fetchall()

            if emails:
                # Create a DataFrame from the scheduled emails
                df = pd.DataFrame(emails)

                # Display the DataFrame
                st.dataframe(df)

                # Display a bar chart of email statuses
                st.bar_chart(df.groupby('status')['id'].count())

            else:
                st.warning("No scheduled emails found.")
            
            # Add a section to delete an email by ID
            st.subheader("Delete Scheduled Email by ID")
            email_id_to_delete = st.text_input("Enter the Email ID to delete")
            
            if st.button("Delete Email"):
                if email_id_to_delete:
                    try:
                        # Ensure the ID is an integer
                        email_id_to_delete = int(email_id_to_delete)
                        
                        # Check if the email ID exists in the database
                        cursor.execute("SELECT * FROM scheduled_emails WHERE id = %s", (email_id_to_delete,))
                        email = cursor.fetchone()
                        
                        if email:
                            # Delete the email from the scheduled_emails table
                            cursor.execute("DELETE FROM scheduled_emails WHERE id = %s", (email_id_to_delete,))
                            conn.commit()
                            st.success(f"Email with ID {email_id_to_delete} has been deleted successfully.")
                            
                        else:
                            st.warning(f"No email found with ID {email_id_to_delete}. Please check the ID.")
                    except ValueError:
                        st.error("Please enter a valid email ID.")
                    except Exception as e:
                        st.error(f"Error deleting email with ID {email_id_to_delete}: {e}")
                else:
                    st.warning("Please enter an email ID to delete.")
        except Exception as e:
            st.error(f"Error fetching scheduled email reports: {e}")
        finally:
            conn.close()

   


#Function to display email dashboard
def email_dashboard():
    sendcss = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Delius+Unicase:wght@400;700&family=DynaPuff:wght@400..700&family=Funnel+Sans:ital,wght@0,300..800;1,300..800&display=swap');
                
        [data-testid="stApp"]{
        background-color:white;
        color:black;}
        [data-testid="stBaseButton-secondary"]{
        border:2px solid black;
        }
        h1{
        font-family: 'Delius Unicase', cursive;}
        h3{
        font-family: 'DanPuff', sans-serif;}
        [data-testid="stSidebarContent"]{
        background-color:#4f6367;}

        [data-testid="stHeader"]{
        background-color:black;
        }
        [data-testid="stSidebarUserContent"]{
        border-radius:5px;}
        [class="st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7"]{
        border:2px solid black;
        border-radius:5px;}
        [class="st-bt st-bu st-bv st-bw st-bx st-by st-c5 st-bz st-c7"]{
        border:2px solid black;
        border-radius:5px;
        }
        [class="st-c7"]{
        border:2px solid black;
        border-radius:5px;
        }
        [data-testid="stTextAreaRootElement"]{
        border:2px solid black;
        border-radius:5px;
        } 
        [data-testid="stFileUploaderDropzone"]{
        border:2px solid black;
        border-radius:5px;
        }
        [data-testid="stDataFrame"]{
        width:700px;
         border:2px solid black;
        border-radius:5px;}
        text-align:center;
        }
        [class="marks"]{
        border:2px solid black;
        border-radius:5px;}
        .st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7{
        background-color:white;
        }
        [data-testid="stTextInputRootElement"]{
        border:2px solid black;
        background-color:white;}
       
        </style>
        """
    st.markdown(sendcss,unsafe_allow_html=True)
    st.title("Email Dashboard")

    # Use Streamlit session state to keep track of fetched user details
    if 'user_details' not in st.session_state:
        st.session_state['user_details'] = None

    # Always display Compose Email Form
    st.subheader("Compose Email")

    # Input for User ID
    user_id = st.text_input("Enter User ID to fetch details", key="userid")
    user_details = st.session_state.get('user_details')

    # Fetch and display user details when button is clicked
    if st.button("Fetch User Details"):
        if user_id:
            user_details = fetch_user_details(user_id)
            if user_details:
                if user_details.get('is_enabled') == 0:
                    st.warning("This user is not enabled for sending emails.")
                    st.session_state['user_details'] = None  # Disable further processing
                else:
                    st.session_state['user_details'] = user_details
                    st.success(f"Fetched details for user: {user_details['username']}")
                    st.write(f"**Email Address (From):** {user_details['username']}")
                    st.write(f"**User ID:** {user_details['user_id']}")  # Display the fetched user ID
            else:
                st.error("User not found.")
        else:
            st.warning("Please enter a valid User ID.")

    # Ensure user details are available in session state
    user_details = st.session_state['user_details']
    if user_details:
        from_address = user_details['username']
        user_id = user_details['user_id']

        # CSV Upload Sections for To, CC, and BCC
        st.subheader("Upload Contacts")
        
        # To Address Upload
        st.markdown("### To Address")
    
        to_addresses = st.text_input("To")

        # CC Address Upload
        st.markdown("### CC Address")

        cc_uploaded_file = st.file_uploader("Choose a CSV file for CC", type=["csv"], key="cc_upload")
        cc_addresses = []
        if cc_uploaded_file:
            try:
                cc_df = pd.read_csv(cc_uploaded_file)
                if 'username' in cc_df.columns:
                    cc_addresses = cc_df['username'].tolist()
                    st.write("CC Addresses:")
                    st.dataframe(cc_df)
                else:
                    st.error("The CSV file must contain an 'username' column.")
            except Exception as e:
                st.error(f"Error reading CC CSV file: {e}")
        else:
            cc_addresses = st.text_input("Cc")

        # BCC Address Upload
        st.markdown("### BCC Address")
        bcc_uploaded_file = st.file_uploader("Choose a CSV file for BCC", type=["csv"], key="bcc_upload")
        bcc_addresses = []
        if bcc_uploaded_file:
            try:
                bcc_df = pd.read_csv(bcc_uploaded_file)
                if 'username' in bcc_df.columns:
                    bcc_addresses = bcc_df['username'].tolist()
                    st.write("BCC Addresses:")
                    st.dataframe(bcc_df)
                else:
                    st.error("The CSV file must contain an 'username' column.")
            except Exception as e:
                st.error(f"Error reading BCC CSV file: {e}")
        else:
            bcc_addresses = st.text_input("Bcc")
        
         #Manual Inputs for Subject, Body, and Signature
        subject = st.text_input(
            "Subject", 
            value=st.session_state.get('selected_subject', '')  # Pre-load if a template is selected
        )

        # Template Dropdown in email_dashboard
        st.subheader("Choose a Template")
        conn = get_db_connection()
        body = ""  # Initialize body variable

        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT template_name, template_content FROM templates WHERE user_id = %s or superuser=1", (user_id,))
                templates = cursor.fetchall()
                
                if templates:
                    # Create a dictionary of templates
                    template_dict = {name: content for name, content in templates}
                    
                    # Dropdown for template selection
                    selected_template = st.selectbox("Choose a Template", ["Select a template"] + list(template_dict.keys()))
                    
                    if selected_template and selected_template != "Select a template":
                        # Display the selected template's content
                        st.session_state['selected_template'] = template_dict[selected_template]
                        st.write("Selected Template Content:")
                        st.markdown(template_dict[selected_template], unsafe_allow_html=True)
                        # Pre-fill the body with the selected template's content
                        body = st.text_area("Body", value=template_dict[selected_template])
                    else:
                        # If no template is selected, allow manual body entry
                        body = st.text_area("Body", placeholder="Enter your email content here.")
                else:
                    st.warning("No templates found for this user.")
                    body = st.text_area("Body", placeholder="Enter your email content here.")
            except Exception as e:
                st.error(f"Database error: {e}")
            finally:
                cursor.close()
                conn.close()
        else:
            st.error("Failed to connect to the database.")
            body = st.text_area("Body", placeholder="Enter your email content here.")
    
        signature = st.text_area(
            "Signature", 
            value=st.session_state.get('selected_signature', '') if 'selected_signature' in st.session_state else ''
        )
        

        # Send Email Button
        if st.button("Send Email"):
            if to_addresses:
                full_body = body + f"\n\n{signature}" if signature else body
                try:
                    service = authenticate_gmail_api()
                    send_email(service, from_address, to_addresses, subject, full_body, user_id, ",".join(cc_addresses), ",".join(bcc_addresses))
                    st.success("Email sent successfully!")
                except Exception as e:
                    st.error(f"Failed to send email: {e}")
            else:
                st.warning("Please upload a CSV file with valid To contacts.")


        schedule_date = st.date_input("Schedule Date")
        schedule_time = st.time_input("Schedule Time")  # Default time is the current time

        # Combine Date and Time
        schedule_datetime = datetime.combine(schedule_date, schedule_time)

        # Scheduling Section
        if schedule_datetime <= datetime.now():
            st.error("Schedule date and time must be in the future.")
        else:
            if st.button("Schedule Email"):
                from_address = user_details['username'] 
                if to_addresses:
                    full_body = body + f"\n\n{signature}" if signature else body
                    schedule_email_with_apscheduler(user_id, to_addresses, subject, full_body, schedule_datetime, cc_addresses, bcc_addresses)
                else:
                    st.warning("Please add recipients.")



def app():
    
    class MultiApp:
        def __init__(self):
            self.apps=[]
        def add_app(self,title,function):
            self.apps.append({
                "title":title,
                "function":function
            })
        def run():
            with st.sidebar:
                app=option_menu(
                    menu_title="Send Mail",
                    options=['Compose Mail','Scheduled mails'],
                    default_index=0   
                )

            if app=='Compose Mail':
                email_dashboard()
            if app=='Scheduled mails':
                generate_scheduled_email_reports()

        run()







    