import streamlit as st
import pymysql
import pandas as pd

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

#User authentication
def check_user_and_store(user_id):
    """Check if the user is enabled and store the user ID for future use."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            if not user_id:
                st.session_state['user_id'] = "superuser"
                st.success("No User ID entered. Using default 'superuser' account.")
                return True

            # Check if the user is enabled
            cursor.execute("SELECT is_enabled FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            if result and result[0] == 1:
                st.session_state['user_id'] = user_id
                st.success(f"User {user_id} is enabled and stored successfully!")
                return True
            else:
                st.warning("User is not enabled or does not exist.")
                return False
        except Exception as e:
            st.error(f"Database error: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        st.error("Failed to connect to the database.")
        return False

#Function to create template
def create_template(user_id, template_name, template_content):
    """Create a new template for the given user."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Assign default user_id as 'superuser' if not provided
            user_id = user_id or "superuser"

            # Check if the template name is already in use for this user
            cursor.execute("SELECT * FROM templates WHERE user_id = %s AND template_name = %s", (user_id, template_name))
            existing_template = cursor.fetchone()
            if existing_template:
                st.warning("Template name already exists for this user. Please choose a different name.")
                return False

            # Insert the new template
            cursor.execute(
                "INSERT INTO templates (user_id, template_name, template_content) VALUES (%s, %s, %s)",
                (user_id, template_name, f"{template_content}")
            )
            conn.commit()
            st.success(f"Template '{template_name}' created successfully for User ID: {user_id}")
            return True
        except Exception as e:
            st.error(f"Failed to create template: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        st.error("Failed to connect to the database.")
        return False

#Function to update template
def update_template(template_name, new_template_content):
    """Update an existing template."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE templates SET template_content = %s WHERE template_name = %s",
                (f"{new_template_content}", template_name)
            )
            conn.commit()
            st.success("Template updated successfully!")
        except Exception as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close()
            conn.close()

#Function to delete template
def delete_template(template_name):
    """Delete a template."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM templates WHERE template_name = %s", (template_name,))
            conn.commit()
            st.success("Template deleted successfully!")
        except Exception as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close()
            conn.close()
            
#Functionto get user customized templates
def get_templates(user_id):
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT template_name as Template_Name ,template_content as Template_Content  FROM templates WHERE  user_id=%s", (user_id))
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            return users
        return []

#Function to get Ready made templates
def get_Supertemplates():
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT template_name as Template_Name ,template_content as Template_Content  FROM templates WHERE  superuser=%s", (True))
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            return users
        return []

#Display and manage templates
def manage_templates():
    tempcss="""<style>
    @import url('https://fonts.googleapis.com/css2?family=Delius+Unicase:wght@400;700&family=DynaPuff:wght@400..700&family=Funnel+Sans:ital,wght@0,300..800;1,300..800&display=swap');
                
    [data-testid="stApp"]{
        background-color:#ffffff;
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

    [data-testid="stTable"]{
        border:2px solid black;
        background-color:#deeded;
        padding:8px;}
        [data-testid="stBaseButton-secondary"]{
        border:2px solid black;
        }
        [class="st-bt st-bu st-bv st-da st-bx st-by st-c5 st-bz st-c7"]{
        border:2px solid black;
        border-radius:5px;}
        [data-testid="stTextInputRootElement"]{
        border:2px solid black;
        background-color:white;}
        [data-testid="stTextAreaRootElement"]{
        border:2px solid black;
        border-radius:5px;
    </style>"""


    st.markdown(tempcss,unsafe_allow_html=True);
    st.title("Manage Templates")
    st.markdown("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        
    # Fetch and display superuser templates
    st.subheader("Ready-made Templates")
    superuser_templates = get_Supertemplates()
    if superuser_templates:
        st.table(pd.DataFrame(superuser_templates, columns=["Template_Name", "Template_Content"]))
    else:
        st.write("No templates found for the superuser.")

    st.markdown("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        
    st.header("User Authentication")
    user_id = st.text_input("Enter your User ID (Leave blank for default superuser)")
    if st.button("Check User Status and Proceed"):
        if check_user_and_store(user_id):
            st.success("User ID stored successfully. You can now manage templates or send emails.")

    # Retrieve user_id from session state
    user_id = st.session_state.get('user_id', "superuser")
    st.write(f"**Managing templates for User ID:** {user_id}")

    # Fetch and display user templates
    st.subheader("Available Templates")
    user_templates = get_templates(user_id)
    if user_templates:
        st.table(pd.DataFrame(user_templates, columns=["Template_Name", "Template_Content"]))
    else:
        st.write("No templates found for this user.")
    st.markdown("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        
    # Create Template
    st.subheader("Create Template")
    template_name = st.text_input("Template Name")
    template_content = st.text_area("Template Content")
    if st.button("Create Template"):
        if template_name and template_content:
            create_template(user_id, template_name, template_content)
        else:
            st.warning("Please fill out all fields to create a template.")
    st.markdown("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        
    # Update/Delete Template
    st.subheader("Update/Delete Template")
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT template_name FROM templates WHERE user_id = %s or superuser=1", (user_id,))
            templates = cursor.fetchall()
            template_options = [template_name[0] for template_name in templates]
            selected_template = st.selectbox("Select a Template to Update/Delete", template_options)

            if selected_template:
                new_content = st.text_area("New Template Content", "")
                
                if st.button("Update Template"):
                    if new_content:
                        update_template(selected_template, new_content)
                    else:
                        st.warning("Please fill out the new content to update the template.")
                
                if st.button("Delete Template"):
                    delete_template(selected_template)
        except Exception as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close()
            conn.close()

def app():
    manage_templates()
