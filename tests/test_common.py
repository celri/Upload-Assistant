# Tests for COMMON tracker base class
"""
Test suite for COMMON tracker base class utilities.
Covers: check_language_requirements() — coercion, matching, flags.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.trackers.COMMON import COMMON

# ─── Helpers ──────────────────────────────────────────────────


def _config() -> dict[str, Any]:
    return {"DEFAULT": {"tmdb_api": "fake"}, "TRACKERS": {}}


def _run(coro):
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════
#  check_language_requirements() — coercion and matching edge cases
# ═══════════════════════════════════════════════════════════════


class TestCheckLanguageRequirementsEdgeCases:
    """Direct tests of COMMON.check_language_requirements with edge-case inputs."""

    @pytest.fixture
    def common(self):
        return COMMON(config=_config())

    def test_audio_languages_is_string(self, common):
        """audio_languages as a string should be coerced to list."""
        meta = {
            "audio_languages": "French",
            "subtitle_languages": [],
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"], check_audio=True
            ))
        assert result is True

    def test_audio_languages_is_none(self, common):
        """audio_languages = None should be coerced to []."""
        meta = {
            "audio_languages": None,
            "subtitle_languages": [],
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"], check_audio=True
            ))
        assert result is False

    def test_subtitle_languages_is_none(self, common):
        """subtitle_languages = None should be coerced to []."""
        meta = {
            "audio_languages": [],
            "subtitle_languages": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"], check_subtitle=True
            ))
        assert result is False

    def test_no_check_flags_returns_true(self, common):
        """If neither check_audio nor check_subtitle, should return True."""
        meta = {
            "audio_languages": [],
            "subtitle_languages": [],
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"]
            ))
        assert result is True

    def test_require_both_needs_audio_and_subtitle(self, common):
        """require_both=True: having only audio French should fail."""
        meta = {
            "audio_languages": ["French"],
            "subtitle_languages": ["English"],
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"],
                check_audio=True, check_subtitle=True, require_both=True
            ))
        assert result is False

    def test_require_both_passes_when_both_present(self, common):
        meta = {
            "audio_languages": ["French"],
            "subtitle_languages": ["French"],
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"],
                check_audio=True, check_subtitle=True, require_both=True
            ))
        assert result is True

    def test_case_insensitive_matching(self, common):
        """Language matching should be case-insensitive."""
        meta = {
            "audio_languages": ["FRENCH"],
            "subtitle_languages": [],
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"], check_audio=True
            ))
        assert result is True

    def test_mixed_list_with_non_strings(self, common):
        """Non-string elements in audio_languages should be filtered out."""
        meta = {
            "audio_languages": ["French", 42, None, "English"],
            "subtitle_languages": [],
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            result = _run(common.check_language_requirements(
                meta, "TEST", languages_to_check=["french"], check_audio=True
            ))
        assert result is True
