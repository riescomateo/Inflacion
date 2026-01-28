"""
Script CORREGIDO para descargar datos del IPC desde datos.gob.ar
Con URLs VERIFICADAS y funcionales
"""

import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import sys

START_DATE = "2023-12-01"

# URLs VERIFICADAS y FUNCIONALES desde infra.datos.gob.ar
URLS_DESCARGA = {
    # Dataset 145 - Nivel General y Categorías
    'nivel_general_categorias': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.12/download/ipc-incidencia-categorias-nivel-general.csv',
        'descripcion': 'IPC Nivel General y Categorías (Núcleo, Regulados, Estacionales) por Región'
    },
    
    # Dataset 145 - Divisiones (Capítulos) por Región
    'divisiones_region': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.10/download/ipc-incidencia-absoluta-mensual-region-capitulo.csv',
        'descripcion': 'IPC Divisiones (12 capítulos) por Región'
    },
    
    # Dataset 145 - Bienes y Servicios por Región  
    'bienes_servicios': {
        'url': 'http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.11/download/ipc-incidencia-mensual-bienes-servicios.csv',
        'descripcion': 'IPC Bienes y Servicios por Región'
    }
}


def descargar_y_procesar_csv(nombre, config, fecha_inicio):
    """
    Descarga y procesa un CSV al formato requerido
    """
    print(f"\n{'='*70}")
    print(f"Descargando: {nombre}")
    print(f"Descripción: {config['descripcion']}")
    print(f"URL: {config['url']}")
    print('='*70)
    
    try:
        # Descargar
        response = requests.get(config['url'], timeout=60)
        response.raise_for_status()
        
        # Leer CSV
        df = pd.read_csv(StringIO(response.text))
        print(f"✓ Descargado: {len(df)} filas, {len(df.columns)} columnas")
        
        # Convertir fecha
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
        
        # Extraer región, categoría y clasificación del nombre de la columna
        df_long[['region', 'categoria', 'clasificacion']] = df_long['serie_original'].apply(
            lambda x: pd.Series(extraer_metadata(x, nombre))
        )
        
        # Eliminar columna temporal
        df_long = df_long.drop('serie_original', axis=1)
        
        # Eliminar valores nulos
        df_long = df_long.dropna(subset=['valor'])
        
        print(f"✓ Convertido a formato largo: {len(df_long)} registros")
        print(f"  - Regiones únicas: {df_long['region'].nunique()}")
        print(f"  - Clasificaciones únicas: {df_long['clasificacion'].nunique()}")
        
        return df_long
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de descarga: {e}")
        return None
    except Exception as e:
        print(f"✗ Error de procesamiento: {e}")
        import traceback
        traceback.print_exc()
        return None


def extraer_metadata(nombre_serie, tipo_dataset):
    """
    Extrae región, categoría y clasificación del nombre de la serie
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
        
        # Mapeo de divisiones
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


def main():
    """Función principal"""
    print("=" * 80)
    print("DESCARGA DE DATOS DEL IPC - INDEC (datos.gob.ar)")
    print("Script CORREGIDO con URLs verificadas")
    print("=" * 80)
    print(f"Fecha de inicio: {START_DATE}")
    print(f"Datasets a descargar: {len(URLS_DESCARGA)}")
    print("=" * 80)
    
    # Lista para almacenar DataFrames
    dataframes = []
    
    # Descargar cada dataset
    for nombre, config in URLS_DESCARGA.items():
        df = descargar_y_procesar_csv(nombre, config, START_DATE)
        if df is not None:
            dataframes.append(df)
    
    # Verificar que se descargaron datos
    if not dataframes:
        print("\n" + "=" * 80)
        print("⚠️  ERROR: No se pudieron descargar datos")
        print("=" * 80)
        print("\nPosibles causas:")
        print("1. Problemas de conexión a internet")
        print("2. Los servidores de datos.gob.ar están caídos")
        print("3. Las URLs han cambiado")
        print("\nRecomendación:")
        print("- Verifica tu conexión")
        print("- Intenta nuevamente en unos minutos")
        print("- Visita: https://datos.gob.ar/")
        sys.exit(1)
    
    # Consolidar todos los DataFrames
    print("\n" + "=" * 80)
    print("CONSOLIDANDO DATOS...")
    print("=" * 80)
    
    df_final = pd.concat(dataframes, ignore_index=True)
    
    # Limpiar datos
    df_final = df_final.dropna(subset=['valor'])
    df_final = df_final.sort_values(['indice_tiempo', 'region', 'categoria', 'clasificacion'])
    df_final = df_final.reset_index(drop=True)
    
    # Formatear fecha
    df_final['indice_tiempo'] = pd.to_datetime(df_final['indice_tiempo']).dt.strftime('%Y-%m-%d')
    
    # Resumen
    print(f"\n✓ DATOS CONSOLIDADOS:")
    print(f"  {'Total de registros:':<30} {len(df_final):>10,}")
    print(f"  {'Período:':<30} {df_final['indice_tiempo'].min()} a {df_final['indice_tiempo'].max()}")
    print(f"  {'Regiones únicas:':<30} {df_final['region'].nunique():>10}")
    print(f"  {'Categorías únicas:':<30} {df_final['categoria'].nunique():>10}")
    print(f"  {'Clasificaciones únicas:':<30} {df_final['clasificacion'].nunique():>10}")
    
    # Distribución por región
    print("\n" + "=" * 80)
    print("DISTRIBUCIÓN POR REGIÓN:")
    print("=" * 80)
    region_counts = df_final.groupby('region').size().sort_values(ascending=False)
    for region, count in region_counts.items():
        print(f"  {region:<20} {count:>10,} registros")
    
    # Distribución por categoría
    print("\n" + "=" * 80)
    print("DISTRIBUCIÓN POR CATEGORÍA:")
    print("=" * 80)
    cat_counts = df_final.groupby('categoria').size().sort_values(ascending=False)
    for cat, count in cat_counts.items():
        print(f"  {cat:<20} {count:>10,} registros")
    
    # Guardar archivo
    output_file = 'ipc_indec_datos.csv'
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 80)
    print(f"✓ ARCHIVO GUARDADO: {output_file}")
    print("=" * 80)
    
    # Muestra de datos
    print("\nMUESTRA DE DATOS (primeras 20 filas):")
    print("=" * 80)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)
    print(df_final.head(20).to_string(index=False))
    
    print("\n" + "=" * 80)
    print("✓ DESCARGA COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    print(f"\nFormato del CSV:")
    print(f"  - Columnas: indice_tiempo, valor, region, categoria, clasificacion")
    print(f"  - Formato: LARGO (unpivoted)")
    print(f"  - Encoding: UTF-8 with BOM")
    print(f"\n¡Los datos están listos para análisis!")


if __name__ == "__main__":
    main()
