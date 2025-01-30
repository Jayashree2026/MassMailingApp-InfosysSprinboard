import streamlit as st 
import pymysql
from hashlib import sha256
import mainpage

# Initialize session state for login status
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

st.set_page_config(
        page_title="Mass Mailing",
    )
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

# Function to register a superuser
def register_superuser(username, password):
    # Validate inputs
    if not username or not username.strip():
        return {"status": "error", "message": "Username cannot be empty or blank."}
    if not password or len(password) < 8:
        return {"status": "error", "message": "Password must be at least 8 characters long."}

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        hashed_password = sha256(password.encode()).hexdigest()  # Hash the password
        try:
            # Register as a superuser
            cursor.execute(
                "INSERT INTO users (username, password, is_superuser, is_enabled) VALUES (%s, %s, %s, %s)",
                (username.strip(), hashed_password, True, True)
            )
            conn.commit()
            return {"status": "success", "message": "Admin registered successfully!"}
        except pymysql.MySQLError as e:
            return {"status": "error", "message": f"Registration failed: {e}"}
        finally:
            cursor.close()
            conn.close()
    return {"status": "error", "message": "Database connection failed"}


# Function to login a superuser
def login_superuser(username, password):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        hashed_password = sha256(password.encode()).hexdigest()  # Hash the password for verification
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s AND is_superuser = %s",
            (username, hashed_password, True)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            return {"status": "success", "user": user}
        else:
            return {"status": "error", "message": "Invalid credentials or not a Admin"}
    return {"status": "error", "message": "Database connection failed"}



# Function to display the login/register page for superusers
def show_login_page():
    logincss="""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Delius+Unicase:wght@400;700&family=DynaPuff:wght@400..700&family=Funnel+Sans:ital,wght@0,300..800;1,300..800&display=swap');
       body{
       font-family: 'DynaPuff', sans-serif;}         
    h1{
        font-size:40px;
        font-family: 'Delius Unicase', cursive;
        }
        label p{
        color:#1e1d1c;
        }
        [data-testid="stradio"]{
        color:#1e1d1c;
        }
        [data-testid="stBaseButton-secondary"]{
        background-color:black;}

        [data-testid="stTextInputRootElement"]{
        border:2px solid black;
        }
        button p{
        color:white;
        width:#1e1d1c;
        }
        [data-testid="stButton"]{
        backgoround-color:black;}
        </style>
        """
    st.markdown(logincss, unsafe_allow_html=True)

    col1,col2 = st.columns([1,1])
    with col1:
        st.image("./massmailit.png")


    with col2:
        col2_style = """
        <style>
        div[data-testid="stVerticalBlock"] > div:nth-child(n) {
            font-family: 'DynaPuff', sans-serif;
        
            </style>

        """
        st.markdown(col2_style, unsafe_allow_html=True)
    

        st.title("Welcome !")
        st.subheader("Admin Authentication")

        auth_action = st.radio("Choose action", ["Register", "Login"])

        # Authentication form
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")

        # Register Button
        if auth_action == "Register":
            if st.button("Register", key="register", help="Click to Register as Admin"):
                response = register_superuser(username, password)
                if response['status'] == "success":
                    st.success(response['message'])
                else:
                    st.error(response.get('message', "Registration failed"))

        # Login Button
        elif auth_action == "Login":
            if st.button("Login", key="login", help="Click to Login as Admin"):
                response = login_superuser(username, password)
                if response['status'] == "success":
                    st.session_state['user'] = response['user']
                    st.session_state.is_logged_in = True
                    st.success("Logged in successfully!")
                else:
                    st.error(response.get('message', "Login failed"))


# Main app logic
if st.session_state.is_logged_in:
    mainpage.app()
else:
    show_login_page()