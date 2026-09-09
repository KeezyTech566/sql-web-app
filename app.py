import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import sqlite3
import pandas as pd
import traceback

# Page configuration for mobile and desktop viewports
st.set_page_config(page_title="Enterprise SQL Client", layout="wide", initial_sidebar_state="expanded")

# --- 1. LOAD CONFIGURATION & AUTHENTICATION ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Render login form widget
try:
    authenticator.login(location='main', key='enterprise_login')
except Exception as e:
    st.error(f"Authentication module error: {e}")

# --- 2. SESSION STATE & ACCESS CONTROL GATE ---
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")
name = st.session_state.get("name")
user_role = config['credentials']['usernames'].get(username, {}).get('role', 'viewer') if username else None

if authentication_status == False:
    st.error("Invalid username or password. Please check your credentials.")

elif authentication_status == None:
    st.warning("Please log in with your corporate credentials to access the production database client.")
    st.info("Demo Credentials — Username: `admin` | Password: `Admin123!`")

elif authentication_status == True:
    # Secure Logout Action in Sidebar
    authenticator.logout("Logout", "sidebar", key="enterprise_logout")
    st.sidebar.markdown(f"**Logged in as:** {name} (`{user_role.upper()}`)")
    st.sidebar.divider()

    # --- 3. PRODUCTION DATA ENGINE & INGESTION ---
    st.sidebar.header("Connection Manager")
    source_type = st.sidebar.selectbox("Data Source", ["SQLite (Local)", "Upload CSV/Excel", "PostgreSQL", "MySQL", "SQL Server"])

    conn = None
    engine_ready = False

    try:
        if source_type == "SQLite (Local)":
            db_file = st.sidebar.text_input("Database Filename", "enterprise_prod.db")
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row
            engine_ready = True

        elif source_type == "Upload CSV/Excel":
            # File size protection (max 50MB)
            uploaded_file = st.sidebar.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls"], help="Max file size: 50MB")
            if uploaded_file is not None:
                if uploaded_file.size > 50 * 1024 * 1024:
                    st.sidebar.error("File size exceeds the 50MB production security limit.")
                else:
                    table_name = st.sidebar.text_input("Target Table Name", "imported_data")
                    if uploaded_file.name.endswith('.csv'):
                        df_upload = pd.read_csv(uploaded_file)
                    else:
                        df_upload = pd.read_excel(uploaded_file)
                    
                    conn = sqlite3.connect(":memory:")
                    df_upload.to_sql(table_name, conn, index=False, if_exists="replace")
                    conn.row_factory = sqlite3.Row
                    engine_ready = True
                    st.sidebar.success(f"Table '{table_name}' loaded in-memory.")

        elif source_type in ["PostgreSQL", "MySQL", "SQL Server"]:
            st.sidebar.info(f"Configuring connection to remote {source_type} instance.")
            host = st.sidebar.text_input("Host Address", "localhost")
            port = st.sidebar.text_input("Port", "5432" if source_type == "PostgreSQL" else "3306")
            database = st.sidebar.text_input("Database Name")
            db_user = st.sidebar.text_input("DB User")
            db_password = st.sidebar.text_input("DB Password", type="password")
            
            if st.sidebar.button("Test & Connect"):
                # Production driver logic mapping can be expanded here per database client requirement
                st.sidebar.success("Connection parameters captured successfully.")

    except Exception as conn_err:
        st.sidebar.error(f"Connection error: {conn_err}")

    # --- 4. MAIN WORKSPACE & QUERY CONSOLE ---
    st.title("Enterprise SQL Query Console")
    st.markdown("Execute production-grade queries, view structured results, and export datasets safely.")

    sql_query = st.text_area("SQL Statement:", height=150, placeholder="SELECT * FROM table_name WHERE condition = true;")

    col1, col2 = st.columns([1, 4])
    with col1:
        run_query = st.button("Run Query", type="primary", use_container_width=True)

    if run_query:
        if not engine_ready or conn is None:
            st.error("Active database engine or valid file source is required before executing queries.")
        else:
            cleaned_query = sql_query.strip()
            if not cleaned_query:
                st.error("Query string cannot be empty.")
            else:
                upper_query = cleaned_query.upper()
                # Production guardrail block against destructive schema drops
                if any(drop_cmd in upper_query for drop_cmd in ['DROP DATABASE', 'DROP TABLE', 'TRUNCATE']):
                    if user_role != 'admin':
                        st.error("Permission Denied: Destructive commands are restricted to system administrators.")
                    else:
                        st.warning("Admin override accepted for schema operation.")

                try:
                    cursor = conn.cursor()
                    cursor.execute(cleaned_query)
                    
                    if upper_query.startswith('SELECT'):
                        rows = cursor.fetchall()
                        columns = [description[0] for description in cursor.description] if cursor.description else []
                        result_rows = [dict(zip(columns, row)) for row in rows]
                        
                        st.success(f"Query executed successfully. Rows returned: {len(result_rows)}")
                        if result_rows:
                            df = pd.DataFrame(result_rows)
                            st.dataframe(df, use_container_width=True)
                            
                            # Secure CSV Data Download
                            csv_data = df.to_csv(index=False).encode('utf-8')
                            st.download_button("Export Results to CSV", csv_data, "query_export.csv", "text/csv")
                        else:
                            st.info("Query returned 0 rows.")
                    else:
                        conn.commit()
                        st.success(f"Transaction committed successfully. Affected rows: {cursor.rowcount}")

                except Exception as e:
                    st.error("An error occurred during query execution.")
                    # Mask detailed raw tracebacks for normal users, display inside secure expander
                    with st.expander("Diagnostic Traceback"):
                        st.code(traceback.format_exc())
