"""Inspect the UNECE ADR PDF to understand the table structure around page 299."""

from pathlib import Path

# Local path provided by user
pdf_path = Path(
    r"C:\Users\E1732506\OneDrive - Saint-Gobain\PycharmProjects\Markdowns\2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf"
)
print(f"File size: {pdf_path.stat().st_size} bytes")

import pdfplumber

pdf = pdfplumber.open(pdf_path)
print(f"\nTotal pages: {len(pdf.pages)}")

# Check start and end of table
for i in [298, 299, 300, 529, 530]:
    page = pdf.pages[i]
    text = page.extract_text() or ""
    tables = page.find_tables()

    print(f"\n{'='*80}")
    print(f"--- Page {i+1} ({len(text)} chars, {len(tables)} tables found) ---")

    for ti, tbl in enumerate(tables):
        print(f"\n  Table {ti+1}: {len(tbl.rows)} rows x {len(tbl.columns)} columns")
        print(f"  Bounding box: {tbl.bbox}")

        # Show first 3 data rows
        for ri in range(min(3, len(tbl.rows))):
            row = tbl.rows[ri]
            print(f"  Row {ri}: {[str(c)[:40] for c in row.cells]}")

        # Show last 2 rows
        if len(tbl.rows) > 4:
            for ri in range(len(tbl.rows) - 2, len(tbl.rows)):
                row = tbl.rows[ri]
                print(f"  Row {ri}: {[str(c)[:40] for c in row.cells]}")

        print()

    # Show raw table extraction for first table
    if tables:
        print("  --- Raw cell dump (first table, first 3 rows) ---")
        for ri in range(min(3, len(tables[0].rows))):
            row = tables[0].rows[ri]
            for ci, cell in enumerate(row.cells):
                print(f"    [{ri},{ci}] = '{str(cell)[:80]}'")
