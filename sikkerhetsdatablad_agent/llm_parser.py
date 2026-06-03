from __future__ import annotations

import json
import logging
from typing import Optional

from sikkerhetsdatablad_agent.config import PROVIDER, get_model_name, get_openai_client
from sikkerhetsdatablad_agent.extractor import ExtractedTexts
from sikkerhetsdatablad_agent.models import SDSData

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Du er en ekspert på sikkerhetsdatablad (SDS/MSDS) og farlig gods-regelverk (ADR, RID, IMDG, IATA).
Du mottar tekst fra et sikkerhetsdatablad og skal trekke ut strukturert informasjon.

Retningslinjer:
- Svar KUN med de feltene du er bedt om. Ikke legg til fritekst utenfor JSON-skjemaet.
- Hvis et felt ikke finnes i teksten, bruk null.
- Konverter datoer til ISO-format (ÅÅÅÅ-MM-DD) hvis mulig, ellers behold originalformatet.
- For 14.3 transportfareklasse: inkluder eventuelle underklasser, f.eks. "3" eller "3, 6.1".
- Produktnavnet finnes typisk i seksjon 1 (IDENTIFIKASJON) eller i dokumenthoder.
- Revisjonsdatoen finnes typisk som "Revisjonsdato:", "Revision date:", "Utarbeidet:" o.l.
  i dokumentets topptekst, bunntekst, forside eller seksjon 1.
- Skriv av feltverdier på det språket de forekommer i dokumentet (norsk/engelsk).
- Bruk "notes"-feltet til å melde fra om usikkerhet, manglende informasjon eller
  om PDFen ser ut til å være skannet/ulest.
"""


def _build_user_prompt(
    url: str,
    header_text: str,
    section14_text: str,
    revision_date_hint: Optional[str],
) -> str:
    hint_line = (
        f"\n[Regex-hint revisjonsdato: {revision_date_hint}]"
        if revision_date_hint
        else ""
    )

    return f"""\
Kilde-URL: {url}{hint_line}

=== TOPPTEKST / SIDE 1 (for produktnavn og revisjonsdato) ===
{header_text[:3000]}

=== SEKSJON 14 — TRANSPORTINFORMASJON ===
{section14_text[:4000] if section14_text else "(Seksjon 14 ble ikke funnet i dokumentet — sett alle 14.x-felt til null og meld fra i notes)"}

Fyll ut alle feltene i SDSData-skjemaet basert på teksten ovenfor.
"""


def parse_sds(url: str, extracted: ExtractedTexts) -> SDSData:
    """
    Sender tekst til OpenAI og returnerer et strukturert *SDSData*-objekt.
    """
    client = get_openai_client()
    model = get_model_name()

    user_prompt = _build_user_prompt(
        url=url,
        header_text=extracted.header_text,
        section14_text=extracted.section14_text,
        revision_date_hint=extracted.revision_date_hint,
    )

    logger.debug("Sender forespørsel til %s (modell: %s).", PROVIDER, model)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        if PROVIDER == "deepseek":
            result = _parse_with_json_mode(client, model, messages, url)
        else:
            result = _parse_with_structured_output(client, model, messages)
    except Exception as exc:
        logger.error("LLM-kall feilet: %s", exc)
        raise

    result.source_url = url

    # Legg til advarsel hvis skannet PDF
    if extracted.is_scanned:
        warning = "ADVARSEL: PDFen ser ut til å være skannet — tekstutvinning kan være ufullstendig."
        result.notes = f"{warning}\n{result.notes}" if result.notes else warning

    logger.debug(
        "Parset: produkt='%s', revisjonsdato='%s', UN='%s', klasse='%s'",
        result.product_name,
        result.revision_date,
        result.section14.un_number,
        result.section14.transport_hazard_class,
    )

    return result


def _parse_with_structured_output(client, model: str, messages: list) -> SDSData:
    """Bruker OpenAI native structured output (.parse) — for OpenAI og Azure."""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=SDSData,
        temperature=0,
    )
    return response.choices[0].message.parsed


def _parse_with_json_mode(client, model: str, messages: list, url: str) -> SDSData:
    """
    Bruker JSON-modus med manuell Pydantic-parsing — for DeepSeek.
    Legger til JSON-skjema i system-prompten slik at modellen vet hva som forventes.
    """
    schema = SDSData.model_json_schema()
    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

    # Injiser skjema i siste system-melding
    augmented_messages = list(messages)
    augmented_messages[0] = {
        "role": "system",
        "content": messages[0]["content"]
        + f"\n\nSvar med gyldig JSON som passer dette JSON Schema:\n```json\n{schema_str}\n```",
    }

    response = client.chat.completions.create(
        model=model,
        messages=augmented_messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw_json = response.choices[0].message.content
    data = json.loads(raw_json)
    # source_url settes av kalleren
    data.setdefault("source_url", url)
    return SDSData.model_validate(data)
