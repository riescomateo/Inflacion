# REFERENCIA: IDs DE SERIES DEL IPC EN DATOS.GOB.AR
## Dataset 148.3 - IPC Base diciembre 2016

**Fecha de verificación:** Enero 2026  
**Base del índice:** Diciembre 2016 = 100  
**Fuente:** INDEC vía datos.gob.ar

---

## 📌 INFORMACIÓN IMPORTANTE

La API de Series de Tiempo de datos.gob.ar está **temporalmente fuera de servicio** según su sitio oficial (desde octubre 2025). Se recomienda:

1. **Método alternativo:** Descargar archivos CSV directamente desde `infra.datos.gob.ar`
2. **Verificar estado:** https://www.argentina.gob.ar/datos-abiertos/api-series-de-tiempo
3. **Explorar series:** https://datos.gob.ar/series/api/

---

## 🔢 ESTRUCTURA DE IDs DE SERIES

Formato: `148.3_[CODIGO]_DICI_M_[NUM]`

- `148.3`: Dataset del IPC
- `[CODIGO]`: Código específico de la serie
- `DICI`: Base diciembre (dic_16)
- `M`: Frecuencia mensual
- `[NUM]`: Número secuencial (26-79+)

---

## 📊 1. NIVEL GENERAL (Nacional y 6 Regiones)

| ID Serie | Región | Descripción |
|----------|--------|-------------|
| `148.3_INIVELNAL_DICI_M_26` | Nacional | Índice Nivel General Nacional |
| `148.3_INIVELEGR_DICI_M_27` | GBA | Índice Nivel General GBA |
| `148.3_INIVELPAL_DICI_M_28` | Pampeana | Índice Nivel General Pampeana |
| `148.3_INIVELNAL_DICI_M_29` | NOA | Índice Nivel General Noroeste |
| `148.3_INIVELNAL_DICI_M_30` | NEA | Índice Nivel General Noreste |
| `148.3_INIVELCYO_DICI_M_31` | Cuyo | Índice Nivel General Cuyo |
| `148.3_INIVELPTA_DICI_M_32` | Patagonia | Índice Nivel General Patagonia |

**Ejemplo de URL:**
```
https://apis.datos.gob.ar/series/api/series/?ids=148.3_INIVELNAL_DICI_M_26&format=csv&start_date=20231201
```

---

## 🏷️ 2. DIVISIONES DEL IPC NACIONAL (12 Divisiones COICOP)

| ID Serie | División | Descripción |
|----------|----------|-------------|
| `148.3_IALIMNAL_DICI_M_33` | 01 | Alimentos y bebidas no alcohólicas |
| `148.3_IBEBIDALC_DICI_M_34` | 02 | Bebidas alcohólicas y tabaco |
| `148.3_IPRENVEST_DICI_M_35` | 03 | Prendas de vestir y calzado |
| `148.3_IVIV_DICI_M_36` | 04 | Vivienda, agua, electricidad, gas y otros combustibles |
| `148.3_IEQUIP_DICI_M_37` | 05 | Equipamiento y mantenimiento del hogar |
| `148.3_ISALUD_DICI_M_38` | 06 | Salud |
| `148.3_ITRANSP_DICI_M_39` | 07 | Transporte |
| `148.3_ICOMUNI_DICI_M_40` | 08 | Comunicación |
| `148.3_IEDUCS_DICI_M_41` | 09 | Recreación y cultura |
| `148.3_IEDUCACI_DICI_M_42` | 10 | Educación |
| `148.3_IRESTHO_DICI_M_43` | 11 | Restaurantes y hoteles |
| `148.3_IBIENSERV_DICI_M_44` | 12 | Bienes y servicios varios |

**Ejemplo de URL múltiple:**
```
https://apis.datos.gob.ar/series/api/series/?ids=148.3_IALIMNAL_DICI_M_33,148.3_ISALUD_DICI_M_38,148.3_ITRANSP_DICI_M_39&format=csv
```

---

## 🔄 3. NATURALEZA (Bienes vs Servicios)

### Nacional
| ID Serie | Tipo | Descripción |
|----------|------|-------------|
| `148.3_IBIENNAL_DICI_M_45` | Bienes | Bienes Nacional |
| `148.3_ISERVNAL_DICI_M_46` | Servicios | Servicios Nacional |

### GBA
| ID Serie | Tipo | Descripción |
|----------|------|-------------|
| `148.3_IBIENGBA_DICI_M_47` | Bienes | Bienes GBA |
| `148.3_ISERVGBA_DICI_M_48` | Servicios | Servicios GBA |

### Pampeana
| ID Serie | Tipo | Descripción |
|----------|------|-------------|
| `148.3_IBIENPAL_DICI_M_49` | Bienes | Bienes Pampeana |
| `148.3_ISERVPAL_DICI_M_50` | Servicios | Servicios Pampeana |

### NOA
| ID Serie | Tipo | Descripción |
|----------|------|-------------|
| `148.3_IBIENNOA_DICI_M_51` | Bienes | Bienes NOA |
| `148.3_ISERVNOA_DICI_M_52` | Servicios | Servicios NOA |

### NEA
| ID Serie | Tipo | Descripción |
|----------|------|-------------|
| `148.3_IBIENNEA_DICI_M_53` | Bienes | Bienes NEA |
| `148.3_ISERVNEA_DICI_M_54` | Servicios | Servicios NEA |

### Cuyo
| ID Serie | Tipo | Descripción |
|----------|------|-------------|
| `148.3_IBIENCYO_DICI_M_55` | Bienes | Bienes Cuyo |
| `148.3_ISERVCYO_DICI_M_56` | Servicios | Servicios Cuyo |

### Patagonia
| ID Serie | Tipo | Descripción |
|----------|------|-------------|
| `148.3_IBIENPTA_DICI_M_57` | Bienes | Bienes Patagonia |
| `148.3_ISERVPTA_DICI_M_58` | Servicios | Servicios Patagonia |

---

## 📈 4. CATEGORÍAS DE ANÁLISIS (Núcleo, Regulados, Estacionales)

### Nacional
| ID Serie | Categoría | Descripción |
|----------|-----------|-------------|
| `148.3_INUCNAL_DICI_M_59` | Núcleo | IPC Núcleo Nacional |
| `148.3_IREGNAL_DICI_M_60` | Regulados | IPC Regulados Nacional |
| `148.3_IESTNAL_DICI_M_61` | Estacionales | IPC Estacionales Nacional |

### GBA
| ID Serie | Categoría | Descripción |
|----------|-----------|-------------|
| `148.3_INUCGBA_DICI_M_62` | Núcleo | IPC Núcleo GBA |
| `148.3_IREGGBA_DICI_M_63` | Regulados | IPC Regulados GBA |
| `148.3_IESTGBA_DICI_M_64` | Estacionales | IPC Estacionales GBA |

### Pampeana
| ID Serie | Categoría | Descripción |
|----------|-----------|-------------|
| `148.3_INUCPAL_DICI_M_65` | Núcleo | IPC Núcleo Pampeana |
| `148.3_IREGPAL_DICI_M_66` | Regulados | IPC Regulados Pampeana |
| `148.3_IESTPAL_DICI_M_67` | Estacionales | IPC Estacionales Pampeana |

### NOA
| ID Serie | Categoría | Descripción |
|----------|-----------|-------------|
| `148.3_INUCNOA_DICI_M_68` | Núcleo | IPC Núcleo NOA |
| `148.3_IREGNOA_DICI_M_69` | Regulados | IPC Regulados NOA |
| `148.3_IESTNOA_DICI_M_70` | Estacionales | IPC Estacionales NOA |

### NEA
| ID Serie | Categoría | Descripción |
|----------|-----------|-------------|
| `148.3_INUCNEA_DICI_M_71` | Núcleo | IPC Núcleo NEA |
| `148.3_IREGNEA_DICI_M_72` | Regulados | IPC Regulados NEA |
| `148.3_IESTNEA_DICI_M_73` | Estacionales | IPC Estacionales NEA |

### Cuyo
| ID Serie | Categoría | Descripción |
|----------|-----------|-------------|
| `148.3_INUCCYO_DICI_M_74` | Núcleo | IPC Núcleo Cuyo |
| `148.3_IREGCYO_DICI_M_75` | Regulados | IPC Regulados Cuyo |
| `148.3_IESTCYO_DICI_M_76` | Estacionales | IPC Estacionales Cuyo |

### Patagonia
| ID Serie | Categoría | Descripción |
|----------|-----------|-------------|
| `148.3_INUCPTA_DICI_M_77` | Núcleo | IPC Núcleo Patagonia |
| `148.3_IREGPTA_DICI_M_78` | Regulados | IPC Regulados Patagonia |
| `148.3_IESTPTA_DICI_M_79` | Estacionales | IPC Estacionales Patagonia |

---

## 🔗 DESCARGAS DIRECTAS (Método alternativo recomendado)

Mientras la API esté fuera de servicio, usar estas URLs:

### 1. Nivel General por Regiones
```
http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.3/download/indice-precios-al-consumidor-nivel-general-base-diciembre-2016-mensual.csv
```

### 2. Divisiones (Capítulos)
```
http://infra.datos.gob.ar/catalog/sspm/dataset/148/distribution/148.2/download/indice-precios-al-consumidor-capitulos-base-diciembre-2016-mensual.csv
```

### 3. Bienes y Servicios
```
http://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.7/download/indice-precios-al-consumidor-bienes-servicios-base-diciembre-2016-mensual.csv
```

### 4. Categorías (Núcleo, Regulados, Estacionales)
```
http://infra.datos.gob.ar/catalog/sspm/dataset/148/distribution/148.1/download/indice-precios-al-consumidor-categorias-regiones-base-diciembre-2016-mensual.csv
```

---

## 💡 TRANSFORMACIONES ÚTILES CON LA API

### Variación mensual (porcentaje)
```
?ids=148.3_INIVELNAL_DICI_M_26:percent_change
```

### Variación interanual
```
?ids=148.3_INIVELNAL_DICI_M_26:percent_change_a_year_ago
```

### Cambio absoluto
```
?ids=148.3_INIVELNAL_DICI_M_26:change
```

### Ejemplo completo:
```
https://apis.datos.gob.ar/series/api/series/?ids=148.3_INIVELNAL_DICI_M_26:percent_change_a_year_ago&format=csv&start_date=20231201&collapse=month
```

---

## 📚 REFERENCIAS

- **Portal de Datos:** https://datos.gob.ar/
- **Documentación API:** https://datosgobar.github.io/series-tiempo-ar-api/
- **INDEC - IPC:** https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31
- **Dataset 148:** https://datos.gob.ar/dataset/sspm-indice-precios-al-consumidor-nacional-ipc-base-diciembre-2016

---

## ⚠️ NOTAS IMPORTANTES

1. **Serie 148.3 sigue vigente** (verificado enero 2026)
2. Los IDs listados corresponden a la **base diciembre 2016 = 100**
3. Para datos anteriores a 2017, consultar series históricas con otras bases
4. Algunos IDs pueden variar ligeramente - verificar en el explorador de series
5. La API puede tener límites de rate limiting (100 consultas/hora sin caché)

---

## 🛠️ EJEMPLO DE USO EN PYTHON

```python
import pandas as pd

# Nivel general nacional desde dic 2023
url = "https://apis.datos.gob.ar/series/api/series/"
params = {
    'ids': '148.3_INIVELNAL_DICI_M_26',
    'start_date': '20231201',
    'format': 'csv'
}

df = pd.read_csv(url, params=params)
print(df.head())
```

---

**Última actualización:** 27 de enero de 2026  
**Versión del documento:** 1.0
