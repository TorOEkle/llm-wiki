---
layout: page
title: "Wiki Schema: Economic Development (Norway & Sweden)"
categories: [Economy]
tags: [Norway, Sweden]
---
# Wiki Schema: Economic Development (Norway & Sweden)

This schema defines how the Economic Development Wiki is structured and maintained.

## Directory Structure

- `raw/`: Immutable source documents (Markdown converted from PDFs).
- `docs/`: LLM-generated markdown files (hosted via GitHub Pages).
  - `index.md`: Catalog of all pages.
  - `log.md`: Chronological record of ingests and updates.
  - `entities/`: Pages for countries (Norway.md, Sweden.md).
  - `indicators/`: Pages for specific metrics (Unemployment.md, Salaries.md, Currency.md, Interest_Rates.md).
  - `comparisons/`: Comparison tables and analyses.
  - `raw/`: Copy of source markdown files for web linking.

## Page Templates

### Entity Page (entities/*.md)
- Overview
- Current Economic Status
- Historical Data (Table)
- Key Trends
- Sources

### Indicator Page (indicators/*.md)
- Definition
- Development in Norway (Table/Timeline)
- Development in Sweden (Table/Timeline)
- Comparison/Analysis
- Sources

### Comparison Page (comparisons/*.md)
- Objective
- Comparison Table (Norway vs. Sweden)
- Key Differences/Similarities
- Social Media Hooks (Drafts for posts)

## Ingest Workflow

1. **Read**: Analyze the raw report.
2. **Extract**: Identify key figures for Unemployment, Salaries, Currency, and Interest Rates.
3. **Update Entity**: Append new data to the country's page.
4. **Update Indicator**: Append new data to the specific metric pages.
5. **Report Summary**: Create a page in `reports/` for the specific report.
6. **Log**: Record the update in `log.md`.
7. **Index**: Update `index.md` if new pages were created.

## Conventions

- Use tables for time-series data.
- Always cite the source report (e.g., [PPR 1/2024]).
- Use clear, concise headings.
- Maintain interlinks between entities, indicators, and reports.
