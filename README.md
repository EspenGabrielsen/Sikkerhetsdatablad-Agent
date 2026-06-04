# Sikkerhetsdatablad-Agent

**Extract Section 14 (Transport Information) and revision dates from Safety Data Sheet (SDS) PDFs using LLMs.**

This tool downloads SDS PDFs from URLs, extracts the text, and uses an LLM (OpenAI, Azure OpenAI, or DeepSeek) to parse structured data — primarily **Section 14 (Transport Information)** and the **revision date**. Results are saved to CSV, Excel, and an **SQLite database** for easy querying and re-runs.

---

## Features

- **Automatic PDF download** with retry logic and size limits
- **Smart text extraction** — finds Section 14 even with varying headers (SEKSJON, SECTION, AVSNITT, etc.)
- **LLM-powered parsing** — extracts UN number, proper shipping name, hazard class, packing group, and more
- **Multiple LLM providers** — OpenAI, Azure OpenAI, DeepSeek
- **SQLite database** — upserts per document so partial results are never lost
- **CSV / Excel export** — human-readable output with Norwegian column headers
- **Batch processing** — process multiple URLs from a text file

---

## Installation

### Option 1: Install as a package (recommended)

```bash
# 1. Clone or download the project
cd Sikkerhetsdatablad-Agent

# 2. Install the package (creates the `sds-agent` CLI command)
pip install -e .

# 3. Configure your API key
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

### Option 2: Virtual environment + requirements

```bash
# 1. Clone or download the project
cd Sikkerhetsdatablad-Agent

# 2. Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and set your preferred LLM provider:

```ini
# --- OpenAI (default) ---
PROVIDER=openai
OPENAI_API_KEY=sk-...

# --- OR Azure OpenAI ---
# PROVIDER=azure
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT=gpt-4o

# --- OR DeepSeek ---
# PROVIDER=deepseek
# DEEPSEEK_API_KEY=sk-...
```

---

## Usage

After installing with `pip install -e .`, you can use the `sds-agent` CLI command **or** run the module directly:

```bash
# Via CLI command (after pip install -e .)
sds-agent --url "https://api-prd.dahl.no/int-mdm/1/asset/<uuid>"

# Or via python -m
python -m sikkerhetsdatablad_agent.main --url "https://..."
```

### Single document

```bash
sds-agent --url "https://api-prd.dahl.no/int-mdm/1/asset/<uuid>"
```

This will:
1. Download the PDF
2. Extract Section 14 text
3. Parse it with the LLM
4. Print a summary
5. Upsert the result to `sikkerhetsdatablad.db`
6. Save `resultater.xlsx` and `resultater.csv`

### Batch processing

Create a text file with one URL per line (lines starting with `#` are ignored):

```text
# urls.txt
https://api-prd.dahl.no/int-mdm/1/asset/aaaa...
https://api-prd.dahl.no/int-mdm/1/asset/bbbb...
https://api-prd.dahl.no/int-mdm/1/asset/cccc...
```

Then run:

```bash
sds-agent --batch urls.txt
```

### Custom output paths

```bash
# Custom Excel/CSV output
sds-agent --url "https://..." --output my_results.xlsx

# Custom database path
sds-agent --url "https://..." --db my_database.db

# Custom database via environment variable
set DATABASE_PATH=my_database.db   # Windows
# export DATABASE_PATH=my_database.db   # macOS/Linux
sds-agent --url "https://..."
```

### Verbose / debug logging

```bash
sds-agent --url "https://..." --verbose
```

---

## Output

### SQLite database (`sikkerhetsdatablad.db`)

The database is updated **immediately after each successful document parse** (upsert by `source_url`). This means if a batch run is interrupted, all results processed so far are safely stored.

```sql
-- Query all results
SELECT * FROM sds_results;

-- Check when a URL was last processed
SELECT source_url, updated_at FROM sds_results
WHERE source_url = 'https://...';
```

### CSV / Excel (`resultater.xlsx` + `resultater.csv`)

| Column | Description |
|---|---|
| Kilde-URL | Source URL of the PDF |
| Produktnavn | Product name (from Section 1) |
| Revisjonsdato | Revision / issue date |
| 14.1 UN-nummer | UN number (e.g. UN1263) |
| 14.2 Offisielt transportnavn | Proper Shipping Name |
| 14.3 Transportfareklasse | Transport hazard class(es) |
| 14.4 Emballasjegruppe | Packing group |
| 14.5 Miljøfarer | Environmental hazards |
| 14.6 Spesielle forholdsregler | Special precautions for user |
| 14.7 Bulktransport | Bulk transport (MARPOL / IBC) |
| Merknader | Notes / warnings |

---

## UNECE ADR Table A — Dangerous Goods List

This project also includes a script to extract **Table A: Dangerous Goods List** from the official UNECE ADR 2025 publication.

The table spans pages 300–531 of the PDF. Because the table is too wide for A4 format, each spread consists of two pages that must be concatenated horizontally — the left page contains columns (1)–(14) and the right page contains columns (15)–(20).

### Source

- **Original PDF**: [2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf](https://unece.org/sites/default/files/2025-01/2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf)
  (Download manually if needed — the UNECE server may block automated requests.)

### Usage

```bash
# 1. Download the PDF manually from the link above
# 2. Update the PDF_PATH in unece_table_a.py to point to your local copy
# 3. Run the extraction script
python unece_table_a.py
```

This will produce:
- `table_a_dangerous_goods.csv` — all ~3 500+ rows with 20 columns
- `table_a_dangerous_goods.xlsx` — same data in Excel format (if `openpyxl` is installed)

### Output columns

| # | Column | ADR Ref |
|---|--------|---------|
| 1 | UN_No | (1) |
| 2 | Name_and_description | (2) |
| 3 | Class | (3a) |
| 4 | Classification_code | (3b) |
| 5 | Packing_group | (4) |
| 6 | Labels | (5) |
| 7 | Special_provisions | (6) |
| 8 | Limited_quantities | (7a) |
| 9 | Excepted_quantities | (7b) |
| 10 | Packaging_instructions | (8) |
| 11 | Special_packing_provisions | (9a) |
| 12 | Mixed_packing_provisions | (9b) |
| 13 | Portable_tank_instructions | (10) |
| 14 | Portable_tank_special_prov | (11) |
| 15 | ADR_tank_code | (12) |
| 16 | Tank_special_provisions | (13) |
| 17 | Vehicle_tank_code | (14) |
| 18 | Transport_category | (15) |
| 19 | Tunnel_restriction_code | (16) |
| 20 | Hazard_identification_No | (19) |

---

## Project structure

```
Sikkerhetsdatablad-Agent/
├── sikkerhetsdatablad_agent/   # Python package
│   ├── __init__.py
│   ├── main.py          # CLI entry point
│   ├── config.py        # LLM provider configuration
│   ├── database.py      # SQLite upsert layer
│   ├── extractor.py     # PDF text extraction (Section 14 regex)
│   ├── fetcher.py       # PDF download with retries
│   ├── llm_parser.py    # LLM prompt building & response parsing
│   ├── models.py        # Pydantic data models (SDSData, Section14)
│   └── output.py        # CSV / Excel export
├── .env.example         # Environment variable template
├── .gitignore
├── pyproject.toml       # Package build configuration
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## Requirements

- Python 3.10+
- An API key for one of: OpenAI, Azure OpenAI, or DeepSeek
- Dependencies listed in `requirements.txt`

---

## License

Internal use — Saint-Gobain.
