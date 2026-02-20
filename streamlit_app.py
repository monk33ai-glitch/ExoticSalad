
import streamlit as st
import sqlite3
import pandas as pd
import os
import json
import google.generativeai as genai
from datetime import datetime

# --- CONFIGURATION ---
DB_NAME = "hortus_v2.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS plants (
            id TEXT PRIMARY KEY,
            common_name TEXT,
            scientific_name TEXT,
            usda_zones TEXT,
            min_temp REAL,
            max_temp REAL,
            drought_tolerance TEXT,
            watering_requirements TEXT,
            watering_frequency TEXT,
            sunlight TEXT,
            soil_type TEXT,
            fertilization_schedule TEXT,
            notes TEXT,
            herbal_benefits TEXT,
            herbal_properties TEXT,
            herbal_dosage TEXT,
            herbal_notes TEXT,
            is_wishlist BOOLEAN,
            date_added TIMESTAMP,
            images TEXT,
            grounding_sources TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_plant(p):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO plants VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        p['id'], p['common_name'], p['scientific_name'], json.dumps(p['usda_zones']),
        p['min_temp'], p['max_temp'], p['drought_tolerance'], p['watering_requirements'],
        p['watering_frequency'], p['sunlight'], p['soil_type'], p['fertilization_schedule'],
        p['notes'], p['herbal_benefits'], p['herbal_properties'], p['herbal_dosage'],
        p['herbal_notes'], p['is_wishlist'], p['date_added'], json.dumps(p.get('images', [])),
        json.dumps(p.get('grounding_sources', []))
    ))
    conn.commit()
    conn.close()

def get_all_plants():
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM plants", conn)
        conn.close()
        # Convert JSON columns back to objects
        df['usda_zones'] = df['usda_zones'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
        return df
    except Exception as e:
        st.error(f"Vault Read Error: {e}")
        return pd.DataFrame()

# --- AI RESEARCH ---
def perform_research(common, scientific, description):
    api_key = st.secrets.get("API_KEY") or os.environ.get("API_KEY")
    
    if not api_key:
        st.warning("API_KEY not found in Secrets or Environment. Research capabilities are offline.")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Botanical Analysis Protocol for: {common} {scientific}.
    Clues: {description}
    Return JSON only: common_name, scientific_name, usda_zones (int list), min_temp (F), max_temp (F), 
    drought_tolerance, watering_requirements, watering_frequency, sunlight, soil_type, 
    fertilization_schedule, herbal_benefits, herbal_properties, herbal_dosage, herbal_notes, notes.
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        st.error(f"AI Core Failure: {e}")
        return None

# --- UI ---
st.set_page_config(page_title="Exotica Hortus 2.0", page_icon="🌿", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0c110f; color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: #161c1a; border-right: 1px solid #2d3632; }
    h1, h2, h3 { color: #10b981 !important; font-family: 'Georgia', serif; letter-spacing: -0.02em; }
    .stDataFrame { border: 1px solid #2d3632; border-radius: 12px; }
    .stExpander { background-color: #161c1a; border: 1px solid #2d3632 !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

init_db()

# --- NAVIGATION ---
with st.sidebar:
    st.title("🌿 Hortus 2.0")
    st.caption("Fresh Relational Build v2.1")
    st.divider()
    page = st.radio("Access Terminal", ["Vault Archives", "Research Lab", "System Tools"])
    
    st.divider()
    st.info("System Status: Healthy")

# --- PAGES ---
if page == "Vault Archives":
    st.header("Specimen Archives")
    df = get_all_plants()
    
    if df.empty:
        st.info("Archives empty. Use the Research Lab to populate the vault.")
    else:
        search = st.text_input("Filter Registry...", "")
        if search:
            df = df[df['common_name'].str.contains(search, case=False) | df['scientific_name'].str.contains(search, case=False)]
        
        # Grid View for Relational Data
        for _, row in df.iterrows():
            with st.expander(f"📖 {row['common_name']} — {row['scientific_name']}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**Climate**")
                    st.write(f"Zones: {row['usda_zones']}")
                    st.write(f"Range: {row['min_temp']}°F - {row['max_temp']}°F")
                with c2:
                    st.markdown("**Care**")
                    st.write(f"Water: {row['watering_frequency']}")
                    st.write(f"Sun: {row['sunlight']}")
                with c3:
                    st.markdown("**Status**")
                    st.write("Wishlist" if row['is_wishlist'] else "In Collection")
                
                st.divider()
                st.markdown("**Herbal Benefits**")
                st.write(row['herbal_benefits'])
                st.markdown("**Herbalist Notes**")
                st.write(row['herbal_notes'])

elif page == "Research Lab":
    st.header("Botanical Research Lab")
    st.write("Identify and analyze rare botanical life.")
    
    with st.form("research_form"):
        col1, col2 = st.columns(2)
        with col1: common_in = st.text_input("Common Name")
        with col2: scientific_in = st.text_input("Scientific Name")
        desc_in = st.text_area("Contextual Observations (Physical description, etc.)")
        wish_in = st.checkbox("Mark for Acquisition (Wishlist)")
        
        if st.form_submit_button("Initiate Research Protocol"):
            if not common_in and not scientific_in and not desc_in:
                st.error("Identification requires at least one data point.")
            else:
                with st.spinner("Accessing Botanical Knowledge Base..."):
                    res = perform_research(common_in, scientific_in, desc_in)
                    if res:
                        res['id'] = str(datetime.now().timestamp())
                        res['date_added'] = datetime.now()
                        res['is_wishlist'] = wish_in
                        save_plant(res)
                        st.success(f"Archived: {res['common_name']}")
                        st.balloons()

elif page == "System Tools":
    st.header("Maintenance & Migration")
    st.write("Tools for database management and CSV portability.")
    
    df = get_all_plants()
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Export Vault Snapshot (CSV)", csv, "hortus_vault_v2_export.csv", "text/csv")
    
    st.divider()
    st.warning("Database Management")
    if st.button("Flush Cache"):
        st.cache_data.clear()
        st.success("System Cache Cleared.")
import streamlit as st
from supabase import create_client


# Temporary Hard-Wire Bypass
url = "https://fgdujxyepmgclimcpwgl.supabase.co"
key = "sb_publishable_yGb5vK50XCUc9xQvkIhXZg_5UJJxEAT"

# This creates the actual connection
supabase = create_client(url, key)
