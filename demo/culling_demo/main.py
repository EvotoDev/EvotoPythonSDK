"""Culling automation demo."""

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
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QLabel,
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import evoto
from demo.shared import Card, Phase2DemoWindow, apply_theme
from evoto.core.api_commands import CullingCmd
from evoto.core.api_fields import CullingField, Field

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("culling_demo")


class CullingDemoWindow(Phase2DemoWindow):
    """Dedicated CullingAPI debug window."""

    culling_event_received = Signal(str, object)

    window_title = "Culling Results Demo"
    connect_title = "Culling Results Demo"
    image_hint = "Select rows to limit culling result inspection when needed."

    def __init__(self):
        self._culling_event_callbacks: list[tuple[str, object]] = []
        self._active_culling_projects: set[int] = set()
        self._finished_culling_projects: set[int] = set()
        self._last_culling_progress: dict[int, int] = {}
        super().__init__()
        self.culling_event_received.connect(self._on_culling_event_main)

    def build_actions_panel(self) -> QWidget:
        box = Card(
            title="CullingAPI",
            subtitle="Task controls and scoped culling result queries",
        )

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self._culling_tab_group = QButtonGroup(self)
        self.btn_tab_task = QPushButton("Task")
        self.btn_tab_results = QPushButton("Image Results")
        self.btn_tab_faces = QPushButton("Faces")
        self.btn_tab_clusters = QPushButton("Clusters")
        self.btn_tab_qr_code = QPushButton("QR Code")
        for button in (
            self.btn_tab_task,
            self.btn_tab_results,
            self.btn_tab_faces,
            self.btn_tab_clusters,
            self.btn_tab_qr_code,
        ):
            button.setObjectName("taskSegBtn")
            button.setCheckable(True)
            button.setMinimumHeight(24)
        self._culling_tab_group.addButton(self.btn_tab_task, 0)
        self._culling_tab_group.addButton(self.btn_tab_results, 1)
        self._culling_tab_group.addButton(self.btn_tab_faces, 2)
        self._culling_tab_group.addButton(self.btn_tab_clusters, 3)
        self._culling_tab_group.addButton(self.btn_tab_qr_code, 4)
        self.btn_tab_task.setChecked(True)
        for button in (
            self.btn_tab_task,
            self.btn_tab_results,
            self.btn_tab_faces,
            self.btn_tab_clusters,
            self.btn_tab_qr_code,
        ):
            tab_row.addWidget(button, 1)
        box.layout().addLayout(tab_row)

        self.scope_label = QLabel("Scope: selected image rows, or all loaded rows when nothing is selected.")
        self.scope_label.setProperty("ev_role", "section-caption")
        box.layout().addWidget(self.scope_label)

        self._culling_stack = QStackedWidget()
        self._culling_stack.addWidget(self._build_task_page())
        self._culling_stack.addWidget(self._build_image_results_page())
        self._culling_stack.addWidget(self._build_faces_page())
        self._culling_stack.addWidget(self._build_clusters_page())
        self._culling_stack.addWidget(self._build_qr_code_page())
        self._culling_tab_group.buttonClicked.connect(
            lambda button: self._culling_stack.setCurrentIndex(self._culling_tab_group.id(button))
        )
        box.layout().addWidget(self._culling_stack, 1)

        return box

    def _build_task_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        for button in (
            self.action_button("Status", self._culling_status),
            self.action_button("Start", self._culling_start),
            self.action_button("Restart", self._culling_restart),
            self.action_button("Stop", self._culling_stop),
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label = QLabel("Progress: idle")
        self.progress_label.setProperty("ev_role", "section-caption")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        hint = QLabel(
            "Start/restart accepts the task first; progress and final state "
            "arrive through culling.* events."
        )
        hint.setProperty("ev_role", "section-caption")
        layout.addWidget(hint)
        layout.addStretch(1)

        return page

    def _build_image_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.filter_ai_selected = QCheckBox("AI selected")
        self.filter_candidate = QCheckBox("Candidate")
        self.filter_blurry = QCheckBox("Blurry")
        self.filter_sharp = QCheckBox("Sharp")
        self.filter_closed_eyes = QCheckBox("Closed eyes")
        self.filter_overexposed = QCheckBox("Overexposed")
        self.filter_underexposed = QCheckBox("Underexposed")
        self.filter_similar = QCheckBox("Similar")

        filter_groups = QHBoxLayout()
        filter_groups.setSpacing(10)
        filter_groups.addWidget(self._filter_group(
            "Selection",
            (
                self.filter_ai_selected,
                self.filter_candidate,
            ),
        ))
        filter_groups.addWidget(self._filter_group(
            "Quality",
            (
                self.filter_blurry,
                self.filter_sharp,
                self.filter_closed_eyes,
            ),
        ))
        filter_groups.addWidget(self._filter_group(
            "Exposure",
            (
                self.filter_overexposed,
                self.filter_underexposed,
            ),
        ))
        filter_groups.addWidget(self._filter_group(
            "Grouping",
            (
                self.filter_similar,
            ),
        ))
        layout.addLayout(filter_groups)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addStretch(1)
        action_row.addWidget(self.action_button("List Image Results", self._culling_results))
        layout.addLayout(action_row)
        layout.addStretch(1)
        return page

    @staticmethod
    def _filter_group(title: str, checkboxes: tuple[QCheckBox, ...]) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(6)
        for checkbox in checkboxes:
            layout.addWidget(checkbox)
        layout.addStretch(1)
        return group

    def _build_faces_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        hint = QLabel("Uses only image scope. Image result filters do not apply.")
        hint.setProperty("ev_role", "section-caption")
        layout.addWidget(hint)
        layout.addWidget(self.action_button("List Faces", self._culling_faces))
        layout.addStretch(1)
        return page

    def _build_clusters_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.cluster_type_combo = self._combo(
            [
                ("All clusters", ""),
                ("Similar clusters", "similar"),
                ("Person clusters", "person"),
            ],
            default_value="",
        )
        hint = QLabel("Uses image scope and cluster type. Image result filters do not apply.")
        hint.setProperty("ev_role", "section-caption")
        layout.addWidget(hint)
        layout.addWidget(self.cluster_type_combo)
        layout.addWidget(self.action_button("List Clusters", self._culling_clusters))
        layout.addStretch(1)
        return page

    def _build_qr_code_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.qr_force_scan = QCheckBox("Force re-scan checked images")
        hint = QLabel(
            "Scan selected rows, or current project when nothing is selected. "
            "Results contain image_id, absolute_path, qr_code_checked and has_qr_code."
        )
        hint.setProperty("ev_role", "section-caption")

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.qr_force_scan)
        actions.addStretch(1)
        actions.addWidget(self.action_button("Scan QR Codes", self._qr_code_scan))
        actions.addWidget(self.action_button("List QR Results", self._qr_code_results))

        layout.addWidget(hint)
        layout.addLayout(actions)
        layout.addStretch(1)
        return page

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("ev_role", "section-title")
        return label

    def _culling_status(self) -> None:
        self._run(
            "culling.status",
            lambda: evoto.culling.status(
                self._project_id(),
                image_ids=self._query_image_ids(),
            ),
        )

    def _culling_results(self) -> None:
        self._run(
            "culling.list_results",
            lambda: evoto.culling.list_results(
                self._project_id(),
                image_ids=self._query_image_ids(),
                filters=self._result_filters(),
            ),
        )

    def _culling_faces(self) -> None:
        self._run(
            "culling.list_faces",
            lambda: evoto.culling.list_faces(
                self._project_id(),
                image_ids=self._query_image_ids(),
            ),
        )

    def _culling_clusters(self) -> None:
        self._run(
            "culling.list_clusters",
            lambda: evoto.culling.list_clusters(
                self._project_id(),
                image_ids=self._query_image_ids(),
                cluster_type=self._combo_value(self.cluster_type_combo) or None,
            ),
        )

    def _culling_start(self) -> None:
        self._run(
            "culling.start",
            lambda: evoto.culling.start(self._project_id()),
        )

    def _culling_restart(self) -> None:
        self._run(
            "culling.restart",
            lambda: evoto.culling.restart(self._project_id()),
        )

    def _culling_stop(self) -> None:
        self._run(
            "culling.stop",
            lambda: evoto.culling.stop(self._project_id()),
        )

    def _qr_code_scan(self) -> None:
        self._run(
            "culling.scan_qr_codes",
            lambda: evoto.culling.scan_qr_codes(
                self._project_id(),
                image_ids=self._query_image_ids(),
                force=self.qr_force_scan.isChecked(),
            ),
        )

    def _qr_code_results(self) -> None:
        self._run(
            "culling.list_qr_code_results",
            lambda: evoto.culling.list_qr_code_results(
                self._project_id(),
                image_ids=self._query_image_ids(),
            ),
        )

    def _query_image_ids(self) -> list[int]:
        image_ids = self.image_table.selected_image_ids()
        if image_ids:
            self._log(f"Query scope: selected rows, count={len(image_ids)}")
        else:
            self._log("Query scope: no selected rows, host queries current project")
        return image_ids

    def _result_filters(self) -> dict:
        filters = {}
        if self.filter_ai_selected.isChecked():
            filters[CullingField.AI_SELECTED] = True
        if self.filter_candidate.isChecked():
            filters[CullingField.CANDIDATE] = True
        if self.filter_blurry.isChecked():
            filters[CullingField.BLURRY] = True
        if self.filter_sharp.isChecked():
            filters[CullingField.SHARP] = True
        if self.filter_closed_eyes.isChecked():
            filters[CullingField.CLOSED_EYES] = True
        if self.filter_overexposed.isChecked():
            filters[CullingField.OVEREXPOSED] = True
        if self.filter_underexposed.isChecked():
            filters[CullingField.UNDEREXPOSED] = True
        if self.filter_similar.isChecked():
            filters[CullingField.SIMILAR] = True
        return filters

    def _on_connected(self) -> None:
        super()._on_connected()
        self._register_culling_events()

    def _on_disconnected(self) -> None:
        self._unregister_culling_events()
        super()._on_disconnected()

    def _register_culling_events(self) -> None:
        if self._culling_event_callbacks:
            return
        for event_name in (
            CullingCmd.STARTED,
            CullingCmd.PROGRESS,
            CullingCmd.COMPLETED,
            CullingCmd.FAILED,
            CullingCmd.CANCELED,
            CullingCmd.QR_CODE_STARTED,
            CullingCmd.QR_CODE_PROGRESS,
            CullingCmd.QR_CODE_COMPLETED,
            CullingCmd.QR_CODE_FAILED,
        ):
            def callback(data, _event_name=event_name):
                self.culling_event_received.emit(_event_name, data or {})

            evoto.on(event_name, callback)
            self._culling_event_callbacks.append((event_name, callback))

    def _unregister_culling_events(self) -> None:
        for event_name, callback in self._culling_event_callbacks:
            try:
                evoto.off(event_name, callback)
            except Exception as exc:  # noqa: BLE001 - disconnect cleanup best effort
                logger.debug("Failed to unsubscribe %s: %s", event_name, exc)
        self._culling_event_callbacks.clear()

    def _on_culling_event_main(self, event_name: str, data: object) -> None:
        try:
            if not isinstance(data, dict):
                self._log(f"{event_name}: {data}")
                return

            project_id = data.get(CullingField.PROJECT_ID)
            current_project_id = self.loader.project_id
            if current_project_id and project_id and int(project_id) != int(current_project_id):
                return
            if project_id is None:
                return
            project_id = int(project_id)

            if event_name in (
                CullingCmd.QR_CODE_STARTED,
                CullingCmd.QR_CODE_PROGRESS,
                CullingCmd.QR_CODE_COMPLETED,
                CullingCmd.QR_CODE_FAILED,
            ):
                self._on_qr_code_event(event_name, project_id, data)
                return

            progress = max(0, min(int(data.get(CullingField.PROGRESS, 0) or 0), 100))
            total = int(data.get("total", 0) or 0)
            seconds = data.get(CullingField.SECONDS_REMAINING, "-")
            status = data.get(Field.STATUS, "-")
            success = data.get("success", "-")

            if event_name == CullingCmd.STARTED:
                self._active_culling_projects.add(project_id)
                self._finished_culling_projects.discard(project_id)
                self._last_culling_progress[project_id] = 0
                progress = 0
            elif event_name == CullingCmd.PROGRESS:
                if project_id not in self._active_culling_projects:
                    return
                if project_id in self._finished_culling_projects:
                    return
                last_progress = self._last_culling_progress.get(project_id, -1)
                if progress <= last_progress:
                    return
                self._last_culling_progress[project_id] = progress
            elif event_name in (CullingCmd.COMPLETED, CullingCmd.FAILED, CullingCmd.CANCELED):
                self._active_culling_projects.discard(project_id)
                self._finished_culling_projects.add(project_id)
                if event_name == CullingCmd.COMPLETED:
                    progress = 100
                self._last_culling_progress[project_id] = progress

            if event_name == CullingCmd.COMPLETED:
                completed = total
            else:
                completed = (total * progress + 99) // 100 if total > 0 else 0

            self.progress_bar.setValue(max(0, min(progress, 100)))
            self.progress_label.setText(
                f"Progress: {progress}%  {completed}/{total}  "
                f"status={status}  eta={seconds}s"
            )
            self._log(
                f"{event_name}: project={project_id}, progress={progress}%, "
                f"completed={completed}/{total}, eta={seconds}s, "
                f"status={status}, success={success}, reason={data.get('reason', '-')}"
            )
        except Exception as exc:  # noqa: BLE001 - keep Qt slot exceptions non-fatal
            logger.exception("Failed to handle culling event %s", event_name)
            self._log(f"{event_name}: event handler failed: {exc}")

    def _on_qr_code_event(self, event_name: str, project_id: int, data: dict) -> None:
        requested = int(data.get(CullingField.REQUESTED_COUNT, 0) or 0)
        completed = int(data.get(CullingField.COMPLETED_COUNT, 0) or 0)
        progress = int(data.get(CullingField.PROGRESS, 0) or 0)
        if requested > 0 and CullingField.PROGRESS not in data:
            progress = (completed * 100) // requested
        progress = max(0, min(progress, 100))
        status = data.get(Field.STATUS, "-")
        image_id = data.get(CullingField.IMAGE_ID, "-")
        has_qr_code = data.get(CullingField.HAS_QR_CODE, "-")
        absolute_path = data.get(CullingField.ABSOLUTE_PATH, "-")

        self.progress_bar.setValue(progress)
        self.progress_label.setText(
            f"QR Code: {progress}%  {completed}/{requested}  status={status}"
        )
        self._log(
            f"{event_name}: project={project_id}, image={image_id}, "
            f"progress={progress}%, completed={completed}/{requested}, "
            f"has_qr_code={has_qr_code}, status={status}, path={absolute_path}"
        )


def main() -> int:
    app = QApplication(sys.argv)
    window = CullingDemoWindow()
    apply_theme(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
