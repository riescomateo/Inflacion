"""
Automated monthly update script for IPC database.
This script:
1. Checks the last date recorded in the database
2. Downloads only new data from datos.gob.ar
3. Updates the database with new records (UPSERT)

Reuses build_incidence_df(), build_mom_variation_df() and merge_datasets()
from ipc_scraper.py to avoid duplicating download and parsing logic.
"""

import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from config import Config
from db_setup_secure import get_engine, setup_db
from ipc_scraper import build_incidence_df, build_mom_variation_df, merge_datasets, NATURE_MAP
import sys


def get_last_date_in_db():
    """Returns the most recent date recorded in fact_inflation, or None if empty."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = pd.read_sql("SELECT MAX(date) as last_date FROM fact_inflation", conn)
            last_date = result['last_date'].iloc[0]
            return None if pd.isna(last_date) else pd.to_datetime(last_date)
    except Exception as e:
        print(f"⚠️  Error getting last date: {e}")
        return None


def update_dimensions(df, conn):
    """
    Upserts dim_region and dim_category with any new values found in df.
    nature is included in dim_category since it is a property of the category.
    """
    # dim_region
    for reg in df['region'].drop_duplicates():
        conn.execute(
            text("INSERT INTO dim_region (region_name) VALUES (:r) "
                 "ON CONFLICT DO NOTHING"),
            {"r": reg}
        )

    # dim_category — include nature, update it in case mapping changed
    cats = df[['category', 'classification', 'nature']].drop_duplicates()
    for _, row in cats.iterrows():
        conn.execute(
            text("""
                INSERT INTO dim_category (category_name, classification, nature)
                VALUES (:n, :c, :nat)
                ON CONFLICT (category_name, classification)
                DO UPDATE SET nature = EXCLUDED.nature
            """),
            {
                "n":   row['category'],
                "c":   row['classification'],
                "nat": None if pd.isna(row['nature']) else row['nature']
            }
        )

    conn.commit()


def insert_facts(df, conn):
    """
    Upserts fact_inflation with incidence and mom_variation.
    Returns (inserted, updated) counts using RETURNING (xmax = 0).
    """
    # Build ID mappings from current dimension tables
    res_reg = pd.read_sql("SELECT * FROM dim_region", conn)
    res_cat = pd.read_sql("SELECT * FROM dim_category", conn)

    dict_reg = dict(zip(res_reg['region_name'], res_reg['region_id']))

    dict_cat = {}
    for _, row in res_cat.iterrows():
        dict_cat[(row['category_name'], row['classification'])] = row['category_id']

    df['region_id']   = df['region'].map(dict_reg)
    df['category_id'] = df.apply(
        lambda x: dict_cat.get((x['category'], x['classification'])), axis=1
    )

    inserted = 0
    updated  = 0

    for _, row in df.iterrows():
        result = conn.execute(
            text("""
                INSERT INTO fact_inflation
                    (date, region_id, category_id, incidence, mom_variation)
                VALUES
                    (:d, :r_id, :c_id, :inc, :mom)
                ON CONFLICT (date, region_id, category_id)
                DO UPDATE SET
                    incidence     = EXCLUDED.incidence,
                    mom_variation = EXCLUDED.mom_variation
                RETURNING (xmax = 0) AS inserted
            """),
            {
                "d":    row['time_index'],
                "r_id": row['region_id'],
                "c_id": row['category_id'],
                "inc":  None if pd.isna(row['incidence'])    else row['incidence'],
                "mom":  None if pd.isna(row['mom_variation']) else row['mom_variation']
            }
        )
        if result.fetchone()[0]:
            inserted += 1
        else:
            updated += 1

    conn.commit()
    return inserted, updated


def main():
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
            print("Run the initial load script first: db_setup_secure.py")
            sys.exit(1)

        print(f"\n📅 Last date in DB: {last_date_in_db.strftime('%Y-%m-%d')}")

        # 3. Calculate start date
        # Go back 2 months to capture any INDEC retroactive revisions
        start_date = (last_date_in_db - timedelta(days=60)).replace(day=1)
        start_date_str = start_date.strftime('%Y-%m-%d')
        print(f"📥 Downloading data from: {start_date_str}")

        # 4. Download and process using the same functions as ipc_scraper.py
        df_incidence = build_incidence_df(start_date_str)
        if df_incidence is None:
            print("❌ Could not build incidence dataset. Aborting.")
            sys.exit(1)

        df_mom = build_mom_variation_df(start_date_str)
        if df_mom is None:
            print("❌ Could not build MoM variation dataset. Aborting.")
            sys.exit(1)

        # 5. Merge and add nature column (same as ipc_scraper.py main())
        df_new = merge_datasets(df_incidence, df_mom)
        df_new['time_index'] = pd.to_datetime(df_new['time_index'])
        df_new['nature'] = df_new['classification'].map(NATURE_MAP)

        # 6. Filter only truly new data (>= last date to catch same-month revisions)
        df_new = df_new[df_new['time_index'] >= last_date_in_db]

        if len(df_new) == 0:
            print("\n✅ No new data to update — database is up to date!")
            return

        print(f"\n📊 New data found:")
        print(f"   Records : {len(df_new):,}")
        print(f"   Period  : {df_new['time_index'].min().strftime('%Y-%m-%d')} "
              f"to {df_new['time_index'].max().strftime('%Y-%m-%d')}")

        # 7. Update database
        print("\n🔄 Updating database...")
        engine = get_engine()

        with engine.connect() as conn:
            update_dimensions(df_new, conn)
            inserted, updated = insert_facts(df_new, conn)

        print("\n" + "=" * 80)
        print("✅ UPDATE COMPLETED")
        print("=" * 80)
        print(f"   Records inserted : {inserted:,}")
        print(f"   Records updated  : {updated:,}")
        print(f"   Total processed  : {inserted + updated:,}")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()