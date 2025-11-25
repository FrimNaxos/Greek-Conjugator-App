import pandas as pd
import sqlite3
import os
import random
import numpy as np 
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
# IMPORTANT: Ensure this matches your exact CSV filename!
CSV_FILE = 'greek verb conjugation table v2.csv' 
DATABASE = 'verbs.db'


# --- Utility Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def initialize_database():
    """Creates the database and populates it from the CSV file if it doesn't exist or is corrupted."""
    # We check if the database file is small, which suggests it might be empty or corrupted.
    # The database will be rebuilt on every deployment to ensure the latest CSV data (including fixes) is used.
    # On Render, this guarantees the most recent CSV data is loaded after a git push.
    
    # Check if the database file is missing or suspiciously small
    if not os.path.exists(DATABASE) or os.path.getsize(DATABASE) < 100: 
        print(f"Database '{DATABASE}' not found or is corrupted. Initializing...")
    else:
        # For simplicity and to ensure the latest CSV is always used, we will delete and rebuild 
        # the database if it exists, especially during development/deployment cycles.
        os.remove(DATABASE)
        print(f"Existing database '{DATABASE}' deleted. Rebuilding from CSV...")

    try:
        # Use a robust encoding to handle Greek characters
        try:
            df = pd.read_csv(CSV_FILE, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(CSV_FILE, encoding='iso-8859-1')
        
        # --- CRITICAL CLEANING STEPS (ROBUST) ---
        
        # 1. Replace empty strings/whitespace in the whole DataFrame with NumPy's NaN
        df = df.replace(r'^\s*$', np.nan, regex=True) 
        
        # 2. Strip whitespace from all string columns (only affects valid data now)
        for col in df.select_dtypes(['object']).columns:
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
        
        # 3. DROP rows where any essential display field is missing (fixes the 'nan (nan)' issue)
        # Assuming these four columns must exist for a verb record to be useful.
        critical_cols = ['ID', 'Greek_Verb', 'Translation', 'English_Verb']
        df_cleaned = df.dropna(subset=critical_cols)

        # 4. Fill any remaining NaN (mostly in conjugation cells) with an empty string
        df_cleaned = df_cleaned.fillna('')
        
        # --- END CLEANING ---

        conn = get_db_connection()
        # Write the cleaned DataFrame to a table named 'verbs'
        df_cleaned.to_sql('verbs', conn, if_exists='replace', index=False)
        conn.close()
        print(f"Database initialized successfully with {len(df_cleaned)} clean records.")
    except FileNotFoundError:
        print(f"ERROR: The file '{CSV_FILE}' was not found. Please check the filename in app.py and ensure it is pushed to Render.")
    except Exception as e:
        print(f"Error during database initialization: {e}")

# Ensure database is initialized on startup
initialize_database()

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/all_verbs', methods=['GET'])
def all_verbs():
    conn = get_db_connection()
    try:
        # Fetching only the clean, critical columns (and Verb_Group)
        verbs_cursor = conn.execute('SELECT ID, Greek_Verb, English_Verb, Translation, Verb_Group FROM verbs ORDER BY Greek_Verb ASC').fetchall()
        
        verbs_list = [{
            'ID': verb['ID'],
            'Greek_Verb': verb['Greek_Verb'],
            'English_Verb': verb['English_Verb'],
            'Translation': verb['Translation'],
            # Safely get Verb_Group if it exists (for compatibility)
            'Verb_Group': verb['Verb_Group'] if 'Verb_Group' in verb.keys() else ''
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
        # Selecting all columns (*) 
        verb_row = conn.execute(
            'SELECT * FROM verbs WHERE Greek_Verb LIKE ? OR English_Verb LIKE ? OR Translation LIKE ?',
            (term_like, term_like, term_like)
        ).fetchone()

        if verb_row:
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
        # Selects a random verb where the Greek verb is not an empty string (extra safety)
        verb_row = conn.execute("SELECT * FROM verbs WHERE Greek_Verb IS NOT '' ORDER BY RANDOM() LIMIT 1").fetchone()
        
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
    conn = get_db_connection()
    try:
        # Fetching Greek_Verb, Present_Ego form, AND English Translation
        random_row = conn.execute("SELECT Greek_Verb, Present_Ego, Translation FROM verbs WHERE Present_Ego IS NOT '' AND Translation IS NOT '' ORDER BY RANDOM() LIMIT 1").fetchone()

        if random_row:
            greek_verb = random_row['Greek_Verb']
            form = random_row['Present_Ego'] 
            english_translation = random_row['Translation'] # English infinitive (e.g., 'to open')
            
            # Use the English translation in the parenthesis for clarity
            sentence = f"Εγώ {form} κάθε μέρα. (I {english_translation} every day.)"
            
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