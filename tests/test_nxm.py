# Tests for NXM tracker — nexum-core.com (Nostradamus)
"""
Test suite for the NXM tracker implementation.
Covers: category mapping, URL configuration,
        and French tracker mixin integration.
"""

import asyncio
from typing import Any

import pytest

from src.trackers.NXM import NXM

# ─── Helpers ──────────────────────────────────────────────────


def _config(extra_tracker: dict[str, Any] | None = None) -> dict[str, Any]:
    tracker_cfg: dict[str, Any] = {
        "api_key": "fake-token",
        "announce_url": "",
        "anon": False,
    }
    if extra_tracker:
        tracker_cfg.update(extra_tracker)
    return {
        "TRACKERS": {"NXM": tracker_cfg},
        "DEFAULT": {"tmdb_api": "fake-tmdb-key"},
    }


def _meta_base(**overrides: Any) -> dict[str, Any]:
    m: dict[str, Any] = {
        "category": "MOVIE",
        "type": "WEBDL",
        "title": "War Machine",
        "year": "2026",
        "resolution": "1080p",
        "source": "WEB",
        "audio": "DDP5.1",
        "video_encode": "x264",
        "video_codec": "AVC",
        "service": "NF",
        "tag": "-FW",
        "edition": "",
        "repack": "",
        "3D": "",
        "uhd": "",
        "hdr": "",
        "season": "",
        "episode": "",
        "part": "",
        "genres": "",
        "keywords": "",
        "anime": False,
        "imdb_id": 1234567,
        "tmdb": 42,
        "debug": False,
        "audio_languages": ["French"],
        "subtitle_languages": [],
        "mediainfo": {},
    }
    m.update(overrides)
    return m


# ═══════════════════════════════════════════════════════════════
#   URL Configuration
# ═══════════════════════════════════════════════════════════════


class TestURLs:
    def test_base_url(self):
        tracker = NXM(_config())
        assert tracker.base_url == "https://nexum-core.com/"

    def test_upload_url(self):
        tracker = NXM(_config())
        assert tracker.upload_url == "https://nexum-core.com/api/v1/upload"

    def test_search_url(self):
        tracker = NXM(_config())
        assert tracker.search_url == "https://nexum-core.com/api/v1/torrents/"

    def test_torrent_url(self):
        tracker = NXM(_config())
        assert tracker.torrent_url == "https://nexum-core.com/torrents/"


# ═══════════════════════════════════════════════════════════════
#   Category mapping
# ═══════════════════════════════════════════════════════════════


class TestGetCategoryId:
    @pytest.mark.parametrize(
        "category,genres,keywords,anime,expected_id",
        [
            # Standard movie → numeric 1 (film)
            ("MOVIE", "", "", False, 1),
            # Standard TV → numeric 2 (serie-tv)
            ("TV", "", "", False, 2),
            # Documentary movie → numeric 3 (documentaire)
            ("MOVIE", "Documentary", "", False, 3),
            # Documentary TV → numeric 3 (documentaire)
            ("TV", "Documentary", "", False, 3),
            # Anime movie → numeric 4 (animation)
            ("MOVIE", "", "", True, 4),
            # Anime TV → numeric 4 (animation-serie)
            ("TV", "", "", True, 4),
            # Concerts → numeric 5 (concerts-spectacles)
            ("TV", "concert", "", False, 5),
            ("MOVIE", "concert", "", False, 5),
        ],
    )

    def test_category_mapping(
        self,
        category: str,
        genres: str,
        keywords: str,
        anime: bool,
        expected_id: int,
    ):
        tracker = NXM(_config())
        meta = _meta_base(category=category, genres=genres, keywords=keywords, anime=anime)
        result = asyncio.run(tracker._get_category(meta))
        assert result == expected_id

# ═══════════════════════════════════════════════════════════════
#   Tracker identity
# ═══════════════════════════════════════════════════════════════


class TestTrackerIdentity:
    def test_tracker_name(self):
        tracker = NXM(_config())
        assert tracker.tracker == "NXM"

    def test_source_flag(self):
        tracker = NXM(_config())
        assert tracker.source_flag == "NXM"

    def test_web_label(self):
        assert NXM.WEB_LABEL == "WEB"

    def test_prefer_original_title(self):
        assert NXM.PREFER_ORIGINAL_TITLE is True

    def test_include_service_in_name(self):
        assert NXM.INCLUDE_SERVICE_IN_NAME is True
