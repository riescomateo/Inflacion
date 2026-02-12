"""
Secure database setup and population script for IPC data
Uses environment variables for credentials
"""
import pandas as pd
from sqlalchemy import create_engine, text
from config import Config


def get_engine():
    """Creates and returns a database engine with secure credentials"""
    Config.validate()
    return create_engine(Config.get_db_url())


def setup_db():
    """Creates the Star Schema structure if it does not exist."""
    create_schema_query = """
    CREATE TABLE IF NOT EXISTS dim_region (
        region_id SERIAL PRIMARY KEY,
        region_name VARCHAR(50) UNIQUE
    );
    
    CREATE TABLE IF NOT EXISTS dim_category (
        category_id SERIAL PRIMARY KEY,
        category_name VARCHAR(100),
        classification VARCHAR(50),
        UNIQUE(category_name, classification)
    );
    
    CREATE TABLE IF NOT EXISTS fact_inflation (
        date DATE,
        region_id INT REFERENCES dim_region(region_id),
        category_id INT REFERENCES dim_category(category_id),
        index_value DECIMAL(18, 4),
        PRIMARY KEY (date, region_id, category_id)
    );
    
    -- Indexes to improve query performance
    CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_inflation(date);
    CREATE INDEX IF NOT EXISTS idx_fact_region ON fact_inflation(region_id);
    CREATE INDEX IF NOT EXISTS idx_fact_category ON fact_inflation(category_id);
    """
    
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(create_schema_query))
        conn.commit()
    
    print("✅ Database structure verified/created in Supabase.")


def populate_from_csv(file_path):
    """Reads the CSV and inserts it into the relational model."""
    # Load data - The CSV already has headers: time_index, value, region, category, classification
    df = pd.read_csv(file_path)
    df['time_index'] = pd.to_datetime(df['time_index'])

    engine = get_engine()
    with engine.connect() as conn:
        # A. Populate dim_region
        regions = df[['region']].drop_duplicates()
        for reg in regions['region']:
            conn.execute(
                text("INSERT INTO dim_region (region_name) VALUES (:r) ON CONFLICT DO NOTHING"),
                {"r": reg}
            )
        
        # B. Populate dim_category
        # Use the column names exactly as they appear in the CSV
        cats = df[['category', 'classification']].drop_duplicates()
        for _, row in cats.iterrows():
            conn.execute(
                text("""INSERT INTO dim_category (category_name, classification) 
                        VALUES (:n, :c) 
                        ON CONFLICT (category_name, classification) DO NOTHING"""),
                {"n": row['category'], "c": row['classification']}
            )
        conn.commit()
        
        # C. ID mapping
        res_reg = pd.read_sql("SELECT * FROM dim_region", conn)
        res_cat = pd.read_sql("SELECT * FROM dim_category", conn)
        
        dict_reg = dict(zip(res_reg['region_name'], res_reg['region_id']))

        dict_cat = {}
        for _, row in res_cat.iterrows():
            # Map using the SQL column names
            key = (row['category_name'], row['classification'])
            dict_cat[key] = row['category_id']

        df['region_id'] = df['region'].map(dict_reg)
        df['category_id'] = df.apply(lambda x: dict_cat.get((x['category'], x['classification'])), axis=1)
        
        # D. Load fact_inflation
        print("Uploading data to the fact table...")
        for _, row in df.iterrows():
            insert_query = """
            INSERT INTO fact_inflation (date, region_id, category_id, index_value)
            VALUES (:d, :r_id, :c_id, :v)
            ON CONFLICT (date, region_id, category_id) 
            DO UPDATE SET index_value = EXCLUDED.index_value
            """
            conn.execute(text(insert_query), {
                "d": row['time_index'],
                "r_id": row['region_id'],
                "c_id": row['category_id'],
                "v": row['value']
            })
        conn.commit()
    
    print(f"✅ Process completed! Data from {file_path} synchronized.")


# Execution
if __name__ == "__main__":
    try:
        setup_db()
        populate_from_csv("ipc_indec_datos.csv")
    except Exception as e:
        print(f"❌ Error during process: {e}")