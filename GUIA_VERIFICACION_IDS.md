# GUÍA: Cómo Verificar IDs Actualizados de Series del IPC

Esta guía te ayudará a verificar si los IDs de las series del IPC siguen vigentes o si han cambiado.

## 🔍 Método 1: Explorador Web de Series

### Paso 1: Acceder al explorador
Visita: https://datos.gob.ar/series/api/

### Paso 2: Buscar series del IPC
1. En el buscador, escribe: `IPC`
2. Filtra por organización: `Subsecretaría de Programación Macroeconómica`
3. Busca series con el código `148.3_`

### Paso 3: Verificar IDs
- **Dataset 148**: IPC base diciembre 2016
- **Dataset 103**: IPC categorías (complementario)
- **Dataset 145**: IPC nivel general y regional

## 🔍 Método 2: Descarga del Catálogo Completo

### Opción A: Archivo CSV con todas las series

```bash
# Descargar listado completo de series
wget http://infra.datos.gob.ar/catalog/sspm/dataset/series/distribution/series.1/download/series-tiempo-metadatos.csv
```

### Opción B: Script Python para buscar IDs

```python
import pandas as pd

# Descargar catálogo
url = "http://infra.datos.gob.ar/catalog/sspm/dataset/series/distribution/series.1/download/series-tiempo-metadatos.csv"
df = pd.read_csv(url)

# Filtrar series del IPC (dataset 148.3)
ipc_series = df[df['serie_id'].str.contains('148.3', na=False)]

# Mostrar IDs disponibles
print("Series del IPC (148.3):")
print(ipc_series[['serie_id', 'serie_titulo']].to_string(index=False))

# Guardar a archivo
ipc_series[['serie_id', 'serie_titulo', 'serie_descripcion']].to_csv('ipc_series_disponibles.csv', index=False)
```

## 🔍 Método 3: Consulta Directa a la API

### Verificar si una serie existe

```python
import requests

def verificar_serie(serie_id):
    """Verifica si un ID de serie es válido"""
    url = f"https://apis.datos.gob.ar/series/api/series/?ids={serie_id}&format=json&limit=1"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'data' in data and len(data['data']) > 0:
            print(f"✓ Serie {serie_id} EXISTE")
            return True
        else:
            print(f"✗ Serie {serie_id} NO ENCONTRADA")
            return False
    except:
        print(f"⚠️  No se pudo verificar {serie_id}")
        return None

# Probar serie principal
verificar_serie("148.3_INIVELNAL_DICI_M_26")
```

## 🔍 Método 4: Verificar desde INDEC directamente

### Archivos Excel del INDEC

El INDEC publica archivos Excel con todas las aperturas:

```bash
# Descargar archivo de aperturas
wget https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_aperturas.xls
```

Este archivo contiene:
- Todas las series históricas
- Códigos internos del INDEC
- Puede no coincidir exactamente con los IDs de datos.gob.ar

### Correspondencia INDEC ↔ datos.gob.ar

El mapeo no siempre es directo. Los IDs de datos.gob.ar son:
- Creados por el Ministerio de Economía
- Basados en convenciones propias
- Pueden diferir de los códigos del INDEC

## ⚠️ Cambios Conocidos en IDs

### Cambio de Base (Dic 2013 → Dic 2016)

Cuando el INDEC cambió la base del IPC:
- **Base anterior**: octubre 2013 = 100
- **Base actual**: diciembre 2016 = 100
- **Impacto**: Cambio en los IDs de series

Ejemplo:
```
Base Oct 2013: 103.1_I2NG_2016_M_22
Base Dic 2016: 148.3_INIVELNAL_DICI_M_26
```

### Estructura de IDs actual (2026)

```
[DATASET].[DIST]_[CODIGO]_[BASE]_[FREQ]_[NUM]

Donde:
- DATASET: 148 (IPC actual)
- DIST: 3 (distribución)
- CODIGO: Código de la serie (INIVELNAL, IALIMNAL, etc.)
- BASE: DICI (diciembre 2016)
- FREQ: M (mensual)
- NUM: Número secuencial
```

## 🔧 Script de Validación Automática

```python
#!/usr/bin/env python3
"""
Valida todos los IDs de series del script principal
"""

import requests
import time

# IDs a verificar (lista parcial como ejemplo)
SERIES_A_VERIFICAR = [
    "148.3_INIVELNAL_DICI_M_26",  # Nacional
    "148.3_INIVELEGR_DICI_M_27",  # GBA
    "148.3_IALIMNAL_DICI_M_33",   # Alimentos
    "148.3_IBIENNAL_DICI_M_45",   # Bienes
    "148.3_INUCNAL_DICI_M_59",    # Núcleo
]

def validar_series(serie_ids):
    """Valida múltiples series"""
    resultados = []
    
    for serie_id in serie_ids:
        url = f"https://apis.datos.gob.ar/series/api/series/?ids={serie_id}&format=json&limit=1"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            existe = 'data' in data and len(data['data']) > 0
            
            resultados.append({
                'serie_id': serie_id,
                'existe': existe,
                'status': '✓' if existe else '✗'
            })
            
            print(f"{resultados[-1]['status']} {serie_id}")
            
        except Exception as e:
            resultados.append({
                'serie_id': serie_id,
                'existe': None,
                'status': '⚠️',
                'error': str(e)
            })
            print(f"⚠️  {serie_id} - Error: {e}")
        
        time.sleep(0.5)  # Respetar rate limiting
    
    return resultados

# Ejecutar validación
print("Validando series del IPC...")
print("=" * 60)
resultados = validar_series(SERIES_A_VERIFICAR)

# Resumen
print("\n" + "=" * 60)
print("RESUMEN:")
existentes = sum(1 for r in resultados if r['existe'] is True)
no_encontradas = sum(1 for r in resultados if r['existe'] is False)
errores = sum(1 for r in resultados if r['existe'] is None)

print(f"✓ Existentes: {existentes}")
print(f"✗ No encontradas: {no_encontradas}")
print(f"⚠️  Errores: {errores}")
```

## 📞 Contacto para Dudas

Si encuentras discrepancias o IDs que no funcionan:

1. **Verifica el estado de la API**: https://www.argentina.gob.ar/datos-abiertos/api-series-de-tiempo
2. **Consulta el dataset**: https://datos.gob.ar/dataset/sspm-indice-precios-al-consumidor-nacional-ipc-base-diciembre-2016
3. **Contacta a Datos Argentina**: datosargentina@jefatura.gob.ar
4. **INDEC**: https://www.indec.gob.ar/indec/web/Institucional-Indec-Contacto

## 🔄 Frecuencia de Actualización

- **Serie 148.3**: Sigue activa (verificado enero 2026)
- **Cambios esperados**: Solo con cambio de base del IPC
- **Próximo cambio de base**: No anunciado (última fue en 2017)

## 💡 Recomendación

**Mejor práctica**: Usar el método de descarga directa de CSVs del script `descargar_ipc_completo.py`, ya que:
- Es más confiable que la API
- Siempre está actualizado
- No depende de IDs específicos
- Incluye todas las series automáticamente

---

**Última actualización:** 27 de enero de 2026
