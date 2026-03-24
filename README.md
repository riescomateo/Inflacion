# IPC Argentina - Automated Data Pipeline

End-to-end ETL pipeline for Argentine inflation analysis using a PostgreSQL star schema and automated monthly updates.

---

## 🚀 Summary

Built a production-style data pipeline that ingests public CPI data from Argentina, transforms it into analytical metrics, and loads it into a PostgreSQL data warehouse with automated monthly updates.

- Processes **35,000+ records** across 7 regions and multiple categories  
- Computes **MoM variation** and **incidence metrics** for inflation analysis  
- Supports **incremental updates with data revision handling**  

---

## 📊 Key Features

- **End-to-End ETL Pipeline** — Extraction from datos.gob.ar API, transformation, and loading into PostgreSQL  
- **Star Schema Design** — Optimized for analytical queries and BI tools  
- **Dual Metrics** — Stores both:
  - MoM variation (% change)
  - Incidence (contribution to total inflation)  
- **Incremental Updates** — Handles late data revisions using UPSERT logic  
- **Automation** — Monthly updates via GitHub Actions / Cron  

---

## 🏗️ System Architecture


API (datos.gob.ar) → Pandas ETL → PostgreSQL (Star Schema) → BI / SQL Analysis


---

## 📐 Data Model

Star schema with:

- `fact_inflation` → metrics (MoM, incidence)  
- `dim_region` → 7 regions  
- `dim_category` → categories + classifications  

Optimized for time-series and multidimensional analysis.

---

## 📊 Example Analysis

- Regional inflation drivers (top contributing categories)  
- Month-over-month inflation trends  
- Year-over-year comparisons using SQL window functions  
- Goods vs services breakdown  

---

## ⚙️ Tech Stack

- Python (Pandas, Requests)  
- PostgreSQL (Supabase)  
- SQLAlchemy  
- GitHub Actions / Cron  
- Power BI / Tableau / Streamlit  

---

## ▶️ Quick Start

```bash
python ipc_scraper.py
python db_setup_secure.py
🔄 Automation
Monthly updates via:
GitHub Actions
Cron jobs

Includes incremental loading and handling of retroactive data revisions.

📄 License

MIT License