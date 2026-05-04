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
