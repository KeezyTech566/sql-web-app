from flask import Flask, render_template, request, jsonify
import sqlite3
import traceback

app = Flask(__name__)

DB_NAME = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def run_query():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Invalid JSON request'}), 400
            
        sql_query = data.get('query', '').strip()
        if not sql_query:
            return jsonify({'error': 'Query cannot be empty'}), 400

        upper_query = sql_query.upper()
        if 'DROP DATABASE' in upper_query or 'DROP TABLE' in upper_query:
            return jsonify({'error': 'Destructive DROP operations are restricted.'}), 403

        conn = get_db_connection()
        cursor = conn.cursor()
        
        if ';' in sql_query[:-1] or 'CREATE TABLE' in upper_query:
            cursor.executescript(sql_query)
            conn.commit()
            conn.close()
            return jsonify({'message': 'Table created / Script executed successfully.', 'row_count': 0})
        else:
            cursor.execute(sql_query)
            if upper_query.startswith('SELECT'):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                result_rows = [dict(zip(columns, row)) for row in rows]
                conn.close()
                return jsonify({'columns': columns, 'rows': result_rows, 'row_count': len(result_rows)})
            else:
                conn.commit()
                row_count = cursor.rowcount
                conn.close()
                return jsonify({'message': 'Query executed successfully.', 'row_count': row_count})
                
    except Exception as e:
        print("\n--- ERROR TRACEBACK ---")
        traceback.print_exc()
        print("-----------------------\n")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)