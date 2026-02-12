"""
Script to download IPC (Consumer Price Index) data from datos.gob.ar
With verified and functional URLs
"""

import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import sys

START_DATE = "2023-12-01"

# Verified and functional download URLs from infra.datos.gob.ar
DOWNLOAD_URLS = {
    # Dataset 145 - General Level and Categories
    'general_level_categories': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.12/download/ipc-incidencia-categorias-nivel-general.csv',
        'description': 'IPC Nivel General y Categorías (Núcleo, Regulados, Estacionales) por Región'
    },
    
    # Dataset 145 - Divisions (Chapters) by Region
    'divisions_by_region': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.10/download/ipc-incidencia-absoluta-mensual-region-capitulo.csv',
        'description': 'IPC Divisiones (12 capítulos) por Región'
    },
    
    # Dataset 145 - Goods and Services by Region
    'goods_services': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.11/download/ipc-incidencia-mensual-bienes-servicios.csv',
        'description': 'IPC Bienes y Servicios por Región'
    }
}


def download_and_process_csv(name, config, start_date):
    """
    Downloads and processes a CSV into the required format
    """
    print(f"\n{'='*70}")
    print(f"Downloading: {name}")
    print(f"Description: {config['description']}")
    print(f"URL: {config['url']}")
    print('='*70)
    
    try:
        # Download
        response = requests.get(config['url'], timeout=60)
        response.raise_for_status()
        
        # Read CSV
        df = pd.read_csv(StringIO(response.text))
        print(f"✓ Downloaded: {len(df)} rows, {len(df.columns)} columns")
        
        # Convert date
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
        
        # Extract region, category and classification from column name
        df_long[['region', 'category', 'classification']] = df_long['original_series'].apply(
            lambda x: pd.Series(extract_metadata(x, name))
        )
        
        # Drop temporary column
        df_long = df_long.drop('original_series', axis=1)
        
        # Drop null values
        df_long = df_long.dropna(subset=['value'])
        
        print(f"✓ Converted to long format: {len(df_long)} records")
        print(f"  - Unique regions: {df_long['region'].nunique()}")
        print(f"  - Unique classifications: {df_long['classification'].nunique()}")
        
        return df_long
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Download error: {e}")
        return None
    except Exception as e:
        print(f"✗ Processing error: {e}")
        import traceback
        traceback.print_exc()
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


def main():
    """Main function"""
    print("=" * 80)
    print("IPC DATA DOWNLOAD - INDEC (datos.gob.ar)")
    print("Script with verified URLs")
    print("=" * 80)
    print(f"Start date: {START_DATE}")
    print(f"Datasets to download: {len(DOWNLOAD_URLS)}")
    print("=" * 80)
    
    # List to store DataFrames
    dataframes = []
    
    # Download each dataset
    for name, config in DOWNLOAD_URLS.items():
        df = download_and_process_csv(name, config, START_DATE)
        if df is not None:
            dataframes.append(df)
    
    # Check that data was downloaded
    if not dataframes:
        print("\n" + "=" * 80)
        print("⚠️  ERROR: Could not download data")
        print("=" * 80)
        print("\nPossible causes:")
        print("1. Internet connection issues")
        print("2. datos.gob.ar servers are down")
        print("3. URLs have changed")
        print("\nRecommendation:")
        print("- Check your connection")
        print("- Try again in a few minutes")
        print("- Visit: https://datos.gob.ar/")
        sys.exit(1)
    
    # Consolidate all DataFrames
    print("\n" + "=" * 80)
    print("CONSOLIDATING DATA...")
    print("=" * 80)
    
    df_final = pd.concat(dataframes, ignore_index=True)
    
    # Clean data
    df_final = df_final.dropna(subset=['value'])
    df_final = df_final.sort_values(['time_index', 'region', 'category', 'classification'])
    df_final = df_final.reset_index(drop=True)
    
    # Format date
    df_final['time_index'] = pd.to_datetime(df_final['time_index']).dt.strftime('%Y-%m-%d')
    
    # Summary
    print(f"\n✓ CONSOLIDATED DATA:")
    print(f"  {'Total records:':<30} {len(df_final):>10,}")
    print(f"  {'Period:':<30} {df_final['time_index'].min()} to {df_final['time_index'].max()}")
    print(f"  {'Unique regions:':<30} {df_final['region'].nunique():>10}")
    print(f"  {'Unique categories:':<30} {df_final['category'].nunique():>10}")
    print(f"  {'Unique classifications:':<30} {df_final['classification'].nunique():>10}")
    
    # Distribution by region
    print("\n" + "=" * 80)
    print("DISTRIBUTION BY REGION:")
    print("=" * 80)
    region_counts = df_final.groupby('region').size().sort_values(ascending=False)
    for region, count in region_counts.items():
        print(f"  {region:<20} {count:>10,} records")
    
    # Distribution by category
    print("\n" + "=" * 80)
    print("DISTRIBUTION BY CATEGORY:")
    print("=" * 80)
    cat_counts = df_final.groupby('category').size().sort_values(ascending=False)
    for cat, count in cat_counts.items():
        print(f"  {cat:<20} {count:>10,} records")
    
    # Save file
    output_file = 'ipc_indec_datos.csv'
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 80)
    print(f"✓ FILE SAVED: {output_file}")
    print("=" * 80)
    
    # Data sample
    print("\nDATA SAMPLE (first 20 rows):")
    print("=" * 80)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)
    print(df_final.head(20).to_string(index=False))
    
    print("\n" + "=" * 80)
    print("✓ DOWNLOAD COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nCSV format:")
    print(f"  - Columns: time_index, value, region, category, classification")
    print(f"  - Format: LONG (unpivoted)")
    print(f"  - Encoding: UTF-8 with BOM")
    print(f"\nData is ready for analysis!")


if __name__ == "__main__":
    main()