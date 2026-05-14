# Tests for HHD tracker — hd-home.net
"""
Test suite for the HHD tracker implementation.
Covers: English language requirement in get_additional_checks(),
        search_existing() language gate.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.trackers.HHD import HHD

# ─── Helpers ──────────────────────────────────────────────────


def _config() -> dict[str, Any]:
    return {
        "TRACKERS": {"HHD": {"api_key": "fake", "announce_url": ""}},
        "DEFAULT": {"tmdb_api": "fake"},
    }


def _run(coro):
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════
#  English language requirement — get_additional_checks()
# ═══════════════════════════════════════════════════════════════


class TestHHDEnglishLanguageCheck:
    """English language requirement in HHD.get_additional_checks()."""

    @pytest.fixture
    def hhd(self):
        return HHD(config=_config())

    def test_english_audio_passes(self, hhd):
        meta = {
            "audio_languages": ["English"],
            "subtitle_languages": [],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(hhd.get_additional_checks(meta)) is True

    def test_no_english_fails(self, hhd):
        meta = {
            "audio_languages": ["French"],
            "subtitle_languages": [],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(hhd.get_additional_checks(meta)) is False

    def test_english_subtitle_passes(self, hhd):
        meta = {
            "audio_languages": ["French"],
            "subtitle_languages": ["English"],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(hhd.get_additional_checks(meta)) is True

    def test_disc_bdmv_skips_language_check(self, hhd):
        """BDMV/DVD should bypass the English language requirement."""
        meta = {
            "audio_languages": [],
            "subtitle_languages": [],
            "is_disc": "BDMV",
            "type": "DISC",
            "debug": False,
            "unattended": True,
        }
        assert _run(hhd.get_additional_checks(meta)) is True

    def test_disc_dvd_skips_language_check(self, hhd):
        meta = {
            "audio_languages": [],
            "subtitle_languages": [],
            "is_disc": "DVD",
            "type": "DISC",
            "debug": False,
            "unattended": True,
        }
        assert _run(hhd.get_additional_checks(meta)) is True

    def test_dvdrip_blocked(self, hhd):
        """HHD blocks DVDRIP uploads entirely."""
        meta = {
            "audio_languages": ["English"],
            "subtitle_languages": [],
            "is_disc": None,
            "type": "DVDRIP",
            "debug": False,
            "unattended": True,
        }
        assert _run(hhd.get_additional_checks(meta)) is False

    def test_missing_audio_languages_with_english_subs(self, hhd):
        """Missing audio_languages key should still work (defaults to [])."""
        meta = {
            "subtitle_languages": ["English"],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(hhd.get_additional_checks(meta)) is True


# ═══════════════════════════════════════════════════════════════
#  search_existing() language gate
# ═══════════════════════════════════════════════════════════════


class TestHHDSearchExistingLanguageGate:
    """search_existing() sets skipping when English check fails."""

    def test_skips_when_no_english(self):
        hhd = HHD(config=_config())
        meta = {
            "audio_languages": ["French"],
            "subtitle_languages": [],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
            "tracker_status": {},
            "skipping": None,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            dupes = _run(hhd.search_existing(meta, ""))
        assert dupes == []
        assert meta["skipping"] == "HHD"
