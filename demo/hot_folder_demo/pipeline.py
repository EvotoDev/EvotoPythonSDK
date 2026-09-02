"""Hot-folder pipeline - watcher -> import -> group by (row, sub-dir) -> export.

The pipeline assumes all lanes share one Evoto project. A single
:class:`WatcherAPI` instance is started with every runnable row's
watch folder merged into one ``paths`` list; incoming file events
are routed back to the owning row by longest-prefix match. A row is
"runnable" when it has a watch folder, an export folder and at least
one preset suit - there is no separate on/off toggle.

Images are imported asynchronously with a per-row
``import_listener_uuid=f"hotfolder-<row.id>"`` tag so that
``image.on_completed`` can tell which row a batch belongs to.
When the host pushes back ``import.completed``, we compute
``rel_dir = dirname(origin_path) - row.watch_folder`` for every image
and bucket the image IDs by ``(row.id, rel_dir)``. Each bucket then
fires one ``export.start_with_custom`` with
``export_dir = row.export_folder / rel_dir``, so the output side
mirrors the source sub-folder tree.
"""

from __future__ import annotations

import logging
import os
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

import evoto
from evoto.core.api_fields import ExportField, Field

from demo.hot_folder_demo.config import (
    HotFolderConfig, MappingRow,
    iter_files_matching_row, join_export_dir, relative_dir,
)

logger = logging.getLogger('hot_folder_demo.pipeline')


def _uuid_for(row_id: str) -> str:
    return f'hotfolder-{row_id}'


class Pipeline(QObject):
    """Orchestrate watcher + import + export chain for a HotFolderConfig.

    All host callbacks are marshalled onto the Qt main thread via signals
    before they touch the UI.
    """

    log = Signal(str)
    row_status = Signal(str, str)
    _files_added_sig = Signal(dict)
    _import_completed_sig = Signal(dict)
    _import_failed_sig = Signal(dict)
    _export_started_sig = Signal(dict)
    _export_progress_sig = Signal(dict)
    _export_item_sig = Signal(dict)
    _export_completed_sig = Signal(dict)
    _export_failed_sig = Signal(dict)

    def __init__(self, config: HotFolderConfig, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._rows_by_uuid: dict[str, MappingRow] = {}
        # ``export.progress`` / ``export.item_finished`` carry the
        # ``export_dir_id`` but not always the ``export_listener_uuid``,
        # so we keep a dir_id -> row map populated at ``start_with_custom``
        # time and fall back to it when the UUID is missing.
        self._dir_to_row: dict[int, MappingRow] = {}
        self._pending: dict[tuple[str, str], list[int]] = {}
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(500)
        self._flush_timer.timeout.connect(self._flush)
        self._running = False

        self._files_added_sig.connect(self._on_files_added_main)
        self._import_completed_sig.connect(self._on_import_completed_main)
        self._import_failed_sig.connect(self._on_import_failed_main)
        self._export_started_sig.connect(self._on_export_started_main)
        self._export_progress_sig.connect(self._on_export_progress_main)
        self._export_item_sig.connect(self._on_export_item_main)
        self._export_completed_sig.connect(self._on_export_completed_main)
        self._export_failed_sig.connect(self._on_export_failed_main)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        return self._running

    def set_config(self, cfg: HotFolderConfig) -> None:
        if self._running:
            raise RuntimeError('Stop the pipeline before swapping config')
        self._cfg = cfg

    def start(self) -> tuple[bool, str]:
        """Validate config and start watching. Returns (ok, err_msg)."""
        if self._running:
            return False, 'Already running'
        if not self._cfg.project.id:
            return False, 'Pick or create a project first'

        runnable = self._cfg.runnable_rows()
        if not runnable:
            skipped = []
            for r in self._cfg.mappings:
                ok, why = r.is_runnable()
                if not ok:
                    skipped.append(f'"{r.label or r.id}": {why}')
            msg = 'No runnable rows. ' + ('; '.join(skipped) if skipped
                                          else 'Add at least one row.')
            return False, msg

        self._rows_by_uuid = {_uuid_for(r.id): r for r in runnable}
        self._dir_to_row.clear()
        self._pending.clear()

        # Prefer the explicit watcher paths from the config (single source
        # of truth, populated via the shared WatchConfigPanel). Fall back
        # to the union of row watch folders for older configs that didn't
        # persist a global list.
        paths = list(dict.fromkeys(self._cfg.watcher.paths or []))
        if not paths:
            paths = list(dict.fromkeys(
                r.watch_folder for r in runnable if r.watch_folder))
        if not paths:
            return False, 'Add at least one watch folder'
        try:
            evoto.watcher.start(
                paths,
                filters=self._cfg.watcher.filters or None,
                include_sub_dir=self._cfg.watcher.include_sub_dir,
            )
        except Exception as exc:
            return False, f'watcher.start failed: {exc}'

        evoto.watcher.on_files_added(self._on_files_added_worker)
        # Subscribe *before* registering the callback. The host only
        # forwards ``import.completed`` / ``export.completed`` to plugins
        # that have called the matching ``subscribe``; ``on_completed``
        # alone just wires a local dispatcher. Without these calls the
        # pipeline would import images asynchronously and then go silent
        # forever.
        #
        # We subscribe *without* a UUID filter so every row's events come
        # back (each row tags its requests with ``hotfolder-<row.id>``;
        # filtering happens client-side in ``_on_import_completed_main``).
        try:
            evoto.image.subscribe()
        except Exception as exc:
            logger.warning('image.subscribe: %s', exc)
        evoto.image.on_completed(self._on_import_completed_worker)
        evoto.image.on_failed(self._on_import_failed_worker)
        try:
            evoto.export.subscribe()
        except Exception as exc:
            logger.warning('export.subscribe: %s', exc)
        # Wire the full ``export.*`` lifecycle so the UI can render
        # realtime progress and per-item results (mirrors the
        # preset_export_demo handler set).
        evoto.export.on_started(self._on_export_started_worker)
        evoto.export.on_progress(self._on_export_progress_worker)
        evoto.export.on_item_finished(self._on_export_item_worker)
        evoto.export.on_completed(self._on_export_completed_worker)
        evoto.export.on_failed(self._on_export_failed_worker)

        self._running = True
        self.log.emit(f'Watching {len(paths)} folder(s); '
                      f'include_sub_dir={self._cfg.watcher.include_sub_dir}')
        for r in runnable:
            self.row_status.emit(r.id, 'watching')
        return True, ''

    def stop(self) -> None:
        if not self._running:
            return
        try:
            evoto.watcher.off_files_added(self._on_files_added_worker)
        except Exception:
            pass
        try:
            evoto.image.off_completed(self._on_import_completed_worker)
        except Exception:
            pass
        try:
            evoto.image.off_failed(self._on_import_failed_worker)
        except Exception:
            pass
        try:
            evoto.image.unsubscribe()
        except Exception:
            pass
        for off, cb in (
            (evoto.export.off_started, self._on_export_started_worker),
            (evoto.export.off_progress, self._on_export_progress_worker),
            (evoto.export.off_item_finished, self._on_export_item_worker),
            (evoto.export.off_completed, self._on_export_completed_worker),
            (evoto.export.off_failed, self._on_export_failed_worker),
        ):
            try:
                off(cb)
            except Exception:
                pass
        try:
            evoto.watcher.stop()
        except Exception as exc:
            self.log.emit(f'watcher.stop: {exc}')

        if self._flush_timer.isActive():
            self._flush_timer.stop()
            self._flush()

        self._running = False
        self.log.emit('Pipeline stopped')
        for r in self._cfg.mappings:
            self.row_status.emit(r.id, 'idle')

    # ------------------------------------------------------------------
    # Worker-thread callbacks - just forward via signal
    # ------------------------------------------------------------------

    def _on_files_added_worker(self, data: dict):
        self._files_added_sig.emit(data or {})

    def _on_import_completed_worker(self, data: dict):
        self._import_completed_sig.emit(data or {})

    def _on_import_failed_worker(self, data: dict):
        self._import_failed_sig.emit(data or {})

    def _on_export_started_worker(self, data: dict):
        self._export_started_sig.emit(data or {})

    def _on_export_progress_worker(self, data: dict):
        self._export_progress_sig.emit(data or {})

    def _on_export_item_worker(self, data: dict):
        self._export_item_sig.emit(data or {})

    def _on_export_completed_worker(self, data: dict):
        self._export_completed_sig.emit(data or {})

    def _on_export_failed_worker(self, data: dict):
        self._export_failed_sig.emit(data or {})

    # ------------------------------------------------------------------
    # Main-thread handlers
    # ------------------------------------------------------------------

    def _on_files_added_main(self, data: dict):
        files = list(data.get('files') or [])
        if not files:
            return
        grouped = iter_files_matching_row(files, self._cfg.runnable_rows())
        if not grouped:
            self.log.emit(f'{len(files)} files ignored (no matching row)')
            return

        for row_id, paths in grouped.items():
            row = self._cfg.row(row_id)
            if not row:
                continue
            self.log.emit(
                f'[{row.label or row.id}] +{len(paths)} file(s), importing...')
            self.row_status.emit(row.id, f'import ({len(paths)})')
            try:
                ack = evoto.image.import_files_async(
                    paths,
                    project_id=self._cfg.project.id,
                    import_listener_uuid=_uuid_for(row.id),
                )
                import_id = (ack or {}).get('import_id') or (ack or {}).get('importId')
                self.log.emit(
                    f'[{row.label or row.id}] import accepted '
                    f'(import_id={import_id or "?"}, uuid={_uuid_for(row.id)})')
            except Exception as exc:
                self.log.emit(f'[{row.label or row.id}] import failed: {exc}')
                self.row_status.emit(row.id, 'import error')

    def _on_import_completed_main(self, data: dict):
        uuid_tag = data.get('import_listener_uuid') or ''
        row = self._rows_by_uuid.get(uuid_tag)
        if not row:
            # Not one of ours - some other plugin imported, or the
            # host delivered an event from a previous run. Surface it
            # once in the log so silent no-ops are obvious.
            if uuid_tag:
                self.log.emit(
                    f'import.completed with unknown uuid "{uuid_tag}" - ignored')
            return
        images = data.get('images') or []
        if not images:
            self.log.emit(f'[{row.label or row.id}] import.completed with 0 images')
            return

        buckets: dict[str, list[int]] = {}
        for img in images:
            image_id = img.get('id') or img.get('image_id')
            if image_id is None:
                continue
            origin = img.get('origin_path') or ''
            rel = relative_dir(origin, row.watch_folder) if origin else ''
            buckets.setdefault(rel, []).append(int(image_id))

        for rel_dir, ids in buckets.items():
            key = (row.id, rel_dir)
            self._pending.setdefault(key, []).extend(ids)

        total = sum(len(v) for v in buckets.values())
        sub_note = (f' across {len(buckets)} sub-dir(s)'
                    if any(k for k in buckets) else '')
        self.log.emit(
            f'[{row.label or row.id}] imported {total} image(s){sub_note}')
        self.row_status.emit(row.id, f'queued ({total})')
        self._flush_timer.start()

    def _on_import_failed_main(self, data: dict):
        uuid_tag = data.get('import_listener_uuid') or ''
        row = self._rows_by_uuid.get(uuid_tag)
        if not row:
            return
        reason = data.get('reason') or data.get('message') or 'unknown'
        self.log.emit(f'[{row.label or row.id}] import FAILED: {reason}')
        self.row_status.emit(row.id, 'import error')

    def _flush(self):
        if not self._pending:
            return
        buckets = self._pending
        self._pending = {}

        for (row_id, rel_dir), ids in buckets.items():
            row = self._cfg.row(row_id)
            if row is None or not ids:
                continue
            target_dir = join_export_dir(row.export_folder, rel_dir)
            try:
                os.makedirs(target_dir, exist_ok=True)
            except OSError as exc:
                self.log.emit(
                    f'[{row.label or row.id}] cannot create {target_dir}: {exc}')
                self.row_status.emit(row.id, 'export error')
                continue

            sub_note = f'/{rel_dir}' if rel_dir else ''
            # The host runs every image through *each* selected preset
            # suit, so the emitted task count (and later the
            # success/failed totals on ``export.completed``) equals
            # ``images * suits``. Use the same basis here so the
            # "exporting (N)" cell matches the "done s=X/f=Y" result.
            suits = max(len(row.preset_suit_ids), 1)
            expected = len(ids) * suits
            suits_note = f' × {suits} preset(s)' if suits > 1 else ''
            self.log.emit(
                f'[{row.label or row.id}] exporting {len(ids)} image(s)'
                f'{suits_note} -> {row.export_folder}{sub_note}')
            self.row_status.emit(row.id, f'exporting ({expected})')
            try:
                result = evoto.export.start_with_custom(
                    project_id=self._cfg.project.id,
                    export_dir=target_dir,
                    preset_suit_ids=list(row.preset_suit_ids),
                    imageIds=ids,
                    export_listener_uuid=_uuid_for(row.id),
                    options=row.export_options or None,
                )
                dir_id = result.get('export_dir_id') or result.get('exportDirId')
                requested = (result.get('requested_count')
                             or result.get('requestedCount')
                             or expected)
                if dir_id is not None:
                    # Remember this assignment so progress / item events
                    # without an ``export_listener_uuid`` can still be
                    # routed back to the lane that created the job.
                    self._dir_to_row[int(dir_id)] = row
                self.log.emit(
                    f'[{row.label or row.id}] export accepted '
                    f'(export_dir_id={dir_id}, items={requested})')
            except Exception as exc:
                self.log.emit(f'[{row.label or row.id}] export failed: {exc}')
                self.row_status.emit(row.id, 'export error')

    # ------------------------------------------------------------------
    # Export lifecycle - started / progress / item_finished / completed / failed
    # ------------------------------------------------------------------

    def _match_row(self, data: dict) -> MappingRow | None:
        """Route an export event to the lane that originated it.

        Prefers the ``export_listener_uuid`` tag we set on every
        ``start_with_custom`` call (unique per row); falls back to the
        ``export_dir_id`` we recorded when the host accepted the job.
        Returns ``None`` for events that don't belong to this pipeline
        so they can be silently skipped.
        """
        uuid_tag = data.get(ExportField.EXPORT_LISTENER_UUID) or data.get(
            'export_listener_uuid') or ''
        if uuid_tag:
            row = self._rows_by_uuid.get(uuid_tag)
            if row is not None:
                return row
        dir_id = data.get(ExportField.EXPORT_DIR_ID)
        if dir_id is None:
            dir_id = data.get('export_dir_id') or data.get('exportDirId')
        if dir_id is None:
            return None
        try:
            dir_id_int = int(dir_id)
        except (TypeError, ValueError):
            return None
        return self._dir_to_row.get(dir_id_int)

    @staticmethod
    def _counts(data: dict) -> tuple[int, int, int, int]:
        """Pull ``(done, total, ok, fail)`` tolerating snake/camel casing."""
        done = int(data.get(ExportField.COMPLETED_COUNT)
                   or data.get('completed_count')
                   or data.get('completedCount') or 0)
        total = int(data.get(ExportField.REQUESTED_COUNT)
                    or data.get('requested_count')
                    or data.get('requestedCount') or 0)
        ok = int(data.get(ExportField.SUCCESS_COUNT)
                 or data.get('success_count')
                 or data.get('successCount') or 0)
        fail = int(data.get(ExportField.FAILED_COUNT)
                   or data.get('failed_count')
                   or data.get('failedCount') or 0)
        return done, total, ok, fail

    def _on_export_started_main(self, data: dict):
        row = self._match_row(data)
        if row is None:
            return
        _, total, _, _ = self._counts(data)
        dir_id = data.get(ExportField.EXPORT_DIR_ID)
        self.log.emit(
            f'[{row.label or row.id}] export started '
            f'(dir_id={dir_id}, items={total})')
        self.row_status.emit(row.id, f'0/{total or "?"}')

    def _on_export_progress_main(self, data: dict):
        row = self._match_row(data)
        if row is None:
            return
        done, total, _, _ = self._counts(data)
        self.row_status.emit(row.id, f'{done}/{total or "?"}')

    def _on_export_item_main(self, data: dict):
        row = self._match_row(data)
        if row is None:
            return
        item = data.get(ExportField.ITEM) or {}
        status = item.get(Field.STATUS) or item.get('status') or ''
        out = item.get(ExportField.OUTPUT_PATH) or item.get('output_path') or ''
        image_id = item.get(ExportField.IMAGE_ID) or item.get('image_id') or ''
        filename = item.get(ExportField.FILENAME) or os.path.basename(out)
        # Plain-text ok/fail marker keeps the log grep-friendly and
        # avoids pulling unicode into an otherwise ASCII stream.
        is_ok = bool(status) and status.lower() in ('ok', 'success', 'succeeded')
        mark = 'ok  ' if is_ok else 'FAIL'
        line = (f'[{row.label or row.id}] {mark} {filename or image_id} '
                f'[{status or "?"}]')
        # For failures, surface whatever host-side diagnostic fields are
        # available - message / error_code / internal_error_code - noting
        # that any of them may be empty (e.g. pure timeout, or the engine
        # didn't attach a reason). Only non-empty parts end up in the line.
        if not is_ok:
            reason = (item.get(ExportField.MESSAGE)
                      or item.get('message') or '')
            err_code = item.get(ExportField.ERROR_CODE) or item.get('error_code')
            internal = (item.get(ExportField.INTERNAL_ERROR_CODE)
                        or item.get('internal_error_code'))
            detail_bits = []
            if err_code:
                detail_bits.append(f'code={err_code}')
            if internal:
                detail_bits.append(f'internal={internal}')
            if reason:
                detail_bits.append(str(reason))
            if detail_bits:
                line += '  - ' + ' - '.join(detail_bits)
        self.log.emit(line)

    def _on_export_completed_main(self, data: dict):
        row = self._match_row(data)
        if row is None:
            return
        _, total, ok, fail = self._counts(data)
        dir_id = data.get(ExportField.EXPORT_DIR_ID)
        self.log.emit(
            f'[{row.label or row.id}] export finished '
            f'(success={ok}, failed={fail}, total={total or ok + fail})')
        self.row_status.emit(row.id, f'done s={ok}/f={fail}')
        # Drop the dir_id -> row binding so a subsequent progress event
        # from a stale job doesn't keep updating this lane.
        if dir_id is not None:
            try:
                self._dir_to_row.pop(int(dir_id), None)
            except (TypeError, ValueError):
                pass

    def _on_export_failed_main(self, data: dict):
        row = self._match_row(data)
        if row is None:
            return
        dir_id = data.get(ExportField.EXPORT_DIR_ID)
        message = (data.get(ExportField.MESSAGE)
                   or data.get('message')
                   or data.get('reason')
                   or 'unknown error')
        _, total, ok, fail = self._counts(data)
        self.log.emit(
            f'[{row.label or row.id}] export FAILED '
            f'(dir_id={dir_id}, success={ok}, failed={fail}, '
            f'total={total}): {message}')
        self.row_status.emit(row.id, 'export error')
        if dir_id is not None:
            try:
                self._dir_to_row.pop(int(dir_id), None)
            except (TypeError, ValueError):
                pass
