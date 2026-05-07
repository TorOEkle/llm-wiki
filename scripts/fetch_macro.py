"""
fetch_macro.py
Pulls macro data from SSB (Norway) and SCB (Sweden) APIs into a local DuckDB file.
Run this first before generate_articles.py
"""

import requests
import duckdb
import json
from datetime import datetime
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
        "table": "03013",
        "label": "KPI (konsumprisindeks)",
        "unit": "Indeks (2015=100)",
        "query": {
            "query": [
                {"code": "Konsumgruppe", "selection": {"filter": "item", "values": ["TOTAL"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiIndMnd"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "unemployment": {
        "table": "05111",
        "label": "Arbeidsledighet (AKU)",
        "unit": "Prosent av arbeidsstyrken",
        "query": {
            "query": [
                {"code": "Kjonn", "selection": {"filter": "item", "values": ["0"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["Ledige"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "employment_rate": {
        "table": "05111",
        "label": "Sysselsettingsandel",
        "unit": "Prosent av befolkningen",
        "query": {
            "query": [
                {"code": "Kjonn", "selection": {"filter": "item", "values": ["0"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["Sysselsatte"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "gdp": {
        "table": "09190",
        "label": "BNP Fastlands-Norge",
        "unit": "Millioner kroner",
        "query": {
            "query": [
                {"code": "NACE", "selection": {"filter": "item", "values": ["nr23_6"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BNPB"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
            ],
            "response": {"format": "json-stat2"}
        }
    },
    "housing_prices": {
        "table": "07241",
        "label": "Boligprisindeks",
        "unit": "Indeks (2015=100)",
        "query": {
            "query": [
                {"code": "Boligtype", "selection": {"filter": "item", "values": ["00"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BpIndeks"]}},
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
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
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
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
                {"code": "Tid", "selection": {"filter": "top", "values": ["6"]}}
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
                {"code": "Tid", "selection": {"filter": "top", "values": ["6"]}}
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
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
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
                {"code": "Tid", "selection": {"filter": "top", "values": ["13"]}}
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
    fetched_at = datetime.utcnow().isoformat()
    con.execute("""
        CREATE TABLE IF NOT EXISTS macro_data (
            country     VARCHAR,
            indicator   VARCHAR,
            label       VARCHAR,
            unit        VARCHAR,
            period      VARCHAR,
            value       DOUBLE,
            fetched_at  VARCHAR,
            PRIMARY KEY (country, indicator, period)
        )
    """)
    for row in rows:
        con.execute("""
            INSERT OR REPLACE INTO macro_data
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [country, indicator, label, unit, row["period"], row["value"], fetched_at])
    print(f"  ✓ {country.upper()} {indicator}: {len(rows)} periods")


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

    # Quick summary
    print("\n── Summary ───────────────────────────────────")
    result = con.execute("""
        SELECT country, indicator, COUNT(*) as periods, MAX(period) as latest
        FROM macro_data
        GROUP BY country, indicator
        ORDER BY country, indicator
    """).fetchall()
    for row in result:
        print(f"  {row[0]:<8} {row[1]:<20} {row[2]} periods  latest: {row[3]}")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
