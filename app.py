import streamlit as st
import sqlite3
import pandas as pd
import traceback

st.set_page_config(page_title="Universal SQL Client", layout="wide")

st.title("Universal SQL Query Tool & Data Ingestion")
st.markdown("Connect to external databases or upload flat files to run SQL queries live.")

# Sidebar for Connection Management
st.sidebar.header("Data Source Configuration")
source_type = st.sidebar.selectbox("Select Source Type", ["SQLite (Local)", "Upload CSV/Excel", "PostgreSQL", "MySQL", "SQL Server"])

conn = None
engine_ready = False

try:
    if source_type == "SQLite (Local)":
        db_file = st.sidebar.text_input("Database Filename", "database.db")
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        engine_ready = True

    elif source_type == "Upload CSV/Excel":
        uploaded_file = st.sidebar.file_uploader("Upload File", type=["csv", "xlsx", "xls"])
        if uploaded_file is not None:
            table_name = st.sidebar.text_input("Table Name in SQL", "uploaded_data")
            if uploaded_file.name.endswith('.csv'):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)
            
            # Load into temporary SQLite memory database
            conn = sqlite3.connect(":memory:")
            df_upload.to_sql(table_name, conn, index=False, if_exists="replace")
            conn.row_factory = sqlite3.Row
            engine_ready = True
            st.sidebar.success(f"Table '{table_name}' loaded successfully! Try: SELECT * FROM {table_name};")

    elif source_type in ["PostgreSQL", "MySQL", "SQL Server"]:
        host = st.sidebar.text_input("Host", "localhost")
        port = st.sidebar.text_input("Port", "5432" if source_type == "PostgreSQL" else "3306")
        database = st.sidebar.text_input("Database Name")
        user = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button("Connect"):
            # Placeholder for external connectors using sqlalchemy / pymysql / psycopg2
            st.sidebar.info("External DB drivers require respective packages in requirements.txt.")

except Exception as conn_err:
    st.sidebar.error(f"Connection failed: {conn_err}")

# Main Query Editor Area
sql_query = st.text_area("Enter SQL Query:", height=150, placeholder="SELECT * FROM table_name;")

if st.button("Run Query"):
    if not engine_ready or conn is None:
        st.error("Please configure a valid data source or upload a file first.")
    else:
        cleaned_query = sql_query.strip()
        if not cleaned_query:
            st.error("Query cannot be empty.")
        else:
            upper_query = cleaned_query.upper()
            if 'DROP DATABASE' in upper_query or 'DROP TABLE' in upper_query:
                st.error("Destructive DROP operations are restricted.")
            else:
                try:
                    cursor = conn.cursor()
                    cursor.execute(cleaned_query)
                    
                    if upper_query.startswith('SELECT'):
                        rows = cursor.fetchall()
                        columns = [description[0] for description in cursor.description] if cursor.description else []
                        result_rows = [dict(zip(columns, row)) for row in rows]
                        
                        st.success(f"Query executed successfully. Total rows: {len(result_rows)}")
                        if result_rows:
                            df = pd.DataFrame(result_rows)
                            st.dataframe(df, use_container_width=True)
                            
                            # CSV Export feature for mobile/desktop users
                            csv_data = df.to_csv(index=False).encode('utf-8')
                            st.download_button("Download Results as CSV", csv_data, "query_results.csv", "text/csv")
                        else:
                            st.info("Query returned 0 rows.")
                    else:
                        conn.commit()
                        st.success("Query executed successfully.")
                        
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    with st.expander("View Error Details"):
                        st.code(traceback.format_exc())
