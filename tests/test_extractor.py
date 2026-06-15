"""Tests for extractor.py — PDF text extraction and regex patterns."""

from sikkerhetsdatablad_agent.extractor import (
    _SEC14_START,
    _SEC15_START,
    _REVISION_DATE_PATTERNS,
    _find_revision_date_hint,
    _extract_section14_text,
)


class TestSection14Regex:
    """Test the regex patterns that find Section 14 in SDS text."""

    def test_sec14_norwegian_seksjon(self):
        text = "SEKSJON 14: Transportinformasjon\nSome content here"
        assert _SEC14_START.search(text) is not None

    def test_sec14_english_section(self):
        text = "SECTION 14: Transport information\nSome content here"
        assert _SEC14_START.search(text) is not None

    def test_sec14_avsnitt(self):
        text = "AVSNITT 14: Transportopplysninger\nSome content here"
        assert _SEC14_START.search(text) is not None

    def test_sec14_without_prefix(self):
        text = "14 Transportinformasjon\nSome content here"
        assert _SEC14_START.search(text) is not None

    def test_sec14_dot_format(self):
        text = "14. Transportinformasjon\nSome content here"
        assert _SEC14_START.search(text) is not None

    def test_sec14_no_match(self):
        text = "Section 13: Avfallshåndtering\nSome content here"
        assert _SEC14_START.search(text) is None


class TestSection15Regex:
    def test_sec15_norwegian(self):
        text = "SEKSJON 15: Regelverksinformasjon\nSome content here"
        assert _SEC15_START.search(text) is not None

    def test_sec15_english(self):
        text = "SECTION 15: Regulatory information\nSome content here"
        assert _SEC15_START.search(text) is not None


class TestRevisionDateRegex:
    def test_revision_date_norwegian(self):
        text = "Revisjonsdato: 15.03.2024"
        result = _find_revision_date_hint(text)
        assert result == "15.03.2024"

    def test_revision_date_english(self):
        text = "Revision date: 2024-03-15"
        result = _find_revision_date_hint(text)
        assert result == "2024-03-15"

    def test_revision_date_issued(self):
        text = "Utstedt: 01.01.2024"
        result = _find_revision_date_hint(text)
        assert result == "01.01.2024"

    def test_version_date(self):
        text = "Versjonsdato: 12. januar 2023"
        result = _find_revision_date_hint(text)
        assert result is not None
        assert "januar" in result

    def test_no_date(self):
        text = "This document contains no date information whatsoever."
        result = _find_revision_date_hint(text)
        assert result is None


class TestExtractSection14:
    def test_extract_basic(self):
        text = (
            "Some preamble text\n"
            "SEKSJON 14: Transportinformasjon\n"
            "UN1263, Paint, Class 3, PG II\n"
            "SEKSJON 15: Regelverksinformasjon\n"
            "Some regulatory text"
        )
        result = _extract_section14_text(text)
        assert "UN1263" in result
        assert "SEKSJON 14" in result
        assert "SEKSJON 15" not in result

    def test_extract_no_section15(self):
        text = (
            "Some preamble\n"
            "SEKSJON 14: Transportinformasjon\n"
            "UN1263, Paint, Class 3, PG II\n"
            "End of document"
        )
        result = _extract_section14_text(text)
        assert "UN1263" in result
        assert "End of document" in result

    def test_extract_not_found(self):
        text = "This document has no Section 14 at all."
        result = _extract_section14_text(text)
        assert result == ""
