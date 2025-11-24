import pandas as pd
import sqlite3
import os
import random
import numpy as np # Added numpy for reliable NaN representation
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
    """Creates the database and populates it from the CSV file if it doesn't exist."""
    if not os.path.exists(DATABASE) or os.path.getsize(DATABASE) < 100: 
        print(f"Database '{DATABASE}' not found or is corrupted. Initializing...")
        try:
            # Use a robust encoding to handle Greek characters
            try:
                df = pd.read_csv(CSV_FILE, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(CSV_FILE, encoding='iso-8859-1')
            
            # --- CRITICAL CLEANING STEPS (REVISED FOR ROBUSTNESS) ---
            
            # 1. Replace empty strings/whitespace in the whole DataFrame with NumPy's NaN
            # This ensures pandas recognizes them as missing data.
            df = df.replace(r'^\s*$', np.nan, regex=True) 
            
            # 2. Strip whitespace from all string columns (only affects valid data now)
            for col in df.select_dtypes(['object']).columns:
                # Need to convert to string first, but ignore true NaNs
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            
            # 3. DROP rows where any essential display field is missing (fixes the 'nan (nan)' issue)
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
            print(f"ERROR: The file '{CSV_FILE}' was not found. Please check the filename in app.py.")
        except Exception as e:
            print(f"Error during database initialization: {e}")
    else:
        print("Database already exists.")

# Ensure database is initialized on startup
initialize_database()

# --- Flask Routes (No changes here) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/all_verbs', methods=['GET'])
def all_verbs():
    conn = get_db_connection()
    try:
        verbs_cursor = conn.execute('SELECT ID, Greek_Verb, English_Verb, Translation FROM verbs ORDER BY Greek_Verb ASC').fetchall()
        
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
    conn = get_db_connection()
    try:
        random_row = conn.execute("SELECT Greek_Verb, Present_Ego FROM verbs WHERE Present_Ego IS NOT '' ORDER BY RANDOM() LIMIT 1").fetchone()

        if random_row:
            greek_verb = random_row['Greek_Verb']
            form = random_row['Present_Ego'] 
            sentence = f"Εγώ {form} κάθε μέρα. (I {greek_verb} every day.)"
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