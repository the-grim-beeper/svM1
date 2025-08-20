import streamlit as st
import pandas as pd
import sqlite3
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Journalist DB Tool",
    page_icon="🗃️",
    layout="wide",
)

# --- Database Configuration ---
DB_FILE = "journalists.db"

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    .journalist-card {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
        transition: 0.3s;
        background-color: #ffffff; /* Changed to white for a cleaner look */
    }
    .journalist-card:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }
    .journalist-name {
        font-size: 1.5em;
        font-weight: bold;
        color: #2c3e50;
    }
    .journalist-category {
        font-style: italic;
        color: #3498db;
        margin-bottom: 10px;
    }
    .journalist-details {
        font-size: 1em;
        color: #34495e;
    }
</style>
""", unsafe_allow_html=True)


# --- Database Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        return None

@st.cache_data(ttl=600)
def get_all_journalists():
    """Fetches all journalists from the database, including their unique rowid."""
    conn = get_db_connection()
    if conn:
        try:
            # Fetch the unique rowid along with all other columns (*)
            journalists = pd.read_sql_query("SELECT rowid, * FROM journalists", conn)
            conn.close()
            return journalists
        except Exception as e:
            st.warning(f"Could not read from 'journalists' table. Has the database been created? Error: {e}")
            conn.close()
    return pd.DataFrame()

def search_journalists(search_term):
    """
    Searches for a term and includes the rowid in the results.
    """
    conn = get_db_connection()
    if conn:
        try:
            query = """
            SELECT rowid, * FROM journalists
            WHERE Ämnesområden LIKE ? OR "Analys av Position" LIKE ?
            """
            search_pattern = f"%{search_term}%"
            results = pd.read_sql_query(query, conn, params=(search_pattern, search_pattern))
            conn.close()
            return results
        except Exception as e:
            st.error(f"An error occurred during search: {e}")
            conn.close()
    return pd.DataFrame()

def add_interest_to_journalist(rowid, new_interest):
    """Appends a new interest to a journalist using their unique rowid."""
    conn = get_db_connection()
    if conn and new_interest:
        try:
            cursor = conn.cursor()
            # 1. Get current interests using the unique rowid
            cursor.execute("SELECT Ämnesområden FROM journalists WHERE rowid = ?", (rowid,))
            result = cursor.fetchone()
            if result:
                current_interests = result['Ämnesområden']
                updated_interests = f"{current_interests}, {new_interest.strip()}"
                # 3. Update the database using the unique rowid
                cursor.execute("UPDATE journalists SET Ämnesområden = ? WHERE rowid = ?", (updated_interests, rowid))
                conn.commit()
                st.success(f"Updated interests for journalist ID {rowid}.")
            else:
                st.warning(f"Could not find journalist with ID: {rowid}")
        except sqlite3.Error as e:
            st.error(f"Database error while updating: {e}")
        finally:
            conn.close()
            # Clear the cache to reflect changes immediately
            get_all_journalists.clear()


# --- UI Display Function ---

def display_journalist(journalist):
    """Displays a single journalist's info and uses rowid for widget keys."""
    st.markdown(f"""
    <div class="journalist-card">
        <div class="journalist-name">{journalist['Namn']}</div>
        <div class="journalist-category">{journalist['Kategori']}</div>
        <div class="journalist-details">
            <strong><p>📝 Ämnesområden:</p></strong>
            <p>{journalist['Ämnesområden']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Visa detaljer och redigera"):
        st.write("**Typiska Plattformar:**", journalist['Typiska Plattformar'])
        st.write("**Analys av Position:**", journalist['Analys av Position'])
        st.markdown("---")
        st.subheader("Lägg till nytt ämnesområde")

        # FIX: Use the unique 'rowid' for the key to prevent duplicates.
        unique_key = journalist['rowid']
        new_interest = st.text_input("Nytt ämne:", key=f"interest_{unique_key}")
        if st.button("Spara ämne", key=f"btn_{unique_key}"):
            # Pass the unique rowid to the update function
            add_interest_to_journalist(unique_key, new_interest)
            st.rerun()


# --- Main Application Logic ---

def main():
    st.title("🗃️ Journalistdatabas")
    st.write("Sök i databasen eller lägg till nya ämnesområden för en journalist.")

    if not os.path.exists(DB_FILE):
        st.error(f"Databasfilen '{DB_FILE}' hittades inte. Kör skriptet `create_db.py` först.")
        return

    st.sidebar.header("Kontroller")
    app_mode = st.sidebar.radio("Välj läge", ["Sök", "Visa alla"])

    if app_mode == "Sök":
        st.header("🔍 Sök efter journalist")
        search_term = st.text_input(
            "Sök på ämne eller i analysen (t.ex. 'politik', 'liberal', 'public service')", ""
        )
        if search_term:
            results = search_journalists(search_term)
            st.subheader(f"Resultat för '{search_term}': {len(results)} träffar")
            if not results.empty:
                col1, col2 = st.columns(2)
                for index, journalist in results.iterrows():
                    with col1 if index % 2 == 0 else col2:
                        display_journalist(journalist)
            else:
                st.warning("Inga journalister hittades.")

    elif app_mode == "Visa alla":
        st.header("👥 Alla Journalister")
        all_journalists = get_all_journalists()
        st.write(f"Visar totalt {len(all_journalists)} journalister.")
        if not all_journalists.empty:
            col1, col2 = st.columns(2)
            for index, journalist in all_journalists.iterrows():
                with col1 if index % 2 == 0 else col2:
                    display_journalist(journalist)

if __name__ == "__main__":
    main()
