"""Auto-built data backing for the Qt API Reference Viewer.

This module is a **facade**. At import time it composes three sources:

1. Hand-curated UI metadata     (:mod:`_config`)
2. Generated Python API data   (``docs-data/python_api_reference.json``)
   or live Python introspection (:mod:`_introspect` -> ``evoto/*.py``)
3. Hand-written code examples   (:mod:`_examples`)

The viewer is intentionally **Python-only**: it presents what plugin
authors call from Python (``evoto.project.create(...)``,
``evoto.image.delete(...)``, etc.), not the underlying JSON-RPC wire
format.

The module-level constants exported here keep the same names and shapes
the existing widgets already consume, so :mod:`main` and ``widgets/``
need no changes:

* :data:`MODULE_ORDER`             - sidebar ordering of SDK modules.
* :data:`MODULE_DATA`              - keyed by module key, each value is the
                                     viewer's standard dict
                                     (``title``, ``subtitle``,
                                     ``import_path``, ``demo_key``,
                                     ``methods``).
* :data:`WORKFLOW_GROUPS`          - sidebar grouping (passed to ``Sidebar``).
* :data:`SIDEBAR_DISPLAY_NAMES`    - friendly labels per key.
* :data:`TOOL_BUNDLES_ORDER`
* :data:`TOOL_BUNDLE_DATA`         - hot-folder-style bundles.

Where each bit of data comes from
---------------------------------

* Want to change the **method signature / docstring** the viewer shows?
  Edit the docstring in ``evoto/*.py`` - it flows through here on next
  start.
* Want to add or update an **example** for some method? Edit
  :mod:`_examples`.
* Want to change the **sidebar** layout, friendly names, or which demo
  the "Open Demo" button launches? Edit :mod:`_config`.

Failure mode
------------

If any introspection step raises (typically because ``evoto`` source
moved), the module logs a warning and degrades gracefully: that single
SDK module is skipped, the rest of the viewer still works.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import _config
import _examples
import _introspect

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = REPO_ROOT / "docs-data" / "python_api_reference.json"


# ---------------------------------------------------------------------------
# SDK module assembly
# ---------------------------------------------------------------------------


def _introspect_for(spec: dict) -> list[dict]:
    """Run the right introspection strategy for one SDK module spec."""
    kind = spec["kind"]
    qualifier = spec.get("qualifier")
    if kind == "module_functions":
        return _introspect.introspect_module_functions(
            spec["module"], spec["members"], qualifier=qualifier
        )
    if kind == "instance_methods":
        methods = _introspect.introspect_instance_methods(
            spec["target"], qualifier=qualifier
        )
        excluded = set(spec.get("exclude_members") or [])
        if excluded:
            methods = [m for m in methods if m.get("name") not in excluded]
        return methods
    if kind == "module":
        # API class methods + enums + dataclasses, all from one module.
        return _introspect.introspect_module(
            spec["module"], api_qualifier=qualifier
        )
    raise ValueError(f"Unknown SDK module kind: {kind!r}")


def _apply_example_overrides(module_key: str, methods: list[dict]) -> None:
    """Inject hand-written example snippets when the auto-extracted one is empty.

    The introspector only finds examples that the SDK source itself
    spells out under a ``Example:`` docstring section; everything else
    falls back to the legacy hand-written pool kept in :mod:`_examples`.
    """
    for m in methods:
        if m.get("example"):
            continue
        snippet = _examples.EXAMPLES.get((module_key, m["name"]))
        if snippet:
            m["example"] = snippet


def _build_sdk_section() -> tuple[list[str], dict[str, dict]]:
    keys: list[str] = []
    data: dict[str, dict] = {}
    for spec in _config.SDK_MODULES:
        try:
            methods = _introspect_for(spec)
        except Exception:
            logger.exception(
                "Failed to introspect SDK module %r; skipping.", spec.get("key")
            )
            continue
        _apply_example_overrides(spec["key"], methods)
        keys.append(spec["key"])
        data[spec["key"]] = {
            "title": spec["title"],
            "subtitle": spec["subtitle"],
            "import_path": spec["import_path"],
            "demo_key": spec.get("demo_key"),
            "methods": methods,
        }
    return keys, data


def _runtime_payload() -> dict:
    """Build the full viewer data payload from Python source introspection."""
    sdk_keys, sdk_data = _build_sdk_section()
    return {
        "MODULE_ORDER": list(sdk_keys),
        "MODULE_DATA": dict(sdk_data),
        "WORKFLOW_GROUPS": list(_config.WORKFLOW_GROUPS),
        "SIDEBAR_DISPLAY_NAMES": dict(_config.SIDEBAR_DISPLAY_NAMES),
        "TOOL_BUNDLES_ORDER": [b["key"] for b in _config.TOOL_BUNDLES],
        "TOOL_BUNDLE_DATA": {b["key"]: dict(b) for b in _config.TOOL_BUNDLES},
    }


def _load_generated_payload() -> dict | None:
    """Load pre-generated docs-data payload when available.

    The viewer falls back to live introspection if the JSON is absent or
    invalid, preserving the historical startup behavior.
    """
    if os.environ.get("EVOTO_API_REFERENCE_FORCE_INTROSPECT"):
        return None
    if not DEFAULT_DATA_PATH.exists():
        return None
    try:
        with DEFAULT_DATA_PATH.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        logger.exception("Failed to load generated API reference data; falling back.")
        return None
    required = {
        "MODULE_ORDER",
        "MODULE_DATA",
        "WORKFLOW_GROUPS",
        "SIDEBAR_DISPLAY_NAMES",
        "TOOL_BUNDLES_ORDER",
        "TOOL_BUNDLE_DATA",
    }
    if not required.issubset(payload):
        logger.warning("Generated API reference data is missing keys; falling back.")
        return None
    return payload


# ---------------------------------------------------------------------------
# Top-level constants (the public surface the rest of the viewer imports)
# ---------------------------------------------------------------------------

_payload = _load_generated_payload() or _runtime_payload()

MODULE_ORDER: list[str] = list(_payload["MODULE_ORDER"])
MODULE_DATA: dict[str, dict] = dict(_payload["MODULE_DATA"])
WORKFLOW_GROUPS: list[dict] = list(_payload["WORKFLOW_GROUPS"])
SIDEBAR_DISPLAY_NAMES: dict[str, str] = dict(_payload["SIDEBAR_DISPLAY_NAMES"])

TOOL_BUNDLES_ORDER: list[str] = list(_payload["TOOL_BUNDLES_ORDER"])
TOOL_BUNDLE_DATA: dict[str, dict] = dict(_payload["TOOL_BUNDLE_DATA"])
