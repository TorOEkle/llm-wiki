# Semantic Modeling for Macroeconomic Data

## Introduction
Semantic modeling in the context of macroeconomic data involves moving beyond flat spreadsheets or relational tables toward a **knowledge graph** approach. By using W3C standards (RDF, OWL, SKOS), we transform raw numbers into self-describing, interlinked entities.

This project employs a multi-layered ontological approach to capture the complexity of economic indicators, their geographic and temporal contexts, and their revision history.

## Core Modeling Decisions

### 1. W3C Data Cube Vocabulary (QB)
We use the **Data Cube** vocabulary to represent statistical data.
*   **Dimensions:** Indicator, Reference Area, Reference Period, Frequency.
*   **Attributes:** Unit, Adjustment Method, Status.
*   **Measures:** Observation Value.
*   **Strength:** Industry standard for "Linked Data" statistics (used by Eurostat, UK government, etc.). It allows tools like CubeViz to visualize the data automatically.
*   **Weakness:** Adds complexity to SPARQL queries (multi-hop joins) compared to a simplified flat triple structure.

### 2. Indicators as Individuals (not Classes)
Following best practices for the Data Cube, specific indicators (e.g., `UnemploymentRate`) are modeled as **individuals** of an `EconomicIndicator` class.
*   **Strength:** Makes the ontology more data-driven. Adding a new indicator doesn't require changing the schema; it just means adding a new individual. It simplifies SPARQL queries for dashboards.
*   **Weakness:** Loses some of the formal reasoning power of OWL (like property restrictions on specific indicator types) unless using advanced modeling techniques like Punning.

### 3. Revision Tracking with PROV-O
Economic data is frequently revised. We use the **PROV-O** ontology to track "vintages."
*   **Decision:** Every observation is a `prov:Entity`. Revisions are linked via `prov:wasRevisionOf`.
*   **Strength:** Allows "time-travel" queries. We can see what the GDP for 2023 looked like *as of* March 2024 vs. what it looks like today.
*   **Weakness:** Significantly increases the triple count, as we store all historical versions of a data point, not just the latest.

### 4. Decoupling Units, Multipliers, and Currencies
Instead of a single "Millions of EUR" unit, we break this down into component parts.
*   **Strength:** Enables automated unit conversion. A query can automatically scale "Millions" to "Billions" or convert "EUR" to "USD" using a lookup table.
*   **Weakness:** Requires more complex data entry and more triples per observation.

### 5. OWL-Time for Temporal Precision
Quarters and years are modeled as `time:Interval` individuals.
*   **Strength:** Allows for topological temporal reasoning (e.g., finding all observations that occurred *during* a specific fiscal year).
*   **Weakness:** Requires minting URIs for every time period (2024-Q1, 2024-Q2), which can be verbose compared to simple `xsd:date` literals.

## Strengths of the Overall Approach
1.  **Interoperability:** Data can be merged with external datasets (like DBpedia or Eurostat) via `owl:sameAs` links.
2.  **Explicit Metadata:** No more ambiguity about whether a number is seasonally adjusted or what its base year is; the metadata is "baked in."
3.  **Traceability:** The full provenance from organization to dataset to specific revision is preserved.

## Weaknesses and Challenges
1.  **Learning Curve:** Requires knowledge of SPARQL and Semantic Web concepts to query effectively.
2.  **Storage Overhead:** The descriptive nature of RDF leads to larger storage requirements than CSV or Parquet.
3.  **Performance:** Complex analytical queries (like YoY changes) can be slow on very large datasets without specialized triple store optimizations or pre-computation.
