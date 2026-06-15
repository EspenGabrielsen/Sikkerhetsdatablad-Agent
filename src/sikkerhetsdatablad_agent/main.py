"""
Sikkerhetsdatablad-Agent — ekstraherer seksjon 14 og revisjonsdato fra SDS-PDFer.

Bruk:
  Enkelt dokument:
    python main.py --url "https://api-prd.dahl.no/int-mdm/1/asset/<id>"

  Batch (tekstfil med én URL per linje):
    python main.py --batch urls.txt --output resultater.xlsx

  Med egendefinert utfil:
    python main.py --url "https://..." --output mitt_resultat.csv
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from sikkerhetsdatablad_agent.database import (
    DEFAULT_DB_PATH,
    get_connection,
    init_db,
    upsert_result,
)
from sikkerhetsdatablad_agent.extractor import extract_texts
from sikkerhetsdatablad_agent.fetcher import FetchError, fetch_pdf
from sikkerhetsdatablad_agent.llm_parser import parse_sds
from sikkerhetsdatablad_agent.models import SDSData
from sikkerhetsdatablad_agent.output import save_results

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Kjernelogikk for ett dokument
# ---------------------------------------------------------------------------


def process_url(url: str) -> Optional[SDSData]:
    """
    Laster ned, leser og parser ett sikkerhetsdatablad fra *url*.
    Returnerer SDSData, eller None ved feil.
    """
    pdf_path: Optional[Path] = None
    try:
        logger.info("Behandler: %s", url)
        pdf_path = fetch_pdf(url)
        extracted = extract_texts(pdf_path)
        result = parse_sds(url, extracted)
        return result

    except FetchError as exc:
        logger.error("Nedlastingsfeil for '%s': %s", url, exc)
        return None
    except ValueError as exc:
        logger.error("PDF-lesefeil for '%s': %s", url, exc)
        return None
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Uventet feil for '%s': %s", url, exc, exc_info=True)
        return None
    finally:
        if pdf_path and pdf_path.exists():
            try:
                os.unlink(pdf_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ekstraher seksjon 14 og revisjonsdato fra sikkerhetsdatablad-PDFer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--url",
        metavar="URL",
        help="URL til ett sikkerhetsdatablad (PDF).",
    )
    group.add_argument(
        "--batch",
        metavar="FIL",
        help="Tekstfil med én URL per linje (tomme linjer og linjer som starter med # ignoreres).",
    )
    parser.add_argument(
        "--output",
        metavar="FIL",
        default="resultater.xlsx",
        help="Utfil (.xlsx eller .csv). Standard: resultater.xlsx",
    )
    parser.add_argument(
        "--db",
        metavar="FIL",
        default=None,
        help=(
            "SQLite databasefil. Standard: sikkerhetsdatablad.db "
            "(kan overstyres med DATABASE_PATH i .env)."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Aktiver DEBUG-logging.",
    )
    return parser


def load_urls_from_file(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        logger.error("Batch-filen '%s' finnes ikke.", path)
        sys.exit(1)
    urls = []
    for line in p.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    if not urls:
        logger.error("Batch-filen '%s' inneholder ingen URLer.", path)
        sys.exit(1)
    return urls


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Bestem URL-liste
    if args.url:
        urls = [args.url]
    else:
        urls = load_urls_from_file(args.batch)

    # Åpne SQLite-database (opprettes automatisk hvis den ikke finnes)
    db_path = args.db or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    db_conn = get_connection(db_path)
    init_db(db_conn)
    logger.info("Database: %s", db_path)

    # Behandle alle URLer
    results: list[SDSData] = []
    failed = 0

    for url in tqdm(urls, desc="Behandler", unit="dok", disable=len(urls) == 1):
        result = process_url(url)
        if result is not None:
            results.append(result)
            # Upsert umiddelbart – sikrer at delresultater lagres selv ved avbrudd
            upsert_result(db_conn, result)
            if len(urls) == 1:
                _print_summary(result)
        else:
            failed += 1

    db_conn.close()

    # Lagre CSV/Excel
    if results:
        save_results(results, args.output)
    else:
        logger.warning("Ingen vellykkede resultater — ingen fil ble lagret.")

    if failed:
        print(
            f"\n{failed} av {len(urls)} dokument(er) feilet. Sjekk loggmeldingene ovenfor."
        )

    sys.exit(0 if not failed else 1)


def _print_summary(result: SDSData) -> None:
    """Skriver ut en lesbar oppsummering for enkelt-URL-modus."""
    s = result.section14
    print("\n" + "=" * 60)
    print(f"  Produkt       : {result.product_name or '(ikke funnet)'}")
    print(f"  Revisjonsdato : {result.revision_date or '(ikke funnet)'}")
    print(f"  14.1 UN-nr    : {s.un_number or '—'}")
    print(f"  14.2 Navn     : {s.proper_shipping_name or '—'}")
    print(f"  14.3 Klasse   : {s.transport_hazard_class or '—'}")
    print(f"  14.3 ADR/RID  : {s.adr_rid_classification_code or '—'}")
    print(f"  14.4 Emb.gr.  : {s.packing_group or '—'}")
    print(f"  14.5 Miljø    : {s.environmental_hazards or '—'}")
    print(f"  14.6 Forholdr.: {s.special_precautions_for_user or '—'}")
    print(f"  14.7 Bulk     : {s.bulk_transport or '—'}")
    if result.notes:
        print(f"  Merknader     : {result.notes}")
    print("=" * 60)


if __name__ == "__main__":
    main()
