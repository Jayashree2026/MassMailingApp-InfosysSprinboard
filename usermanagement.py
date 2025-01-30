import streamlit as st
from streamlit_option_menu import option_menu
import pymysql
from hashlib import sha256
from datetime import datetime
import pandas as pd

# Function to establish a connection to the MySQL database
def get_db_connection():
        try:
            conn = pymysql.connect(
                host='localhost',
                user='root',
                password='602696',
                database='mail_app',
                cursorclass=pymysql.cursors.DictCursor
            )
            return conn
        except pymysql.MySQLError as e:
            st.error(f"Error connecting to the database: {e}")
            return None    
    
#Function to display superusers
def get_enabled_superusers():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id as ID,username as UserName  FROM users WHERE  is_superuser=%s", (True))
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    return []
    


#Function to display all enabled users
def get_enabled_users():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id as ID,username as UserName  FROM users WHERE is_enabled = %s & is_superuser=%s", (True,False))
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    return []
 

#Function to display all users
def get_users():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id as ID,username as UserName  FROM users WHERE  is_superuser=%s", (False))
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    return []      

#display contacts   
def get_contacts():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contacts")
        contacts = cursor.fetchall()
        if contacts:
            df = pd.DataFrame(contacts)
            st.dataframe(df)
        cursor.close()
        conn.close()
    
#fetch the contact details
def fetch_contact(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username FROM contacts WHERE id = %s", (id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                cont_details = {"username": result['username']}
                return cont_details
            else:
                return None  
        except Exception as e:
            st.error(f"Database connection error: {e}")
            return None
        
def is_email_in_database(username):
    """Checks if the username exists in the contacts table by fetching one matching row."""
    conn = get_db_connection()  # Ensure this function returns a valid database connection
    if not conn:
        st.error("Database connection could not be established.")
        return False

    try:
        cursor = conn.cursor()
        
        # Use a parameterized query to prevent SQL injection
        query = "SELECT username FROM contacts WHERE username = %s LIMIT 1"
        cursor.execute(query, (username,))
        result = cursor.fetchone()

        # If result is not None, the username exists
        if result:
            return True
        else:
            return False

    except Exception as e:
        st.error(f"Error checking username in the database: {e}")
        return False

    finally:
        # Ensure resources are cleaned up
        if cursor:
            cursor.close()
        if conn:
            conn.close()


        
#function to create new contact manually or using csv file
def create_contact(username,added_at):
        
        if is_email_in_database(username):
            return {"status": "error", "message": f"The contact {username} already exists in the database."}

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO contacts (username,added_at) 
                    VALUES (%s, %s)
                    """,
                    (username,added_at)  
                )
                conn.commit()
                return {"status": "success", "message": "Contact created successfully!"}
            except pymysql.MySQLError as e:
                return {"status": "error", "message": f"Error creating Contact: {e}"}
            finally:
                cursor.close()
                conn.close()
        return {"status": "error", "message": "Database connection failed"}

#function to update contact
def update_contact(id, username,added_at):
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Construct the update query dynamically
                query = """
                    UPDATE contacts 
                    SET username = %s, added_at = %s
                """
                values = [username, added_at] 
                query += " WHERE id = %s"
                values.append(id) 
                
                # Execute the query
                cursor.execute(query, values)
                conn.commit()
                
                return {"status": "success", "message": "Contact updated successfully."}
            except Exception as e:
                return {"status": "error", "message": f"Error updating contact: {e}"}
            finally:
                conn.close()
        else:
            return {"status": "error", "message": "Database connection failed."}

#function to delete contact
def delete_contact(id):
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM contacts WHERE id = %s", (id,))
                conn.commit()
                return {"status": "success", "message": "Contact deleted successfully!"}
            except pymysql.MySQLError as e:
                return {"status": "error", "message": f"Error deleting contact: {e}"}
            finally:
                cursor.close()
                conn.close()
        return {"status": "error", "message": "Database connection failed"}

# Function to create a new user
def create_user(username, password, is_enabled=False):
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            hashed_password = sha256(password.encode()).hexdigest()
            try:
                # Insert user with default is_superuser = False and is_enabled based on input
                cursor.execute(
                    """
                    INSERT INTO users (username, password, is_enabled, is_superuser) 
                    VALUES (%s, %s, %s, %s)
                    """,
                    (username, hashed_password, int(is_enabled), False)  
                )
                conn.commit()
                return {"status": "success", "message": "User created successfully!"}
            except pymysql.MySQLError as e:
                return {"status": "error", "message": f"Error creating user: {e}"}
            finally:
                cursor.close()
                conn.close()
        return {"status": "error", "message": "Database connection failed"}

# Function to update a user's details
def update_user(user_id, username, hashed_password=None, is_enabled=False):
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Construct the update query dynamically
                query = """
                    UPDATE users 
                    SET username = %s, is_enabled = %s, is_superuser = %s
                """
                values = [username, is_enabled, False]  
                
                if hashed_password:  
                    query += ", password = %s"
                    values.append(hashed_password)  
                
                query += " WHERE id = %s"
                values.append(user_id) 
                
                # Execute the query
                cursor.execute(query, values)
                conn.commit()
                
                return {"status": "success", "message": "User updated successfully."}
            except Exception as e:
                return {"status": "error", "message": f"Error updating user: {e}"}
            finally:
                conn.close()
        else:
            return {"status": "error", "message": "Database connection failed."}

# Function to delete a user
def delete_user(user_id):
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                return {"status": "success", "message": "User deleted successfully!"}
            except pymysql.MySQLError as e:
                return {"status": "error", "message": f"Error deleting user: {e}"}
            finally:
                cursor.close()
                conn.close()
        return {"status": "error", "message": "Database connection failed"}

# Admin Dashboard
def superuser_dashboard():
        supercss="""<style>
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
        table{
        color:white;
        
        font-size:15px;
        }
        [data-testid="stTable"]{
        border:2px solid black;
        background-color:white;
        padding:8px;
        box-shadow: 0 10px 10px rgba(0, 0, 0, 0.8);}

        button p{
        color:black;}
        </style>"""
    

        st.markdown(supercss,unsafe_allow_html=True);
        
        st.title("Users Dashboard")
        
        st.subheader("List of Admins")
        st.table(get_enabled_superusers())

        st.subheader("List of Enabled Users")
        st.table(get_enabled_users()) 

        st.subheader("List of All Users")
        st.table(get_users()) 

#User management portal
def manageusers():
        usercss = """
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
        [data-testid="stSidebarUserContent"]{
        border-radius:5px;}
        [class="st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7"]{
        border:2px solid black;
        border-radius:5px;}
        
        [data-testid="stBaseButton-secondary"]{
        border:2px solid black;
        }
        text-align:center;
        }
        .st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7{
        background-color:white;
        }
        [data-testid="stTextInputRootElement"]{
        border:2px solid black;
        background-color:white;}
       
        </style>
        """
        st.markdown(usercss,unsafe_allow_html=True)
        st.title("Manage users and their email permissions.")
        st.markdown("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        
        # Dropdown menu to select action
        action = st.selectbox("Select Action", ["Create User", "Update User", "Delete User"])

        if action == "Create User":
            st.subheader("Create New User")
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            is_enabled = st.checkbox("Enable Email Permissions", value=True)  # Toggle for email permissions

            if st.button("Create User"):
                if new_username and new_password:
                    if is_enabled:
                        is_enabled=True
                        st.warning("user is enabled")
                    else:
                        is_enabled=False
                        st.warning("user is disabled")
                    response = create_user(new_username, new_password,is_enabled)
                    if response['status'] == "success":
                        st.success(response['message'])
                        
                    else:
                        st.error(response['message'])
                else:
                    st.warning("Username and password are required.")
                    
        elif action == "Update User":
            st.subheader("Update Existing User")
            update_user_id = st.text_input("Enter User ID to Update")  # Manual ID input
            update_username = st.text_input("Updated Username")
            update_password = st.text_input("Updated Password", type="password")
            update_is_enabled = st.checkbox("Enable Email Permissions", value=True)  # Toggle for email permissions

            if st.button("Update User"):
                if update_user_id and update_username:
                    # Hash the password if provided
                    hashed_password = sha256(update_password.encode()).hexdigest() if update_password else None
                    if update_is_enabled:
                        is_enabled=True
                        st.warning("user is enabled")
                    else:
                        update_is_enabled=False
                        st.warning("user is disabled")
                    # Call the update_user function with the provided inputs
                    response = update_user(update_user_id, update_username,hashed_password,update_is_enabled)

                    if response['status'] == "success":
                        st.success(response['message'])
                    else:
                        st.error(response['message'])
                else:
                    st.warning("User ID and username are required.")


        elif action == "Delete User":
            st.subheader("Delete User")
            delete_user_id = st.text_input("Enter User ID to Delete")  # Manual ID input

            if st.button("Delete User"):
                if delete_user_id:
                    response = delete_user(delete_user_id)
                    if response['status'] == "success":
                        st.success(response['message'])
                    else:
                        st.error(response['message'])
                else:
                    st.warning("User ID is required.")

#Contact Management portal
def managecontacts():
        contcss = """
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
        
        [data-testid="stDataFrame"]{
        width:700px;
         border:2px solid black;
        border-radius:5px;}
        text-align:center;
        
        }
        .st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7{
        background-color:white;
        }
        [data-testid="stTextInputRootElement"]{
        border:2px solid black;
        background-color:white;}
       
        </style>
        """
        st.markdown(contcss,unsafe_allow_html=True)
        st.title("Manage contacts")
        st.markdown("-------------------------------------------------------------------------------------------------------------------")

        st.subheader("Available Contacts")
        get_contacts()
        action = st.selectbox("Select Action", ["Create Contact", "Update Contact", "Delete Contact"])

        if action == "Create Contact":
            st.subheader("Create New Contact")
            option = st.radio("Choose an option to create contact:", ["Enter Manually", "Upload CSV"])
            
            if option == "Enter Manually":
                new_username = st.text_input("Enter Username")

            uploaded_file = None
            if option == "Upload CSV":
                uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
                st.write("Contacts must be written under the column 'username'")

            if st.button("Create Contact"):
                if option == "Enter Manually":
                    if new_username:
                        if is_email_in_database(new_username):
                            st.warning(f"The email '{new_username}' is already in the database.")
                        else:
                            added_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # ISO 8601 format
                            response = create_contact(new_username, added_at)
                            if response['status'] == "success":
                                st.success(response['message'])
                            else:
                                st.error(response['message'])
                    else:
                        st.warning("Username is required.")

                elif option == "Upload CSV" and uploaded_file is not None:
                    try:
                        df = pd.read_csv(uploaded_file)

                        if "username" not in df.columns:
                            st.error("CSV file must contain 'username' column.")
                            return

                        # Initialize tracking variables
                        duplicate_emails = []
                        existing_emails = []
                        added_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        successful_contacts = []
                        seen_emails = set()

                        for _, row in df.iterrows():
                            email = row['username']

                            # Check for duplicates within the file
                            if email in seen_emails:
                                duplicate_emails.append(email)
                            # Check if the email already exists in the database
                            elif is_email_in_database(email):
                                existing_emails.append(email)
                            else:
                                seen_emails.add(email)
                                response = create_contact(email, added_at)
                                if response['status'] == "success":
                                    successful_contacts.append(email)

                        # Display results
                        if successful_contacts:
                            st.success(f"{len(successful_contacts)} emails added successfully: {', '.join(successful_contacts)}")

                        if duplicate_emails:
                            st.warning(f"Duplicate email addresses found in the uploaded file: {', '.join(duplicate_emails)}")

                        if existing_emails:
                            st.info(f"The following emails already exist in the database: {', '.join(existing_emails)}")

                    except Exception as e:
                        st.error(f"Error reading CSV file: {e}")
                else:
                    st.warning("Please provide the required input.")

        elif action=="Update Contact":
            if "contact_details" not in st.session_state:
                st.session_state.contact_details = None

            contact_id = st.text_input("Enter ID of the contact to update")

            if st.button("Fetch Contact"):
                if contact_id:
                    response = fetch_contact(contact_id)
                    if response:
                        st.session_state.contact_details = response  # Store contact details in session state
                        st.success("Contact details fetched successfully!")
                    else:
                        st.error("Contact not found.")
                        st.session_state.contact_details = None  # Clear session state if not found
                else:
                    st.warning("Contact ID is required.")

            # Display and update only if contact details are fetched
            if st.session_state.contact_details:
                current_username = st.session_state.contact_details['username']
                st.write(f"Current Username: {current_username}")

                update_username = st.text_input("Enter Updated Username")

                if st.button("Update Contact"):
                    if update_username:
                        added_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  #  ISO 8601 format
                        update_response = update_contact(contact_id, update_username, added_at)

                        if update_response['status'] == "success":
                            st.success(update_response['message'])
                            st.session_state.contact_details = None  
                        else:
                            st.error(update_response['message'])
                    else:
                        st.warning("Updated Username is required.")




        elif action == "Delete Contact":
            st.subheader("Delete Contact")
            delete_user_id = st.text_input("Enter ID to Delete")  # Manual ID input

            if st.button("Delete Contact"):
                if delete_user_id:
                    response = delete_contact(delete_user_id)
                    if response['status'] == "success":
                        st.success(response['message'])
                    else:
                        st.error(response['message'])
                else:
                    st.warning("User ID is required.")







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
                    menu_title="User & Contact Management",
                    options=['Admin Dashboard','Manage users','Manage contacts'],
                    default_index=0   
                )

            if app=='Admin Dashboard':
                superuser_dashboard()
            if app=='Manage users':
                manageusers()
            if app=='Manage contacts':
                managecontacts()

        run()
     
