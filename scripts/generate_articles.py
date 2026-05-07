"""
generate_articles.py
Reads macro data from DuckDB, renders Jinja2 templates, and optionally
calls Gemini CLI to write the commentary sections.

Usage:
    python generate_articles.py                  # all articles, with Gemini
    python generate_articles.py --no-llm         # skip Gemini, leave placeholders
    python generate_articles.py --article cpi    # single article only
"""

import argparse
import duckdb
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Paths  (adjust ROOT if you move scripts/ somewhere else)
# ---------------------------------------------------------------------------

ROOT       = Path(__file__).parent.parent          # repo root
DB_PATH    = ROOT / "_data" / "macro.duckdb"
TMPL_DIR   = Path(__file__).parent / "templates"
DOCS_DIR   = ROOT / "docs"
RAW_DIR    = ROOT / "raw"                          # Norges Bank / Riksbank PDFs

# ---------------------------------------------------------------------------
# Article definitions  — add more here as you expand the wiki
# ---------------------------------------------------------------------------

ARTICLES = {
    "norway": {
        "template": "norway.md.j2",
        "output":   DOCS_DIR / "entities" / "norway.md",
        "country":  "norway",
        "indicators": ["cpi", "gdp", "unemployment", "employment_rate", "housing_prices"],
        "pdf_glob": "pengepolitisk_rapport*.pdf",   # latest PDF matched from raw/
        "llm_context": "Norges Bank pengepolitisk rapport",
        "lang": "no",
    },
    "sweden": {
        "template": "sweden.md.j2",
        "output":   DOCS_DIR / "entities" / "sweden.md",
        "country":  "sweden",
        "indicators": ["cpi", "gdp", "unemployment", "employment_rate", "housing_prices"],
        "pdf_glob": "penningpolitisk_rapport*.pdf",
        "llm_context": "Sveriges Riksbank penningpolitisk rapport",
        "lang": "sv",
    },
    "unemployment": {
        "template": "unemployment.md.j2",
        "output":   DOCS_DIR / "indicators" / "unemployment.md",
        "country":  None,                           # both countries
        "indicators": ["unemployment", "employment_rate"],
        "pdf_glob": None,
        "llm_context": "Norges Bank og Riksbank om arbeidsmarkedet",
        "lang": "no",
    },
    "norway_vs_sweden": {
        "template": "norway_vs_sweden.md.j2",
        "output":   DOCS_DIR / "comparison" / "norway_vs_sweden.md",
        "country":  None,
        "indicators": ["cpi", "gdp", "unemployment", "employment_rate", "housing_prices"],
        "pdf_glob": None,
        "llm_context": "Norges Bank og Riksbank sammenligning",
        "lang": "no",
    },
}

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_series(con, country: str, indicator: str, n: int = 12) -> list[dict]:
    """Return the last n periods for a country/indicator, newest first."""
    rows = con.execute("""
        SELECT period, value, label, unit
        FROM macro_data
        WHERE country = ? AND indicator = ?
        ORDER BY period DESC
        LIMIT ?
    """, [country, indicator, n]).fetchall()
    return [{"period": r[0], "value": r[1], "label": r[2], "unit": r[3]} for r in rows]


def latest(series: list[dict]) -> dict | None:
    return series[0] if series else None


def change(series: list[dict], periods: int = 1) -> float | None:
    """Absolute change vs N periods ago."""
    if len(series) > periods:
        return round(series[0]["value"] - series[periods]["value"], 2)
    return None


def pct_change(series: list[dict], periods: int = 12) -> float | None:
    """Year-on-year % change."""
    if len(series) > periods:
        prev = series[periods]["value"]
        if prev:
            return round((series[0]["value"] - prev) / prev * 100, 2)
    return None


def build_context(con, article_cfg: dict) -> dict:
    """Build the full template context dict for one article."""
    ctx = {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        "llm_summary": "[LLM SUMMARY PLACEHOLDER]",
        "llm_commentary": "[LLM COMMENTARY PLACEHOLDER]",
    }

    def load(country, indicator):
        s = load_series(con, country, indicator)
        return {
            "series":     s,
            "latest":     latest(s),
            "mom_change": change(s, 1),
            "yoy_change": pct_change(s, 12),
        }

    country = article_cfg["country"]
    indicators = article_cfg["indicators"]

    if country:
        # Single-country article
        for ind in indicators:
            ctx[ind] = load(country, ind)
    else:
        # Comparison article — load both
        for ind in indicators:
            ctx[f"norway_{ind}"] = load("norway", ind)
            ctx[f"sweden_{ind}"] = load("sweden", ind)

    return ctx


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def find_latest_pdf(glob_pattern: str | None) -> Path | None:
    if not glob_pattern:
        return None
    pdfs = sorted(RAW_DIR.glob(glob_pattern))
    return pdfs[-1] if pdfs else None


def read_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF using markitdown, fallback to pypdf."""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(pdf_path))
        return result.text_content[:12000]  # keep prompt manageable
    except Exception as e:
        print(f"  ⚠ markitdown failed ({e}), falling back to pypdf")

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        text = "\n".join(p.extract_text() or "" for p in reader.pages[:15])
        return text[:12000]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Gemini CLI
# ---------------------------------------------------------------------------

def call_gemini(prompt: str) -> str:
    """Call Gemini CLI and return the response text."""
    try:
        result = subprocess.run(
            ["gemini", prompt],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"  ⚠ Gemini error: {result.stderr[:200]}")
            return "[Gemini feil – se logg]"
    except FileNotFoundError:
        print("  ⚠ 'gemini' command not found — skipping LLM step")
        return "[Gemini ikke installert]"


def build_llm_prompts(article_key: str, cfg: dict, ctx: dict, pdf_text: str) -> tuple[str, str]:
    """Build summary and commentary prompts for Gemini."""
    lang_instruction = (
        "Svar på norsk bokmål." if cfg["lang"] == "no"
        else "Svara på svenska."
    )

    data_snippet = ""
    if cfg["country"]:
        for ind in cfg["indicators"]:
            d = ctx.get(ind)
            if d and d["latest"]:
                data_snippet += (
                    f"- {d['latest']['label']}: {d['latest']['value']} {d['latest']['unit']} "
                    f"(periode: {d['latest']['period']})\n"
                )
    else:
        for ind in cfg["indicators"]:
            for c in ["norway", "sweden"]:
                d = ctx.get(f"{c}_{ind}")
                if d and d["latest"]:
                    data_snippet += (
                        f"- {c.capitalize()} {d['latest']['label']}: "
                        f"{d['latest']['value']} {d['latest']['unit']} "
                        f"(periode: {d['latest']['period']})\n"
                    )

    pdf_section = f"\n\nUTDRAG FRA RAPPORT:\n{pdf_text}" if pdf_text else ""

    summary_prompt = (
        f"{lang_instruction} "
        f"Skriv et kort sammendrag (3-4 setninger) av den makroøkonomiske situasjonen "
        f"basert på følgende nøkkeltall og sentralbankrapport. "
        f"Kontekst: {cfg['llm_context']}.\n\n"
        f"NØKKELTALL:\n{data_snippet}"
        f"{pdf_section}"
    )

    commentary_prompt = (
        f"{lang_instruction} "
        f"Skriv en analytisk vurdering (2-3 avsnitt) av den pengepolitiske situasjonen "
        f"basert på nøkkeltallene og rapporten nedenfor. "
        f"Fokuser på trender, risiko og sentralbankens signaler. "
        f"Kontekst: {cfg['llm_context']}.\n\n"
        f"NØKKELTALL:\n{data_snippet}"
        f"{pdf_section}"
    )

    return summary_prompt, commentary_prompt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_article(article_key: str, use_llm: bool, con):
    cfg = ARTICLES[article_key]
    print(f"\n── {article_key} ──────────────────────────────")

    ctx = build_context(con, cfg)

    if use_llm:
        pdf_path = find_latest_pdf(cfg.get("pdf_glob"))
        pdf_text = read_pdf_text(pdf_path) if pdf_path else ""
        if pdf_path:
            print(f"  PDF: {pdf_path.name}")

        summary_prompt, commentary_prompt = build_llm_prompts(article_key, cfg, ctx, pdf_text)

        print("  Calling Gemini for summary...")
        ctx["llm_summary"] = call_gemini(summary_prompt)

        print("  Calling Gemini for commentary...")
        ctx["llm_commentary"] = call_gemini(commentary_prompt)

    # Render template
    env = Environment(loader=FileSystemLoader(str(TMPL_DIR)), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(cfg["template"])
    rendered = template.render(**ctx)

    # Write output
    out_path: Path = cfg["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"  ✓ Written → {out_path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm",   action="store_true", help="Skip Gemini, leave placeholders")
    parser.add_argument("--article",  help="Generate one article only (e.g. 'norway')")
    args = parser.parse_args()

    use_llm = not args.no_llm

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run fetch_macro.py first.")
        sys.exit(1)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    keys = [args.article] if args.article else list(ARTICLES.keys())
    for key in keys:
        if key not in ARTICLES:
            print(f"Unknown article '{key}'. Available: {list(ARTICLES.keys())}")
            continue
        generate_article(key, use_llm, con)

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
