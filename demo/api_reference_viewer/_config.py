"""Hand-curated UI metadata for the Qt API Reference Viewer.

This file deliberately holds only the bits the viewer needs that
**cannot** be inferred from the generated Python API data:

* sidebar layout: which modules / groups appear, in what order
* friendly names: shorter labels than the raw class name
* demo wiring: which demo each module's "Open Demo" button launches
* tool bundles: end-to-end demos (e.g. Hot Folder) that stitch together
  multiple APIs and don't expose a single class surface

Everything else - method signatures, parameter tables, return types,
docstring blurbs - is **derived at viewer startup** from
``docs-data/python_api_reference.json`` or, as a fallback, from
``evoto/*.py`` by the sibling ``_introspect`` module.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Python SDK module specs.
#
# Each entry produces one entry in MODULE_DATA at viewer startup. The
# ``kind`` discriminator picks the introspection strategy:
#
#   "module_functions"  - introspect the named functions on a module
#                         (e.g. ``evoto.connect`` / ``evoto.task``)
#   "instance_methods"  - introspect the public methods on a singleton
#                         instance, e.g. ``evoto.host``
#   "class_methods"     - introspect the public methods of a class, e.g.
#                         ``evoto.project.ProjectAPI``
#   "module_enums"      - render every Enum subclass + ExportOptions class
#                         declared in the named module
# ---------------------------------------------------------------------------

SDK_MODULES: list[dict] = [
    {
        "key": "evoto",
        "kind": "module_functions",
        "module": "evoto",
        "qualifier": "evoto",
        "members": [
            "connect",
            "run",
            "shutdown",
            "disconnect",
            "on_shutdown",
            "task",
            "on",
            "off",
            "log",
        ],
        "title": "evoto - Top-level Facade",
        "subtitle": (
            "``import evoto`` is the product itself: connect, register "
            "tasks, subscribe to events, and reach every domain API "
            "through module attributes."
        ),
        "import_path": "import evoto",
        "demo_key": None,
    },
    {
        "key": "host",
        "kind": "instance_methods",
        "target": "evoto.host",
        "qualifier": "evoto.host",
        "title": "evoto.host - Low-level Host Handle",
        "subtitle": (
            "Raw JSON-RPC, host-process discovery, and host lifecycle. "
            "Evoto itself can run in the background when its executable "
            "is started with -silent; the SDK connects to it the same "
            "way. Reach for it only when the domain APIs are not enough."
        ),
        "import_path": "evoto.host",
        "demo_key": "runtime_demo",
        "exclude_members": ["discover"],
    },
    {
        "key": "ProjectAPI",
        "kind": "module",
        "module": "evoto.project",
        "qualifier": "evoto.project",
        "title": "ProjectAPI - Project Management",
        "subtitle": (
            "CRUD + listing for projects and project groups. "
            "Reached as ``evoto.project``."
        ),
        "import_path": "evoto.project",
        "demo_key": "project_image_demo",
    },
    {
        "key": "ImageAPI",
        "kind": "module",
        "module": "evoto.image",
        "qualifier": "evoto.image",
        "title": "ImageAPI - Image Import & Management",
        "subtitle": (
            "Import files, list images, react to import lifecycle "
            "events. Reached as ``evoto.image``. The ``ImageInfo`` "
            "dataclass at the bottom is what ``image.info()`` returns."
        ),
        "import_path": "evoto.image",
        "demo_key": "project_image_demo",
    },
    {
        "key": "PresetAPI",
        "kind": "module",
        "module": "evoto.preset",
        "qualifier": "evoto.preset",
        "title": "PresetAPI - Preset Management",
        "subtitle": (
            "Apply / reset preset suits on selected images. "
            "Reached as ``evoto.preset``."
        ),
        "import_path": "evoto.preset",
        "demo_key": "preset_demo",
    },
    {
        "key": "ExportAPI",
        "kind": "module",
        "module": "evoto.export",
        "qualifier": "evoto.export",
        "title": "ExportAPI - Image Export",
        "subtitle": (
            "Run exports, follow lifecycle, retry / pause / resume. "
            "Reached as ``evoto.export``."
        ),
        "import_path": "evoto.export",
        "demo_key": "preset_export_demo",
    },
    {
        "key": "ExportOptions",
        "kind": "module",
        "module": "evoto.export_options",
        # No api_qualifier so ExportOptions methods read as
        # ``ExportOptions.file_format(...)`` rather than e.g.
        # ``evoto.export_options.file_format(...)``.
        "qualifier": None,
        "title": "ExportOptions - Builder & Enums",
        "subtitle": (
            "Builder + enums for the ``options`` dict accepted by "
            "``ExportAPI.start_with_custom``. Spells out every legal "
            "value the host accepts."
        ),
        "import_path": "from evoto import ExportOptions",
        "demo_key": "preset_export_demo",
    },
    {
        "key": "WatcherAPI",
        "kind": "module",
        "module": "evoto.watcher",
        "qualifier": "evoto.watcher",
        "title": "WatcherAPI - Folder Watch & Export Monitor",
        "subtitle": (
            "Folder watching plus the per-project export monitor. "
            "Reached as ``evoto.watcher``. ``ExportStatus`` and "
            "``TimeUnit`` enums are listed at the bottom."
        ),
        "import_path": "evoto.watcher",
        "demo_key": "watcher_demo",
    },
    {
        "key": "UserAPI",
        "kind": "module",
        "module": "evoto.user",
        "qualifier": "evoto.user",
        "title": "UserAPI - Current User Info",
        "subtitle": (
            "Current user / subscription / credits info. "
            "Reached as ``evoto.user``. The ``UserInfo`` dataclass at "
            "the bottom is what ``user.info()`` returns."
        ),
        "import_path": "evoto.user",
        "demo_key": "user_info_demo",
    },
    {
        "key": "MetadataAPI",
        "kind": "module",
        "module": "evoto.metadata",
        "qualifier": "evoto.metadata",
        "title": "MetadataAPI - Metadata Automation",
        "subtitle": (
            "Read and update image metadata, refresh metadata from files, "
            "and save host metadata back to files or sidecars. Reached as "
            "``evoto.metadata``."
        ),
        "import_path": "evoto.metadata",
        "demo_key": "metadata_demo",
    },
    {
        "key": "LibraryAPI",
        "kind": "module",
        "module": "evoto.library",
        "qualifier": "evoto.library",
        "title": "LibraryAPI - Data Library Automation",
        "subtitle": (
            "Query library images without changing host UI filters and "
            "update lightweight labels. Reached as ``evoto.library``."
        ),
        "import_path": "evoto.library",
        "demo_key": "library_demo",
    },
    {
        "key": "CullingAPI",
        "kind": "module",
        "module": "evoto.culling",
        "qualifier": "evoto.culling",
        "title": "CullingAPI - Culling Results",
        "subtitle": (
            "Read culling status, image-level results, face records, and "
            "clusters. Reached as ``evoto.culling``."
        ),
        "import_path": "evoto.culling",
        "demo_key": "culling_demo",
    },
    {
        "key": "EditAPI",
        "kind": "module",
        "module": "evoto.edit",
        "qualifier": "evoto.edit",
        "title": "EditAPI - Edit Summaries",
        "subtitle": (
            "Read edit summaries, with guarded edit "
            "workflows returning explicit host responses. Reached as "
            "``evoto.edit``."
        ),
        "import_path": "evoto.edit",
        "demo_key": "edit_recipe_demo",
    },
    {
        "key": "FaceAPI",
        "kind": "module",
        "module": "evoto.face",
        "qualifier": "evoto.face",
        "title": "FaceAPI - Standalone Face Detection",
        "subtitle": (
            "Load the face detect model asynchronously, then detect face "
            "boxes, age, gender and glasses on library images. "
            "Reached as ``evoto.face``."
        ),
        "import_path": "evoto.face",
        "demo_key": "face_detect_demo",
    },
]

# ---------------------------------------------------------------------------
# Sidebar grouping. Items are module keys matching ``SDK_MODULES`` keys.
# A "label" turns the entry into a labelled sub-group; otherwise items
# are listed flat.
# ---------------------------------------------------------------------------

WORKFLOW_GROUPS: list[dict] = [
    {"items": ["evoto", "host"]},
    {"items": ["ProjectAPI"]},
    {"items": ["ImageAPI"]},
    {"items": ["PresetAPI"]},
    {"items": ["ExportAPI"]},
    {"items": ["ExportOptions"]},
    {"items": ["WatcherAPI"]},
    {"items": ["UserAPI"]},
    {
        "label": "Automation",
        "items": ["MetadataAPI", "LibraryAPI", "CullingAPI", "EditAPI", "FaceAPI"],
    },
]

# ---------------------------------------------------------------------------
# Friendly display names for the sidebar.
# ---------------------------------------------------------------------------

SIDEBAR_DISPLAY_NAMES: dict[str, str] = {
    "evoto": "Top-level",
    "host": "Host",
    "ProjectAPI": "Project",
    "ImageAPI": "Image",
    "PresetAPI": "Preset",
    "ExportAPI": "Export",
    "ExportOptions": "Export Options",
    "WatcherAPI": "Watcher",
    "UserAPI": "User Info",
    "MetadataAPI": "Metadata",
    "LibraryAPI": "Library",
    "CullingAPI": "Culling",
    "EditAPI": "Edit",
    "FaceAPI": "Face Detect",
}

# ---------------------------------------------------------------------------
# Tool bundles - end-to-end workflow demos rendered under the sidebar's
# "TOOL BUNDLES" section. They reuse the OverviewPage layout but expose a
# curated "Highlights" list rather than a real API surface.
# ---------------------------------------------------------------------------

TOOL_BUNDLES: list[dict] = [
    {
        "key": "__hot_folder__",
        "title": "Hot Folder Tool",
        "subtitle": (
            "End-to-end workflow demo: folder watcher -> async import -> "
            "multi-preset export, all driven by a shared ``config.json``."
        ),
        "import_path": "demo/hot_folder_demo/main.py",
        "demo_key": "hot_folder_demo",
        "members_heading": "Highlights",
        "members_clickable": False,
        "methods": [
            {
                "name": "Folder -> Export mapping table",
                "brief": (
                    "Route each watched folder to its own export "
                    "directory and preset suits"
                ),
                "params": [],
            },
            {
                "name": "Silent Evoto launcher",
                "brief": (
                    "Optionally spawn the Evoto executable with -silent "
                    "so the host runs in the background with no UI, then "
                    "auto-reconnect"
                ),
                "params": [],
            },
            {
                "name": "Per-lane progress + event log",
                "brief": (
                    "Live status (X/Y) and lifecycle events from the host"
                ),
                "params": [],
            },
            {
                "name": "evoto.host.quit() integration",
                "brief": (
                    "Stop button asks Evoto to shut down via the runtime "
                    "helper; falls back to local kill"
                ),
                "params": [],
            },
        ],
    },
]
