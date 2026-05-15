# Tests for IHD tracker — iheartdrama.org
"""
Test suite for the IHD tracker implementation.
Covers: edition stripping for non-Full Disc types in get_name().
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.trackers.IHD import IHD

# ─── Helpers ──────────────────────────────────────────────────


def _config() -> dict[str, Any]:
    return {
        "TRACKERS": {"IHD": {"api_key": "fake", "announce_url": ""}},
        "DEFAULT": {"tmdb_api": "fake"},
    }


def _run(coro):
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════
#  get_name() — edition stripping for non-Full Disc types
# ═══════════════════════════════════════════════════════════════


class TestIHDGetNameEdition:
    """IHD naming guide: Edition is omitted for non-Full Disc types."""

    @pytest.fixture
    def ihd(self):
        return IHD(config=_config())

    def _run_get_name(self, ihd, meta):
        with patch("src.trackers.IHD.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            mock_lm.has_english_language = AsyncMock(return_value=True)
            return _run(ihd.get_name(meta))

    def test_encode_strips_edition(self, ihd):
        """Regression: RESTORED must be removed from an encode title (IHD staff rejection)."""
        meta = {
            "name": "Seven Samurai AKA Shichinin no samurai 1954 RESTORED REPACK 1080p BluRay AAC 1.0 x264-hallowed",
            "resolution": "1080p",
            "edition": "RESTORED",
            "is_disc": None,
            "type": "ENCODE",
            "language_checked": True,
            "audio_languages": ["Japanese"],
        }
        with patch("src.trackers.IHD.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            mock_lm.has_english_language = AsyncMock(return_value=False)
            result = _run(ihd.get_name(meta))
        assert "RESTORED" not in result["name"]
        assert "Seven Samurai" in result["name"]
        assert "1080p" in result["name"]

    def test_webdl_strips_edition(self, ihd):
        """Edition must also be stripped for WEB-DL releases."""
        meta = {
            "name": "Some Film 2020 Remastered 1080p AMZN WEB-DL AAC 2.0 x264-GRP",
            "resolution": "1080p",
            "edition": "Remastered",
            "is_disc": None,
            "type": "WEBDL",
            "language_checked": True,
            "audio_languages": ["English"],
        }
        result = self._run_get_name(ihd, meta)
        assert "Remastered" not in result["name"]
        assert "Some Film" in result["name"]

    def test_remux_strips_edition(self, ihd):
        """Edition must also be stripped for REMUX releases (non-Full Disc)."""
        meta = {
            "name": "Some Film 2020 Extended 1080p BluRay REMUX DTS 5.1 AVC-GRP",
            "resolution": "1080p",
            "edition": "Extended",
            "is_disc": None,
            "type": "REMUX",
            "language_checked": True,
            "audio_languages": ["English"],
        }
        result = self._run_get_name(ihd, meta)
        assert "Extended" not in result["name"]
        assert "Some Film" in result["name"]

    def test_bdmv_keeps_edition(self, ihd):
        """Full Disc (BDMV) releases must keep their edition."""
        meta = {
            "name": "Some Film 2020 Collector Edition Blu-ray AVC DTS-HD MA 5.1-GRP",
            "resolution": "1080p",
            "edition": "Collector Edition",
            "is_disc": "BDMV",
            "type": "DISC",
            "language_checked": True,
            "audio_languages": ["English"],
        }
        result = self._run_get_name(ihd, meta)
        assert "Collector Edition" in result["name"]

    def test_dvd_keeps_edition(self, ihd):
        """Full Disc (DVD) releases must keep their edition."""
        meta = {
            "name": "Some Film 2020 Director's Cut DVD AC3 2.0-GRP",
            "resolution": "576p",
            "edition": "Director's Cut",
            "is_disc": "DVD",
            "type": "DISC",
            "language_checked": True,
            "audio_languages": ["English"],
        }
        result = self._run_get_name(ihd, meta)
        assert "Director's Cut" in result["name"]

    def test_no_edition_name_unchanged(self, ihd):
        """When edition is empty, name must not be altered."""
        original = "Some Film 2020 1080p BluRay AAC 2.0 x264-GRP"
        meta = {
            "name": original,
            "resolution": "1080p",
            "edition": "",
            "is_disc": None,
            "type": "ENCODE",
            "language_checked": True,
            "audio_languages": ["English"],
        }
        result = self._run_get_name(ihd, meta)
        assert result["name"] == original

    def test_foreign_language_prefix_applied_after_edition_strip(self, ihd):
        """Language prefix must be inserted at the right position even when edition was stripped."""
        meta = {
            "name": "Seven Samurai AKA Shichinin no samurai 1954 RESTORED REPACK 1080p BluRay AAC 1.0 x264-hallowed",
            "resolution": "1080p",
            "edition": "RESTORED",
            "is_disc": None,
            "type": "ENCODE",
            "language_checked": True,
            "audio_languages": ["Japanese"],
        }
        with patch("src.trackers.IHD.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            mock_lm.has_english_language = AsyncMock(return_value=False)
            result = _run(ihd.get_name(meta))
        assert "RESTORED" not in result["name"]
        assert "JAPANESE 1080p" in result["name"]


# ═══════════════════════════════════════════════════════════════
#  get_name() — service token preservation (MGMP / MGM+)
# ═══════════════════════════════════════════════════════════════


class TestIHDGetNameService:
    """IHD naming: service tokens such as MGMP must be preserved in the output name."""

    @pytest.fixture
    def ihd(self):
        return IHD(config=_config())

    def test_mgmp_preserved_in_webdl_name(self, ihd):
        """Back to the Future (MGMP WEB-DL) must keep the MGMP service token."""
        meta = {
            "name": "Back to the Future 1985 1080p MGMP WEB-DL DD+ 5.1 H.264-PiRaTeS",
            "resolution": "1080p",
            "edition": "",
            "is_disc": None,
            "type": "WEBDL",
            "language_checked": True,
            "audio_languages": ["English"],
        }
        with patch("src.trackers.IHD.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            mock_lm.has_english_language = AsyncMock(return_value=True)
            result = _run(ihd.get_name(meta))
        assert result["name"] == "Back to the Future 1985 1080p MGMP WEB-DL DD+ 5.1 H.264-PiRaTeS"
