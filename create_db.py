import pandas as pd
import sqlite3
import os

def create_database_from_csv(csv_filepath, db_filepath):
    """
    Reads data from a CSV file and creates an SQLite database with that data.

    Args:
        csv_filepath (str): The path to the input CSV file.
        db_filepath (str): The path where the output SQLite database will be saved.
    """
    # --- 1. Validate Input File ---
    if not os.path.exists(csv_filepath):
        print(f"❌ Error: The file '{csv_filepath}' was not found.")
        return

    try:
        # --- 2. Read CSV into a pandas DataFrame ---
        # This is the most efficient way to load and handle tabular data.
        df = pd.read_csv(csv_filepath)
        print(f"✅ Successfully loaded '{csv_filepath}' with {len(df)} rows.")

        # Basic data cleaning: remove rows where essential info might be missing
        df.dropna(subset=['Namn', 'Ämnesområden'], inplace=True)
        print(f"🧹 Data cleaned. {len(df)} rows remaining after removing empty entries.")

        # --- 3. Establish Database Connection ---
        # sqlite3.connect() will create the database file if it doesn't exist.
        conn = sqlite3.connect(db_filepath)
        table_name = 'journalists'

        # --- 4. Write DataFrame to SQL Table ---
        # The `to_sql` method is a powerful pandas feature that handles:
        # - Creating the SQL table schema based on the DataFrame's columns and data types.
        # - Inserting all the data.
        # - `if_exists='replace'` means if you run the script again, it will overwrite
        #   the existing table, which is useful for updates.
        # - `index=False` prevents pandas from writing its own DataFrame index as a column.
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"✅ Data successfully written to table '{table_name}' in '{db_filepath}'.")

        # --- 5. Verify and Close Connection ---
        print("\n🔍 Verifying by reading the first 3 rows back from the database:")
        # Reading data back to confirm it's working
        verify_df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 3", conn)
        print(verify_df)

        conn.close()
        print("\n✅ Database connection closed. Process complete.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    # Define the input and output file names
    csv_file = 'journalists.csv'
    db_file = 'journalists.db'

    print(f"Starting conversion: '{csv_file}' -> '{db_file}'")
    create_database_from_csv(csv_file, db_file)
