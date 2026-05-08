"""
fetch_macro.py
Pulls macro data from SSB (Norway) and SCB (Sweden) APIs into a local DuckDB file.
Run this first before generate_articles.py
"""

import requests
import duckdb
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "_data" / "macro.duckdb"
DB_PATH.parent.mkdir(exist_ok=True)

SSB_BASE = "https://data.ssb.no/api/v0/no/table"
SCB_BASE = "https://api.scb.se/OV0104/v1/doris/sv/ssd"

# ---------------------------------------------------------------------------
# SSB queries (Norway)
# Each entry: (table_id, query_body, series_label, unit)
# PxWebAPI: POST JSON query, returns JSON-stat
# ---------------------------------------------------------------------------

SSB_QUERIES = {
    "cpi": {
        "table": "14700",
        "label": "KPI (konsumprisindeks)",
        "unit": "Indeks (2025=100)",
        "query": {
            "query": [
                {"code": "VareTjenesteGrp", "selection": {"filter": "item", "values": ["00"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiIndMnd"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "unemployment": {
        "table": "13760",
        "label": "Arbeidsledighet (AKU) begge kjønn 15-74år",
        "unit": "Prosent av arbeidsstyrken",
        "query": {
            "query": [
                {"code": "Kjonn", "selection": {"filter": "item", "values": ["0"]}},
                {"code": "Alder", "selection": {"filter": "item", "values": ["15-74"]}},
                {"code": "Justering", "selection": {"filter": "item", "values": ["S"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["ArbledProsArbstyrk"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "employment_rate": {
        "table": "13760",
        "label": "Sysselsetting (AKU) begge kjønn 15-74år",
        "unit": "Prosent av befolkningen",
        "query": {
            "query": [
                {"code": "Kjonn", "selection": {"filter": "item", "values": ["0"]}},
                {"code": "Alder", "selection": {"filter": "item", "values": ["15-74"]}},
                {"code": "Justering", "selection": {"filter": "item", "values": ["S"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["SysselProsBefolkn"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "gdp": {
        "table": "11721",
        "label": "BNP Fastlands-Norge",
        "unit": "Millioner kroner (sesongjustert)",
        "query": {
            "query": [
                {"code": "Makrost", "selection": {"filter": "item", "values": ["bnpb.nr23_9fn"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["FastePriserSesJust"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "housing_prices": {
        "table": "07221",
        "label": "Boligprisindeks (brukte boliger)",
        "unit": "Indeks (2015=100, kvartalsvis, sesongjustert)",
        "query": {
            "query": [
                {"code": "Region", "selection": {"filter": "item", "values": ["TOTAL"]}},
                {"code": "Boligtype", "selection": {"filter": "item", "values": ["00"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["SesJustBoligindeks"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
}

# ---------------------------------------------------------------------------
# SCB queries (Sweden) — same PxWebAPI spec, different base URL and table IDs
# ---------------------------------------------------------------------------

SCB_QUERIES = {
    "cpi": {
        "table": "PR/PR0101/PR0101A/KPItotM",
        "label": "KPI (konsumentprisindex)",
        "unit": "Index (1980=100)",
        "query": {
            "query": [
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["000004VU"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "unemployment": {
        "table": "AM/AM0401/AM0401A/NAKUArssni",
        "label": "Arbetslöshet (AKU)",
        "unit": "Procent av arbetskraften",
        "query": {
            "query": [
                {"code": "Kon", "selection": {"filter": "item", "values": ["1+2"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["000000RY"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "employment_rate": {
        "table": "AM/AM0401/AM0401A/NAKUArssni",
        "label": "Sysselsättningsgrad",
        "unit": "Procent av befolkningen",
        "query": {
            "query": [
                {"code": "Kon", "selection": {"filter": "item", "values": ["1+2"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["000000RX"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "gdp": {
        "table": "NR/NR0103/NR0103A/NR0103ENS2010T01Kv",
        "label": "BNP (Sverige)",
        "unit": "Miljoner kronor",
        "query": {
            "query": [
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["000002IT"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "housing_prices": {
        "table": "BO/BO0501/BO0501A/FastprisSHRegionKv",
        "label": "Fastighetsprisindex",
        "unit": "Index",
        "query": {
            "query": [
                {"code": "Region", "selection": {"filter": "item", "values": ["00"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BO0501A1"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["48"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_pxweb(base_url: str, table: str, query: dict) -> list[dict]:
    """
    POST a PxWebAPI query and return a flat list of {period, value} dicts.
    Both SSB and SCB use the same JSON-stat2 response format.
    """
    url = f"{base_url}/{table}"
    resp = requests.post(url, json=query, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # JSON-stat2: values are flat, dimensions tell us the labels
    values = data.get("value", [])
    # Time dimension is always the last dimension in these queries
    time_dim_key = list(data["dimension"].keys())[-1]
    periods = list(data["dimension"][time_dim_key]["category"]["label"].values())

    rows = []
    for i, (period, value) in enumerate(zip(periods, values)):
        if value is not None:
            rows.append({"period": period, "value": float(value)})
    return rows


def upsert_series(con, country: str, indicator: str, label: str, unit: str, rows: list[dict]):
    """Insert or replace rows into the macro_data table."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    con.execute("""
        CREATE TABLE IF NOT EXISTS macro_data (
            country     VARCHAR,
            indicator   VARCHAR,
            label       VARCHAR,
            unit        VARCHAR,
            period      VARCHAR,
            value       DOUBLE,
            fetched_at  VARCHAR,
            mom_change  DOUBLE,
            yoy_change  DOUBLE,
            PRIMARY KEY (country, indicator, period)
        )
    """)
    for row in rows:
        con.execute("""
            INSERT OR REPLACE INTO macro_data (country, indicator, label, unit, period, value, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [country, indicator, label, unit, row["period"], row["value"], fetched_at])
    print(f"  ✓ {country.upper()} {indicator}: {len(rows)} periods")


def calculate_changes(con):
    """
    Compute MoM (previous period) and YoY (same period last year) changes.
    Indices use percentage change, others use absolute change.
    """
    print("\n── Calculating MoM and YoY changes ────────────────")
    # Update using a JOIN on a subquery with window functions
    con.execute("""
        UPDATE macro_data 
        SET 
            mom_change = ROUND(sub.mom, 4),
            yoy_change = ROUND(sub.yoy, 4)
        FROM (
            SELECT 
                country, indicator, period,
                CASE 
                    WHEN (unit LIKE '%Indeks%' OR unit LIKE '%Index%') 
                         AND prev_val IS NOT NULL AND prev_val != 0
                    THEN (value / prev_val) - 1
                    ELSE value - prev_val
                END as mom,
                CASE 
                    WHEN (unit LIKE '%Indeks%' OR unit LIKE '%Index%') 
                         AND year_ago_val IS NOT NULL AND year_ago_val != 0
                    THEN (value / year_ago_val) - 1
                    ELSE value - year_ago_val
                END as yoy
            FROM (
                SELECT 
                    *,
                    LAG(value, 1) OVER (PARTITION BY country, indicator ORDER BY period) as prev_val,
                    CASE 
                        WHEN period LIKE '%M%' THEN LAG(value, 12) OVER (PARTITION BY country, indicator ORDER BY period)
                        WHEN period LIKE '%K%' THEN LAG(value, 4) OVER (PARTITION BY country, indicator ORDER BY period)
                        ELSE NULL
                    END as year_ago_val
                FROM macro_data
            )
        ) sub
        WHERE macro_data.country = sub.country 
          AND macro_data.indicator = sub.indicator 
          AND macro_data.period = sub.period
    """)
    print("  ✓ Calculations completed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Opening database at {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))

    print("\n── Norway (SSB) ──────────────────────────────")
    for indicator, cfg in SSB_QUERIES.items():
        try:
            rows = fetch_pxweb(SSB_BASE, cfg["table"], cfg["query"])
            upsert_series(con, "norway", indicator, cfg["label"], cfg["unit"], rows)
        except Exception as e:
            print(f"  ✗ norway/{indicator}: {e}")

    print("\n── Sweden (SCB) ──────────────────────────────")
    for indicator, cfg in SCB_QUERIES.items():
        try:
            rows = fetch_pxweb(SCB_BASE, cfg["table"], cfg["query"])
            upsert_series(con, "sweden", indicator, cfg["label"], cfg["unit"], rows)
        except Exception as e:
            print(f"  ✗ sweden/{indicator}: {e}")

    calculate_changes(con)

    # Quick summary
    print("\n── Summary ───────────────────────────────────")
    result = con.execute("""
        SELECT country, indicator, COUNT(*) as periods, MAX(period) as latest
        FROM macro_data
        GROUP BY country, indicator
        ORDER BY country, indicator
    """).fetchall()
    for row in result:
        # Get the latest values and unit for this series
        latest_data = con.execute("""
            SELECT value, mom_change, yoy_change, unit 
            FROM macro_data 
            WHERE country = ? AND indicator = ? AND period = ?
        """, [row[0], row[1], row[3]]).fetchone()
        
        val, mom, yoy, unit = latest_data
        is_index = "Indeks" in unit or "Index" in unit
        
        val_str = f"{val:,.1f}"
        mom_str = f"{mom*100:+.2f}%" if is_index and mom is not None else f"{mom:+.2f}"
        yoy_str = f"{yoy*100:+.2f}%" if is_index and yoy is not None else f"{yoy:+.2f}"

        print(f"  {row[0]:<8} {row[1]:<20} {row[2]} periods  latest: {row[3]}  val: {val_str:>10}  MoM: {mom_str:>8}  YoY: {yoy_str:>8}")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
