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
        region_id   SERIAL PRIMARY KEY,
        region_name VARCHAR(50) UNIQUE
    );

    CREATE TABLE IF NOT EXISTS dim_category (
        category_id    SERIAL PRIMARY KEY,
        category_name  VARCHAR(100),
        classification VARCHAR(100),
        nature         VARCHAR(50),
        UNIQUE(category_name, classification)
    );

    CREATE TABLE IF NOT EXISTS fact_inflation (
        date          DATE,
        region_id     INT REFERENCES dim_region(region_id),
        category_id   INT REFERENCES dim_category(category_id),
        incidence     DECIMAL(18, 6),
        mom_variation DECIMAL(18, 6),
        PRIMARY KEY (date, region_id, category_id)
    );

    -- Indexes to improve query performance
    CREATE INDEX IF NOT EXISTS idx_fact_date     ON fact_inflation(date);
    CREATE INDEX IF NOT EXISTS idx_fact_region   ON fact_inflation(region_id);
    CREATE INDEX IF NOT EXISTS idx_fact_category ON fact_inflation(category_id);
    """

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(create_schema_query))
        conn.commit()

    print("✅ Database structure verified/created in Supabase.")


def populate_from_csv(file_path):
    """Reads the CSV and inserts it into the relational model."""
    # Load data
    # CSV columns: time_index, region, category, classification,
    #              nature, incidence, mom_variation
    df = pd.read_csv(file_path)
    df['time_index'] = pd.to_datetime(df['time_index'])

    engine = get_engine()
    with engine.connect() as conn:

        # A. Populate dim_region
        for reg in df['region'].drop_duplicates():
            conn.execute(
                text("INSERT INTO dim_region (region_name) VALUES (:r) "
                     "ON CONFLICT DO NOTHING"),
                {"r": reg}
            )

        # B. Populate dim_category
        # nature is a property of the category → lives in dim, not in fact
        cats = df[['category', 'classification', 'nature']].drop_duplicates()
        for _, row in cats.iterrows():
            conn.execute(
                text("""
                    INSERT INTO dim_category (category_name, classification, nature)
                    VALUES (:n, :c, :nat)
                    ON CONFLICT (category_name, classification)
                    DO UPDATE SET nature = EXCLUDED.nature
                """),
                {
                    "n":   row['category'],
                    "c":   row['classification'],
                    "nat": None if pd.isna(row['nature']) else row['nature']
                }
            )
        conn.commit()

        # C. ID mapping
        res_reg = pd.read_sql("SELECT * FROM dim_region", conn)
        res_cat = pd.read_sql("SELECT * FROM dim_category", conn)

        dict_reg = dict(zip(res_reg['region_name'], res_reg['region_id']))

        dict_cat = {}
        for _, row in res_cat.iterrows():
            key = (row['category_name'], row['classification'])
            dict_cat[key] = row['category_id']

        df['region_id']   = df['region'].map(dict_reg)
        df['category_id'] = df.apply(
            lambda x: dict_cat.get((x['category'], x['classification'])), axis=1
        )

        # D. Load fact_inflation with both metrics
        print("Uploading data to the fact table (this may take a few seconds)...")
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO fact_inflation
                        (date, region_id, category_id, incidence, mom_variation)
                    VALUES
                        (:d, :r_id, :c_id, :inc, :mom)
                    ON CONFLICT (date, region_id, category_id)
                    DO UPDATE SET
                        incidence     = EXCLUDED.incidence,
                        mom_variation = EXCLUDED.mom_variation
                """),
                {
                    "d":    row['time_index'],
                    "r_id": row['region_id'],
                    "c_id": row['category_id'],
                    "inc":  None if pd.isna(row['incidence'])    else row['incidence'],
                    "mom":  None if pd.isna(row['mom_variation']) else row['mom_variation']
                }
            )
        conn.commit()

    print(f"✅ Process completed! Data from {file_path} synchronized.")


# Execution
if __name__ == "__main__":
    try:
        setup_db()
        populate_from_csv("ipc_indec_datos.csv")
    except Exception as e:
        print(f"❌ Error during process: {e}")