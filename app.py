import streamlit as st
import sqlite3
import pandas as pd
import traceback

DB_NAME = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

st.title("SQL Web Application & Database Query Tool")
st.markdown("Enter your SQL query below to execute statements or query your SQLite database.")

sql_query = st.text_area("SQL Query:", height=150, placeholder="SELECT * FROM your_table;")

if st.button("Run Query"):
    cleaned_query = sql_query.strip()
    
    if not cleaned_query:
        st.error("Query cannot be empty.")
    else:
        upper_query = cleaned_query.upper()
        if 'DROP DATABASE' in upper_query or 'DROP TABLE' in upper_query:
            st.error("Destructive DROP operations are restricted.")
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                if ';' in cleaned_query[:-1] or 'CREATE TABLE' in upper_query:
                    cursor.executescript(cleaned_query)
                    conn.commit()
                    conn.close()
                    st.success("Table created / Script executed successfully.")
                else:
                    cursor.execute(cleaned_query)
                    if upper_query.startswith('SELECT'):
                        rows = cursor.fetchall()
                        columns = [description[0] for description in cursor.description] if cursor.description else []
                        result_rows = [dict(zip(columns, row)) for row in rows]
                        conn.close()
                        
                        st.success(f"Query executed successfully. Total rows: {len(result_rows)}")
                        if result_rows:
                            df = pd.DataFrame(result_rows)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info("Query returned 0 rows.")
                    else:
                        conn.commit()
                        row_count = cursor.rowcount
                        conn.close()
                        st.success(f"Query executed successfully. Rows affected: {row_count}")
                        
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                with st.expander("View Error Details"):
                    st.code(traceback.format_exc())
