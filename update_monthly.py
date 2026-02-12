"""
Automated monthly update script for IPC database
This script:
1. Downloads the latest IPC data from datos.gob.ar
2. Checks for new data not yet in the database
3. Updates the database with only new records
"""

import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
from sqlalchemy import text
from config import Config
from db_setup import get_engine, setup_db
import sys

# Download URLs (same as in the original scraper)
DOWNLOAD_URLS = {
    'general_level_categories': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.12/download/ipc-incidencia-categorias-nivel-general.csv',
        'description': 'IPC Nivel General y Categorías'
    },
    'divisions_by_region': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.10/download/ipc-incidencia-absoluta-mensual-region-capitulo.csv',
        'description': 'IPC Divisiones por Región'
    },
    'goods_services': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.11/download/ipc-incidencia-mensual-bienes-servicios.csv',
        'description': 'IPC Bienes y Servicios'
    }
}


def get_last_date_in_db():
    """
    Gets the most recent date recorded in the database
    """
    engine = get_engine()
    query = "SELECT MAX(date) as last_date FROM fact_inflation"
    
    try:
        with engine.connect() as conn:
            result = pd.read_sql(query, conn)
            last_date = result['last_date'].iloc[0]
            
            if pd.isna(last_date):
                return None
            
            return pd.to_datetime(last_date)
    except Exception as e:
        print(f"⚠️  Error getting last date: {e}")
        return None


def extract_metadata(series_name, dataset_type):
    """
    Extracts region, category and classification from the series name.
    Search strings are kept in Spanish to match source data.
    Returned values are also kept in Spanish for data consistency.
    """
    name = str(series_name).lower().replace('_', ' ')
    
    # Detect region
    region = "Nacional"
    if 'gba' in name:
        region = "GBA"
    elif 'pampeana' in name:
        region = "Pampeana"
    elif 'noa' in name or 'noroeste' in name:
        region = "NOA"
    elif 'nea' in name or 'noreste' in name:
        region = "NEA"
    elif 'cuyo' in name:
        region = "Cuyo"
    elif 'patagonia' in name:
        region = "Patagonia"
    
    # Determine category and classification based on dataset type
    if dataset_type == 'general_level_categories':
        category = "Análisis"
        
        if 'nivel general' in name:
            category = "Nivel General"
            classification = "Total"
        elif 'nucleo' in name or 'núcleo' in name:
            classification = "Núcleo"
        elif 'regulado' in name:
            classification = "Regulados"
        elif 'estacional' in name:
            classification = "Estacionales"
        else:
            classification = name.replace(region.lower(), '').strip()
    
    elif dataset_type == 'divisions_by_region':
        category = "División"
        
        if 'alimentos bebidas no alcoholica' in name:
            classification = "Alimentos y bebidas"
        elif 'bebidas alcoholica' in name or 'tabaco' in name:
            classification = "Bebidas alcohólicas y tabaco"
        elif 'prenda' in name or 'vestir' in name or 'calzado' in name:
            classification = "Prendas de vestir y calzado"
        elif 'vivienda' in name or 'agua' in name or 'electricidad' in name or 'combustible' in name:
            classification = "Vivienda y servicios básicos"
        elif 'equipamiento' in name or 'mantenimiento' in name:
            classification = "Equipamiento del hogar"
        elif 'salud' in name:
            classification = "Salud"
        elif 'transporte' in name:
            classification = "Transporte"
        elif 'comunicacion' in name:
            classification = "Comunicación"
        elif 'recreacion' in name or 'cultura' in name:
            classification = "Recreación y cultura"
        elif 'educacion' in name:
            classification = "Educación"
        elif 'restaurante' in name or 'hotel' in name:
            classification = "Restaurantes y hoteles"
        elif 'otros' in name or 'bienes servicios' in name:
            classification = "Bienes y servicios varios"
        else:
            classification = name.replace(region.lower(), '').strip()
    
    elif dataset_type == 'goods_services':
        category = "Naturaleza"
        
        if 'bien' in name and 'servicio' not in name:
            classification = "Bienes"
        elif 'servicio' in name:
            classification = "Servicios"
        else:
            classification = name.replace(region.lower(), '').strip()
    
    else:
        category = "Otros"
        classification = name
    
    return region, category, classification


def download_and_process_csv(name, config, start_date):
    """
    Downloads and processes a CSV into the required format
    """
    print(f"\n{'='*70}")
    print(f"Downloading: {name}")
    print(f"URL: {config['url']}")
    print('='*70)
    
    try:
        response = requests.get(config['url'], timeout=60)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text))
        print(f"✓ Downloaded: {len(df)} rows")
        
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Filter by date
        df_filtered = df[df[date_col] >= start_date].copy()
        print(f"✓ Filtered from {start_date}: {len(df_filtered)} rows")
        
        # Convert to long format
        df_long = pd.melt(
            df_filtered,
            id_vars=[date_col],
            var_name='original_series',
            value_name='value'
        )
        
        df_long = df_long.rename(columns={date_col: 'time_index'})
        
        # Extract metadata
        df_long[['region', 'category', 'classification']] = df_long['original_series'].apply(
            lambda x: pd.Series(extract_metadata(x, name))
        )
        
        df_long = df_long.drop('original_series', axis=1)
        df_long = df_long.dropna(subset=['value'])
        
        print(f"✓ Processed: {len(df_long)} records")
        
        return df_long
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def update_dimensions(df, conn):
    """
    Updates dimension tables with new values if they exist
    """
    # Update dim_region
    regions = df[['region']].drop_duplicates()
    for reg in regions['region']:
        conn.execute(
            text("INSERT INTO dim_region (region_name) VALUES (:r) ON CONFLICT DO NOTHING"),
            {"r": reg}
        )
    
    # Update dim_category
    cats = df[['category', 'classification']].drop_duplicates()
    for _, row in cats.iterrows():
        conn.execute(
            text("INSERT INTO dim_category (category_name, classification) VALUES (:n, :c) ON CONFLICT DO NOTHING"),
            {"n": row['category'], "c": row['classification']}
        )
    
    conn.commit()


def insert_facts(df, conn):
    """
    Inserts new data into fact_inflation
    """
    # Get ID mappings
    res_reg = pd.read_sql("SELECT * FROM dim_region", conn)
    res_cat = pd.read_sql("SELECT * FROM dim_category", conn)
    
    dict_reg = dict(zip(res_reg['region_name'], res_reg['region_id']))

    # Composite key mapping for categories (category_name + classification)
    dict_cat = {}
    for _, row in res_cat.iterrows():
        key = (row['category_name'], row['classification'])
        dict_cat[key] = row['category_id']

    df['region_id'] = df['region'].map(dict_reg)
    df['category_id'] = df.apply(lambda x: dict_cat.get((x['category'], x['classification'])), axis=1)
    
    # Insert with UPSERT
    inserted = 0
    updated = 0
    
    for _, row in df.iterrows():
        insert_query = """
        INSERT INTO fact_inflation (date, region_id, category_id, index_value)
        VALUES (:d, :r_id, :c_id, :v)
        ON CONFLICT (date, region_id, category_id) 
        DO UPDATE SET index_value = EXCLUDED.index_value
        RETURNING (xmax = 0) AS inserted
        """
        result = conn.execute(text(insert_query), {
            "d": row['time_index'],
            "r_id": row['region_id'],
            "c_id": row['category_id'],
            "v": row['value']
        })
        
        was_inserted = result.fetchone()[0]
        if was_inserted:
            inserted += 1
        else:
            updated += 1
    
    conn.commit()
    
    return inserted, updated


def main():
    """
    Main update function
    """
    print("=" * 80)
    print("AUTOMATED IPC DATA UPDATE")
    print("=" * 80)
    print(f"Execution date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # 1. Verify DB structure
        setup_db()
        
        # 2. Get last date in DB
        last_date_in_db = get_last_date_in_db()
        
        if last_date_in_db is None:
            print("\n⚠️  The database is empty.")
            print("Run the initial load script first: db_setup.py")
            sys.exit(1)
        
        print(f"\n📅 Last date in DB: {last_date_in_db.strftime('%Y-%m-%d')}")
        
        # 3. Calculate start date for the update
        # Download from 2 months back in case of revisions
        start_date = (last_date_in_db - timedelta(days=60)).replace(day=1)
        print(f"📥 Downloading data from: {start_date.strftime('%Y-%m-%d')}")
        
        # 4. Download updated data
        dataframes = []
        for name, config in DOWNLOAD_URLS.items():
            df = download_and_process_csv(name, config, start_date)
            if df is not None:
                dataframes.append(df)
        
        if not dataframes:
            print("\n❌ Could not download data")
            sys.exit(1)
        
        # 5. Consolidate data
        df_new = pd.concat(dataframes, ignore_index=True)
        df_new['time_index'] = pd.to_datetime(df_new['time_index'])
        
        # 6. Filter only truly new data
        df_new = df_new[df_new['time_index'] >= last_date_in_db]
        
        if len(df_new) == 0:
            print("\n✅ No new data to update")
            print("The database is up to date!")
            return
        
        print(f"\n📊 New data found:")
        print(f"   Records: {len(df_new)}")
        print(f"   Period: {df_new['time_index'].min().strftime('%Y-%m-%d')} to {df_new['time_index'].max().strftime('%Y-%m-%d')}")
        
        # 7. Update database
        print("\n🔄 Updating database...")
        engine = get_engine()
        
        with engine.connect() as conn:
            # Update dimensions
            update_dimensions(df_new, conn)
            
            # Insert facts
            inserted, updated = insert_facts(df_new, conn)
        
        print("\n" + "=" * 80)
        print("✅ UPDATE COMPLETED")
        print("=" * 80)
        print(f"   Records inserted: {inserted}")
        print(f"   Records updated: {updated}")
        print(f"   Total processed: {inserted + updated}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()