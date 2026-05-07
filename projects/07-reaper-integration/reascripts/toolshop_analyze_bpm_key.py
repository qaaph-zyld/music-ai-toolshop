"""ReaScript: Analyze BPM and key of the selected media item.

Workflow:

1. User selects a media item in Reaper (audio).
2. Run this script (Actions list -> Run ReaScript, or assign a shortcut).
3. The script resolves the underlying audio file, calls
   ``toolshop analyze bpm-key --json`` on it, and writes the result back to
   Reaper as:

   * a console message,
   * a ``BPM:`` / ``Key:`` block in the item's ``P_NOTES`` field, and
   * a project marker at the item's start position labelled
     ``<bpm> BPM <key> <mode>`` so the analysis is visible in the timeline.

Install: copy this file (and ``_toolshop_bridge.py``) into your Reaper
``Scripts/`` folder, add it to the Action List as a ReaScript, then bind a
shortcut. See ``../README.md`` for full instructions.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Make sibling helper module importable regardless of how Reaper invokes us.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _toolshop_bridge import (  # noqa: E402  (sys.path tweak above)
    BpmKeyResult,
    ToolshopError,
    analyze_bpm_key,
)

try:  # pragma: no cover - only importable inside Reaper's Python runtime
    from reaper_python import (  # type: ignore[import-not-found]
        RPR_AddProjectMarker,
        RPR_GetActiveTake,
        RPR_GetMediaItemInfo_Value,
        RPR_GetMediaItemTake_Source,
        RPR_GetMediaSourceFileName,
        RPR_GetSelectedMediaItem,
        RPR_GetSetMediaItemInfo_String,
        RPR_ShowConsoleMsg,
    )
except ImportError:  # Allows static analysis / unit tests outside Reaper.
    RPR_AddProjectMarker = None  # type: ignore[assignment]
    RPR_GetActiveTake = None  # type: ignore[assignment]
    RPR_GetMediaItemInfo_Value = None  # type: ignore[assignment]
    RPR_GetMediaItemTake_Source = None  # type: ignore[assignment]
    RPR_GetMediaSourceFileName = None  # type: ignore[assignment]
    RPR_GetSelectedMediaItem = None  # type: ignore[assignment]
    RPR_GetSetMediaItemInfo_String = None  # type: ignore[assignment]
    RPR_ShowConsoleMsg = None  # type: ignore[assignment]


def _log(msg: str) -> None:
    if RPR_ShowConsoleMsg is not None:
        RPR_ShowConsoleMsg(msg + "\n")
    else:
        print(msg)


def _selected_audio_path() -> Path:
    """Return the audio file path of the currently selected media item.

    Raises:
        RuntimeError: if no item is selected, the active take has no source,
            or the source is not backed by a file on disk.
    """
    if RPR_GetSelectedMediaItem is None:
        raise RuntimeError(
            "This script must be run from inside Reaper (reaper_python not available)."
        )

    item = RPR_GetSelectedMediaItem(0, 0)
    if not item:
        raise RuntimeError("No media item selected. Select an audio item and re-run.")

    take = RPR_GetActiveTake(item)
    if not take:
        raise RuntimeError("Selected item has no active take.")

    source = RPR_GetMediaItemTake_Source(take)
    if not source:
        raise RuntimeError("Active take has no source.")

    # Reaper's swig wrapper returns (filename, source, "", buf_len)
    filename = RPR_GetMediaSourceFileName(source, "", 4096)
    if isinstance(filename, tuple):
        filename = filename[0]
    if not filename:
        raise RuntimeError(
            "Active take's source is not backed by a file on disk (in-project MIDI?)."
        )

    return item, Path(filename)


def _set_item_notes(item: object, result: BpmKeyResult) -> None:
    if RPR_GetSetMediaItemInfo_String is None:
        return
    notes = (
        f"BPM: {result.bpm:.2f}\n"
        f"Key: {result.key} {result.mode}\n"
        f"Duration: {result.duration_seconds:.2f}s\n"
        f"Source: {result.file}\n"
    )
    RPR_GetSetMediaItemInfo_String(item, "P_NOTES", notes, True)


def _add_marker(item: object, result: BpmKeyResult) -> None:
    if RPR_AddProjectMarker is None or RPR_GetMediaItemInfo_Value is None:
        return
    position = RPR_GetMediaItemInfo_Value(item, "D_POSITION")
    label = f"{result.bpm:.1f} BPM {result.key} {result.mode}"
    RPR_AddProjectMarker(0, False, position, 0, label, -1)


def main() -> int:
    try:
        item, audio_path = _selected_audio_path()
    except RuntimeError as exc:
        _log(f"[toolshop] {exc}")
        return 1

    _log(f"[toolshop] Analyzing {audio_path} ...")

    try:
        result = analyze_bpm_key(audio_path)
    except FileNotFoundError as exc:
        _log(f"[toolshop] {exc}")
        return 1
    except ToolshopError as exc:
        _log(f"[toolshop] {exc}")
        return 1
    except Exception:  # pragma: no cover - last-resort safety net
        _log("[toolshop] Unexpected error:\n" + traceback.format_exc())
        return 1

    _log("[toolshop] " + result.summary())
    _set_item_notes(item, result)
    _add_marker(item, result)
    return 0


if __name__ == "__main__":
    # Reaper does not look at exit codes, but pytest / direct invocation will.
    sys.exit(main() if not os.environ.get("TOOLSHOP_NOOP") else 0)
