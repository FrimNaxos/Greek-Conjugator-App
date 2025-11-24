import pandas as pd
import sqlite3
import os
import random
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DATABASE = 'verbs.db'
CSV_FILE = 'greek verb conjugation table v2.csv'

# --- Utility Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def initialize_database():
    """Creates the database and populates it from the CSV file if it doesn't exist."""
    if not os.path.exists(DATABASE):
        print(f"Database '{DATABASE}' not found. Initializing...")
        try:
            df = pd.read_csv(CSV_FILE)
            # Remove leading/trailing spaces from string columns
            for col in df.select_dtypes(['object']).columns:
                df[col] = df[col].astype(str).str.strip()
            
            # Filter out rows where Greek_Verb is NaN
            df_filtered = df.dropna(subset=['Greek_Verb'])
            
            conn = get_db_connection()
            # Write the filtered DataFrame to a table named 'verbs'
            df_filtered.to_sql('verbs', conn, if_exists='replace', index=False)
            conn.close()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Error during database initialization: {e}")
    else:
        print("Database already exists.")

# Ensure database is initialized on startup
initialize_database()

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# NEW ROUTE: Fetch list of all verbs for filtering/list view
@app.route('/all_verbs', methods=['GET'])
def all_verbs():
    conn = get_db_connection()
    try:
        # Select key information needed for the list view, ordered by Greek verb
        verbs_cursor = conn.execute('SELECT ID, Greek_Verb, English_Verb, Translation FROM verbs ORDER BY Greek_Verb ASC').fetchall()
        
        # Convert rows to a list of dictionaries
        verbs_list = [{
            'ID': verb['ID'],
            'Greek_Verb': verb['Greek_Verb'],
            'English_Verb': verb['English_Verb'],
            'Translation': verb['Translation']
        } for verb in verbs_cursor]
        
        return jsonify({'success': True, 'verbs': verbs_list})
    except Exception as e:
        print(f"Error fetching all verbs: {e}")
        return jsonify({'success': False, 'message': 'Could not retrieve verb list.'}), 500
    finally:
        conn.close()

@app.route('/search', methods=['GET'])
def search_verb():
    term = request.args.get('term', '').strip()
    if not term:
        return jsonify({'success': False, 'message': 'Please enter a term.'})

    conn = get_db_connection()
    term_like = f'%{term}%'
    try:
        # Search Greek_Verb, English_Verb, and Translation
        verb_row = conn.execute(
            'SELECT * FROM verbs WHERE Greek_Verb LIKE ? OR English_Verb LIKE ? OR Translation LIKE ?',
            (term_like, term_like, term_like)
        ).fetchone()

        if verb_row:
            # If multiple rows match, we only return the first one found.
            return jsonify({'success': True, 'verb': dict(verb_row)})
        else:
            return jsonify({'success': False, 'verb_not_found': True, 'message': f"Verb '{term}' not found."})

    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'A database error occurred.'}), 500
    finally:
        conn.close()

@app.route('/random_verb', methods=['GET'])
def random_verb():
    conn = get_db_connection()
    try:
        max_id_row = conn.execute('SELECT MAX(ID) FROM verbs').fetchone()
        max_id = max_id_row[0] if max_id_row else 0
        
        if max_id == 0:
            return jsonify({'success': False, 'message': 'No verbs found in database.'})

        # Select a random row
        random_id = random.randint(1, max_id)
        
        # Keep searching for a valid ID (handles gaps in IDs)
        verb_row = None
        attempts = 0
        while verb_row is None and attempts < 10:
             verb_row = conn.execute('SELECT * FROM verbs WHERE ID = ?', (random_id,)).fetchone()
             if verb_row is None:
                random_id = random.randint(1, max_id)
                attempts += 1

        if verb_row:
            return jsonify({'success': True, 'verb': dict(verb_row)})
        else:
            # Fallback if random ID selection fails
            verb_row = conn.execute('SELECT * FROM verbs ORDER BY RANDOM() LIMIT 1').fetchone()
            if verb_row:
                 return jsonify({'success': True, 'verb': dict(verb_row)})
            else:
                 return jsonify({'success': False, 'message': 'Could not retrieve a random verb.'})

    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'A database error occurred.'}), 500
    finally:
        conn.close()
        
@app.route('/generate_sentence', methods=['GET'])
def generate_sentence():
    # Placeholder for sentence generation
    conn = get_db_connection()
    try:
        random_row = conn.execute('SELECT Greek_Verb, Present_Ego FROM verbs ORDER BY RANDOM() LIMIT 1').fetchone()

        if random_row:
            greek_verb = random_row['Greek_Verb']
            form = random_row['Present_Ego'] 
            sentence = f"Εγώ {form} κάθε μέρα. (I {random_row['Greek_Verb']} every day.)"
            return jsonify({'success': True, 'verb': greek_verb, 'sentence': sentence})
        else:
            return jsonify({'success': False, 'sentence': 'No verbs available to generate a sentence.'})
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'success': False, 'sentence': 'Error retrieving verb for sentence generation.'}), 500
    finally:
        conn.close()

@app.route('/report_missing_verb', methods=['POST'])
def report_missing_verb():
    data = request.get_json()
    verb = data.get('verb', 'Unknown')
    
    print(f"--- MISSING VERB REPORTED: {verb} ---")
    
    return jsonify({'success': True, 'message': 'Report received.'})

if __name__ == '__main__':
    app.run(debug=True)