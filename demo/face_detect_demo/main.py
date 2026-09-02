"""Standalone face detection demo.

Walks through the whole flow: load the model asynchronously, watch its state,
then start a detect task on selected images or on a whole project.

Both halves are asynchronous. ``detect()`` returns a task ID immediately and the
UI is driven by the ``face.detect.*`` events, which is the pattern a real plugin
should follow - the alternative, ``detect_and_wait()``, would block the calling
thread for the whole batch. The task can also be polled with ``detect_status()``
or stopped with ``cancel_detect()``.

Results stream in: every ``face.detect.progress`` event carries the finished
image's result, so the table fills row by row instead of all at once at the end.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import evoto
from demo.shared import (
    Card,
    Phase2DemoWindow,
    apply_theme,
    fix_checkbox_width,
)
from evoto.core.api_commands import FaceCmd
from evoto.core.api_fields import FaceField, FaceModelStatusValue

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("face_detect_demo")

MODEL_EVENTS = (
    FaceCmd.MODEL_LOADING,
    FaceCmd.MODEL_LOADED,
    FaceCmd.MODEL_FAILED,
)
DETECT_EVENTS = (
    FaceCmd.DETECT_STARTED,
    FaceCmd.DETECT_PROGRESS,
    FaceCmd.DETECT_COMPLETED,
    FaceCmd.DETECT_FAILED,
    FaceCmd.DETECT_CANCELED,
)
# Exactly one of these fires per task, which is how the demo knows detection
# is really over rather than just progressing.
TERMINAL_DETECT_EVENTS = (
    FaceCmd.DETECT_COMPLETED,
    FaceCmd.DETECT_FAILED,
    FaceCmd.DETECT_CANCELED,
)

RESULT_COLUMNS = ("Image ID", "Status", "Faces", "Age / Gender / Glasses", "Cost(ms)")


class FaceDetectDemoWindow(Phase2DemoWindow):
    """Dedicated FaceAPI debug window."""

    face_event_received = Signal(str, object)

    window_title = "Face Detect Demo"
    connect_title = "Face Detect Demo"
    image_hint = "Select rows to detect only those images; select nothing to detect the whole project."

    def __init__(self):
        self._face_event_callbacks: list[tuple[str, object]] = []
        self._current_task_id: str = ""
        super().__init__()
        self.face_event_received.connect(self._on_face_event_main)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def build_actions_panel(self) -> QWidget:
        box = Card(
            title="FaceAPI",
            subtitle="Async model load, async detect tasks with status polling and cancel",
        )
        layout = box.layout()

        layout.addWidget(self._build_model_section())
        layout.addWidget(self._build_detect_section())
        layout.addWidget(self._build_result_table(), 1)
        return box

    def _build_model_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        caption = QLabel(
            "The model is hundreds of megabytes, so loading is asynchronous and "
            "the model stays resident in the host once loaded."
        )
        caption.setProperty("ev_role", "section-caption")
        caption.setWordWrap(True)
        layout.addWidget(caption)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Model folder:"))
        self.model_folder_edit = QLineEdit()
        self.model_folder_edit.setPlaceholderText(
            "Leave empty to use the host's own model resource path (recommended)"
        )
        folder_row.addWidget(self.model_folder_edit, 1)
        layout.addLayout(folder_row)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        button_row.addWidget(self.action_button("Load Model", self._load_model))
        button_row.addWidget(self.action_button("Wait For Model", self._wait_for_model))
        button_row.addWidget(self.action_button("Model Status", self._model_status))
        button_row.addWidget(self.action_button("Unload Model", self._unload_model))
        layout.addLayout(button_row)

        self.model_status_label = QLabel("Model: unknown")
        self.model_status_label.setProperty("ev_role", "section-caption")
        # The resource path is long enough to widen the whole card if it is
        # allowed to stay on one line.
        self.model_status_label.setWordWrap(True)
        layout.addWidget(self.model_status_label)
        return section

    def _build_detect_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.chk_auto_load = QCheckBox("auto_load_model")
        self.chk_auto_load.setChecked(True)
        self.chk_auto_load.setToolTip(
            "Load the model on demand. Uncheck to fail fast with a 412 error instead."
        )
        self.chk_whole_project = QCheckBox("whole project")
        self.chk_whole_project.setToolTip(
            "Ignore the selected rows and detect every image of the loaded project."
        )

        # One column per option so each checkbox lines up with the button
        # underneath it. fix_checkbox_width keeps the labels from being
        # truncated once the columns get tight.
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        options = (
            self.chk_auto_load,
            self.chk_whole_project,
        )
        for column, check in enumerate(options):
            fix_checkbox_width(check)
            grid.addWidget(check, 0, column)
            grid.setColumnStretch(column, 1)

        buttons = (
            self.action_button("Detect Faces", self._detect),
            self.action_button("Task Status", self._detect_status),
            self.action_button("Cancel Detect", self._cancel_detect),
        )
        for column, button in enumerate(buttons):
            grid.addWidget(button, 1, column)

        layout.addLayout(grid)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Idle")
        self.progress_label.setProperty("ev_role", "section-caption")
        self.progress_label.setWordWrap(True)
        layout.addWidget(self.progress_label)

        self.task_label = QLabel("Task: -")
        self.task_label.setProperty("ev_role", "section-caption")
        self.task_label.setWordWrap(True)
        layout.addWidget(self.task_label)
        return section

    def _build_result_table(self) -> QWidget:
        self.result_table = QTableWidget(0, len(RESULT_COLUMNS))
        self.result_table.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.result_table.verticalHeader().setVisible(False)
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        return self.result_table

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _model_folder(self) -> str | None:
        folder = self.model_folder_edit.text().strip()
        return folder or None

    def _load_model(self) -> None:
        self._run(
            "face.load_model",
            lambda: evoto.face.load_model(model_folder=self._model_folder()),
        )

    def _wait_for_model(self) -> None:
        # Blocks until the model is ready; runs on the demo worker thread.
        self._run(
            "face.wait_for_model",
            lambda: evoto.face.wait_for_model(model_folder=self._model_folder()),
        )

    def _model_status(self) -> None:
        self._run("face.model_status", evoto.face.model_status)

    def _unload_model(self) -> None:
        self._run("face.unload_model", evoto.face.unload_model)

    def _detect(self) -> None:
        auto_load_model = self.chk_auto_load.isChecked()

        # Both helpers raise when nothing is loaded or selected yet; surface
        # that in the log instead of letting it escape into the Qt slot.
        try:
            if self.chk_whole_project.isChecked():
                project_id = self._project_id()
                image_ids = None
                self._log(f"Detect scope: whole project {project_id}")
            else:
                project_id = None
                image_ids = self._selected_ids()
                self._log(f"Detect scope: {len(image_ids)} image(s)")
        except RuntimeError as exc:
            self._log(f"Cannot detect: {exc}")
            return

        self.result_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting...")

        # detect() returns as soon as the host queues the task, so the UI stays
        # responsive and is driven entirely by the face.detect.* events below.
        self._run(
            "face.detect",
            lambda: evoto.face.detect(
                image_ids=image_ids,
                project_id=project_id,
                auto_load_model=auto_load_model,
            ),
        )

    def _detect_status(self) -> None:
        # Omitting task_id asks about whatever the host is running right now,
        # which also works after a restart of this demo.
        task_id = self._current_task_id or None
        self._run(
            "face.detect_status",
            lambda: evoto.face.detect_status(task_id, include_results=True),
        )

    def _cancel_detect(self) -> None:
        task_id = self._current_task_id or None
        self._run("face.cancel_detect", lambda: evoto.face.cancel_detect(task_id))

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _on_call_success(self, label: str, payload: object) -> None:
        super()._on_call_success(label, payload)
        if not isinstance(payload, dict):
            return
        # task_id is what separates a task payload from a model payload; both
        # carry a "status" field, so keying on that alone would confuse them.
        if FaceField.TASK_ID in payload:
            self._render_task_state(payload)
        elif FaceField.STATUS in payload:
            self._render_model_state(payload)

    def _render_model_state(self, payload: dict) -> None:
        status = payload.get(FaceField.STATUS, "-")
        folder = payload.get(FaceField.MODEL_FOLDER) or "(host default)"
        text = f"Model: {status}  folder={folder}"
        if status == FaceModelStatusValue.FAILED:
            text += f"  error={payload.get(FaceField.ERROR_MESSAGE, '-')}"
        self.model_status_label.setText(text)

    def _render_task_state(self, payload: dict) -> None:
        task_id = payload.get(FaceField.TASK_ID) or ""
        if task_id:
            self._current_task_id = task_id

        status = payload.get(FaceField.STATUS, "-")
        parts = [f"Task: {task_id or '-'}", f"status={status}"]
        if payload.get(FaceField.CANCEL_REQUESTED):
            parts.append("cancel requested")
        if FaceField.ELAPSED_MS in payload:
            parts.append(f"{payload[FaceField.ELAPSED_MS]}ms")
        self.task_label.setText("  ".join(parts))

        if FaceField.RESULTS in payload:
            self._render_detect_results(payload)
        else:
            self._render_task_counters(payload)

    def _render_task_counters(self, payload: dict) -> None:
        total = payload.get(FaceField.TOTAL, payload.get(FaceField.REQUESTED_COUNT, 0))
        self.progress_bar.setValue(int(payload.get(FaceField.PROGRESS, 0) or 0))
        self.progress_label.setText(
            "{ok} ok, {failed} failed of {total}".format(
                ok=payload.get(FaceField.SUCCESS_COUNT, 0),
                failed=payload.get(FaceField.FAILED_COUNT, 0),
                total=total,
            )
        )

    def _fill_result_row(self, row_index: int, row: dict) -> None:
        faces = row.get(FaceField.FACES) or []
        summary = " | ".join(
            "{age}/{gender}/{glasses}".format(
                age=face.get(FaceField.AGE, -1),
                gender=face.get(FaceField.GENDER, "-"),
                glasses="glasses" if face.get(FaceField.WEAR_GLASSES) else "no-glasses",
            )
            for face in faces
        )
        if not summary:
            # Either no face was found, or the image failed; reason says which.
            summary = row.get(FaceField.REASON, "-")

        cells = (
            str(row.get(FaceField.IMAGE_ID, "-")),
            str(row.get(FaceField.STATUS, "-")),
            str(row.get(FaceField.FACE_COUNT, "-")),
            summary,
            str(row.get(FaceField.ELAPSED_MS, "-")),
        )
        for column, value in enumerate(cells):
            self.result_table.setItem(row_index, column, QTableWidgetItem(value))

    def _append_result_row(self, row: dict) -> None:
        """Append one image's result as it streams in from face.detect.progress."""
        row_index = self.result_table.rowCount()
        self.result_table.insertRow(row_index)
        self._fill_result_row(row_index, row)
        self.result_table.scrollToBottom()

    def _render_detect_results(self, payload: dict) -> None:
        results = payload.get(FaceField.RESULTS) or []
        # The terminal event repeats every row, so rebuild rather than append -
        # this also repairs the table if a progress event was ever missed.
        self.result_table.setRowCount(len(results))
        for row_index, row in enumerate(results):
            self._fill_result_row(row_index, row)

        self.progress_bar.setValue(int(payload.get(FaceField.PROGRESS, 100) or 0))
        self.progress_label.setText(
            "{status}: {ok} ok, {failed} failed of {total}".format(
                status=payload.get(FaceField.STATUS, "done"),
                ok=payload.get(FaceField.SUCCESS_COUNT, 0),
                failed=payload.get(FaceField.FAILED_COUNT, 0),
                total=payload.get(FaceField.TOTAL, payload.get(FaceField.REQUESTED_COUNT, 0)),
            )
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_connected(self) -> None:
        super()._on_connected()
        self._register_face_events()
        self._run("face.model_status", evoto.face.model_status)

    def _on_disconnected(self) -> None:
        self._unregister_face_events()
        super()._on_disconnected()

    def _register_face_events(self) -> None:
        if self._face_event_callbacks:
            return
        for event_name in MODEL_EVENTS + DETECT_EVENTS:
            def callback(data, _event_name=event_name):
                self.face_event_received.emit(_event_name, data or {})

            evoto.on(event_name, callback)
            self._face_event_callbacks.append((event_name, callback))

    def _unregister_face_events(self) -> None:
        for event_name, callback in self._face_event_callbacks:
            try:
                evoto.off(event_name, callback)
            except Exception as exc:  # noqa: BLE001 - disconnect cleanup best effort
                logger.debug("Failed to unsubscribe %s: %s", event_name, exc)
        self._face_event_callbacks.clear()

    def _on_face_event_main(self, event_name: str, data: object) -> None:
        try:
            if not isinstance(data, dict):
                self._log(f"{event_name}: {data}")
                return

            if event_name in MODEL_EVENTS:
                self._render_model_state(data)
                self._log(
                    f"{event_name}: status={data.get(FaceField.STATUS, '-')}, "
                    f"folder={data.get(FaceField.MODEL_FOLDER, '-')}, "
                    f"error={data.get(FaceField.ERROR_MESSAGE) or '-'}"
                )
                return

            progress = max(0, min(int(data.get(FaceField.PROGRESS, 0) or 0), 100))
            total = int(data.get(FaceField.TOTAL, 0) or 0)
            completed = int(data.get(FaceField.COMPLETED_COUNT, 0) or 0)
            task_id = data.get(FaceField.TASK_ID) or ""
            if task_id:
                self._current_task_id = task_id

            if event_name == FaceCmd.DETECT_STARTED:
                self.progress_bar.setValue(0)
                self.progress_label.setText(f"Started, {total} image(s) queued")
                self.task_label.setText(f"Task: {task_id or '-'}  status=running")
            elif event_name == FaceCmd.DETECT_PROGRESS:
                self.progress_bar.setValue(progress)
                self.progress_label.setText(
                    f"Detecting {completed}/{total} ({progress}%)"
                )
                # Each progress event carries the result of the image that just
                # finished, so the table fills in live.
                row = data.get(FaceField.RESULT)
                if isinstance(row, dict):
                    self._append_result_row(row)
            elif event_name == FaceCmd.DETECT_FAILED:
                self.task_label.setText(f"Task: {task_id or '-'}  status=failed")
                self.progress_label.setText(
                    f"Failed: {data.get(FaceField.ERROR_MESSAGE, 'unknown error')}"
                )
            elif event_name in TERMINAL_DETECT_EVENTS:
                # completed / canceled both carry the full task state including
                # the per-image rows, so the table can be filled straight from
                # the event without another round trip.
                self._render_task_state(data)

            row = data.get(FaceField.RESULT)
            row_note = ""
            if isinstance(row, dict):
                row_note = (
                    f", result={row.get(FaceField.STATUS, '-')}"
                    f"/{row.get(FaceField.FACE_COUNT, row.get(FaceField.REASON, '-'))}"
                )
            self._log(
                f"{event_name}: task={task_id or '-'}, "
                f"image={data.get(FaceField.IMAGE_ID, '-')}, "
                f"progress={progress}%, completed={completed}/{total}{row_note}"
            )
        except Exception as exc:  # noqa: BLE001 - keep Qt slot exceptions non-fatal
            logger.exception("Failed to handle face event %s", event_name)
            self._log(f"{event_name}: event handler failed: {exc}")


def main() -> int:
    app = QApplication(sys.argv)
    window = FaceDetectDemoWindow()
    apply_theme(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
