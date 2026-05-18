# LLM-Brain Tools

This repository contains tools and data for processing financial and economic reports.

## Link

The wiki can be found here <https://toroekle.github.io/llm-wiki/>

## MarkItDown

[MarkItDown](https://github.com/microsoft/markitdown) is used to convert various file formats (like PDF) into Markdown.

### Setup & Activation

We use `uv` to manage the virtual environment.

1. **Activate the environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **(If not already installed) Install with PDF support:**
   ```bash
   uv pip install "markitdown[pdf]"
   ```

### Usage: PDF to Markdown Conversion

To convert a PDF file in the `raw/` folder to Markdown:

```bash
# Basic conversion (outputs to stdout)
uv run markitdown raw/filename.pdf

# Conversion with output file
uv run markitdown raw/filename.pdf -o raw/filename.md
```

### Git Tagging Convention

When tagging changes, use the following format (as specified in `GEMINI.md`):

```bash
git tag -a "$(date +%Y-%m-%dT%H:%M:%S)" -m "Your description here"
```

## Populate database
Run the following command to populate standalone `Shell uv run scripts/fetch_macro.py`


# Macroeconomic Semantic Model

RDF-based semantic model for macroeconomic indicators built on OWL, W3C Data Cube, SDMX, and PROV-O.

---

## Prerequisites

- WSL (Ubuntu)
- Java 21: `sudo apt install openjdk-21-jdk`
- Apache Jena Fuseki 5.6.0 installed at `~/fuseki`

---

## Triple Store — Apache Jena Fuseki

The database runs as a local SPARQL server at `http://localhost:3030`.
Data is stored persistently at `~/fuseki-data/macrodata` — independent of this repo.

### Start

```bash
~/fuseki/fuseki-server --tdb2 --loc ~/fuseki-data/macrodata /macrodata &
```

Server starts in the background. The SPARQL endpoint is available at:
`http://localhost:3030/macrodata/sparql`

The web UI (query editor, data browser) is available at:
`http://localhost:3030` — open in your Windows browser.

### Stop

```bash
pkill -f fuseki-server
```

### Check if running

```bash
pgrep -a -f fuseki-server
```

---

## Loading Data

### Load the ontology

```bash
curl -X POST http://localhost:3030/macrodata/data \
  -H "Content-Type: text/turtle" \
  --data-binary @macroeconomic-ontology.ttl
```

### Load any other TTL file

```bash
curl -X POST http://localhost:3030/macrodata/data \
  -H "Content-Type: text/turtle" \
  --data-binary @your-file.ttl
```

### Clear all data

```bash
curl -X POST http://localhost:3030/macrodata/update \
  -H "Content-Type: application/sparql-update" \
  --data "DROP ALL"
```

---

## Querying

### Run a query string from the terminal

```bash
curl -X POST http://localhost:3030/macrodata/sparql \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/json" \
  --data "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
```

### Run a query from a `.rq` file

```bash
curl -X POST http://localhost:3030/macrodata/sparql \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/json" \
  --data-binary @queries/your-query.rq
```

### Run a SPARQL update from a file

```bash
curl -X POST http://localhost:3030/macrodata/update \
  -H "Content-Type: application/sparql-update" \
  --data-binary @queries/your-update.ru
```

---

## Shell Aliases (recommended)

Add to `~/.bashrc` to make daily use easier:

```bash
# Start/stop Fuseki
alias fuseki-start='~/fuseki/fuseki-server --tdb2 --loc ~/fuseki-data/macrodata /macrodata >> ~/fuseki-data/fuseki.log 2>&1 &'
alias fuseki-stop='pkill -f fuseki-server'

# Query — accepts a SPARQL string or a .rq file path
sparql-query() {
  if [ -f "$1" ]; then
    curl -s -X POST http://localhost:3030/macrodata/sparql \
      -H "Content-Type: application/sparql-query" \
      -H "Accept: application/json" \
      --data-binary @"$1" | python3 -m json.tool
  else
    curl -s -X POST http://localhost:3030/macrodata/sparql \
      -H "Content-Type: application/sparql-query" \
      -H "Accept: application/json" \
      --data "$1" | python3 -m json.tool
  fi
}

# Load a TTL file into the database
sparql-load() {
  curl -X POST http://localhost:3030/macrodata/data \
    -H "Content-Type: text/turtle" \
    --data-binary @"$1"
}
```

Reload with: `source ~/.bashrc`

Usage:

```bash
fuseki-start
fuseki-stop
sparql-query "SELECT * WHERE { ?s ?p ?o } LIMIT 5"
sparql-query queries/latest-observations.rq
sparql-load macroeconomic-ontology.ttl
```

---

## Auto-start on WSL login (optional)

Add to `~/.bashrc` to start Fuseki automatically whenever you open WSL:

```bash
if ! pgrep -f fuseki-server > /dev/null; then
  ~/fuseki/fuseki-server --tdb2 --loc ~/fuseki-data/macrodata /macrodata \
    >> ~/fuseki-data/fuseki.log 2>&1 &
  echo "Fuseki started → http://localhost:3030"
fi
```

---

## Endpoints Reference

| Endpoint | Purpose |
|---|---|
| `http://localhost:3030` | Web UI (Workbench) |
| `http://localhost:3030/macrodata/sparql` | SPARQL 1.1 Query |
| `http://localhost:3030/macrodata/update` | SPARQL 1.1 Update |
| `http://localhost:3030/macrodata/data` | Graph Store (load/read data) |

---

## Repository Structure

```
.
├── macroeconomic-ontology.ttl   # OWL ontology (namespaces, classes, properties)
├── data/                        # Instance data TTL files
├── queries/                     # SPARQL query files (.rq) and update files (.ru)
└── README.md
```


## Resume last session
`gemini --resume e2c7849c-ee35-4e54-8ce5-4c54c6625cee`
