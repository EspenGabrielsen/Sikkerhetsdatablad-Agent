from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import pandas as pd

from sikkerhetsdatablad_agent.models import SDSData

logger = logging.getLogger(__name__)

_COLUMN_ORDER = [
    "source_url",
    "product_name",
    "revision_date",
    "un_number",
    "proper_shipping_name",
    "transport_hazard_class",
    "packing_group",
    "environmental_hazards",
    "special_precautions_for_user",
    "bulk_transport",
    "notes",
]

_COLUMN_HEADERS = {
    "source_url": "Kilde-URL",
    "product_name": "Produktnavn",
    "revision_date": "Revisjonsdato",
    "un_number": "14.1 UN-nummer",
    "proper_shipping_name": "14.2 Offisielt transportnavn",
    "transport_hazard_class": "14.3 Transportfareklasse",
    "packing_group": "14.4 Emballasjegruppe",
    "environmental_hazards": "14.5 Miljøfarer",
    "special_precautions_for_user": "14.6 Spesielle forholdsregler",
    "bulk_transport": "14.7 Bulktransport",
    "notes": "Merknader",
}


def build_dataframe(results: Sequence[SDSData]) -> pd.DataFrame:
    """Konverterer en liste av SDSData-objekter til en pandas DataFrame."""
    rows = [r.to_flat_dict() for r in results]
    df = pd.DataFrame(rows, columns=_COLUMN_ORDER)
    return df.rename(columns=_COLUMN_HEADERS)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(
        path, index=False, encoding="utf-8-sig"
    )  # utf-8-sig for Excel-kompatibilitet
    logger.info("CSV lagret: %s", path)


def save_excel(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sikkerhetsdatablad")
        # Auto-juster kolonnebredder
        ws = writer.sheets["Sikkerhetsdatablad"]
        for col_cells in ws.columns:
            max_len = max(
                (len(str(cell.value)) if cell.value is not None else 0)
                for cell in col_cells
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(
                max_len + 4, 60
            )
    logger.info("Excel lagret: %s", path)


def save_results(results: Sequence[SDSData], output_path: str) -> None:
    """
    Lagrer resultater til fil.
    Filtype bestemmes av endelsen (.csv, .xlsx eller .xls).
    Hvis endelsen er .xlsx/.xls lagres også en .csv ved siden av.
    """
    if not results:
        logger.warning("Ingen resultater å lagre.")
        return

    df = build_dataframe(results)
    p = Path(output_path)

    if p.suffix.lower() in (".xlsx", ".xls"):
        save_excel(df, p)
        csv_path = p.with_suffix(".csv")
        save_csv(df, csv_path)
        print(f"Lagret: {p}  og  {csv_path}")
    elif p.suffix.lower() == ".csv":
        save_csv(df, p)
        print(f"Lagret: {p}")
    else:
        # Default til Excel
        xlsx_path = p.with_suffix(".xlsx")
        save_excel(df, xlsx_path)
        csv_path = p.with_suffix(".csv")
        save_csv(df, csv_path)
        print(f"Lagret: {xlsx_path}  og  {csv_path}")
