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
    if not os.path.exists(DATABASE_FILE_NAME):
        raise FileNotFoundError(f"Database file not found: {DATABASE_FILE_NAME}. Please run db_builder.py first.")
    
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_verb():
    """API endpoint to search the database and return conjugation data.
       Now searches both English_Verb and Greek_Verb."""
    
    search_term = request.args.get('term', '').strip().lower()

    if not search_term:
        return jsonify({"success": False, "message": "No search term provided."})

    # MODIFIED: Use the LIKE operator for broader searching and check both columns.
    sql_query = f"""
        SELECT * FROM {TABLE_NAME} 
        WHERE LOWER(English_Verb) = ? OR LOWER(Greek_Verb) = ? 
        LIMIT 1;
    """

    try:
        conn = get_db_connection()
        # Pass the search term twice for the two placeholders
        df = pd.read_sql_query(sql_query, conn, params=(search_term, search_term))
        conn.close()

        if df.empty:
            return jsonify({
                "success": False, 
                "message": f"Verb '{search_term}' not found in the database. Try searching by English or Greek infinitive."
            })
        
        conjugation_data = df.iloc[0].to_dict()
        
        return jsonify({
            "success": True, 
            "verb": conjugation_data
        })

    except FileNotFoundError as e:
        return jsonify({"success": False, "message": str(e)})
    except Exception as e:
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})

@app.route('/random_verb', methods=['GET'])
def random_verb():
    """API endpoint to fetch a random verb for the 'Random Verb' button or Quiz function."""
    
    sql_query = f"""
        SELECT * FROM {TABLE_NAME}
        ORDER BY RANDOM()
        LIMIT 1;
    """

    try:
        conn = get_db_connection()
        df = pd.read_sql_query(sql_query, conn)
        conn.close()

        if df.empty:
            return jsonify({
                "success": False, 
                "message": "Database is empty."
            })
        
        conjugation_data = df.iloc[0].to_dict()
        
        return jsonify({
            "success": True, 
            "verb": conjugation_data
        })

    except FileNotFoundError as e:
        return jsonify({"success": False, "message": str(e)})
    except Exception as e:
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})


if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True)