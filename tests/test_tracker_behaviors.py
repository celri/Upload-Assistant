# Tests for per-tracker behavior attributes: skip_nfo, notag_label, language checks.
"""
Edge-case test suite for the three per-tracker behavior features:
  1. skip_nfo   — class attr driving nfo_skip_trackers frozenset
  2. notag_label — class attr driving notag_labels dict + get_name() tag replacement
  3. get_additional_checks() — language requirement gates in search_existing()
"""

import asyncio
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trackers.COMMON import COMMON


def _run(coro):
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════
#  1. skip_nfo — dynamic frozenset construction
# ═══════════════════════════════════════════════════════════════


class TestSkipNfoDynamicSet:
    """Verify nfo_skip_trackers is built correctly from class attrs."""

    def test_known_skip_nfo_members(self):
        from src.trackersetup import nfo_skip_trackers
        expected = {"DP", "FNP", "HHD", "IHD", "LST", "LUME", "STC", "ULCX"}
        assert nfo_skip_trackers == expected

    def test_is_frozenset(self):
        from src.trackersetup import nfo_skip_trackers
        assert isinstance(nfo_skip_trackers, frozenset)

    def test_trackers_without_attr_excluded(self):
        """Trackers that don't define skip_nfo should not be in the set."""
        from src.trackersetup import nfo_skip_trackers, tracker_class_map
        # AITHER has no skip_nfo attr — should not be in set
        assert "AITHER" not in nfo_skip_trackers
        assert not getattr(tracker_class_map["AITHER"], "skip_nfo", False)

    def test_skip_nfo_false_excluded(self):
        """A tracker with skip_nfo = False should not be in the set."""
        from src.trackersetup import tracker_class_map
        # BLU inherits from UNIT3D, has no skip_nfo — getattr defaults to False
        assert not getattr(tracker_class_map["BLU"], "skip_nfo", False)

    def test_getattr_robustness(self):
        """getattr(cls, 'skip_nfo', False) handles missing, False, 0, None, ''."""
        class NoAttr:
            pass

        class ExplicitFalse:
            skip_nfo = False

        class ExplicitZero:
            skip_nfo = 0

        class ExplicitNone:
            skip_nfo = None

        class ExplicitEmpty:
            skip_nfo = ""

        class ExplicitTrue:
            skip_nfo = True

        for cls in (NoAttr, ExplicitFalse, ExplicitZero, ExplicitNone, ExplicitEmpty):
            assert not getattr(cls, "skip_nfo", False), f"{cls.__name__} should be falsy"
        assert getattr(ExplicitTrue, "skip_nfo", False)


class TestGetAdditionalFilesSkipNfo:
    """Trackers with skip_nfo=True should return {} from get_additional_files."""

    @pytest.fixture
    def meta(self, tmp_path):
        return {
            "base_dir": str(tmp_path),
            "uuid": "test-uuid",
            "debug": False,
        }

    @pytest.mark.parametrize("tracker_name", ["DP", "FNP", "HHD", "IHD", "LST", "LUME", "STC", "ULCX"])
    def test_get_additional_files_returns_empty(self, tracker_name, meta):
        """skip_nfo trackers that override get_additional_files must return {}."""
        from src.trackersetup import tracker_class_map
        cfg = {
            "TRACKERS": {tracker_name: {"api_key": "fake", "announce_url": ""}},
            "DEFAULT": {"tmdb_api": "fake"},
        }
        tracker = tracker_class_map[tracker_name](config=cfg)
        result = _run(tracker.get_additional_files(meta))
        assert result == {}


# ═══════════════════════════════════════════════════════════════
#  2. notag_label — dynamic dict construction + get_name() tag handling
# ═══════════════════════════════════════════════════════════════


class TestNotagLabelsDynamicDict:
    """Verify notag_labels dict is built correctly from class attrs."""

    def test_known_notag_members(self):
        from src.trackersetup import notag_labels
        expected = {"C411": "NOTAG", "FNP": "NOGROUP", "G3MINI": "NoGrP", "GF": "NoTag", "NXM": "NoGrp"}
        assert notag_labels == expected

    def test_empty_string_excluded(self):
        """notag_label = '' should not appear in the dict."""
        from src.trackersetup import notag_labels
        # FrenchTrackerMixin default is notag_label = "" — should not leak
        assert all(v for v in notag_labels.values()), "No empty labels allowed"

    def test_trackers_without_attr_excluded(self):
        """Trackers without notag_label attr should not be in the dict."""
        from src.trackersetup import notag_labels, tracker_class_map
        # BLU has no notag_label
        assert "BLU" not in notag_labels
        assert not getattr(tracker_class_map["BLU"], "notag_label", "")

    def test_getattr_robustness_notag(self):
        """getattr(cls, 'notag_label', '') handles missing, '', None, False."""
        class NoAttr:
            pass

        class EmptyStr:
            notag_label = ""

        class NoneVal:
            notag_label = None

        class FalseVal:
            notag_label = False

        class ValidLabel:
            notag_label = "TEST"

        for cls in (NoAttr, EmptyStr):
            assert not getattr(cls, "notag_label", ""), f"{cls.__name__} should be empty/falsy"
        # None and False are truthy in getattr but falsy in bool — our filter uses `if` so they're excluded
        assert getattr(NoneVal, "notag_label", "") is None  # attr exists, returns None
        assert getattr(FalseVal, "notag_label", "") is False  # attr exists, returns False
        assert getattr(ValidLabel, "notag_label", "") == "TEST"


# ── Tag replacement edge cases in get_name() ──


def _make_cfg(tracker_name):
    return {
        "TRACKERS": {tracker_name: {"api_key": "fake", "announce_url": ""}},
        "DEFAULT": {"tmdb_api": "fake"},
    }


class TestFrenchMixinNotagGetName:
    """Tag replacement in FrenchTrackerMixin.get_name() (used by C411, NXM, etc.)."""

    @pytest.fixture
    def c411(self):
        from src.trackers.C411 import C411
        return C411(config=_make_cfg("C411"))

    def _base_meta(self, **overrides):
        m = {
            "category": "MOVIE",
            "type": "WEBDL",
            "title": "Le Prenom",
            "year": "2012",
            "resolution": "1080p",
            "source": "WEB",
            "audio": "AC3",
            "video_encode": "x264",
            "service": "",
            "edition": "",
            "repack": "",
            "3D": "",
            "uhd": "",
            "hdr": "",
            "webdv": "",
            "part": "",
            "season": "",
            "episode": "",
            "is_disc": None,
            "search_year": "",
            "manual_year": None,
            "manual_date": None,
            "no_season": False,
            "no_year": False,
            "no_aka": False,
            "debug": False,
            "tv_pack": 0,
            "imdb_info": {"aka": "", "original_language": "fr"},
            "mediainfo": {},
            "audio_languages": ["French"],
            "subtitle_languages": [],
        }
        m.update(overrides)
        return m

    def test_valid_tag_unchanged(self, c411):
        """A valid tag like '-Troxy' should remain as-is."""
        meta = self._base_meta(tag="-Troxy")
        result = _run(c411.get_name(meta))
        assert result["name"].endswith("-Troxy")

    def test_empty_tag_replaced(self, c411):
        """Empty tag '' should be replaced with NOTAG."""
        meta = self._base_meta(tag="")
        result = _run(c411.get_name(meta))
        assert result["name"].endswith("-NOTAG")

    def test_dash_only_tag_replaced(self, c411):
        """Tag '-' (dash only, empty group) should be replaced with NOTAG."""
        meta = self._base_meta(tag="-")
        result = _run(c411.get_name(meta))
        assert result["name"].endswith("-NOTAG")

    def test_nogrp_tag_replaced(self, c411):
        """Tag '-NOGRP' should be replaced with NOTAG."""
        meta = self._base_meta(tag="-NOGRP")
        result = _run(c411.get_name(meta))
        assert "-NOGRP" not in result["name"]
        assert result["name"].endswith("-NOTAG")

    def test_nogroup_tag_replaced(self, c411):
        """Tag '-NOGROUP' should be replaced."""
        meta = self._base_meta(tag="-NOGROUP")
        result = _run(c411.get_name(meta))
        assert "-NOGROUP" not in result["name"]
        assert result["name"].endswith("-NOTAG")

    def test_unknown_tag_replaced(self, c411):
        """Tag '-Unknown' should be replaced."""
        meta = self._base_meta(tag="-Unknown")
        result = _run(c411.get_name(meta))
        assert "-Unknown" not in result["name"]
        assert result["name"].endswith("-NOTAG")


class TestG3MININotagGetName:
    """Tag replacement in G3MINI.get_name()."""

    @pytest.fixture
    def g3mini(self):
        from src.trackers.G3MINI import G3MINI
        return G3MINI(config=_make_cfg("G3MINI"))

    def _base_meta(self, **overrides):
        m = {
            "category": "MOVIE",
            "type": "WEBDL",
            "title": "Chainsaw Man",
            "year": "2024",
            "resolution": "1080p",
            "source": "WEB",
            "audio": "AAC",
            "video_encode": "x264",
            "video_codec": "",
            "service": "",
            "tag": "-GRP",
            "edition": "",
            "repack": "",
            "3D": "",
            "uhd": "",
            "hdr": "",
            "webdv": "",
            "part": "",
            "season": "",
            "episode": "",
            "is_disc": None,
            "search_year": "",
            "manual_year": None,
            "manual_date": None,
            "no_season": False,
            "no_year": False,
            "no_aka": False,
            "debug": False,
            "tv_pack": 0,
            "imdb_info": {"aka": "", "original_language": "ja"},
            "mediainfo": {},
            "audio_languages": ["French"],
            "subtitle_languages": [],
        }
        m.update(overrides)
        return m

    def test_valid_tag_unchanged(self, g3mini):
        meta = self._base_meta(tag="-GRP")
        result = _run(g3mini.get_name(meta))
        assert result["name"].endswith("-GRP")

    def test_empty_tag_uses_nogrp_label(self, g3mini):
        meta = self._base_meta(tag="")
        result = _run(g3mini.get_name(meta))
        assert result["name"].endswith("-NoGrP")

    def test_nogrp_tag_replaced(self, g3mini):
        meta = self._base_meta(tag="-NoGrp")
        result = _run(g3mini.get_name(meta))
        assert result["name"].endswith("-NoGrP")


class TestGFNotagGetName:
    """Tag replacement in GF.get_name() (uses uuid-based name)."""

    @pytest.fixture
    def gf(self):
        from src.trackers.GF import GF
        return GF(config=_make_cfg("GF"))

    def test_valid_uuid_tag_unchanged(self, gf):
        meta = {"uuid": "Movie.2024.1080p.WEB.x264-GRP.mkv", "tag": "-GRP"}
        result = _run(gf.get_name(meta))
        assert "GRP" in result["name"]

    def test_empty_tag_replaced(self, gf):
        meta = {"uuid": "Movie.2024.1080p.WEB.x264.mkv", "tag": ""}
        result = _run(gf.get_name(meta))
        assert result["name"].endswith("-NoTag")

    def test_nogrp_tag_replaced(self, gf):
        meta = {"uuid": "Movie.2024.1080p.WEB.x264-NoGrp.mkv", "tag": "-NoGrp"}
        result = _run(gf.get_name(meta))
        assert "-NoGrp" not in result["name"]
        assert result["name"].endswith("-NoTag")


class TestFNPNotagGetName:
    """Tag replacement in FNP.get_name()."""

    @pytest.fixture
    def fnp(self):
        from src.trackers.FNP import FNP
        return FNP(config=_make_cfg("FNP"))

    def test_valid_tag_unchanged(self, fnp):
        meta = {"name": "Movie 2024 1080p WEB x264-GRP", "tag": "-GRP"}
        result = _run(fnp.get_name(meta))
        # FNP with a valid tag should keep the original name
        assert "GRP" in result["name"]

    def test_empty_tag_replaced(self, fnp):
        meta = {"name": "Movie 2024 1080p WEB x264", "tag": ""}
        result = _run(fnp.get_name(meta))
        assert result["name"].endswith("-NOGROUP")

    def test_nogrp_tag_replaced(self, fnp):
        meta = {"name": "Movie 2024 1080p WEB x264-NoGrp", "tag": "-NoGrp"}
        result = _run(fnp.get_name(meta))
        assert "-NoGrp" not in result["name"]
        assert "NOGROUP" in result["name"]


# ═══════════════════════════════════════════════════════════════
#  3. Language checks — get_additional_checks() edge cases
# ═══════════════════════════════════════════════════════════════


class TestFrenchLanguageCheck:
    """French language requirement in FrenchTrackerMixin.get_additional_checks()."""

    @pytest.fixture
    def c411(self):
        from src.trackers.C411 import C411
        return C411(config=_make_cfg("C411"))

    def test_french_audio_passes(self, c411):
        meta = {
            "audio_languages": ["French"],
            "subtitle_languages": [],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is True

    def test_french_subtitle_passes(self, c411):
        meta = {
            "audio_languages": ["English"],
            "subtitle_languages": ["French"],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is True

    def test_no_french_at_all_fails(self, c411):
        meta = {
            "audio_languages": ["English"],
            "subtitle_languages": ["English"],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is False

    def test_empty_audio_languages_with_french_subs(self, c411):
        meta = {
            "audio_languages": [],
            "subtitle_languages": ["French"],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is True

    def test_missing_audio_languages_key(self, c411):
        """If audio_languages key is absent, COMMON._coerce_language_values returns []."""
        meta = {
            "subtitle_languages": ["French"],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is True

    def test_missing_subtitle_languages_key(self, c411):
        """If subtitle_languages key is absent, check_language_requirements uses []."""
        meta = {
            "audio_languages": ["French"],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is True

    def test_both_languages_missing_fails(self, c411):
        """If neither audio nor subtitle language keys exist, should fail."""
        meta = {
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is False

    def test_french_variant_fra_passes(self, c411):
        """ISO 639-2 'fra' should be accepted."""
        meta = {
            "audio_languages": ["fra"],
            "subtitle_languages": [],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is True

    def test_french_variant_fr_passes(self, c411):
        """ISO 639-1 'fr' should be accepted."""
        meta = {
            "audio_languages": ["fr"],
            "subtitle_languages": [],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is True

    def test_empty_both_lists_fails(self, c411):
        """Empty lists for both audio and subtitle should fail."""
        meta = {
            "audio_languages": [],
            "subtitle_languages": [],
            "is_disc": None,
            "debug": False,
            "unattended": True,
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(c411.get_additional_checks(meta)) is False


class TestEnglishLanguageCheck:
    """English language requirement in HHD/STC get_additional_checks()."""

    @pytest.fixture
    def hhd(self):
        from src.trackers.HHD import HHD
        return HHD(config={
            "TRACKERS": {"HHD": {"api_key": "fake", "announce_url": ""}},
            "DEFAULT": {"tmdb_api": "fake"},
        })

    @pytest.fixture
    def stc(self):
        from src.trackers.STC import STC
        return STC(config={
            "TRACKERS": {"STC": {"api_key": "fake", "announce_url": ""}},
            "DEFAULT": {"tmdb_api": "fake"},
        })

    def test_hhd_english_audio_passes(self, hhd):
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

    def test_hhd_no_english_fails(self, hhd):
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

    def test_hhd_english_subtitle_passes(self, hhd):
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

    def test_hhd_disc_skips_language_check(self, hhd):
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

    def test_hhd_dvd_skips_language_check(self, hhd):
        meta = {
            "audio_languages": [],
            "subtitle_languages": [],
            "is_disc": "DVD",
            "type": "DISC",
            "debug": False,
            "unattended": True,
        }
        assert _run(hhd.get_additional_checks(meta)) is True

    def test_hhd_dvdrip_blocked(self, hhd):
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

    def test_hhd_missing_audio_languages(self, hhd):
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

    def test_stc_english_audio_passes(self, stc):
        meta = {
            "category": "TV",
            "audio_languages": ["English"],
            "subtitle_languages": [],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
            "keywords": "",
            "combined_genres": "",
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(stc.get_additional_checks(meta)) is True

    def test_stc_no_english_fails(self, stc):
        meta = {
            "category": "TV",
            "audio_languages": ["French"],
            "subtitle_languages": [],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
            "keywords": "",
            "combined_genres": "",
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            assert _run(stc.get_additional_checks(meta)) is False

    def test_stc_disc_skips_language_check(self, stc):
        meta = {
            "category": "TV",
            "audio_languages": [],
            "subtitle_languages": [],
            "is_disc": "BDMV",
            "type": "DISC",
            "debug": False,
            "unattended": True,
            "keywords": "",
            "combined_genres": "",
        }
        assert _run(stc.get_additional_checks(meta)) is True

    def test_stc_movie_rejected(self, stc):
        """STC only accepts TV uploads."""
        meta = {
            "category": "MOVIE",
            "audio_languages": ["English"],
            "subtitle_languages": [],
            "is_disc": None,
            "type": "WEBDL",
            "debug": False,
            "unattended": True,
            "keywords": "",
            "combined_genres": "",
        }
        assert _run(stc.get_additional_checks(meta)) is False


# ═══════════════════════════════════════════════════════════════
#  4. COMMON.check_language_requirements — coercion edge cases
# ═══════════════════════════════════════════════════════════════


class TestCheckLanguageRequirementsEdgeCases:
    """Direct tests of COMMON.check_language_requirements with edge-case inputs."""

    @pytest.fixture
    def common(self):
        return COMMON(config={"DEFAULT": {"tmdb_api": "fake"}, "TRACKERS": {}})

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


# ═══════════════════════════════════════════════════════════════
#  5. Integration: search_existing → get_additional_checks gate
# ═══════════════════════════════════════════════════════════════


class TestSearchExistingLanguageGate:
    """Verify search_existing() early-exits when language check fails."""

    def _make_tracker(self, tracker_name):
        cfg = _make_cfg(tracker_name)
        from src.trackersetup import tracker_class_map
        return tracker_class_map[tracker_name](config=cfg)

    def test_unit3d_search_existing_skips_on_failed_check(self):
        """UNIT3D.search_existing should set meta['skipping'] when get_additional_checks returns False."""
        hhd = self._make_tracker("HHD")
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

    def test_c411_search_existing_skips_on_no_french(self):
        """C411.search_existing should skip when no French audio/subtitle."""
        c411 = self._make_tracker("C411")
        meta = {
            "audio_languages": ["English"],
            "subtitle_languages": ["English"],
            "is_disc": None,
            "debug": False,
            "unattended": True,
            "tracker_status": {},
            "skipping": None,
            "imdb_id": "tt1234567",
        }
        with patch("src.trackers.COMMON.languages_manager") as mock_lm:
            mock_lm.process_desc_language = AsyncMock()
            dupes = _run(c411.search_existing(meta, ""))
        assert dupes == []
        assert meta["skipping"] == "C411"
