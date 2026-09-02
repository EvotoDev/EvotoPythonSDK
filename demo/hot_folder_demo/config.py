"""Hot Folder Demo - JSON config schema and I/O.

The config file is a single JSON document that round-trips the UI state:

- Shared project info (id + name)
- Global watcher options (include_sub_dir + filters)
- A list of mapping rows. Each row is a watch_folder -> export_folder
  lane with its own preset suit and ExportOptions dict.

The demo autosaves to ``<demo>/config/config.json`` next to the source
tree so the project stays self-contained; opening the demo reloads it
and any change in the UI writes it back.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable


CONFIG_VERSION = 1

# Config lives inside the demo package so the demo is self-contained
# (no user-home pollution) and easy to version-control per-workspace.
DEFAULT_CONFIG_PATH = str(
    Path(__file__).resolve().parent / 'config' / 'config.json'
)


@dataclass
class ProjectRef:
    """Identifier for the shared Evoto project used by every lane."""
    id: int = 0
    name: str = ''

    @classmethod
    def from_dict(cls, d: dict | None) -> 'ProjectRef':
        if not d:
            return cls()
        return cls(id=int(d.get('id', 0) or 0), name=str(d.get('name', '')))


@dataclass
class LauncherConfig:
    """Settings for launching an Evoto host process from this demo.

    The demo can optionally spawn Evoto itself (mirroring what the Qt
    ``RecvLrcOpenFiles`` helper does) so a machine without a running
    host can be bootstrapped end-to-end. Both fields are persisted to
    ``config.json`` so the preference survives restarts.
    """
    evoto_path: str = ''
    """Absolute path to the Evoto binary (or ``.app`` bundle on macOS).

    On macOS a user-selected ``Evoto.app`` is transparently resolved
    to ``Evoto.app/Contents/MacOS/Evoto`` by the launcher.
    """

    auto_launch: bool = False
    """When true, try to launch Evoto (and auto-reconnect) on startup."""

    @classmethod
    def from_dict(cls, d: dict | None) -> 'LauncherConfig':
        if not d:
            return cls()
        return cls(
            evoto_path=str(d.get('evoto_path', '') or ''),
            auto_launch=bool(d.get('auto_launch', False)),
        )


@dataclass
class WatcherConfig:
    """Global watcher settings. ``watcher.start()`` only accepts these
    globally (not per path), so they live outside each row.

    ``paths`` is the single source of truth for which folders the host
    is told to watch; each :class:`MappingRow` then picks one of these
    paths as the source of its lane.
    """
    paths: list[str] = field(default_factory=list)
    include_sub_dir: bool = True
    filters: list[str] = field(default_factory=list)
    """Empty list means all supported file types."""

    @classmethod
    def from_dict(cls, d: dict | None) -> 'WatcherConfig':
        if not d:
            return cls()
        return cls(
            paths=list(d.get('paths', []) or []),
            include_sub_dir=bool(d.get('include_sub_dir', True)),
            filters=list(d.get('filters', []) or []),
        )


@dataclass
class MappingRow:
    """One lane: watch folder -> export folder + preset(s) + custom options.

    ``preset_suit_ids`` / ``preset_suit_names`` are parallel lists that
    mirror the ``PresetAPI.list()`` structure - each ID has a display
    name next to it so the UI can show a readable label without hitting
    the host again. A lane may bind to one or more preset suits; the
    pipeline forwards the full list to ``export.start_with_custom``.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    label: str = ''
    watch_folder: str = ''
    export_folder: str = ''
    preset_suit_ids: list[str] = field(default_factory=list)
    preset_suit_names: list[str] = field(default_factory=list)
    export_options: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> 'MappingRow':
        # New format - plural list fields.
        raw_ids = d.get('preset_suit_ids')
        raw_names = d.get('preset_suit_names')
        if isinstance(raw_ids, list):
            ids = [str(x) for x in raw_ids if str(x or '')]
        else:
            # Old format - singular keys from before multi-preset support.
            single_id = str(d.get('preset_suit_id', '') or '')
            ids = [single_id] if single_id else []
        if isinstance(raw_names, list):
            names = [str(x) for x in raw_names]
        else:
            single_name = str(d.get('preset_suit_name', '') or '')
            names = [single_name] if single_name else []
        # Keep names aligned with ids: pad with the id as a last-resort
        # label so the UI always has *something* to render per entry.
        if len(names) < len(ids):
            names = names + [ids[i] for i in range(len(names), len(ids))]
        elif len(names) > len(ids):
            names = names[: len(ids)]

        return cls(
            id=str(d.get('id') or uuid.uuid4().hex[:8]),
            label=str(d.get('label', '')),
            watch_folder=str(d.get('watch_folder', '')),
            export_folder=str(d.get('export_folder', '')),
            preset_suit_ids=ids,
            preset_suit_names=names,
            export_options=dict(d.get('export_options') or {}),
        )

    def is_runnable(self) -> tuple[bool, str]:
        if not self.watch_folder:
            return False, 'watch folder is empty'
        if not self.export_folder:
            return False, 'export folder is empty'
        if not self.preset_suit_ids:
            return False, 'preset suit is not picked'
        return True, ''


@dataclass
class HotFolderConfig:
    """Top-level document stored in the JSON file."""
    version: int = CONFIG_VERSION
    project: ProjectRef = field(default_factory=ProjectRef)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    launcher: LauncherConfig = field(default_factory=LauncherConfig)
    mappings: list[MappingRow] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def runnable_rows(self) -> list[MappingRow]:
        """Rows with enough fields filled in to be routed / exported.

        A row is active as soon as it has a watch folder, an export
        folder and at least one preset suit - see ``is_runnable``.
        """
        out = []
        for r in self.mappings:
            ok, _ = r.is_runnable()
            if ok:
                out.append(r)
        return out

    def row(self, row_id: str) -> MappingRow | None:
        for r in self.mappings:
            if r.id == row_id:
                return r
        return None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            'version': self.version,
            'project': asdict(self.project),
            'watcher': asdict(self.watcher),
            'launcher': asdict(self.launcher),
            'mappings': [asdict(r) for r in self.mappings],
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'HotFolderConfig':
        cfg = cls(
            version=int(d.get('version', CONFIG_VERSION) or CONFIG_VERSION),
            project=ProjectRef.from_dict(d.get('project')),
            watcher=WatcherConfig.from_dict(d.get('watcher')),
            launcher=LauncherConfig.from_dict(d.get('launcher')),
            mappings=[MappingRow.from_dict(x) for x in d.get('mappings', []) or []],
        )
        # Backward-compat: configs saved before the global `paths` list
        # existed only carried per-row ``watch_folder``. Lift the unique
        # values up so the UI and pipeline have a single source of truth.
        if not cfg.watcher.paths and cfg.mappings:
            cfg.watcher.paths = list(dict.fromkeys(
                r.watch_folder for r in cfg.mappings if r.watch_folder))
        return cfg

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> 'HotFolderConfig':
        """Load a config file. Returns a fresh default if the file doesn't
        exist or can't be parsed (callers typically log the outcome)."""
        if not os.path.exists(path):
            return cls()
        with open(path, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        return cls.from_dict(raw)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
#
# Hot-folder routing rule:
#     When a new file lands, pick the *closest* configured watch folder
#     on its ancestor chain. If a parent folder and a child folder both
#     have mapping rows, the file goes to the child's row. If the file
#     sits in a sub-tree that is not directly configured, we walk up
#     until we hit a configured ancestor; the file is ignored only if
#     no ancestor is configured at all.
#
# All comparisons are done on a canonicalized form so we tolerate:
#     - trailing separators ("/in/studio/" vs "/in/studio"),
#     - redundant separators ("/in//studio"),
#     - case-only differences on platforms whose filesystem is
#       case-insensitive by default (Windows, macOS APFS/HFS+), since
#       the host may echo a file back with different casing than the
#       user typed into the watch-folder dialog.


def _canon_dir(path: str) -> str:
    """Canonicalize a directory path for ancestor-chain comparison.

    Keeps the on-disk case (needed later for folder name preservation);
    only collapses separators and drops trailing ``/``.
    """
    if not path:
        return ''
    return os.path.normpath(path)


def _fold(path: str) -> str:
    """Case-fold a :func:`_canon_dir` result on platforms whose file
    system treats ``"/In/Studio"`` and ``"/in/studio"`` as the same
    folder - so that our prefix check agrees with what the OS does."""
    if not path:
        return ''
    if sys.platform == 'win32' or sys.platform == 'darwin':
        return path.lower()
    return path


def _iter_ancestors(path: str) -> Iterable[str]:
    """Yield *path*, its parent, its grandparent, ... up to the root."""
    cur = path
    while cur:
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return
        cur = parent


def relative_dir(file_path: str, watch_folder: str) -> str:
    """Return the sub-directory of *file_path* relative to *watch_folder*.

    Always returns POSIX-style separators so the result is stable across
    platforms when used to compose an export sub-directory.

    ``rel_dir == ""`` means the file is directly under *watch_folder*.
    Anything that is not a descendant of *watch_folder* returns ``""``
    (caller is expected to have matched the row first, so this guard is
    really just belt-and-braces against stale inputs).
    """
    if not file_path or not watch_folder:
        return ''
    wf_canon = _canon_dir(watch_folder)
    fd_canon = _canon_dir(os.path.dirname(file_path))
    if not wf_canon or not fd_canon:
        return ''
    if _fold(fd_canon) == _fold(wf_canon):
        return ''
    prefix = _fold(wf_canon) + os.sep
    if not _fold(fd_canon).startswith(prefix):
        return ''
    # normpath preserves the original case, and case-folding is a
    # length-preserving operation on ASCII (the 99% case for hot-folder
    # paths), so the cut at ``len(wf_canon) + 1`` lands on the same
    # byte in fd_canon - keeping the on-disk case of the sub-folder.
    rel = fd_canon[len(wf_canon) + 1:]
    return rel.replace('\\', '/')


def join_export_dir(export_folder: str, rel_dir: str) -> str:
    """Compose the final export directory mirroring the input sub-tree."""
    if not rel_dir:
        return export_folder
    return os.path.join(export_folder, *rel_dir.split('/'))


def iter_files_matching_row(
    files: Iterable[str],
    rows: Iterable[MappingRow],
) -> dict[str, list[str]]:
    """Group files by the closest configured ancestor watch folder.

    For each file we walk up its directory chain and take the *first*
    ancestor that appears in the supplied rows. That gives the deepest
    (i.e. most specific) configured folder automatically - if row B's
    folder ``/in/studio/vip`` is nested inside row A's folder
    ``/in/studio``, files under ``vip/`` land on B and everything else
    under ``/in/studio`` lands on A. Files that sit under no configured
    ancestor are dropped (caller logs how many were ignored).
    """
    watch_map: dict[str, MappingRow] = {}
    for r in rows:
        if not r.watch_folder:
            continue
        key = _fold(_canon_dir(r.watch_folder))
        if not key:
            continue
        # First row wins on exact duplicates; UI normally dedupes paths
        # via the shared combo box, so this is really a safety net.
        watch_map.setdefault(key, r)

    grouped: dict[str, list[str]] = {}
    for f in files:
        directory = os.path.dirname(f)
        if not directory:
            continue
        for ancestor in _iter_ancestors(_canon_dir(directory)):
            row = watch_map.get(_fold(ancestor))
            if row is not None:
                grouped.setdefault(row.id, []).append(f)
                break
    return grouped
