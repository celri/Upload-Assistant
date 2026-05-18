# Upload Assistant © 2025 Audionut & wastaken7 — Licensed under UAPL v1.0
"""Tests for ULCX tracker."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from src.trackers.ULCX import ULCX


def _run(coro):
    return asyncio.run(coro)


def _config() -> dict[str, Any]:
    return {
        "TRACKERS": {"ULCX": {"api_key": "fake", "announce_url": ""}},
        "DEFAULT": {"tmdb_api": "fake"},
    }


# ═══════════════════════════════════════════════════════════════
#  get_additional_checks() — pre-upload validations
# ═══════════════════════════════════════════════════════════════


class TestULCXAdditionalChecks:
    """ULCX additional checks: service presence/absence for WEBDL and WEBRIP."""

    @pytest.fixture
    def ulcx(self):
        return ULCX(config=_config())

    def _base_meta(self) -> dict[str, Any]:
        return {
            "resolution": "1080p",
            "valid_mi_settings": True,
            "source": "BluRay",
            "type": "ENCODE",
            "service": "",
            "is_disc": None,
            "video_codec": "AVC",
            "keywords": [],
            "language_checked": True,
            "audio_languages": ["English"],
            "subtitle_languages": ["English"],
            "unattended": False,
            "debug": False,
            "personalrelease": False,
            "has_multiple_default_audio_tracks": False,
            "has_multiple_default_subtitle_tracks": False,
            "non_disc_has_pcm_audio_tracks": False,
            "has_disallowed_compat_track": False,
            "discs_missing_certificate": [],
            "combined_genres": "",
        }

    def test_valid_meta_passes(self, ulcx):
        """A well-formed BluRay encode with English audio must pass all checks."""
        meta = self._base_meta()
        assert _run(ulcx.get_additional_checks(meta)) is True

    def test_webdl_with_service_passes(self, ulcx):
        """A WEB-DL with a recognised streaming service must pass the source check."""
        meta = self._base_meta()
        meta["source"] = "Web"
        meta["type"] = "WEBDL"
        meta["service"] = "NF"
        assert _run(ulcx.get_additional_checks(meta)) is True

    def test_webdl_without_service_fails(self, ulcx):
        """A WEB-DL without a streaming service must be rejected."""
        meta = self._base_meta()
        meta["source"] = "Web"
        meta["type"] = "WEBDL"
        meta["service"] = ""
        assert _run(ulcx.get_additional_checks(meta)) is False

    def test_webrip_without_service_fails(self, ulcx):
        """A WEBRip without a streaming service must also be rejected."""
        meta = self._base_meta()
        meta["source"] = "Web"
        meta["type"] = "WEBRIP"
        meta["service"] = ""
        assert _run(ulcx.get_additional_checks(meta)) is False

    def test_webdl_missing_service_prints_red_message(self, ulcx, capsys):
        """When a WEB-DL has no service and not unattended, a red console message must be printed."""
        meta = self._base_meta()
        meta["source"] = "Web"
        meta["type"] = "WEBDL"
        meta["service"] = ""
        with patch("src.trackers.ULCX.console") as mock_console:
            result = _run(ulcx.get_additional_checks(meta))
        assert result is False
        mock_console.print.assert_any_call(
            f"[bold red]Streaming service is missing, skipping {ulcx.tracker} upload.[/bold red]"
        )

    def test_unattended_webdl_missing_service_no_print(self, ulcx):
        """In unattended mode, the service-missing message must be suppressed but upload still skipped."""
        meta = self._base_meta()
        meta["source"] = "Web"
        meta["type"] = "WEBDL"
        meta["service"] = ""
        meta["unattended"] = True
        with patch("src.trackers.ULCX.console") as mock_console:
            result = _run(ulcx.get_additional_checks(meta))
        assert result is False
        for call in mock_console.print.call_args_list:
            assert "Streaming service is missing" not in str(call)
