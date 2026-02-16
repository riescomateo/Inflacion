"""
Script to download IPC (Consumer Price Index) data from datos.gob.ar
Produces two metrics per row:
  - incidence:      contribution of each category to total regional inflation (pp)
  - mom_variation:  month-over-month % change, calculated from the base index (145.9)
"""

import pandas as pd
import requests
from io import StringIO
import sys

START_DATE = "2023-12-01"

# --- INCIDENCE ENDPOINTS ---
# These publish the contribution (in percentage points) of each
# category/division/type to the regional total inflation for that month.
INCIDENCE_URLS = {
    'categories_by_region': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.12/download/ipc-incidencia-categorias-nivel-general.csv',
        'description': 'IPC Categories (Core, Regulated, Seasonal) by Region'
    },
    'divisions_by_region': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.10/download/ipc-incidencia-absoluta-mensual-region-capitulo.csv',
        'description': 'IPC Divisions (12 chapters) by Region'
    },
}

# Nature mapping derived from classification.
# Análisis / Nivel General rows → NaN (they are aggregates, not a single nature)
NATURE_MAP = {
    "Alimentos y bebidas":          "Bienes",
    "Bebidas alcohólicas y tabaco": "Bienes",
    "Prendas de vestir y calzado":  "Bienes",
    "Vivienda y servicios básicos": "Servicios",
    "Equipamiento del hogar":       "Bienes",
    "Salud":                        "Servicios",
    "Transporte":                   "Servicios",
    "Comunicación":                 "Servicios",
    "Recreación y cultura":         "Mixto",
    "Educación":                    "Servicios",
    "Restaurantes y hoteles":       "Servicios",
    "Bienes y servicios varios":    "Mixto",
}

# --- BASE INDEX ENDPOINT ---
# Publishes the cumulative index (base Dec 2016 = 100) for all regions
# including Nacional. Used to compute mom_variation via pct_change().
BASE_INDEX_URL = {
    'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.9/download/indice-precios-al-consumidor-apertura-por-categorias-base-diciembre-2016-mensual.csv',
    'description': 'IPC Base Index (Dec 2016=100) - All regions including Nacional'
}

# Region keyword map for column name parsing
REGION_MAP = {
    'gba':       'GBA',
    'pampeana':  'Pampeana',
    'noa':       'NOA',
    'noroeste':  'NOA',
    'nea':       'NEA',
    'noreste':   'NEA',
    'cuyo':      'Cuyo',
    'patagonia': 'Patagonia',
    'nacional':  'Nacional',
}


# =============================================================================
# HELPERS
# =============================================================================

def fetch_csv(url):
    """Downloads a CSV from a URL and returns a DataFrame."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def detect_region(name):
    """
    Detects the region from a column name string.
    Returns 'Nacional' if no regional keyword is found
    (columns with no prefix in INDEC datasets belong to the national aggregate).
    """
    for keyword, region in REGION_MAP.items():
        if keyword in name:
            return region
    return 'Nacional'


def strip_region_noise(name):
    """Removes all region keywords and noise words from a column name."""
    noise = list(REGION_MAP.keys()) + [
        'ipc', 'nivel', 'general', 'mensual', 'acumulada', 'tasa',
        'variacion', 'incidencia', 'absoluta', 'base', 'diciembre'
    ]
    for word in noise:
        name = name.replace(word, '')
    return name.strip()


def extract_metadata(series_name, dataset_type):
    """
    Extracts (region, category, classification) from a column name.
    Search strings are in Spanish to match INDEC source column names.
    """
    name = str(series_name).lower().replace('_', ' ')
    region = detect_region(name)

    if dataset_type in ('categories_by_region', 'categories_nacional'):
        category = "Análisis"
        if 'nivel general' in name:
            category       = "Nivel General"
            classification = "Total"
        elif 'nucleo' in name or 'núcleo' in name:
            classification = "Núcleo"
        elif 'regulado' in name:
            classification = "Regulados"
        elif 'estacional' in name:
            classification = "Estacionales"
        else:
            classification = strip_region_noise(name)

    elif dataset_type == 'divisions_by_region':
        category = "División"
        if   'alimentos' in name and 'no alcoholica' in name:
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
            classification = strip_region_noise(name)

    else:
        category       = "Otros"
        classification = name

    return region, category, classification


# =============================================================================
# STEP 1 — INCIDENCE DATA (145.10, 145.11, 145.12)
# =============================================================================

def build_incidence_df(start_date):
    """
    Downloads all incidence endpoints and returns a single long-format DataFrame
    with columns: time_index, region, category, classification, incidence
    """
    print("\n" + "=" * 70)
    print("STEP 1 — Downloading incidence data (145.12, 145.10)")
    print("=" * 70)

    frames = []

    for dataset_type, config in INCIDENCE_URLS.items():
        print(f"\n  → {config['description']}")
        try:
            df = fetch_csv(config['url'])
            date_col = df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col])
            df = df[df[date_col] >= start_date].copy()

            df_long = pd.melt(df, id_vars=[date_col],
                              var_name='series', value_name='incidence')
            df_long = df_long.rename(columns={date_col: 'time_index'})
            df_long = df_long.dropna(subset=['incidence'])

            df_long[['region', 'category', 'classification']] = (
                df_long['series']
                .apply(lambda x: pd.Series(extract_metadata(x, dataset_type)))
            )
            df_long = df_long.drop(columns='series')
            df_long['source'] = dataset_type  # track origin for deduplication

            print(f"     ✓ {len(df_long):,} records — "
                  f"regions: {sorted(df_long['region'].unique())}")
            frames.append(df_long)

        except Exception as e:
            print(f"     ✗ Error: {e}")

    if not frames:
        return None

    result = pd.concat(frames, ignore_index=True)

    # Deduplicate: if same (time_index, region, category, classification) appears
    # from multiple endpoints, keep the one from the most specific source.
    # Priority: divisions_by_region > categories_by_region
    source_priority = {
        'divisions_by_region':  1,
        'categories_by_region': 2,
    }
    result['_priority'] = result['source'].map(source_priority)
    result = (result
              .sort_values('_priority')
              .drop_duplicates(
                  subset=['time_index', 'region', 'category', 'classification'],
                  keep='first'
              )
              .drop(columns=['_priority', 'source'])
              .reset_index(drop=True))

    print(f"\n  ✓ Total incidence records after dedup: {len(result):,}")
    return result


# =============================================================================
# STEP 2 — MOM VARIATION from base index (145.9)
# =============================================================================

def build_mom_variation_df(start_date):
    """
    Downloads the base index (145.9), computes month-over-month % change
    using pct_change() per series, and returns a long-format DataFrame with:
    time_index, region, category, classification, mom_variation

    Downloads full history from 2016-12-01 so pct_change() has a valid
    previous value for the very first row of the filtered period.
    """
    print("\n" + "=" * 70)
    print("STEP 2 — Calculating MoM variation from base index (145.9)")
    print("=" * 70)

    try:
        df = fetch_csv(BASE_INDEX_URL['url'])
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col).copy()

        value_cols = [c for c in df.columns if c != date_col]

        # Compute pct_change() on full history so first filtered row is valid
        mom = df[value_cols].pct_change() * 100
        mom[date_col] = df[date_col].values

        # Now filter to start_date
        mom = mom[mom[date_col] >= start_date].copy()

        df_long = pd.melt(mom, id_vars=[date_col],
                          var_name='series', value_name='mom_variation')
        df_long = df_long.rename(columns={date_col: 'time_index'})
        df_long = df_long.dropna(subset=['mom_variation'])

        df_long[['region', 'category', 'classification']] = (
            df_long['series']
            .apply(lambda x: pd.Series(extract_metadata(x, 'categories_nacional')))
        )
        df_long = df_long.drop(columns='series')

        df_long['mom_variation'] = df_long['mom_variation'].round(4)

        print(f"  ✓ {len(df_long):,} MoM records — "
              f"regions: {sorted(df_long['region'].unique())}")
        return df_long

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# STEP 3 — MERGE incidence + mom_variation
# =============================================================================

def merge_datasets(df_incidence, df_mom):
    """
    Merges incidence and mom_variation data.

    Strategy:
    - Regional rows (6 regions): LEFT JOIN — incidence is the base,
      mom_variation fills in for Análisis/Nivel General, NaN for divisions.
    - Nacional rows: only exist in df_mom (145.9), so they are appended
      separately with incidence = NaN.

    Result: all 7 regions present, each with whatever metrics are available.
    """
    print("\n" + "=" * 70)
    print("STEP 3 — Merging incidence + MoM variation")
    print("=" * 70)

    df_mom['time_index']       = pd.to_datetime(df_mom['time_index'])
    df_incidence['time_index'] = pd.to_datetime(df_incidence['time_index'])

    # LEFT JOIN for the 6 regional rows (incidence as base)
    df_regional = df_incidence.merge(
        df_mom[['time_index', 'region', 'category', 'classification', 'mom_variation']],
        on=['time_index', 'region', 'category', 'classification'],
        how='left'
    )

    # Nacional rows exist only in df_mom — add them with incidence = NaN
    df_nacional = df_mom[df_mom['region'] == 'Nacional'].copy()
    df_nacional['incidence'] = float('nan')

    # Concat both and sort
    df_final = pd.concat([df_regional, df_nacional], ignore_index=True)
    df_final = df_final.sort_values(
        ['time_index', 'region', 'category', 'classification']
    ).reset_index(drop=True)

    total        = len(df_final)
    has_mom      = df_final['mom_variation'].notna().sum()
    has_inc      = df_final['incidence'].notna().sum()
    has_both     = df_final[df_final['mom_variation'].notna() & df_final['incidence'].notna()].shape[0]
    nacional_cnt = (df_final['region'] == 'Nacional').sum()

    print(f"  ✓ Total rows:                {total:,}")
    print(f"  ✓ Rows with incidence:       {has_inc:,}")
    print(f"  ✓ Rows with MoM variation:   {has_mom:,}")
    print(f"  ✓ Rows with both metrics:    {has_both:,}")
    print(f"  ✓ Nacional rows (mom only):  {nacional_cnt:,}")

    return df_final


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 80)
    print("IPC DATA PIPELINE - INDEC (datos.gob.ar)")
    print("Output columns: incidence | mom_variation")
    print("=" * 80)
    print(f"Start date: {START_DATE}")

    # Step 1 — Incidence
    df_incidence = build_incidence_df(START_DATE)
    if df_incidence is None:
        print("❌ Could not build incidence dataset. Aborting.")
        sys.exit(1)

    # Step 2 — MoM variation
    df_mom = build_mom_variation_df(START_DATE)
    if df_mom is None:
        print("❌ Could not build MoM variation dataset. Aborting.")
        sys.exit(1)

    # Step 3 — Merge
    df_final = merge_datasets(df_incidence, df_mom)

    # Final cleanup
    df_final['time_index'] = pd.to_datetime(df_final['time_index']).dt.strftime('%Y-%m-%d')

    # Add nature column derived from classification
    # Análisis / Nivel General rows → NaN (aggregates, no single nature)
    df_final['nature'] = df_final['classification'].map(NATURE_MAP)

    df_final = df_final.sort_values(
        ['time_index', 'region', 'category', 'classification']
    ).reset_index(drop=True)

    # Summary
    print("\n" + "=" * 80)
    print("FINAL DATASET SUMMARY")
    print("=" * 80)
    print(f"  {'Total records:':<30} {len(df_final):>10,}")
    print(f"  {'Period:':<30} {df_final['time_index'].min()} → {df_final['time_index'].max()}")
    print(f"  {'Unique regions:':<30} {df_final['region'].nunique():>10}")
    print(f"  {'Unique categories:':<30} {df_final['category'].nunique():>10}")
    print(f"  {'Unique classifications:':<30} {df_final['classification'].nunique():>10}")

    print("\nDISTRIBUTION BY REGION:")
    region_counts = df_final.groupby('region').size().sort_values(ascending=False)
    for region, count in region_counts.items():
        print(f"  {region:<20} {count:>10,} records")

    # Save
    output_file = 'ipc_indec_datos.csv'
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n✅ FILE SAVED: {output_file}")
    print(f"   Columns: time_index, region, category, classification, "
          f"nature, incidence, mom_variation")
    print(f"\n   Nature distribution:")
    nature_counts = df_final['nature'].value_counts(dropna=False)
    for nature, count in nature_counts.items():
        label = nature if pd.notna(nature) else "NaN (Análisis/Nivel General)"
        print(f"   {label:<35} {count:>8,} records")
    print(f"\nData is ready for analysis!")


if __name__ == "__main__":
    main()