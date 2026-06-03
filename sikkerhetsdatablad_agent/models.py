from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Section14(BaseModel):
    """Seksjon 14 — Transportinformasjon (ADR/RID/IMDG/IATA)."""

    un_number: Optional[str] = Field(
        None,
        description="14.1 UN-nummer, f.eks. 'UN1263'. Null hvis ikke farlig gods.",
    )
    proper_shipping_name: Optional[str] = Field(
        None,
        description="14.2 Offisielt transportnavn (Proper Shipping Name).",
    )
    transport_hazard_class: Optional[str] = Field(
        None,
        description=(
            "14.3 Transportfareklasse(r), f.eks. '3' eller '3, 6.1'. "
            "Inkluder eventuelle underklasser separert med komma."
        ),
    )
    packing_group: Optional[str] = Field(
        None,
        description="14.4 Emballasjegruppe (Packing Group), f.eks. 'II' eller 'III'.",
    )
    environmental_hazards: Optional[str] = Field(
        None,
        description=(
            "14.5 Miljøfarer. Typisk 'Ja' / 'Nei' / 'Marin forurensning: Ja'. "
            "Gjengi det som står i dokumentet."
        ),
    )
    special_precautions_for_user: Optional[str] = Field(
        None,
        description="14.6 Spesielle forholdsregler for bruker.",
    )
    bulk_transport: Optional[str] = Field(
        None,
        description=(
            "14.7 Bulktransport i henhold til MARPOL vedlegg II og IBC-koden. "
            "Typisk 'Ikke relevant' eller en kort beskrivelse."
        ),
    )


class SDSData(BaseModel):
    """Komplett strukturert uttak fra ett sikkerhetsdatablad."""

    source_url: str = Field(description="URL-en PDFen ble hentet fra.")
    product_name: Optional[str] = Field(
        None, description="Produktnavn slik det fremgår av seksjon 1 eller forsiden."
    )
    revision_date: Optional[str] = Field(
        None,
        description=(
            "Revisjonsdato / utstedelsesdato for sikkerhetsdatabladet. "
            "Formater som ISO-dato ÅÅÅÅ-MM-DD hvis mulig, ellers gjengi originalteksten."
        ),
    )
    section14: Section14 = Field(
        default_factory=Section14,
        description="Strukturerte data fra seksjon 14.",
    )
    notes: Optional[str] = Field(
        None,
        description=(
            "Eventuelle kommentarer, usikkerheter eller manglende informasjon "
            "som LLM-en vil gjøre oppmerksom på."
        ),
    )

    def to_flat_dict(self) -> dict:
        """Flater ut modellen til én rad egnet for CSV/Excel."""
        return {
            "source_url": self.source_url,
            "product_name": self.product_name,
            "revision_date": self.revision_date,
            "un_number": self.section14.un_number,
            "proper_shipping_name": self.section14.proper_shipping_name,
            "transport_hazard_class": self.section14.transport_hazard_class,
            "packing_group": self.section14.packing_group,
            "environmental_hazards": self.section14.environmental_hazards,
            "special_precautions_for_user": self.section14.special_precautions_for_user,
            "bulk_transport": self.section14.bulk_transport,
            "notes": self.notes,
        }
