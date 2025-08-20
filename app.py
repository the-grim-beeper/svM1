import streamlit as st
import pandas as pd
import sqlite3
import os
from pyvis.network import Network
import streamlit.components.v1 as components

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
                # Avoid adding if it already exists
                if new_interest.strip().lower() in [i.lower() for i in current_interests.split(',')]:
                    st.warning(f"'{new_interest}' already exists for this journalist.")
                    return
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


# --- UI Display Functions ---

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

        unique_key = journalist['rowid']
        new_interest = st.text_input("Nytt ämne:", key=f"interest_{unique_key}")
        if st.button("Spara ämne", key=f"btn_{unique_key}"):
            add_interest_to_journalist(unique_key, new_interest)
            st.rerun()


def generate_network_visualization(df):
    """Generates and displays an interactive network graph of journalists and subjects."""
    net = Network(height='750px', width='100%', bgcolor='#222222', font_color='white', notebook=True)

    # Set physics layout for a better-looking graph
    net.set_options("""
    var options = {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -30000,
          "centralGravity": 0.3,
          "springLength": 150
        },
        "minVelocity": 0.75
      }
    }
    """)

    journalists = df['Namn'].unique()
    subjects = set()

    # Process subjects
    for sub_list in df['Ämnesområden'].dropna():
        # Clean up subjects: split by comma, strip whitespace, remove empty strings and periods.
        cleaned_subjects = [s.strip().replace('.', '') for s in sub_list.split(',') if s.strip()]
        subjects.update(cleaned_subjects)

    # Add nodes to the graph
    for journalist in journalists:
        net.add_node(journalist, label=journalist, title=journalist, color='#3498db', size=25)

    for subject in subjects:
        net.add_node(subject, label=subject, title=subject, color='#e74c3c', size=15)

    # Add edges connecting journalists to their subjects
    for _, row in df.iterrows():
        journalist_name = row['Namn']
        if pd.notna(row['Ämnesområden']):
            journalist_subjects = [s.strip().replace('.', '') for s in row['Ämnesområden'].split(',') if s.strip()]
            for subject in journalist_subjects:
                net.add_edge(journalist_name, subject)

    # Save and display the graph
    try:
        path = '/tmp'
        if not os.path.exists(path):
            os.makedirs(path)
        file_path = os.path.join(path, 'pyvis_graph.html')
        net.save_graph(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        components.html(html_content, height=800)
    except Exception as e:
        st.error(f"Could not generate or display the graph: {e}")


# --- Main Application Logic ---

def main():
    st.title("🗃️ Journalistdatabas")
    st.write("Sök, redigera eller visualisera relationerna mellan journalister och deras ämnesområden.")

    if not os.path.exists(DB_FILE):
        st.error(f"Databasfilen '{DB_FILE}' hittades inte. Kör skriptet `create_db.py` först.")
        return

    st.sidebar.header("Kontroller")
    app_mode = st.sidebar.radio("Välj läge", ["Sök", "Visa alla", "Nätverksvisualisering"])

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

    elif app_mode == "Nätverksvisualisering":
        st.header("🕸️ Nätverk av Journalister och Ämnen")
        st.info("Klicka och dra noder för att utforska nätverket. Zooma med scrollhjulet.")
        all_journalists = get_all_journalists()
        if not all_journalists.empty:
            generate_network_visualization(all_journalists)
        else:
            st.warning("Ingen data att visualisera.")


if __name__ == "__main__":
    main()
