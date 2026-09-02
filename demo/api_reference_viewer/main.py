"""Evoto Plugin SDK - API Reference Viewer

A Qt Assistant-style dark-themed documentation browser for the Evoto Plugin SDK.
"""

import sys
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QStackedWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from evoto import __version__ as SDK_VERSION

from api_reference_data import (
    MODULE_ORDER, MODULE_DATA, WORKFLOW_GROUPS, SIDEBAR_DISPLAY_NAMES,
    TOOL_BUNDLES_ORDER, TOOL_BUNDLE_DATA,
)
from widgets.sidebar import Sidebar
from widgets.overview_page import OverviewPage
from widgets.detail_page import DetailPage
from widgets.welcome_page import WelcomePage

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('api_reference_viewer')

DEMO_REGISTRY = {
    "project_image_demo": "demo/project_image_demo/main.py",
    "preset_demo":        "demo/preset_demo/main.py",
    "preset_export_demo": "demo/preset_export_demo/main.py",
    "watcher_demo":       "demo/watcher_demo/main.py",
    "hot_folder_demo":    "demo/hot_folder_demo/main.py",
    "runtime_demo":       "demo/runtime_demo/main.py",
    "user_info_demo":     "demo/user_info_demo/main.py",
    "metadata_demo":      "demo/metadata_demo/main.py",
    "library_demo":       "demo/library_demo/main.py",
    "culling_demo":       "demo/culling_demo/main.py",
    "edit_recipe_demo":   "demo/edit_recipe_demo/main.py",
    "face_detect_demo":   "demo/face_detect_demo/main.py",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Evoto Plugin SDK - API Reference")
        self.resize(1200, 780)
        self._demo_procs: list = []
        self._current_module: str | None = None
        self._init_ui()
        self._sidebar.select_module("__overview__")

    def _init_ui(self):
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topBar")
        topbar.setFixedHeight(40)
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(16, 0, 16, 0)
        topbar_layout.setSpacing(10)

        title_label = QLabel("Evoto Plugin SDK - API Reference")
        title_label.setObjectName("topBarTitle")
        topbar_layout.addWidget(title_label)

        version_label = QLabel(f"v{SDK_VERSION}")
        version_label.setObjectName("versionBadge")
        topbar_layout.addWidget(version_label)

        topbar_layout.addStretch()
        root_layout.addWidget(topbar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self._sidebar = Sidebar(WORKFLOW_GROUPS, SIDEBAR_DISPLAY_NAMES)
        self._sidebar.setMinimumWidth(220)
        self._sidebar.setMaximumWidth(260)
        self._sidebar.module_selected.connect(self._on_module_selected)
        splitter.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")

        self._welcome = WelcomePage()
        self._welcome.module_requested.connect(self._on_welcome_module_requested)
        self._stack.addWidget(self._welcome)

        # Both SDK modules and tool bundles share the OverviewPage layout;
        # we keep a single registry so the rest of the window (`_on_method_clicked`,
        # `_on_open_demo`, `_on_back`) treats them uniformly.
        self._page_data: dict[str, dict] = {**MODULE_DATA, **TOOL_BUNDLE_DATA}

        # Type-name -> (module_key, method_index) so the DetailPage can
        # turn parameter-type references like ``FileFormat`` into clickable
        # links that jump to the corresponding entry's detail view.
        self._type_index: dict[str, tuple[str, int]] = self._build_type_index()

        self._overview_pages: dict[str, OverviewPage] = {}
        for key in (*MODULE_ORDER, *TOOL_BUNDLES_ORDER):
            data = self._page_data[key]
            page = OverviewPage(show_demo_btn=data.get("demo_key") is not None)
            page.load_module(key, data)
            page.method_clicked.connect(self._on_method_clicked)
            page.open_demo_clicked.connect(self._on_open_demo)
            self._stack.addWidget(page)
            self._overview_pages[key] = page

        self._detail = DetailPage(type_index=self._type_index)
        self._detail.back_clicked.connect(self._on_back)
        self._detail.type_link_clicked.connect(self._on_method_clicked)
        self._stack.addWidget(self._detail)

        splitter.addWidget(self._stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root_layout.addWidget(splitter)
        self.setCentralWidget(central)

    def _build_type_index(self) -> dict[str, tuple[str, int]]:
        """Map every enum / dataclass / class entry name to ``(module_key, idx)``.

        Used by the DetailPage to turn parameter type references (e.g.
        ``fmt: FileFormat | str``) into hyperlinks that navigate to the
        matching entry. Method entries are intentionally excluded - we
        do not want type-link tokens to point at functions.
        """
        index: dict[str, tuple[str, int]] = {}
        for module_key, data in self._page_data.items():
            for i, m in enumerate(data.get("methods", [])):
                if m.get("kind") in {"enum", "dataclass", "class"}:
                    index[m["name"]] = (module_key, i)
        return index

    def _on_module_selected(self, module_key: str):
        if module_key == "__overview__":
            self._current_module = None
            self._stack.setCurrentWidget(self._welcome)
            return
        page = self._overview_pages.get(module_key)
        if page is None:
            # Group headers like __demo_workflow__ don't have a dedicated
            # page - stay on whatever's currently shown.
            return
        self._current_module = module_key
        self._stack.setCurrentWidget(page)

    def _on_welcome_module_requested(self, module_key: str):
        self._sidebar.select_module(module_key)

    def _on_method_clicked(self, module_key: str, method_idx: int):
        data = self._page_data[module_key]
        method = data["methods"][method_idx]
        self._detail.load_method(method)
        self._stack.setCurrentWidget(self._detail)

    def _on_back(self):
        if self._current_module and self._current_module in self._overview_pages:
            self._stack.setCurrentWidget(self._overview_pages[self._current_module])
        else:
            self._stack.setCurrentWidget(self._welcome)

    def _on_open_demo(self, module_key: str):
        demo_key = self._page_data[module_key].get("demo_key")
        if not demo_key or demo_key not in DEMO_REGISTRY:
            logger.warning("No demo available for module: %s", module_key)
            return

        import os
        import subprocess

        script = REPO_ROOT / DEMO_REGISTRY[demo_key]
        demo_dir = script.parent
        # Reuse whichever interpreter is running the viewer itself so the
        # child demo inherits its venv (PySide6, evoto_plugin_sdk, ...). This
        # also works on Windows, where venvs live under ``Scripts\`` rather
        # than ``bin/`` - the old hard-coded ``.venv/bin/python`` path
        # raised ``FileNotFoundError: [WinError 2]`` there.
        python = sys.executable
        qss_path = str(Path(__file__).parent / "dark_theme.qss")
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT), "EVOTO_DEMO_QSS": qss_path}

        try:
            proc = subprocess.Popen(
                [python, str(script)],
                cwd=str(demo_dir),
                env=env,
            )
            self._demo_procs.append(proc)
            logger.info(
                "Launched demo %s (pid=%d, python=%s, cwd=%s)",
                demo_key, proc.pid, python, demo_dir,
            )
        except Exception:
            logger.exception(
                "Failed to launch demo %s (python=%s, script=%s)",
                demo_key, python, script,
            )

    def closeEvent(self, event):
        for proc in self._demo_procs:
            if proc.poll() is None:
                proc.terminate()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    font = QFont()
    font.setFamily("SF Pro Text")
    font.setPointSize(12)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    qss_path = Path(__file__).parent / "dark_theme.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
