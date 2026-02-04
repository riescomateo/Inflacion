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
    """Crea la estructura de Star Schema si no existe."""
    query_schema = """
    CREATE TABLE IF NOT EXISTS dim_region (
        region_id SERIAL PRIMARY KEY,
        region_nombre VARCHAR(50) UNIQUE
    );
    
    CREATE TABLE IF NOT EXISTS dim_categoria (
        categoria_id SERIAL PRIMARY KEY,
        categoria_nombre VARCHAR(100) UNIQUE,
        clasificacion VARCHAR(50)
    );
    
    CREATE TABLE IF NOT EXISTS fact_inflacion (
        fecha DATE,
        region_id INT REFERENCES dim_region(region_id),
        categoria_id INT REFERENCES dim_categoria(categoria_id),
        valor_indice DECIMAL(18, 4),
        PRIMARY KEY (fecha, region_id, categoria_id)
    );
    
    -- Índices para mejorar el rendimiento de consultas
    CREATE INDEX IF NOT EXISTS idx_fact_fecha ON fact_inflacion(fecha);
    CREATE INDEX IF NOT EXISTS idx_fact_region ON fact_inflacion(region_id);
    CREATE INDEX IF NOT EXISTS idx_fact_categoria ON fact_inflacion(categoria_id);
    """
    
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(query_schema))
        conn.commit()
    
    print("✅ Estructura de base de datos verificada/creada en Supabase.")

def poblar_desde_csv(file_path):
    """Lee el CSV y lo inserta en el modelo relacional."""
    # Cargar datos
    df = pd.read_csv(file_path)
    df['indice_tiempo'] = pd.to_datetime(df['indice_tiempo'])
    
    engine = get_engine()
    with engine.connect() as conn:
        # A. Poblar dim_region
        regiones = df[['region']].drop_duplicates()
        for reg in regiones['region']:
            conn.execute(
                text("INSERT INTO dim_region (region_nombre) VALUES (:r) ON CONFLICT DO NOTHING"),
                {"r": reg}
            )
        
        # B. Poblar dim_categoria
        cats = df[['categoria', 'clasificacion']].drop_duplicates()
        for _, row in cats.iterrows():
            conn.execute(
                text("INSERT INTO dim_categoria (categoria_nombre, clasificacion) VALUES (:n, :c) ON CONFLICT DO NOTHING"),
                {"n": row['categoria'], "c": row['clasificacion']}
            )
        conn.commit()
        
        # C. Mapeo de IDs (Traemos los IDs generados por el servidor)
        res_reg = pd.read_sql("SELECT * FROM dim_region", conn)
        res_cat = pd.read_sql("SELECT * FROM dim_categoria", conn)
        
        dict_reg = dict(zip(res_reg['region_nombre'], res_reg['region_id']))
        dict_cat = dict(zip(res_cat['categoria_nombre'], res_cat['categoria_id']))
        
        df['region_id'] = df['region'].map(dict_reg)
        df['categoria_id'] = df['categoria'].map(dict_cat)
        
        # D. Carga de fact_inflacion con UPSERT
        print("Subiendo datos a la tabla de hechos (esto puede tardar unos segundos)...")
        for _, row in df.iterrows():
            query_insert = """
            INSERT INTO fact_inflacion (fecha, region_id, categoria_id, valor_indice)
            VALUES (:f, :r_id, :c_id, :v)
            ON CONFLICT (fecha, region_id, categoria_id) 
            DO UPDATE SET valor_indice = EXCLUDED.valor_indice
            """
            conn.execute(text(query_insert), {
                "f": row['indice_tiempo'],
                "r_id": row['region_id'],
                "c_id": row['categoria_id'],
                "v": row['valor']
            })
        conn.commit()
    
    print(f"✅ ¡Proceso completado! Datos de {file_path} sincronizados.")

# Ejecución
if __name__ == "__main__":
    try:
        setup_db()
        poblar_desde_csv("ipc_indec_datos.csv")
    except Exception as e:
        print(f"❌ Error en el proceso: {e}")
