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

# URLs de descarga (mismas que en el scraper original)
URLS_DESCARGA = {
    'nivel_general_categorias': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.12/download/ipc-incidencia-categorias-nivel-general.csv',
        'descripcion': 'IPC Nivel General y Categorías'
    },
    'divisiones_region': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.10/download/ipc-incidencia-absoluta-mensual-region-capitulo.csv',
        'descripcion': 'IPC Divisiones por Región'
    },
    'bienes_servicios': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.11/download/ipc-incidencia-mensual-bienes-servicios.csv',
        'descripcion': 'IPC Bienes y Servicios'
    }
}


def get_last_date_in_db():
    """
    Obtiene la última fecha registrada en la base de datos
    """
    engine = get_engine()
    query = "SELECT MAX(fecha) as ultima_fecha FROM fact_inflacion"
    
    try:
        with engine.connect() as conn:
            result = pd.read_sql(query, conn)
            ultima_fecha = result['ultima_fecha'].iloc[0]
            
            if pd.isna(ultima_fecha):
                return None
            
            return pd.to_datetime(ultima_fecha)
    except Exception as e:
        print(f"⚠️  Error al obtener última fecha: {e}")
        return None


def extraer_metadata(nombre_serie, tipo_dataset):
    """
    Extrae región, categoría y clasificación del nombre de la serie
    (Misma función que en el scraper original)
    """
    nombre = str(nombre_serie).lower().replace('_', ' ')
    
    # Detectar región
    region = "Nacional"
    if 'gba' in nombre:
        region = "GBA"
    elif 'pampeana' in nombre:
        region = "Pampeana"
    elif 'noa' in nombre or 'noroeste' in nombre:
        region = "NOA"
    elif 'nea' in nombre or 'noreste' in nombre:
        region = "NEA"
    elif 'cuyo' in nombre:
        region = "Cuyo"
    elif 'patagonia' in nombre:
        region = "Patagonia"
    
    # Determinar categoría y clasificación según tipo de dataset
    if tipo_dataset == 'nivel_general_categorias':
        categoria = "Análisis"
        
        if 'nivel general' in nombre:
            categoria = "Nivel General"
            clasificacion = "Total"
        elif 'nucleo' in nombre or 'núcleo' in nombre:
            clasificacion = "Núcleo"
        elif 'regulado' in nombre:
            clasificacion = "Regulados"
        elif 'estacional' in nombre:
            clasificacion = "Estacionales"
        else:
            clasificacion = nombre.replace(region.lower(), '').strip()
    
    elif tipo_dataset == 'divisiones_region':
        categoria = "División"
        
        if 'alimentos bebidas no alcoholica' in nombre:
            clasificacion = "Alimentos y bebidas"
        elif 'bebidas alcoholica' in nombre or 'tabaco' in nombre:
            clasificacion = "Bebidas alcohólicas y tabaco"
        elif 'prenda' in nombre or 'vestir' in nombre or 'calzado' in nombre:
            clasificacion = "Prendas de vestir y calzado"
        elif 'vivienda' in nombre or 'agua' in nombre or 'electricidad' in nombre or 'combustible' in nombre:
            clasificacion = "Vivienda y servicios básicos"
        elif 'equipamiento' in nombre or 'mantenimiento' in nombre:
            clasificacion = "Equipamiento del hogar"
        elif 'salud' in nombre:
            clasificacion = "Salud"
        elif 'transporte' in nombre:
            clasificacion = "Transporte"
        elif 'comunicacion' in nombre:
            clasificacion = "Comunicación"
        elif 'recreacion' in nombre or 'cultura' in nombre:
            clasificacion = "Recreación y cultura"
        elif 'educacion' in nombre:
            clasificacion = "Educación"
        elif 'restaurante' in nombre or 'hotel' in nombre:
            clasificacion = "Restaurantes y hoteles"
        elif 'otros' in nombre or 'bienes servicios' in nombre:
            clasificacion = "Bienes y servicios varios"
        else:
            clasificacion = nombre.replace(region.lower(), '').strip()
    
    elif tipo_dataset == 'bienes_servicios':
        categoria = "Naturaleza"
        
        if 'bien' in nombre and 'servicio' not in nombre:
            clasificacion = "Bienes"
        elif 'servicio' in nombre:
            clasificacion = "Servicios"
        else:
            clasificacion = nombre.replace(region.lower(), '').strip()
    
    else:
        categoria = "Otros"
        clasificacion = nombre
    
    return region, categoria, clasificacion


def descargar_y_procesar_csv(nombre, config, fecha_inicio):
    """
    Descarga y procesa un CSV al formato requerido
    """
    print(f"\n{'='*70}")
    print(f"Descargando: {nombre}")
    print(f"URL: {config['url']}")
    print('='*70)
    
    try:
        response = requests.get(config['url'], timeout=60)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text))
        print(f"✓ Descargado: {len(df)} filas")
        
        fecha_col = df.columns[0]
        df[fecha_col] = pd.to_datetime(df[fecha_col])
        
        # Filtrar por fecha
        df_filtrado = df[df[fecha_col] >= fecha_inicio].copy()
        print(f"✓ Filtrado desde {fecha_inicio}: {len(df_filtrado)} filas")
        
        # Convertir a formato largo
        df_long = pd.melt(
            df_filtrado,
            id_vars=[fecha_col],
            var_name='serie_original',
            value_name='valor'
        )
        
        df_long = df_long.rename(columns={fecha_col: 'indice_tiempo'})
        
        # Extraer metadata
        df_long[['region', 'categoria', 'clasificacion']] = df_long['serie_original'].apply(
            lambda x: pd.Series(extraer_metadata(x, nombre))
        )
        
        df_long = df_long.drop('serie_original', axis=1)
        df_long = df_long.dropna(subset=['valor'])
        
        print(f"✓ Procesado: {len(df_long)} registros")
        
        return df_long
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def actualizar_dimensiones(df, conn):
    """
    Actualiza las tablas de dimensiones con nuevos valores si existen
    """
    # Actualizar dim_region
    regiones = df[['region']].drop_duplicates()
    for reg in regiones['region']:
        conn.execute(
            text("INSERT INTO dim_region (region_nombre) VALUES (:r) ON CONFLICT DO NOTHING"),
            {"r": reg}
        )
    
    # Actualizar dim_categoria
    cats = df[['categoria', 'clasificacion']].drop_duplicates()
    for _, row in cats.iterrows():
        conn.execute(
            text("INSERT INTO dim_categoria (categoria_nombre, clasificacion) VALUES (:n, :c) ON CONFLICT DO NOTHING"),
            {"n": row['categoria'], "c": row['clasificacion']}
        )
    
    conn.commit()


def insertar_hechos(df, conn):
    """
    Inserta los nuevos datos en fact_inflacion
    """
    # Obtener mapeos de IDs
    res_reg = pd.read_sql("SELECT * FROM dim_region", conn)
    res_cat = pd.read_sql("SELECT * FROM dim_categoria", conn)
    
    dict_reg = dict(zip(res_reg['region_nombre'], res_reg['region_id']))
    dict_cat = dict(zip(res_cat['categoria_nombre'], res_cat['categoria_id']))
    
    df['region_id'] = df['region'].map(dict_reg)
    df['categoria_id'] = df['categoria'].map(dict_cat)
    
    # Insertar con UPSERT
    insertados = 0
    actualizados = 0
    
    for _, row in df.iterrows():
        query_insert = """
        INSERT INTO fact_inflacion (fecha, region_id, categoria_id, valor_indice)
        VALUES (:f, :r_id, :c_id, :v)
        ON CONFLICT (fecha, region_id, categoria_id) 
        DO UPDATE SET valor_indice = EXCLUDED.valor_indice
        RETURNING (xmax = 0) AS inserted
        """
        result = conn.execute(text(query_insert), {
            "f": row['indice_tiempo'],
            "r_id": row['region_id'],
            "c_id": row['categoria_id'],
            "v": row['valor']
        })
        
        was_inserted = result.fetchone()[0]
        if was_inserted:
            insertados += 1
        else:
            actualizados += 1
    
    conn.commit()
    
    return insertados, actualizados


def main():
    """
    Función principal de actualización automática
    """
    print("=" * 80)
    print("ACTUALIZACIÓN AUTOMÁTICA DE DATOS IPC")
    print("=" * 80)
    print(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # 1. Verificar estructura de DB
        setup_db()
        
        # 2. Obtener última fecha en DB
        ultima_fecha_db = get_last_date_in_db()
        
        if ultima_fecha_db is None:
            print("\n⚠️  La base de datos está vacía.")
            print("Ejecuta primero el script de carga inicial: db_setup_secure.py")
            sys.exit(1)
        
        print(f"\n📅 Última fecha en DB: {ultima_fecha_db.strftime('%Y-%m-%d')}")
        
        # 3. Calcular fecha de inicio para la actualización
        # Descargamos desde 2 meses antes por si hay revisiones
        fecha_inicio = (ultima_fecha_db - timedelta(days=60)).replace(day=1)
        print(f"📥 Descargando datos desde: {fecha_inicio.strftime('%Y-%m-%d')}")
        
        # 4. Descargar datos actualizados
        dataframes = []
        for nombre, config in URLS_DESCARGA.items():
            df = descargar_y_procesar_csv(nombre, config, fecha_inicio)
            if df is not None:
                dataframes.append(df)
        
        if not dataframes:
            print("\n❌ No se pudieron descargar datos")
            sys.exit(1)
        
        # 5. Consolidar datos
        df_nuevo = pd.concat(dataframes, ignore_index=True)
        df_nuevo['indice_tiempo'] = pd.to_datetime(df_nuevo['indice_tiempo'])
        
        # 6. Filtrar solo datos realmente nuevos
        df_nuevo = df_nuevo[df_nuevo['indice_tiempo'] >= ultima_fecha_db]
        
        if len(df_nuevo) == 0:
            print("\n✅ No hay datos nuevos para actualizar")
            print("La base de datos está al día!")
            return
        
        print(f"\n📊 Datos nuevos encontrados:")
        print(f"   Registros: {len(df_nuevo)}")
        print(f"   Período: {df_nuevo['indice_tiempo'].min().strftime('%Y-%m-%d')} a {df_nuevo['indice_tiempo'].max().strftime('%Y-%m-%d')}")
        
        # 7. Actualizar base de datos
        print("\n🔄 Actualizando base de datos...")
        engine = get_engine()
        
        with engine.connect() as conn:
            # Actualizar dimensiones
            actualizar_dimensiones(df_nuevo, conn)
            
            # Insertar hechos
            insertados, actualizados = insertar_hechos(df_nuevo, conn)
        
        print("\n" + "=" * 80)
        print("✅ ACTUALIZACIÓN COMPLETADA")
        print("=" * 80)
        print(f"   Registros insertados: {insertados}")
        print(f"   Registros actualizados: {actualizados}")
        print(f"   Total procesados: {insertados + actualizados}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error durante la actualización: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
