# 📊 IPC Argentina - Automated Data Pipeline

> **End-to-end ETL pipeline for Argentine inflation analysis with dual metrics (incidence + MoM variation) in a PostgreSQL Star Schema**

This project extracts Consumer Price Index (CPI) data from Argentina's public API (datos.gob.ar), transforms it into a dimensional model with two complementary inflation metrics, and loads it into PostgreSQL with automated monthly incremental updates.

## 🎯 Objective

Centralize Argentina's historical inflation data into a relational database optimized for multidimensional analysis, providing **two key metrics per data point**:
- **Incidence:** Contribution of each category to total regional inflation (percentage points)
- **MoM Variation:** Month-over-month percentage change calculated from the base index

Enables analysis across **7 regions** (Nacional + 6 regional), **12 divisions**, and multiple classification levels (Core, Regulated, Seasonal).

---

## 🏗️ System Architecture

<p align="center">
  <img src="./docs/architecture.png" width="650" alt="Pipeline Architecture"/>
</p>

**Data flow:**
1. **Extract:** Downloads from 3 public API endpoints (INDEC)
   - `145.12` → Categories by region (incidence)
   - `145.10` → 12 divisions by region (incidence)
   - `145.9` → Base index for all regions (MoM calculation)
2. **Transform:** 
   - Wide→Long normalization + metadata parsing
   - MoM calculation via `pct_change()` on historical index
   - Nature derivation from classification
3. **Load:** Star Schema with UPSERT logic for both metrics
4. **Visualize:** BI dashboards via SQL queries

---

## ⚙️ ETL Pipeline Highlights

### **Extract**
- **3 endpoints** from datos.gob.ar with error handling and 60s timeout
- Automatic detection of newly available periods
- Downloads last 2 months to capture INDEC retroactive revisions

### **Transform**
- **Unpivot:** Wide→Long format conversion using `pandas.melt()`
- **Metadata parsing:** Extracts region, category, classification from column names
- **MoM calculation:** Applies `pct_change()` on full historical base index, then filters
- **Nature derivation:** Maps classifications to Bienes/Servicios/Mixto based on economic category
- **Deduplication:** Priority-based merge when same key appears in multiple sources

### **Load**
- **Incremental logic:** `ON CONFLICT ... DO UPDATE` prevents duplicates while updating revisions
- **Dual metrics:** Stores both `incidence` (pp) and `mom_variation` (%) in `fact_inflation`
- **Normalized nature:** Stored in `dim_category` to avoid denormalization
- **Indexes:** Optimized for temporal queries on date, region, category

### **Orchestration**
- Modular design: `ipc_scraper.py` → `db_setup_secure.py` → `update_monthly.py`
- Automated via Cron / GitHub Actions for monthly execution
- Detailed logging with insert/update metrics

---

## 📐 Data Model - Star Schema

```sql
-- Dimension: Regions (7 total: Nacional + 6 regional)
CREATE TABLE dim_region (
    region_id   SERIAL PRIMARY KEY,
    region_name VARCHAR(50) UNIQUE
);
-- Values: Nacional, GBA, Pampeana, NOA, NEA, Cuyo, Patagonia

-- Dimension: Categories with nature classification
CREATE TABLE dim_category (
    category_id    SERIAL PRIMARY KEY,
    category_name  VARCHAR(100),     -- División, Análisis, Nivel General
    classification VARCHAR(100),     -- Alimentos, Núcleo, Total, etc.
    nature         VARCHAR(50),      -- Bienes, Servicios, Mixto (NULL for aggregates)
    UNIQUE(category_name, classification)
);

-- Fact: Inflation metrics (dual metrics per row)
CREATE TABLE fact_inflation (
    date          DATE,
    region_id     INT REFERENCES dim_region(region_id),
    category_id   INT REFERENCES dim_category(category_id),
    incidence     DECIMAL(18, 6),   -- pp contribution to regional inflation
    mom_variation DECIMAL(18, 6),   -- % change vs previous month
    PRIMARY KEY (date, region_id, category_id)
);

-- Indexes for query optimization
CREATE INDEX idx_fact_date     ON fact_inflation(date);
CREATE INDEX idx_fact_region   ON fact_inflation(region_id);
CREATE INDEX idx_fact_category ON fact_inflation(category_id);
```

**Key metrics availability:**
- **Incidence:** Available for 6 regional divisions + categories (NULL for Nacional aggregate)
- **MoM Variation:** Available for all 7 regions at Análisis/Nivel General level (NULL for divisions)
- **Nature:** Derived for divisions, NULL for aggregate categories

**Granularity:** Monthly | **Period:** Dec 2023 → Present | **Rows:** ~35,000+

---

## 📊 SQL Query Examples

### **1. Nacional MoM Variation (pre-calculated)**

```sql
SELECT 
    f.date,
    c.classification,
    f.mom_variation
FROM fact_inflation f
JOIN dim_region   r ON f.region_id   = r.region_id
JOIN dim_category c ON f.category_id = c.category_id
WHERE r.region_name   = 'Nacional'
  AND c.category_name = 'Nivel General'
ORDER BY f.date DESC
LIMIT 12;
```

### **2. Regional Incidence Analysis (Top 3 categories driving inflation)**

```sql
SELECT 
    f.date,
    r.region_name,
    c.classification,
    f.incidence,
    RANK() OVER (PARTITION BY f.date, r.region_name ORDER BY f.incidence DESC) as rank
FROM fact_inflation f
JOIN dim_region   r ON f.region_id   = r.region_id
JOIN dim_category c ON f.category_id = c.category_id
WHERE c.category_name = 'División'
  AND f.date = '2024-12-01'
QUALIFY rank <= 3
ORDER BY r.region_name, rank;
```

### **3. Year-over-Year Comparison (using LAG)**

```sql
WITH yoy AS (
    SELECT
        f.date,
        r.region_name,
        c.classification,
        f.mom_variation,
        LAG(f.mom_variation, 12) OVER (
            PARTITION BY r.region_name, c.classification 
            ORDER BY f.date
        ) AS prev_year_mom
    FROM fact_inflation f
    JOIN dim_region   r ON f.region_id   = r.region_id
    JOIN dim_category c ON f.category_id = c.category_id
    WHERE c.category_name = 'Nivel General'
)
SELECT 
    date,
    region_name,
    classification,
    mom_variation,
    prev_year_mom,
    ROUND(mom_variation - prev_year_mom, 2) AS yoy_diff
FROM yoy
WHERE prev_year_mom IS NOT NULL
ORDER BY date DESC, region_name
LIMIT 20;
```

### **4. Nature-Based Aggregation (Bienes vs Servicios)**

```sql
SELECT 
    f.date,
    r.region_name,
    c.nature,
    ROUND(AVG(f.incidence), 4) AS avg_incidence
FROM fact_inflation f
JOIN dim_region   r ON f.region_id   = r.region_id
JOIN dim_category c ON f.category_id = c.category_id
WHERE c.nature IN ('Bienes', 'Servicios')
  AND f.date >= '2024-01-01'
GROUP BY f.date, r.region_name, c.nature
ORDER BY f.date DESC, r.region_name, c.nature;
```

---

## 📊 Business Intelligence & Analytics

The Star Schema is optimized for BI tools and supports complex analytical queries.

### **Available KPIs**

| Metric | Source | Regions | Description |
|--------|--------|---------|-------------|
| **MoM Variation** | Pre-calculated | 7 (all) | % change vs previous month |
| **Incidence** | Direct from INDEC | 6 (regional) | pp contribution to regional total |
| **YoY** | SQL `LAG(mom, 12)` | 7 (all) | Year-over-year comparison |
| **Cumulative** | SQL window function | 7 (all) | Accumulated since period start |
| **Nature Breakdown** | Aggregation on `nature` | 6 (regional) | Bienes vs Servicios inflation drivers |
| **Core vs Regulated** | Filter on `classification` | 7 (all) | Núcleo, Regulados, Estacionales |

### **Visualization Tools**

| Tool | Connection | Use Cases |
|------|------------|-----------|
| **Power BI** | PostgreSQL Connector | Executive dashboards, automated reports |
| **Tableau** | Native PostgreSQL | Ad-hoc analysis, visual storytelling |
| **Streamlit** | SQLAlchemy | Interactive web applications |
| **Python (Pandas)** | psycopg2 / SQLAlchemy | Exploratory analysis, notebooks |

---

## 🚀 Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/ipc-argentina-pipeline.git
cd ipc-argentina-pipeline

# 2. Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up credentials (create .env file)
cp .env.example .env
# Edit .env with your Supabase credentials:
#   DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

# 4. Initial data load
python ipc_scraper.py       # Downloads CSV → ipc_indec_datos.csv
python db_setup_secure.py   # Creates schema + loads data to Supabase

# 5. Verify data
# Connect to Supabase and run:
# SELECT COUNT(*) FROM fact_inflation;  -- Should show ~35,000 rows
# SELECT DISTINCT region_name FROM dim_region;  -- Should show 7 regions

# 6. Automate monthly updates (choose one):
# Option A - Cron (Linux/Mac)
crontab -e
# Add: 0 2 1 * * cd /path/to/project && venv/bin/python update_monthly.py

# Option B - GitHub Actions
# See .github/workflows/update_ipc.yml

# Option C - Windows Task Scheduler
# Set trigger: Monthly, day 1, 2:00 AM
# Action: python.exe update_monthly.py
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **ETL** | Pandas 2.x, Requests |
| **Database** | PostgreSQL 15+ (Supabase) |
| **ORM** | SQLAlchemy 2.x |
| **Orchestration** | GitHub Actions / Cron |
| **BI Tools** | Power BI, Tableau, Streamlit |

---

## 📁 Project Structure

```
ipc-argentina-pipeline/
├── ipc_scraper.py          # Main ETL script (downloads + transforms)
├── db_setup_secure.py      # Initial DB setup + data load
├── update_monthly.py       # Incremental monthly update script
├── config.py               # Environment variable manager
├── .env.example            # Template for credentials
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── docs/
    └── architecture.png    # Pipeline diagram
```

---

## 🔄 Data Pipeline Workflow

**Initial Setup:**
```
ipc_scraper.py → ipc_indec_datos.csv → db_setup_secure.py → PostgreSQL
```

**Monthly Update:**
```
update_monthly.py → build_incidence_df() + build_mom_variation_df() 
                 → merge_datasets() 
                 → UPSERT to PostgreSQL
```

**Key Functions:**
- `build_incidence_df()`: Downloads 145.12 + 145.10, unpivots, deduplicates
- `build_mom_variation_df()`: Downloads 145.9, calculates `pct_change()`, unpivots
- `merge_datasets()`: LEFT JOIN for regional data + CONCAT for Nacional rows

---

## 📚 References

- [INDEC - CPI Methodology](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31)
- [datos.gob.ar - CPI Datasets](https://datos.gob.ar/dataset/sspm-indice-precios-consumidor-nacional-ipc-nivel-general-categorias)
- [Supabase Documentation](https://supabase.com/docs)
- [Star Schema Design Patterns](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)