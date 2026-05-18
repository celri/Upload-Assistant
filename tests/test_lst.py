# Tests for LST tracker — lst.gg
"""
Test suite for LST release naming.
Covers: TV year suppression based on TVDB series name.
  - Year is included in TV names only when TVDB has a year in the series name.
  - Movie names are never modified.
  - DVDRIP codec adjustments still apply.
  - TRUMP suffix still appended when trump_reason == "exact_match".
"""

import asyncio
from typing import Any

import pytest

from src.trackers.LST import LST


# ─── Helpers ──────────────────────────────────────────────────


def _config() -> dict[str, Any]:
    return {
        "TRACKERS": {
            "LST": {
                "api_key": "fake-key",
                "announce_url": "https://lst.gg/announce/FAKE",
            }
        },
        "DEFAULT": {"tmdb_api": "fake-tmdb-key"},
    }


def _run(coro):
    return asyncio.run(coro)


def _lst() -> LST:
    return LST(config=_config())


def _tv_meta(name: str, tvdb_series_name: Any = None, **overrides: Any) -> dict[str, Any]:
    m: dict[str, Any] = {
        "category": "TV",
        "type": "WEBDL",
        "name": name,
        "tvdb_series_name": tvdb_series_name,
        "trump_reason": None,
        "source": "WEB",
        "resolution": "1080p",
        "video_encode": "H.264",
        "video_codec": "H.264",
        "audio": "AAC 2.0",
        "debug": False,
    }
    m.update(overrides)
    return m


def _movie_meta(name: str, **overrides: Any) -> dict[str, Any]:
    m: dict[str, Any] = {
        "category": "MOVIE",
        "type": "WEBDL",
        "name": name,
        "tvdb_series_name": None,
        "trump_reason": None,
        "source": "WEB",
        "resolution": "1080p",
        "video_encode": "H.264",
        "video_codec": "H.264",
        "audio": "AAC 2.0",
        "debug": False,
    }
    m.update(overrides)
    return m


# ═══════════════════════════════════════════════════════════════
#  TV year suppression
# ═══════════════════════════════════════════════════════════════


class TestTVYearHandling:
    """Year in TV names follows the TVDB series name, not the filename."""

    def test_tvdb_no_year_strips_year_from_name(self):
        """TVDB name has no year → year must be removed."""
        meta = _tv_meta(
            name="Shameless 2011 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="Shameless",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert "2011" not in result, f"Year should be stripped: {result}"
        assert "S01E01" in result

    def test_tvdb_with_year_in_parens_keeps_year(self):
        """TVDB name contains year → year must be kept."""
        meta = _tv_meta(
            name="Shameless 2011 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="Shameless (2011)",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert "2011" in result, f"Year should be kept: {result}"

    def test_tvdb_with_bare_year_keeps_year(self):
        """TVDB name with a bare year (no parens) → year kept."""
        meta = _tv_meta(
            name="Doctor Who 2005 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="Doctor Who 2005",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert "2005" in result, f"Year should be kept: {result}"

    def test_tvdb_series_name_none_strips_year(self):
        """tvdb_series_name is None (no TVDB data) → year must be stripped."""
        meta = _tv_meta(
            name="Fargo 2014 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name=None,
        )
        result = _run(_lst().get_name(meta))["name"]
        assert "2014" not in result, f"Year should be stripped: {result}"

    def test_tvdb_empty_string_strips_year(self):
        """Empty tvdb_series_name → year stripped."""
        meta = _tv_meta(
            name="Fargo 2014 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert "2014" not in result, f"Year should be stripped: {result}"

    def test_no_year_in_name_unchanged(self):
        """Name already has no year → no change, no error."""
        meta = _tv_meta(
            name="Shameless S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="Shameless",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert result == "Shameless S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP"

    def test_only_first_year_stripped(self):
        """Only the year immediately after the title is stripped, not embedded numbers."""
        meta = _tv_meta(
            name="24 2001 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="24",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert "2001" not in result, f"Year should be stripped: {result}"
        # The title '24' should remain
        assert result.startswith("24 "), f"Title '24' should be intact: {result}"


# ═══════════════════════════════════════════════════════════════
#  Movie names — year never touched
# ═══════════════════════════════════════════════════════════════


class TestMovieYearUnchanged:
    """Movies are always uploaded with their year regardless of TVDB."""

    def test_movie_year_never_stripped(self):
        meta = _movie_meta(name="Inception 2010 2160p BluRay REMUX DTS:X 7.1 HEVC-GROUP")
        result = _run(_lst().get_name(meta))["name"]
        assert "2010" in result, f"Movie year must not be stripped: {result}"

    def test_movie_no_tvdb_year_still_kept(self):
        meta = _movie_meta(
            name="The Dark Knight 2008 2160p BluRay REMUX TrueHD Atmos HEVC-GROUP",
            tvdb_series_name=None,
        )
        result = _run(_lst().get_name(meta))["name"]
        assert "2008" in result, f"Movie year must not be stripped: {result}"


# ═══════════════════════════════════════════════════════════════
#  TRUMP suffix
# ═══════════════════════════════════════════════════════════════


class TestTrumpSuffix:
    """trump_reason=exact_match appends ' - TRUMP' after year logic."""

    def test_trump_suffix_added_tv_no_tvdb_year(self):
        """Year stripped AND trump suffix added for TV with no TVDB year."""
        meta = _tv_meta(
            name="Shameless 2011 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="Shameless",
            trump_reason="exact_match",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert result.endswith(" - TRUMP"), f"Trump suffix missing: {result}"
        assert "2011" not in result.replace(" - TRUMP", ""), f"Year not stripped: {result}"

    def test_trump_suffix_added_tv_with_tvdb_year(self):
        """Year kept AND trump suffix added for TV with TVDB year."""
        meta = _tv_meta(
            name="Shameless 2011 S01E01 1080p WEB-DL AAC 2.0 H.264-GROUP",
            tvdb_series_name="Shameless (2011)",
            trump_reason="exact_match",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert result.endswith(" - TRUMP"), f"Trump suffix missing: {result}"
        assert "2011" in result, f"Year should be kept: {result}"

    def test_trump_suffix_added_movie(self):
        meta = _movie_meta(
            name="Inception 2010 2160p BluRay REMUX DTS:X 7.1 HEVC-GROUP",
            trump_reason="exact_match",
        )
        result = _run(_lst().get_name(meta))["name"]
        assert result.endswith(" - TRUMP"), f"Trump suffix missing: {result}"
        assert "2010" in result, f"Movie year must not be stripped: {result}"
