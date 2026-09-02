"""Reusable project + image ID loader widget."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox,
)

import evoto


class ProjectImageLoader(QGroupBox):
    """GroupBox that loads the current project and its image IDs.

    Signals:
        project_loaded(int, str): (project_id, project_name)
        images_loaded(list): list of int image IDs
        log(str): log message for the host demo to display
    """

    project_loaded = Signal(int, str)
    images_loaded = Signal(list)
    log = Signal(str)

    def __init__(self, title: str = 'WORKFLOW REQUEST', parent=None):
        super().__init__(title, parent)
        self._current_project_id: int | None = None
        self._image_ids: list[int] = []

        layout = QVBoxLayout(self)

        proj_row = QHBoxLayout()
        proj_row.setSpacing(8)
        lp = QLabel('Project')
        lp.setProperty('ev_role', 'field-label')
        lp.setFixedWidth(70)
        self.project_display = QLineEdit()
        self.project_display.setReadOnly(True)
        self.project_display.setPlaceholderText('Click Load Current')
        self.btn_load_project = QPushButton('Load Current')
        self.btn_load_project.setEnabled(False)
        self.btn_load_project.clicked.connect(self.load_project)
        proj_row.addWidget(lp)
        proj_row.addWidget(self.project_display, 1)
        proj_row.addWidget(self.btn_load_project)
        layout.addLayout(proj_row)

        ids_row = QHBoxLayout()
        ids_row.setSpacing(8)
        li = QLabel('Images')
        li.setProperty('ev_role', 'field-label')
        li.setFixedWidth(70)
        self.image_ids_line = QLineEdit()
        self.image_ids_line.setReadOnly(True)
        self.image_ids_line.setPlaceholderText('Click Load Images')
        self.btn_load_images = QPushButton('Load Images')
        self.btn_load_images.setEnabled(False)
        self.btn_load_images.clicked.connect(lambda: self.load_images(max_count=0))
        ids_row.addWidget(li)
        ids_row.addWidget(self.image_ids_line, 1)
        ids_row.addWidget(self.btn_load_images)
        layout.addLayout(ids_row)

        hint = QLabel('Auto-loads up to 5 images on connect. Click "Load Images" for all.')
        hint.setProperty('ev_role', 'field-label')
        hint.setStyleSheet('font-size: 10px; padding-left: 78px;')
        layout.addWidget(hint)

    def set_enabled(self, enabled: bool):
        self.btn_load_project.setEnabled(enabled)
        self.btn_load_images.setEnabled(enabled)

    @property
    def project_id(self) -> int | None:
        return self._current_project_id

    @property
    def image_ids(self) -> list[int]:
        return list(self._image_ids)

    def _update_display(self):
        if not self._image_ids:
            self.image_ids_line.setText('')
            self.image_ids_line.setToolTip('')
            return
        shown = self._image_ids[:5]
        suffix = f' ... (+{len(self._image_ids) - 5})' if len(self._image_ids) > 5 else ''
        self.image_ids_line.setText(', '.join(str(x) for x in shown) + suffix)
        self.image_ids_line.setToolTip(', '.join(str(x) for x in self._image_ids))

    def load_project(self):
        try:
            result = evoto.project.current()
            proj = result.get('project', {})
            pid = proj.get('id', '')
            name = proj.get('name', '')
            self._current_project_id = int(pid) if pid else None
            display = f'{name}  (ID: {pid})' if name else str(pid)
            self.project_display.setText(display)
            self.log.emit(f'Current project: id={pid} name={name}')
            self.project_loaded.emit(self._current_project_id or 0, name)
        except Exception as exc:
            self.log.emit(f'Failed to load project: {exc}')

    def load_images(self, max_count: int = 0):
        if not self._current_project_id:
            if max_count == 0:
                self.log.emit('No project loaded')
            return
        try:
            images = evoto.image.list(self._current_project_id)
            values = [int(img.get('id')) for img in images if img.get('id')]
            if max_count > 0 and len(values) > max_count:
                values = values[:max_count]
            self._image_ids = values
            self._update_display()
            self.log.emit(f'Loaded {len(values)} image IDs' + (f' (max {max_count})' if max_count > 0 else ''))
            self.images_loaded.emit(list(self._image_ids))
        except Exception as exc:
            self.log.emit(f'Failed to load images: {exc}')

    def auto_load(self, max_images: int = 5):
        """Load project then images - call after connect."""
        self.load_project()
        self.load_images(max_count=max_images)
