from flask import Flask, render_template, jsonify, request
import sqlite3
import pandas as pd
import os

app = Flask(__name__)

# --- CONFIGURATION ---
DATABASE_FILE_NAME = "verbs.db"
TABLE_NAME = "conjugations"

def get_db_connection():
    """Establishes connection to the SQLite database."""
    # Check if the database file exists
    if not os.path.exists(DATABASE_FILE_NAME):
        raise FileNotFoundError(f"Database file not found: {DATABASE_FILE_NAME}. Please run db_builder.py first.")
    
    # Use the connection context manager
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    # Allows column access by name (e.g., row['English_Verb'])
    conn.row_factory = sqlite3.Row 
    return conn

@app.route('/')
def index():
    """Serves the main HTML page."""
    # This route just loads the index.html file
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_verb():
    """API endpoint to search the database and return conjugation data."""
    
    # 1. Get the search term from the web page request (e.g., 'to speak')
    search_term = request.args.get('term', '').strip().lower()

    if not search_term:
        # Return an empty result if no term is provided
        return jsonify({"success": False, "message": "No search term provided."})

    # 2. Build the SQL Query
    # We search the English_Verb column for an exact match (or similar, if you prefer LIKE)
    sql_query = f"""
        SELECT * FROM {TABLE_NAME} 
        WHERE LOWER(English_Verb) = ? 
        LIMIT 1;
    """

    try:
        conn = get_db_connection()
        
        # 3. Execute the query
        # Fetch the data into a pandas DataFrame for easy manipulation
        df = pd.read_sql_query(sql_query, conn, params=(search_term,))
        
        conn.close()

        if df.empty:
            # If no results are found
            return jsonify({
                "success": False, 
                "message": f"Verb '{search_term}' not found in the database."
            })
        
        # 4. Prepare the result
        # Convert the single row DataFrame into a dictionary to send to the frontend
        conjugation_data = df.iloc[0].to_dict()
        
        return jsonify({
            "success": True, 
            "verb": conjugation_data
        })

    except FileNotFoundError as e:
        return jsonify({"success": False, "message": str(e)})
    except Exception as e:
        # Catch any other database or server errors
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})

if __name__ == '__main__':
    # Flask is set to run in debug mode for development
    # The application will be accessible at http://127.0.0.1:5000/
    print("Starting Flask server...")
    app.run(debug=True)