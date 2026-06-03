from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex-mønstre
# ---------------------------------------------------------------------------

# Finn starten på seksjon 14 (norsk og engelsk, med og uten "SEKSJON"/"SECTION"/"AVSNITT")
_SEC14_START = re.compile(
    r"""
    (?:^|\n)                        # linjestarten
    [\s*•\-]*                       # mulig innrykk/bullets
    (?:SEKSJON|SECTION|Seksjon|Section|Avsnitt|AVSNITT)?  # valgfritt prefiks
    \s*
    14[\s.\-:]+                     # "14" etterfulgt av skilletegn
    (?:Transport(?:informasjon)?    # norsk/engelsk
      |Transport(?:\s+information)?
      |Opplysninger\s+om\s+transport
      |Information\s+for\s+transport
      |Farlig\s+gods
      |TRANSPORTOPPLYSNINGER        # norsk sammensatt ord
      |Transportopplysninger
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Finn starten på seksjon 15 (for å avgrense seksjon 14)
_SEC15_START = re.compile(
    r"""
    (?:^|\n)
    [\s*•\-]*
    (?:SEKSJON|SECTION|Seksjon|Section|Avsnitt|AVSNITT)?
    \s*
    15[\s.\-:]+
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Mønster for å finne revisjonsdato i sidetopp/seksjon 1
_REVISION_DATE_PATTERNS = [
    re.compile(
        r"(?:Revisjonsdato|Revision\s+date|Utarbeidet|Revised?|Date\s+of\s+revision"
        r"|Dato\s+for\s+revisjon|Utstedt|Issued|Oppdatert|Updated?"
        r"|Versjonsdato|Version\s+date)\s*[:\-]?\s*"
        r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}"  # DD.MM.ÅÅÅÅ / DD-MM-YYYY / DD/MM/ÅÅÅÅ
        r"|\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}"  # ÅÅÅÅ-MM-DD
        r"|\d{1,2}\.\s*\w+\s*\d{4}"  # 12. januar 2023
        r")",
        re.IGNORECASE,
    ),
    # Fallback: "Version X, 01.01.2024" eller bare en dato nær "versjon"
    re.compile(
        r"(?:Version|Versjon)\s+\S+\s*[,;]?\s*"
        r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}|\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------------------------
# Dataklasse for resultatet
# ---------------------------------------------------------------------------


@dataclass
class ExtractedTexts:
    """Tekst som sendes videre til LLM-parseren."""

    header_text: str  # Side 1 + header/footer fra alle sider
    section14_text: str  # Teksten fra seksjon 14
    revision_date_hint: Optional[str]  # Pre-ekstrahert dato (kan være None)
    is_scanned: bool = False  # True hvis PDFen ser ut til å være bildebasert


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------


def _extract_header_text(pdf) -> str:
    """
    Returnerer fullteksten fra side 1 og header/footer-lignende linjer
    fra de første 3 sidene. Fokusert og kortfattet for å spare tokens.
    """
    lines: list[str] = []
    max_pages = min(len(pdf.pages), 3)
    for i, page in enumerate(pdf.pages[:max_pages]):
        text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
        if i == 0:
            lines.append(text)
        else:
            # Fra side 2-3: bare de 5 første og 5 siste linjene (header/footer)
            page_lines = [l for l in text.splitlines() if l.strip()]
            lines.extend(page_lines[:5])
            lines.extend(page_lines[-5:])
    return "\n".join(lines)


def _find_revision_date_hint(text: str) -> Optional[str]:
    """Prøver å finne revisjonsdato med regex — returnerer None hvis ikke funnet."""
    for pattern in _REVISION_DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return None


def _extract_section14_text(full_text: str) -> str:
    """
    Finner seksjon 14 i *full_text* og returnerer den som en streng.
    Returnerer tom streng hvis ikke funnet.
    """
    m14 = _SEC14_START.search(full_text)
    if not m14:
        logger.warning("Fant ikke seksjon 14 i dokumentet.")
        return ""

    start = m14.start()
    m15 = _SEC15_START.search(full_text, pos=m14.end())
    end = m15.start() if m15 else len(full_text)

    section_text = full_text[start:end].strip()
    logger.debug("Seksjon 14 funnet: %d tegn.", len(section_text))
    return section_text


# ---------------------------------------------------------------------------
# Offentlig funksjon
# ---------------------------------------------------------------------------


def extract_texts(pdf_path: Path) -> ExtractedTexts:
    """
    Leser PDF-en og returnerer et *ExtractedTexts*-objekt med
    header-tekst og seksjon 14-tekst klar for LLM-parsing.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            "pdfplumber er ikke installert: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        if not pdf.pages:
            raise ValueError(f"PDF-filen '{pdf_path}' inneholder ingen sider.")

        # Sjekk om PDFen er skannet (ingen tekstlag)
        sample_text = pdf.pages[0].extract_text() or ""
        is_scanned = len(sample_text.strip()) < 50

        if is_scanned:
            logger.warning(
                "PDFen ser ut til å være skannet (lite/ingen tekst på side 1). "
                "OCR støttes ikke — resultatene kan bli ufullstendige."
            )

        # Trekk ut header/side 1-tekst
        header_text = _extract_header_text(pdf)

        # Trekk ut fullteksten for seksjonssøk (alle sider, samlet)
        all_pages_text = "\n".join(
            (page.extract_text(x_tolerance=2, y_tolerance=2) or "")
            for page in pdf.pages
        )

    # Finn revisjonsdato med regex
    revision_date_hint = _find_revision_date_hint(header_text)
    if not revision_date_hint:
        # Prøv i fullteksten (seksjon 1 er typisk tidlig)
        first_part = all_pages_text[:3000]
        revision_date_hint = _find_revision_date_hint(first_part)

    # Finn seksjon 14
    section14_text = _extract_section14_text(all_pages_text)

    return ExtractedTexts(
        header_text=header_text,
        section14_text=section14_text,
        revision_date_hint=revision_date_hint,
        is_scanned=is_scanned,
    )
