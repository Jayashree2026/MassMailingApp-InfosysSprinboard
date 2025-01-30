import streamlit as st
import pymysql
import matplotlib.pyplot as plt
import pandas as pd
from streamlit_echarts import st_echarts

# Database Connection
def get_db_connection():
    """Function to get a connection to the database"""
    try:
        conn = pymysql.connect(
            host='localhost',           
            user='root',                
            password='602696',          
            database='mail_app'  
        )
        return conn
    except pymysql.MySQLError as e:
        st.error(f"Error connecting to the database: {e}")
        return None

# Fetch user stats
def fetch_user_stats():
    """Function to fetch general email stats"""
    conn = get_db_connection()
    if conn is None:
        return {
            'total_sent': 0,
            'total_delivered': 0,
            'landed_inbox': 0,
            'landed_spam': 0
        }
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            SUM(sent) AS total_sent,
            SUM(delivered) AS total_delivered,
            SUM(inbox) AS landed_inbox,
            SUM(spam) AS landed_spam
        FROM email_stats;
    """)
    stats = cursor.fetchone()
    cursor.close()
    conn.close()

    if stats is None:
        return {
            'total_sent': 0,
            'total_delivered': 0,
            'landed_inbox': 0,
            'landed_spam': 0
        }

    # Return the stats as a dictionary
    return {
        'total_sent': stats[0] if stats[0] is not None else 0,
        'total_delivered': stats[1] if stats[1] is not None else 0,
        'landed_inbox': stats[2] if stats[2] is not None else 0,
        'landed_spam': stats[3] if stats[3] is not None else 0
    }

# Fetch user-specific data for linear chart

def fetch_user_performance():
    """Fetch and visualize performance data for individual users"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    query = """
        SELECT 
            user_id, 
            SUM(sent) AS total_sent
        FROM email_stats 
        GROUP BY user_id 
        ORDER BY user_id;
    """
    try:
        # Fetch data into a DataFrame
        user_data = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Error fetching user performance data: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

    return user_data


# Fetch campaign growth data
def fetch_campaign_growth():
    """Fetch campaign growth data"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    query = """
        SELECT DATE(timestamp) AS campaign_date, COUNT(*) AS total_campaigns 
        FROM email_stats 
        GROUP BY campaign_date 
        ORDER BY campaign_date;
    """
    try:
        campaign_data = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Error fetching campaign growth data: {e}")
        return pd.DataFrame()
    finally:
        conn.close()
    
    return campaign_data


# Display the updated dashboard
def show_superuser_overview():
    dashcss = """<style>
    @import url('https://fonts.googleapis.com/css2?family=Delius+Unicase:wght@400;700&family=DynaPuff:wght@400..700&family=Funnel+Sans:ital,wght@0,300..800;1,300..800&display=swap');
    [data-testid="stApp"] { background-color:#ffffff; color:black; }
    [data-testid="stSidebarContent"]{
        background-color:#4f6367;}
    h1{
        font-family: 'Delius Unicase', cursive;}
    h3{
        font-family: 'DanPuff', sans-serif;}
    [data-testid="stHeader"] { background-color:black; }
    [data-testid="stSidebarUserContent"] { border-radius:5px; }
    [data-testid="stBaseButton-secondary"] { border:2px solid black; }
    [data-testid="stColumn"] { background-color:#deeded; border-radius:5px;margin-bottom:20px; border:3px Solid Black; padding:10px;
     box-shadow: 0 10px 10px rgba(0, 0, 0, 0.8); }
    canvas{ 
    background-color: white; 
    padding: 15px; 
    border-radius: 10px;
    box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
}
    </style>"""

    st.markdown(dashcss, unsafe_allow_html=True)
    st.title("Admin Overview")
    st.markdown("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        
    stats = fetch_user_stats()

    if not stats:
        st.error("No data found. Ensure the database is populated and the query is correct.")
        return

    total_sent = int(stats.get('total_sent', 0))
    total_delivered = int(stats.get('total_delivered', 0))
    landed_inbox = int(stats.get('landed_inbox', 0))
    landed_spam = int(stats.get('landed_spam', 0))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sent", total_sent)
    col2.metric("Total Delivered", total_delivered)
    col3.metric("Landed in Inbox", landed_inbox)
    col4.metric("Landed in Spam", landed_spam)

    # Deliverability Score as a Gauge
    if total_delivered > 0:
        deliverability_score = (landed_inbox / total_delivered) * 100
    else:
        deliverability_score = 0

    st.subheader("Deliverability Score")
    gauge_options = {
        "tooltip": {"formatter": "{a} <br/>{b} : {c}%"},
        "series": [
            {
                "name": "Score",
                "type": "gauge",
                "detail": {"formatter": "{value}%"},
                "data": [{"value": deliverability_score, "name": "Deliverability"}],
            }
        ],
    }
    st_echarts(options=gauge_options)

    # Bar chart for Sent, Delivered, Inbox, and Spam
    st.subheader("Email Performance Breakdown")
    bar_data = {
        "categories": ["Sent", "Delivered", "Inbox", "Spam"],
        "values": [total_sent, total_delivered, landed_inbox, landed_spam],
    }
    bar_options = {
        "xAxis": {"type": "category", "data": bar_data["categories"]},
        "yAxis": {"type": "value"},
        "series": [{"data": bar_data["values"], "type": "bar"}],
    }
    st_echarts(options=bar_options)

    st.subheader("User performance")
    # Linear chart for User Performance
    user_data = fetch_user_performance()

    if user_data.empty:
        st.warning("No data found. Ensure the database is populated with valid records.")
        return

    # Plot a bar graph
    try:
        fig, ax = plt.subplots()
        ax.bar(user_data['user_id'], user_data['total_sent'], color='skyblue')
        ax.set_title("User Participation Based on Sent Emails")
        ax.set_xlabel("User ID")
        ax.set_ylabel("Number of Emails Sent")
        plt.xticks()
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error rendering the graph: {e}")

    # Linear graph for Campaign Growth
    st.subheader("Campaign Growth Over Time")
    campaign_data = fetch_campaign_growth()
    if not campaign_data.empty:
        st.line_chart(campaign_data.set_index("campaign_date"))

# Main app
def app():
    show_superuser_overview()


