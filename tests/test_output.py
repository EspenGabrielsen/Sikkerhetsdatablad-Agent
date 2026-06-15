"""Tests for output.py — CSV/Excel export."""

import pandas as pd
import pytest

from sikkerhetsdatablad_agent.models import SDSData, Section14
from sikkerhetsdatablad_agent.output import build_dataframe, _COLUMN_HEADERS


class TestBuildDataFrame:
    def test_empty_list(self):
        df = build_dataframe([])
        assert len(df) == 0
        # Should still have the expected columns
        assert set(df.columns) == set(_COLUMN_HEADERS.values())

    def test_single_result(self):
        data = SDSData(
            source_url="https://example.com/test.pdf",
            product_name="Test Product",
            revision_date="2024-01-15",
            section14=Section14(un_number="UN1263"),
        )
        df = build_dataframe([data])
        assert len(df) == 1
        assert df.iloc[0]["Kilde-URL"] == "https://example.com/test.pdf"
        assert df.iloc[0]["Produktnavn"] == "Test Product"
        assert df.iloc[0]["Revisjonsdato"] == "2024-01-15"
        assert df.iloc[0]["14.1 UN-nummer"] == "UN1263"

    def test_multiple_results(self):
        results = [SDSData(source_url=f"https://example.com/{i}.pdf") for i in range(3)]
        df = build_dataframe(results)
        assert len(df) == 3

    def test_norwegian_column_order(self):
        """Verify the Norwegian column headers are in the expected order."""
        data = SDSData(source_url="https://example.com/test.pdf")
        df = build_dataframe([data])
        expected_order = [
            "Kilde-URL",
            "Produktnavn",
            "Revisjonsdato",
            "14.1 UN-nummer",
            "14.2 Offisielt transportnavn",
            "14.3 Transportfareklasse",
            "14.3 ADR/RID-klassifiseringskode",
            "14.4 Emballasjegruppe",
            "14.5 Miljøfarer",
            "14.6 Spesielle forholdsregler",
            "14.7 Bulktransport",
            "Merknader",
        ]
        assert list(df.columns) == expected_order
