from __future__ import annotations

import logging
import time
from pathlib import Path
import tempfile

import requests

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # sekunder
_TIMEOUT = 30  # sekunder per forsøk
_MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB


class FetchError(Exception):
    """Kastes ved nedlastingsfeil som ikke kan gjenopprettes."""


def fetch_pdf(url: str) -> Path:
    """
    Laster ned PDF fra *url* og lagrer den i en midlertidig fil.

    Returnerer Path til den midlertidige filen.
    Kaller er ansvarlig for å slette filen etter bruk (eller bruke tempfile.TemporaryDirectory).
    """
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.debug("Forsøk %d/%d: GET %s", attempt, _MAX_RETRIES, url)
            response = requests.get(url, timeout=_TIMEOUT, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                # Noen APIer sender application/octet-stream — vi prøver likevel.
                # Bare kast hvis det er åpenbart HTML/JSON (feilmelding fra server).
                if "html" in content_type.lower() or "json" in content_type.lower():
                    raise FetchError(
                        f"Forventet PDF, fikk Content-Type: '{content_type}'. "
                        f"Sjekk at URL-en peker på et sikkerhetsdatablad."
                    )
                logger.warning(
                    "Uventet Content-Type '%s' — fortsetter og håper det er en PDF.",
                    content_type,
                )

            # Les innholdet med størrelsesgrense
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > _MAX_PDF_BYTES:
                    raise FetchError(
                        f"PDF er større enn {_MAX_PDF_BYTES // (1024*1024)} MB — avbryter."
                    )
                chunks.append(chunk)

            data = b"".join(chunks)

            # Lagre til temp-fil med .pdf-endelse (pdfplumber trenger det ikke,
            # men gjør debugging enklere)
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", delete=False, prefix="sds_"
            )
            tmp.write(data)
            tmp.close()
            logger.debug("PDF lagret i '%s' (%d bytes)", tmp.name, len(data))
            return Path(tmp.name)

        except FetchError:
            raise  # Ikke retry på logiske feil
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE**attempt
                logger.warning(
                    "Nedlasting feilet (forsøk %d/%d): %s — venter %ds.",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                time.sleep(wait)

    raise FetchError(
        f"Klarte ikke laste ned PDF fra '{url}' etter {_MAX_RETRIES} forsøk: {last_exc}"
    )
