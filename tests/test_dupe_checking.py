# Tests for DupeChecker.filter_dupes — filename match logic
"""
Regression tests for the dupe-detection behaviour in DupeChecker.filter_dupes:

  • A filename match alone (without a matching file count) must be enough to:
      1. Keep the entry as a dupe (process_exclusion returns False).
      2. Set meta["filename_match"].
  • When both filename AND count match, meta["file_count_match"] must also be set.
  • Cross-seed detection (line 248 in uphelper.py) intentionally still requires
    file_count_match, so we verify that flag is only present when counts agree.
"""
import asyncio
from typing import Any

import pytest

from src.dupe_checking import DupeChecker


def _run(coro):
    return asyncio.run(coro)


def _checker() -> DupeChecker:
    return DupeChecker(config={})


def _base_meta(**overrides) -> dict[str, Any]:
    """Minimal meta dict for a 1080p BluRay encode (movie)."""
    meta: dict[str, Any] = {
        "name": "Interstellar 2014 IMAX 1080p BluRay DTS-HD MA 5.1 x264-LEGi0N",
        "uuid": "Interstellar 2014 IMAX 1080p BluRay DTS-HD MA 5.1 x264-LEGi0N",
        "tmdb": "157336",
        "resolution": "1080p",
        "category": "MOVIE",
        "type": "ENCODE",
        "source": "Blu-ray",
        "is_disc": None,
        "sd": 0,
        "hdr": None,
        "season": None,
        "episode": None,
        "tag": "-LEGi0N",
        "video_encode": "x264",
        "unattended": True,
        "debug": False,
        "filelist": ["/path/to/Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.mkv"],
    }
    meta.update(overrides)
    return meta


def _rf_entry(files: list[str], file_count: int | None = None) -> dict[str, Any]:
    """Build a RF-style dupe entry with the given file list."""
    if file_count is None:
        file_count = len(files)
    return {
        "name": "Interstellar 2014 IMAX 1080p BluRay DTS-HD MA 5.1 x264-LEGi0N",
        "size": 17_996_567_700,
        "files": files,
        "file_count": file_count,
        "trumpable": False,
        "link": "https://reelflix.cc/torrents/12725",
        "download": "https://reelflix.cc/torrents/12725/download",
        "id": 12725,
        "type": "Encode",
        "res": "1080p",
        "internal": False,
    }


# ═══════════════════════════════════════════════════════════════
#  Filename match — with and without extra tracker files
# ═══════════════════════════════════════════════════════════════


class TestFilenameMatchLogic:
    """filter_dupes behaviour around filename/file-count matching."""

    def test_exact_filename_and_count_match_sets_both_flags(self):
        """
        When the tracker has exactly the same file list as the local copy,
        both filename_match and file_count_match must be set.
        """
        local_file = "Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.mkv"
        meta = _base_meta()
        entry = _rf_entry([local_file])  # 1 file — same as local

        dupes = _run(_checker().filter_dupes([entry], meta, "RF"))

        assert dupes, "entry must remain in the dupe list"
        assert meta.get("filename_match"), "filename_match must be set"
        assert meta.get("file_count_match"), "file_count_match must be set when counts agree"

    def test_filename_match_with_extra_tracker_files_sets_filename_match(self):
        """
        Regression: when the tracker torrent has extra files (NFO, sample) that
        the local copy doesn't have, filename_match must still be set and the
        entry must remain in the dupe list — even though file counts differ.
        """
        local_file = "Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.mkv"
        tracker_files = [
            local_file,
            "Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.nfo",
            "Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.sample.mkv",
        ]
        meta = _base_meta()
        entry = _rf_entry(tracker_files)  # 3 files on tracker, 1 locally

        dupes = _run(_checker().filter_dupes([entry], meta, "RF"))

        assert dupes, "entry must remain in the dupe list"
        assert meta.get("filename_match"), "filename_match must be set despite count mismatch"

    def test_filename_match_with_extra_tracker_files_does_not_set_count_match(self):
        """
        file_count_match must NOT be set when the file counts differ — this
        flag gates cross-seed eligibility, which requires an identical file set.
        """
        local_file = "Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.mkv"
        tracker_files = [
            local_file,
            "Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.nfo",
            "Interstellar.2014.IMAX.1080p.BluRay.DTS-HD.MA.5.1.x264-LEGi0N.sample.mkv",
        ]
        meta = _base_meta()
        entry = _rf_entry(tracker_files)

        _run(_checker().filter_dupes([entry], meta, "RF"))

        assert not meta.get("file_count_match"), (
            "file_count_match must NOT be set when local file count differs "
            "from tracker file count (cross-seed would fail)"
        )

    def test_tracker_files_with_folder_prefix_match_local_basename(self):
        """
        Regression: G3MINI stores files as "Folder/File.mkv".  The comparison
        against local basenames must strip the directory component first.
        """
        local_file = "Atlanta.S04E01.MULTi.1080p.AMZN.WEB-DL.DDP5.1.H264-FRATERNiTY.mkv"
        tracker_files = [
            "Atlanta.S04E01.MULTi.1080p.AMZN.WEB-DL.DDP5.1.H264-FRATERNiTY/Atlanta.S04E01.MULTi.1080p.AMZN.WEB-DL.DDP5.1.H264-FRATERNiTY.mkv",
            "Atlanta.S04E01.MULTi.1080p.AMZN.WEB-DL.DDP5.1.H264-FRATERNiTY/Atlanta.S04E01.MULTi.1080p.AMZN.WEB-DL.DDP5.1.H264-FRATERNiTY.nfo",
        ]
        meta = _base_meta(
            filelist=[f"/downloads/Atlanta.S04E01.MULTi.1080p.AMZN.WEB-DL.DDP5.1.H264-FRATERNiTY/{local_file}"],
        )
        entry = _rf_entry(tracker_files)
        entry["name"] = "Atlanta.S04.MULTi.VFF.1080p.WEB.DDP5.1.H.264-FRATERNiTY"

        dupes = _run(_checker().filter_dupes([entry], meta, "G3MINI"))

        assert dupes, "entry must remain in the dupe list"
        assert meta.get("filename_match"), (
            "filename_match must be set even when tracker stores 'Folder/File.mkv' paths"
        )

    def test_no_filename_overlap_does_not_set_filename_match(self):
        """When no local filename appears in the tracker file list, no match flags are set."""
        tracker_files = [
            "Interstellar.2014.1080p.BluRay.DD.5.1.x264-BHDStudio.mkv",
        ]
        meta = _base_meta()
        entry = _rf_entry(tracker_files)
        entry["name"] = "Interstellar 2014 1080p BluRay DD 5.1 x264-BHDStudio"

        _run(_checker().filter_dupes([entry], meta, "RF"))

        assert not meta.get("filename_match"), "filename_match must not be set for a different release"


# ═══════════════════════════════════════════════════════════════
#  Name-similarity fallback  (TORR9-style trackers with no files)
# ═══════════════════════════════════════════════════════════════


def _torr9_entry_no_files(**overrides) -> dict[str, Any]:
    """Build a TORR9-style dupe entry with *no* file list."""
    entry: dict[str, Any] = {
        "name": "Atlanta.S04.MULTI.1080p.AMZN.H264.DDP5.1-FRATERNiTY",
        "size": 20_000_000_000,
        "link": "https://torr9.net/torrents/50343",
        "id": 50343,
        # No "files" key at all — TORR9 custom API never returns it
    }
    entry.update(overrides)
    return entry


def _atlanta_s04_meta(**overrides) -> dict[str, Any]:
    """Meta for Atlanta S04 WEB season pack — FRATERNiTY group."""
    meta: dict[str, Any] = {
        "name": "Atlanta.S04.MULTI.VFF.1080p.AMZN.WEB.DDP.5.1.H264-FRATERNiTY",
        "uuid": "Atlanta.S04.MULTI.VFF.1080p.AMZN.WEB.DDP.5.1.H264-FRATERNiTY",
        "tmdb": "61818",
        "resolution": "1080p",
        "category": "TV",
        "type": "WEBDL",
        "source": "Amazon Prime",
        "is_disc": None,
        "sd": 0,
        "hdr": None,
        "season": "S04",
        "episode": None,
        "tag": "-FRATERNiTY",
        "video_encode": "H.264",
        "unattended": True,
        "debug": False,
        "filelist": ["/downloads/Atlanta.S04.MULTI.VFF.1080p.AMZN.WEB.DDP.5.1.H264-FRATERNiTY/Atlanta.S04E01.MULTi.VFF.mkv"],
    }
    meta.update(overrides)
    return meta


class TestNameSimilarityFallback:
    """Name-similarity fallback for trackers that return no file lists (e.g. TORR9)."""

    def test_same_group_high_similarity_sets_filename_match(self):
        """
        Regression — TORR9 Atlanta S04 FRATERNiTY:
        Old naming omits VFF/WEB tokens. No file list is returned by the API.
        The name-similarity fallback must detect this as the same release and
        set filename_match (→ "Exact match found!" in the UI).
        """
        meta = _atlanta_s04_meta()
        entry = _torr9_entry_no_files()

        dupes = _run(_checker().filter_dupes([entry], meta, "TORR9"))

        assert dupes, "entry must remain in the dupe list"
        assert meta.get("filename_match"), (
            "filename_match must be set via name-similarity fallback "
            "when tracker returns no file list but names/tags are similar"
        )

    def test_same_group_low_similarity_does_not_set_filename_match(self):
        """
        Two releases by the same group but clearly different content (different show)
        must NOT trigger filename_match even if the tag matches.
        """
        meta = _atlanta_s04_meta()
        # Entry from a completely different show by the same group
        entry = _torr9_entry_no_files(
            name="Succession.S04.MULTI.1080p.AMZN.H264.DDP5.1-FRATERNiTY",
        )

        _run(_checker().filter_dupes([entry], meta, "TORR9"))

        assert not meta.get("filename_match"), (
            "filename_match must NOT be set when the names differ substantially "
            "despite sharing the same release group"
        )
