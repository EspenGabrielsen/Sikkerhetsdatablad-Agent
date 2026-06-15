"""Tests for models.py — Pydantic data models."""

from sikkerhetsdatablad_agent.models import SDSData, Section14


class TestSection14:
    def test_default_values(self):
        """Section14 should have all fields as None by default."""
        s = Section14()
        assert s.un_number is None
        assert s.proper_shipping_name is None
        assert s.transport_hazard_class is None
        assert s.adr_rid_classification_code is None
        assert s.packing_group is None
        assert s.environmental_hazards is None
        assert s.special_precautions_for_user is None
        assert s.bulk_transport is None

    def test_with_values(self):
        s = Section14(
            un_number="UN1263",
            proper_shipping_name="Paint",
            transport_hazard_class="3",
            packing_group="II",
        )
        assert s.un_number == "UN1263"
        assert s.proper_shipping_name == "Paint"
        assert s.transport_hazard_class == "3"
        assert s.packing_group == "II"


class TestSDSData:
    def test_default_section14(self):
        """SDSData should create an empty Section14 by default."""
        data = SDSData(source_url="https://example.com/test.pdf")
        assert data.source_url == "https://example.com/test.pdf"
        assert data.product_name is None
        assert data.revision_date is None
        assert data.notes is None
        assert isinstance(data.section14, Section14)

    def test_to_flat_dict(self):
        data = SDSData(
            source_url="https://example.com/test.pdf",
            product_name="Test Product",
            revision_date="2024-01-15",
            section14=Section14(un_number="UN1263"),
            notes="Test note",
        )
        flat = data.to_flat_dict()
        assert flat["source_url"] == "https://example.com/test.pdf"
        assert flat["product_name"] == "Test Product"
        assert flat["revision_date"] == "2024-01-15"
        assert flat["un_number"] == "UN1263"
        assert flat["notes"] == "Test note"

    def test_to_flat_dict_all_fields(self):
        """Verify all fields are present in flat dict."""
        data = SDSData(source_url="https://example.com/test.pdf")
        flat = data.to_flat_dict()
        expected_keys = {
            "source_url",
            "product_name",
            "revision_date",
            "un_number",
            "proper_shipping_name",
            "transport_hazard_class",
            "adr_rid_classification_code",
            "packing_group",
            "environmental_hazards",
            "special_precautions_for_user",
            "bulk_transport",
            "notes",
        }
        assert set(flat.keys()) == expected_keys
