"""Welcome / Overview page - first landing page of the API Reference Viewer.

Designed as a scrollable, onboarding-oriented document that tells a new
plugin author:

    1. What the Evoto Plugin SDK actually is.
    2. How a Python plugin talks to the Evoto C++ host (architecture).
    3. How to install, set up a plugin directory, and write ``plugin.json``.
    4. The two run-time modes (blocking worker vs. non-blocking Qt GUI).
    5. The module map and where to drill in for details.
    6. A typical end-to-end workflow: import -> preset -> export.
    7. How to run the bundled demos.

The layout reuses the ``docSection`` / ``docBlock`` visual vocabulary from
the detail page so it feels native to the Qt-doc aesthetic.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QTextEdit,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QCursor


# --------------------------------------------------------------------- helpers


def _mono_font(size: int = 12) -> QFont:
    f = QFont("SF Mono", size)
    f.setStyleHint(QFont.Monospace)
    return f


def _make_section(title: str, subtitle: str = "") -> tuple:
    """Create a ``#docSection`` panel; returns (panel, body_layout)."""
    panel = QFrame()
    panel.setObjectName("docSection")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(10)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("docSectionTitle")
    layout.addWidget(title_lbl)

    if subtitle:
        sub = QLabel(subtitle)
        sub.setObjectName("docSectionSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(sub)

    body = QVBoxLayout()
    body.setContentsMargins(0, 0, 0, 0)
    body.setSpacing(8)
    layout.addLayout(body)

    return panel, body


def _code_block(code: str, *, min_height: int = 0, max_height: int = 0) -> QTextEdit:
    te = QTextEdit()
    te.setObjectName("codeBlock")
    te.setReadOnly(True)
    te.setFont(_mono_font(12))
    te.setLineWrapMode(QTextEdit.NoWrap)
    te.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    te.setPlainText(code.rstrip("\n"))
    if min_height:
        te.setMinimumHeight(min_height)
    if max_height:
        te.setMaximumHeight(max_height)
    else:
        # Auto-fit: 20px per line + 20px padding.
        lines = code.count("\n") + 1
        te.setFixedHeight(min(max(lines * 20 + 22, 60), 420))
    return te


def _prose(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setObjectName("proseText")
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
    lbl.setTextFormat(Qt.RichText)
    return lbl


def _bullet_list(items: list[str]) -> QLabel:
    html = (
        '<ul style="margin:0 0 0 18px; padding:0; line-height:170%;">'
        + "".join(f"<li>{it}</li>" for it in items)
        + "</ul>"
    )
    lbl = QLabel(html)
    lbl.setTextFormat(Qt.RichText)
    lbl.setWordWrap(True)
    lbl.setObjectName("proseText")
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl


def _kv_row(key: str, value: str) -> QFrame:
    """Inner ``#docBlock`` row showing a label on the left and prose on the right."""
    block = QFrame()
    block.setObjectName("docBlock")
    lay = QHBoxLayout(block)
    lay.setContentsMargins(12, 8, 12, 8)
    lay.setSpacing(12)

    k = QLabel(key)
    k.setObjectName("kvKey")
    k.setMinimumWidth(150)
    k.setMaximumWidth(170)
    k.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    k.setWordWrap(True)
    lay.addWidget(k, 0)

    v = QLabel(value)
    v.setObjectName("kvValue")
    v.setWordWrap(True)
    v.setTextFormat(Qt.RichText)
    v.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lay.addWidget(v, 1)
    return block


# --------------------------------------------------------------------- cards


class _ModuleCard(QFrame):
    """Clickable module tile used inside the Module Map grid."""

    clicked = Signal(str)

    def __init__(self, title: str, import_path: str, desc: str, key: str, parent=None):
        super().__init__(parent)
        self._key = key
        self.setObjectName("moduleCard")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)

        head_row = QHBoxLayout()
        head_row.setSpacing(6)
        name = QLabel(title)
        name.setObjectName("moduleCardTitle")
        head_row.addWidget(name)
        head_row.addStretch(1)
        arrow = QLabel("\u2192")
        arrow.setObjectName("moduleCardArrow")
        head_row.addWidget(arrow)
        lay.addLayout(head_row)

        imp = QLabel(import_path)
        imp.setObjectName("moduleCardImport")
        imp.setFont(_mono_font(11))
        lay.addWidget(imp)

        body = QLabel(desc)
        body.setObjectName("moduleCardDesc")
        body.setWordWrap(True)
        lay.addWidget(body)

    def mousePressEvent(self, ev):
        ev.accept()
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.clicked.emit(self._key)


# --------------------------------------------------------------------- page


class WelcomePage(QWidget):
    """Landing page shown when the user clicks "Overview" in the sidebar."""

    module_requested = Signal(str)  # emits module key, e.g. "ProjectAPI"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    # ------------------------------------------------------------------ UI --

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(20, 20, 20, 24)
        root.setSpacing(14)

        root.addWidget(self._build_hero())
        root.addWidget(self._build_what_is())
        root.addWidget(self._build_architecture())
        root.addWidget(self._build_install_and_quickstart())
        root.addWidget(self._build_runtime_modes())
        root.addWidget(self._build_manifest())
        root.addWidget(self._build_module_map())
        root.addWidget(self._build_workflow())
        root.addWidget(self._build_demos())
        root.addWidget(self._build_next_steps())
        root.addStretch(1)

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ----- Hero -------------------------------------------------------------

    def _build_hero(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("welcomeHero")

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        title = QLabel("Evoto Plugin SDK")
        title.setObjectName("heroTitle")
        lay.addWidget(title)

        subtitle = QLabel(
            "Build Python plugins and automation tools that drive the Evoto desktop "
            "host \u2014 manage projects, import images, apply presets, run exports, "
            "and watch folders, all through a simple Python API."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        badges = QHBoxLayout()
        badges.setSpacing(8)
        for text in ("SDK v1.0.0", "Python \u2265 3.10", "Local IPC \u00b7 JSON-RPC 2.0"):
            b = QLabel(text)
            b.setObjectName("heroBadge")
            badges.addWidget(b)
        badges.addStretch(1)
        lay.addLayout(badges)

        return frame

    # ----- What it is -------------------------------------------------------

    def _build_what_is(self) -> QWidget:
        panel, body = _make_section(
            "What is the Evoto Plugin SDK?",
            "A Python layer that talks to the Evoto C++ host over local IPC.",
        )

        body.addWidget(_prose(
            "Evoto is a desktop retouching app. The Plugin SDK exposes the host's "
            "internal workflow as a <b>clean Python API</b> so you can automate it, "
            "script it, or embed a Qt UI next to it. Plugins run as a separate "
            "Python process that the host launches and supervises, or as an external "
            "script that connects to a running host."
        ))

        body.addWidget(QLabel("Typical things you can do:"))
        body.addWidget(_bullet_list([
            "<b>Manage projects</b> \u2014 create / list / rename / delete projects and groups.",
            "<b>Import images</b> \u2014 synchronously or asynchronously, with lifecycle events.",
            "<b>Apply presets</b> \u2014 list, apply, reset beauty / color preset suits.",
            "<b>Export images</b> \u2014 fully custom options or saved export presets, with pause / resume / retry.",
            "<b>Watch folders</b> \u2014 react to new files, and auto-export newly imported images.",
            "<b>Read user info</b> \u2014 display name, credit balance, cloud storage, subscription state via <code>evoto.user.info()</code>.",
            "<b>Register tasks</b> \u2014 expose Python callables to the host via <code>@evoto.task</code>.",
        ]))

        return panel

    # ----- Architecture -----------------------------------------------------

    def _build_architecture(self) -> QWidget:
        panel, body = _make_section(
            "How it works \u2014 Architecture",
            "One local IPC connection, JSON-RPC 2.0 in both directions, plus a push channel for events.",
        )

        diagram = (
            "   +----------------------+                 +------------------------+\n"
            "   |   Evoto C++ Host     |  <-- RPC -->    |   Your Python plugin   |\n"
            "   |  (PluginManager)     |                 |   (import evoto)       |\n"
            "   |                      |                 |                        |\n"
            "   |  ProjectApiService   |                 |   evoto.project        |\n"
            "   |  ImageApiService     |                 |   evoto.image          |\n"
            "   |  PresetApiService    |  <-- events --  |   evoto.preset         |\n"
            "   |  ExportApiService    |                 |   evoto.export         |\n"
            "   |  FolderWatchService  |                 |   evoto.watcher        |\n"
            "   |                      |                 |   evoto.host (low)     |\n"
            "   +----------^-----------+                 +----------^-------------+\n"
            "              |                                        |\n"
            "              +--------  Local IPC connection  -------+\n"
        )
        body.addWidget(_code_block(diagram))

        body.addWidget(_prose(
            "The <b>host</b> owns the image library, renderer, and UI. The <b>plugin</b> "
            "calls into it through a stable set of RPC commands "
            "(<code>project.create</code>, <code>image.import</code>, "
            "<code>export.startWithCustom</code>, &hellip;). The host pushes "
            "asynchronous events back on the same connection "
            "(<code>import.started</code>, <code>export.progress</code>, "
            "<code>watch.files.added</code>, &hellip;)."
        ))

        body.addWidget(_prose(
            "All of that is wrapped by the SDK: you <code>import evoto</code>, "
            "call methods on the domain APIs (<code>evoto.project</code>, "
            "<code>evoto.image</code>, &hellip;), and register callbacks. The "
            "wire format, connection discovery, reconnection, and version "
            "handshake are handled for you."
        ))

        return panel

    # ----- Install & quick start --------------------------------------------

    def _build_install_and_quickstart(self) -> QWidget:
        panel, body = _make_section(
            "Install & your first plugin",
            "A minimal plugin lives in its own folder with a manifest and one entry script.",
        )

        body.addWidget(QLabel("<b>1. Install the SDK (editable mode for development)</b>"))
        body.addWidget(_code_block("pip install -e .", max_height=50))

        body.addWidget(QLabel("<b>2. Create a plugin folder</b>"))
        body.addWidget(_code_block(
            "my_plugin/\n"
            "\u251c\u2500\u2500 plugin.json          # manifest (id, entry, dependencies)\n"
            "\u251c\u2500\u2500 main.py              # your entry script\n"
            "\u2514\u2500\u2500 requirements.txt     # optional, merged into plugin.json deps"
        ))

        body.addWidget(QLabel("<b>3. Write <code>main.py</code></b>"))
        body.addWidget(_code_block(
            "import evoto\n\n"
            "@evoto.task\n"
            "def greet(name: str) -> str:\n"
            "    return f\"Hello, {name}!\"\n\n"
            "evoto.connect()              # non-blocking; use evoto.run() for headless\n\n"
            "project = evoto.project.current()\n"
            "evoto.log(f\"Active project: {project['name']}\")\n\n"
            "evoto.shutdown()             # call when your plugin exits"
        ))

        body.addWidget(_prose(
            "When the Evoto host discovers your plugin folder it reads "
            "<code>plugin.json</code>, prepares a private venv from "
            "<code>dependencies</code> / <code>requirements.txt</code>, then launches "
            "<code>main.py</code>. The SDK discovers the host automatically, "
            "so <code>evoto.connect()</code> just works."
        ))

        return panel

    # ----- Runtime modes ----------------------------------------------------

    def _build_runtime_modes(self) -> QWidget:
        panel, body = _make_section(
            "Two runtime modes",
            "Pick <code>evoto.run()</code> for headless workers, or "
            "<code>evoto.connect()</code> when you own a Qt event loop.",
        )

        row = QHBoxLayout()
        row.setSpacing(10)

        # Blocking column
        block_col = QFrame()
        block_col.setObjectName("docBlock")
        bc = QVBoxLayout(block_col)
        bc.setContentsMargins(12, 10, 12, 12)
        bc.setSpacing(6)
        t1 = QLabel("Blocking \u2014 headless worker")
        t1.setObjectName("modeTitle")
        bc.addWidget(t1)
        bc.addWidget(_prose(
            "Best for batch jobs, CLI tools, and tasks that the host triggers "
            "on demand. <code>evoto.run()</code> connects and then blocks until "
            "the host shuts the plugin down."
        ))
        bc.addWidget(_code_block(
            "import evoto\n\n"
            "@evoto.task\n"
            "def batch(folder: str) -> dict:\n"
            "    # ... do work ...\n"
            "    return {'ok': True}\n\n"
            "evoto.run()"
        ))

        # Non-blocking column
        nb_col = QFrame()
        nb_col.setObjectName("docBlock")
        nc = QVBoxLayout(nb_col)
        nc.setContentsMargins(12, 10, 12, 12)
        nc.setSpacing(6)
        t2 = QLabel("Non-blocking \u2014 Qt / PySide GUI")
        t2.setObjectName("modeTitle")
        nc.addWidget(t2)
        nc.addWidget(_prose(
            "Best for panels and tools with a UI. <code>evoto.connect()</code> "
            "returns immediately; your Qt event loop drives the UI, and the SDK "
            "handles host messages on a background thread."
        ))
        nc.addWidget(_code_block(
            "import evoto\n"
            "from PySide6.QtWidgets import QApplication\n\n"
            "evoto.connect()\n\n"
            "app = QApplication([])\n"
            "window = MyWindow()\n"
            "evoto.on_shutdown(window.close)\n"
            "window.show()\n"
            "app.exec()\n"
            "evoto.shutdown()"
        ))

        row.addWidget(block_col, 1)
        row.addWidget(nb_col, 1)
        body.addLayout(row)

        body.addWidget(_prose(
            "<b>Heads up:</b> event callbacks (import/export/watcher) fire on the "
            "SDK's IO thread. In GUI mode, marshal to the main thread with a Qt "
            "signal before touching widgets."
        ))

        return panel

    # ----- Manifest ---------------------------------------------------------

    def _build_manifest(self) -> QWidget:
        panel, body = _make_section(
            "The <code>plugin.json</code> manifest",
            "Tells the host how to identify your plugin and what Python "
            "dependencies it needs.",
        )

        body.addWidget(_code_block(
            "{\n"
            '    "id":           "my_plugin",\n'
            '    "name":         "My Plugin",\n'
            '    "version":      "1.0.0",\n'
            '    "description":  "Automates my batch workflow",\n'
            '    "entry":        "main.py",\n'
            '    "python":       "",\n'
            '    "dependencies": ["PySide6"]\n'
            "}"
        ))

        body.addWidget(_kv_row(
            "<b>id</b> <span style='color:#ef8f8f;'>required</span>",
            "Stable unique identifier; used as the plugin folder key.",
        ))
        body.addWidget(_kv_row(
            "<b>name</b>",
            "Display name shown in the host UI. Defaults to <code>id</code>.",
        ))
        body.addWidget(_kv_row(
            "<b>version</b>",
            "Plugin version string. Defaults to <code>1.0.0</code>.",
        ))
        body.addWidget(_kv_row(
            "<b>description</b>",
            "Short tagline rendered in plugin lists.",
        ))
        body.addWidget(_kv_row(
            "<b>entry</b>",
            "Script the host executes. Defaults to <code>main.py</code>.",
        ))
        body.addWidget(_kv_row(
            "<b>python</b>",
            "Optional absolute path to a Python interpreter. Empty \u2192 global config.",
        ))
        body.addWidget(_kv_row(
            "<b>dependencies</b>",
            "Pip requirements installed into the plugin's private venv. "
            "A sibling <code>requirements.txt</code> is automatically merged in.",
        ))

        return panel

    # ----- Module map (interactive) -----------------------------------------

    def _build_module_map(self) -> QWidget:
        panel, body = _make_section(
            "SDK module map",
            "Click any card to jump to its full reference.",
        )

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        cards = [
            (
                "evoto \u2014 Top-level Fa\u00e7ade",
                "import evoto",
                "Connect, register tasks, subscribe to events, log; reach every domain API via module attributes.",
                "evoto",
            ),
            (
                "evoto.host \u2014 Low-level Handle",
                "evoto.host",
                "Raw JSON-RPC, host-process discovery, and host.quit control.",
                "host",
            ),
            (
                "ProjectAPI \u2014 Projects",
                "evoto.project",
                "Create, list, rename, delete projects and project groups.",
                "ProjectAPI",
            ),
            (
                "ImageAPI \u2014 Images",
                "evoto.image",
                "Import files / folders sync or async, list, query, delete.",
                "ImageAPI",
            ),
            (
                "PresetAPI \u2014 Presets",
                "evoto.preset",
                "Browse preset suits and apply / reset them on image IDs.",
                "PresetAPI",
            ),
            (
                "ExportAPI \u2014 Exports",
                "evoto.export",
                "Kick off exports with custom options or saved presets; subscribe to lifecycle events.",
                "ExportAPI",
            ),
            (
                "ExportOptions \u2014 Builder",
                "from evoto.export_options import ExportOptions",
                "Fluent builder for format, quality, scale, DPI, sharpen, naming, watermark\u2026",
                "ExportOptions",
            ),
            (
                "WatcherAPI \u2014 Folder Watch",
                "evoto.watcher",
                "Watch folders for new files and monitor unexported images.",
                "WatcherAPI",
            ),
            (
                "UserAPI \u2014 Current User",
                "evoto.user",
                "One-shot snapshot of the signed-in user: credits, cloud usage, subscription flags.",
                "UserAPI",
            ),
        ]

        for idx, (title, imp, desc, key) in enumerate(cards):
            card = _ModuleCard(title, imp, desc, key)
            card.clicked.connect(self.module_requested.emit)
            grid.addWidget(card, idx // 2, idx % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        holder = QWidget()
        holder.setLayout(grid)
        body.addWidget(holder)

        return panel

    # ----- Typical workflow -------------------------------------------------

    def _build_workflow(self) -> QWidget:
        panel, body = _make_section(
            "A typical end-to-end workflow",
            "Stitch the APIs together in the order most plugins use them.",
        )

        body.addWidget(_bullet_list([
            "<b>1. Connect</b> \u2014 <code>evoto.connect()</code> (GUI) or "
            "<code>evoto.run()</code> (worker).",
            "<b>2. Locate a project</b> \u2014 "
            "<code>evoto.project.current()</code> or "
            "<code>evoto.project.list(use_current_group=True)</code>; "
            "create one with <code>evoto.project.create(&hellip;)</code> if needed.",
            "<b>3. Bring images in</b> \u2014 "
            "<code>evoto.image.import_files([...], use_current_project=True)</code> "
            "for blocking, or <code>import_files_async</code> + "
            "<code>on_progress / on_completed</code>.",
            "<b>4. Apply presets</b> \u2014 list with "
            "<code>evoto.preset.list()</code>, apply with "
            "<code>evoto.preset.apply_to_image(suit_id, imageIds)</code>.",
            "<b>5. Export</b> \u2014 build options via <code>ExportOptions()</code>, "
            "start with <code>evoto.export.start_with_custom(&hellip;)</code>, then "
            "<code>evoto.export.wait_for_completion(export_dir_id)</code> or subscribe "
            "to <code>on_progress</code>.",
            "<b>6. Tear down</b> \u2014 unsubscribe, then "
            "<code>evoto.shutdown()</code> (or let <code>atexit</code> do it).",
        ]))

        body.addWidget(_code_block(
            "import evoto\n"
            "from evoto.export_options import ExportOptions, FileFormat\n\n"
            "evoto.connect()\n\n"
            "project = evoto.project.current()\n"
            "evoto.image.import_files(['/inbox/batch_01'], project_id=project['id'])\n\n"
            "imgs = evoto.image.list(project_id=project['id'])\n"
            "ids  = [img['id'] for img in imgs]\n\n"
            "evoto.preset.apply_to_image('suit_abc123', ids)\n\n"
            "opts = (ExportOptions()\n"
            "    .file_format(FileFormat.JPEG)\n"
            "    .quality(90)\n"
            "    .scale_long_edge(3000)\n"
            "    .build())\n\n"
            "job = evoto.export.start_with_custom(\n"
            "    project_id=project['id'],\n"
            "    export_dir='/out',\n"
            "    preset_suit_ids=['-1'],\n"
            "    imageIds=ids,\n"
            "    options=opts,\n"
            ")\n"
            "evoto.export.wait_for_completion(job['export_dir_id'])\n"
            "evoto.shutdown()"
        ))

        return panel

    # ----- Demos ------------------------------------------------------------

    def _build_demos(self) -> QWidget:
        panel, body = _make_section(
            "Runnable demos",
            "Every capability ships with a working Qt demo you can inspect and launch.",
        )

        body.addWidget(_kv_row(
            "<code>project_image_demo</code>",
            "Two-level tree (group \u203a project) with image list and basic CRUD.",
        ))
        body.addWidget(_kv_row(
            "<code>preset_demo</code>",
            "Browse preset suits, pick images from a table, apply or reset.",
        ))
        body.addWidget(_kv_row(
            "<code>preset_export_demo</code>",
            "Build custom export options or use saved export presets end-to-end.",
        ))
        body.addWidget(_kv_row(
            "<code>watcher_demo</code>",
            "Watch folders for new files and run the export monitor across projects.",
        ))
        body.addWidget(_kv_row(
            "<code>hot_folder_demo</code>",
            "Table-driven hot-folder pipeline: JSON config, watcher \u2192 import \u2192 "
            "custom-preset export, mirrored per row with sub-folders preserved.",
        ))
        body.addWidget(_kv_row(
            "<code>user_info_demo</code>",
            "Fetch the signed-in user, show credits / cloud usage, and poll periodically.",
        ))
        body.addWidget(_kv_row(
            "<code>api_reference_viewer</code>",
            "The viewer you are currently reading \u2014 great starting point for UIs.",
        ))

        body.addWidget(QLabel("<b>How to run any demo</b>"))
        body.addWidget(_code_block(
            "# Start Evoto, then run the demo\n"
            "python demo/<demo_name>/main.py"
        ))

        body.addWidget(_prose(
            "Each demo also has a <code>plugin.json</code>, so you can drop its "
            "folder into the host's plugins directory and it will be loaded as a "
            "first-class plugin \u2014 no code changes needed."
        ))

        return panel

    # ----- Next steps -------------------------------------------------------

    def _build_next_steps(self) -> QWidget:
        panel, body = _make_section(
            "Where to go next",
            "Pick a module on the left sidebar or jump in from here.",
        )

        row = QHBoxLayout()
        row.setSpacing(8)

        for label, key in [
            ("evoto (top-level) \u2192", "evoto"),
            ("evoto.host \u2192",        "host"),
            ("Projects \u2192",          "ProjectAPI"),
            ("Images \u2192",            "ImageAPI"),
            ("Presets \u2192",           "PresetAPI"),
            ("Exports \u2192",           "ExportAPI"),
            ("Watcher \u2192",           "WatcherAPI"),
            ("User Info \u2192",         "UserAPI"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("linkBtn")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _=False, k=key: self.module_requested.emit(k))
            row.addWidget(btn)
        row.addStretch(1)

        body.addLayout(row)
        return panel
