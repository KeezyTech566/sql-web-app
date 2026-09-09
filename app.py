import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import sqlite3
import pandas as pd
import traceback
import bcrypt

st.set_page_config(page_title="Enterprise SQL Client", layout="wide", initial_sidebar_state="expanded")

# --- PERSISTENT USER DATABASE SETUP ---
def init_user_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT,
            name TEXT,
            password TEXT,
            role TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_pass = bcrypt.hashpw("Admin123!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                       ("admin", "admin@enterprise.com", "System Administrator", default_pass, "admin"))
        conn.commit()
    conn.close()

init_user_db()

def load_credentials_from_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, name, password, role FROM users")
    rows = cursor.fetchall()
    conn.close()
    
    credentials = {"usernames": {}}
    for row in rows:
        credentials["usernames"][row[0]] = {
            "email": row[1],
            "name": row[2],
            "password": row[3],
            "role": row[4]
        }
    return credentials

with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

db_credentials = load_credentials_from_db()

authenticator = stauth.Authenticate(
    db_credentials,
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 1. Toggle View between Login and Registration
auth_selection = st.sidebar.radio("Authentication", ["Login", "Create Account"])

if auth_selection == "Login":
    authenticator.login(location='main', key='login_widget')
    
    if st.session_state.get("authentication_status") == True:
        authenticator.logout("Logout", "sidebar", key="enterprise_logout")
        name = st.session_state.get("name")
        username = st.session_state.get("username")
        user_role = db_credentials['usernames'].get(username, {}).get('role', 'viewer')
        
        st.sidebar.markdown(f"**Logged in as:** {name} (`{user_role.upper()}`)")
        st.sidebar.divider()

        # --- PRODUCTION DATA ENGINE & INGESTION ---
        st.sidebar.header("Connection Manager")
        source_type = st.sidebar.selectbox("Data Source", ["SQLite (Local)", "Upload CSV/Excel", "PostgreSQL", "MySQL", "SQL Server"])

        conn = None
        engine_ready = False

        try:
            if source_type == "SQLite (Local)":
                db_file = st.sidebar.text_input("Database Filename", "enterprise_prod.db")
                conn = sqlite3.connect(db_file, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                engine_ready = True

            elif source_type == "Upload CSV/Excel":
                uploaded_file = st.sidebar.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls"], help="Max file size: 50MB")
                if uploaded_file is not None:
                    if uploaded_file.size > 50 * 1024 * 1024:
                        st.sidebar.error("File size exceeds the 50MB production security limit.")
                    else:
                        table_name = st.sidebar.text_input("Target Table Name", "Training_data")
                        if uploaded_file.name.endswith('.csv'):
                            df_upload = pd.read_csv(uploaded_file)
                        else:
                            df_upload = pd.read_excel(uploaded_file)
                        
                        conn = sqlite3.connect("uploaded_data.db", check_same_thread=False)
                        df_upload.to_sql(table_name, conn, index=False, if_exists="replace")
                        conn.row_factory = sqlite3.Row
                        engine_ready = True
                        st.sidebar.success(f"Table '{table_name}' loaded successfully!")

            elif source_type in ["PostgreSQL", "MySQL", "SQL Server"]:
                st.sidebar.info(f"Configuring connection to remote {source_type} instance.")
                host = st.sidebar.text_input("Host Address", "tsl-db.postgres.database.azure.com")
                port = st.sidebar.text_input("Port", "5432" if source_type == "PostgreSQL" else "3306")
                database = st.sidebar.text_input("Database Name", "TSL_DB")
                db_user = st.sidebar.text_input("DB User", "tsladmin")
                db_password = st.sidebar.text_input("DB Password", type="password")
                
                if st.sidebar.button("Test & Connect") or st.session_state.get("connected_remote", False):
                    try:
                        if source_type == "PostgreSQL":
                            import psycopg2
                            conn = psycopg2.connect(
                                host=host, port=port, database=database, user=db_user, password=db_password, sslmode='require'
                            )
                            engine_ready = True
                            st.session_state["connected_remote"] = True
                            st.sidebar.success("Successfully connected to cloud PostgreSQL!")
                        elif source_type == "MySQL":
                            import pymysql
                            conn = pymysql.connect(
                                host=host, port=int(port), database=database, user=db_user, password=db_password
                            )
                            engine_ready = True
                            st.session_state["connected_remote"] = True
                            st.sidebar.success("Successfully connected to MySQL!")
                        elif source_type == "SQL Server":
                            import pyodbc
                            conn = pyodbc.connect(
                                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={host},{port};DATABASE={database};UID={db_user};PWD={db_password}"
                            )
                            engine_ready = True
                            st.session_state["connected_remote"] = True
                            st.sidebar.success("Successfully connected to SQL Server!")
                    except Exception as ext_err:
                        st.sidebar.error(f"Remote connection failed: {ext_err}")

        except Exception as conn_err:
            st.sidebar.error(f"Connection error: {conn_err}")

        if source_type == "Upload CSV/Excel" and not engine_ready:
            try:
                conn = sqlite3.connect("uploaded_data.db", check_same_thread=False)
                conn.row_factory = sqlite3.Row
                engine_ready = True
            except:
                pass

        # --- MAIN WORKSPACE & QUERY CONSOLE ---
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
                                
                                csv_data = df.to_csv(index=False).encode('utf-8')
                                st.download_button("Export Results to CSV", csv_data, "query_export.csv", "text/csv")
                            else:
                                st.info("Query returned 0 rows.")
                        else:
                            conn.commit()
                            st.success(f"Transaction committed successfully. Affected rows: {cursor.rowcount}")

                    except Exception as e:
                        st.error("An error occurred during query execution.")
                        with st.expander("Diagnostic Traceback"):
                            st.code(traceback.format_exc())

    elif st.session_state.get("authentication_status") == False:
        st.error("Invalid username or password.")
    elif st.session_state.get("authentication_status") == None:
        st.info("Please enter your login credentials.")

elif auth_selection == "Create Account":
    st.subheader("Register a New User Account")
    
    with st.form("registration_form"):
        new_email = st.text_input("Email Address")
        new_name = st.text_input("Full Name")
        new_username = st.text_input("Choose Username")
        new_password = st.text_input("Secure Password", type="password")
        new_confirm_password = st.text_input("Confirm Password", type="password")
        submit_registration = st.form_submit_button("Create Account")
        
        if submit_registration:
            if not new_username or not new_password or not new_email or not new_confirm_password:
                st.error("Please fill in all required fields.")
            elif new_password != new_confirm_password:
                st.error("Passwords do not match.")
            elif new_username in db_credentials['usernames']:
                st.error("Username already exists. Please choose a different one.")
            else:
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                conn = sqlite3.connect("users.db", check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                               (new_username, new_email, new_name, hashed_password, 'viewer'))
                conn.commit()
                conn.close()
                
                st.success("Account successfully created! Switch to the 'Login' view to sign in.")
