import pandas as pd
from sqlalchemy import create_engine
import os

# --- CONFIGURATION ---
# The exact name of your CSV file
CSV_FILE_NAME = "greek verb conjugation table v2.csv"  

# The name of the SQLite database file we will create
DATABASE_FILE_NAME = "verbs.db"
# The name of the table inside the database
TABLE_NAME = "conjugations"

def migrate_data():
    """Reads the CSV and imports it into a SQLite database file."""
    
    print(f"Starting migration from {CSV_FILE_NAME}...")

    # 1. Check if the CSV file exists
    if not os.path.exists(CSV_FILE_NAME):
        print(f"ERROR: CSV file not found! Please check the file name: {CSV_FILE_NAME}")
        return

    # 2. Read the CSV file into a pandas DataFrame
    try:
        # Use UTF-8 encoding to handle Greek characters
        # The header is on row 0, which is the default
        df = pd.read_csv(CSV_FILE_NAME, encoding='utf-8')
        
        # We need to filter out rows where all the verb data is missing
        # Based on the info, rows 36-59 seem to be empty or incomplete.
        # We'll filter on 'Greek_Verb' not being null.
        df = df.dropna(subset=['Greek_Verb'])
        
    except Exception as e:
        print(f"ERROR reading CSV: {e}. Check if the file is truly comma-separated.")
        return

    # 3. Prepare the database engine (Creates the .db file if it doesn't exist)
    # The 'sqlite:///' prefix means we are connecting to a local SQLite file.
    engine = create_engine(f'sqlite:///{DATABASE_FILE_NAME}')

    # 4. Perform the migration!
    # 'if_exists="replace"' means it will DELETE the old table and create a new one.
    try:
        df.to_sql(
            TABLE_NAME, 
            engine, 
            if_exists='replace', 
            index=False # We use our own 'ID' column, so we don't need a pandas index
        )
        print("-" * 50)
        print(f"SUCCESS! Database '{DATABASE_FILE_NAME}' created.")
        print(f"Imported {len(df)} verbs into the '{TABLE_NAME}' table.")
        print("-" * 50)
    except Exception as e:
        print(f"ERROR during SQL import: {e}")

if __name__ == "__main__":
    # Ensure you have the dependencies installed: pip install pandas sqlalchemy
    migrate_data()