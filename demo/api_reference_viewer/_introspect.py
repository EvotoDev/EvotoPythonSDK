"""Build viewer method-dicts by introspecting Python source.

The output mirrors the shape the existing widgets already consume:

    {
      "name":       "create",
      "signature":  "create(self, name: str, ...) -> dict",
      "brief":      "Create a project.",                # first paragraph
      "params":     [(name, type, default, desc), ...], # 4-tuples
      "returns":    "Created project payload from host.",
      "example":    "<code from Example: section, may be empty>",
    }

Implementation notes:

* Docstring parsing recognises Google-style sections (``Args:``,
  ``Returns:``, ``Raises:``, ``Example:``). It deliberately tolerates
  the lightly mixed sphinx-style cross-refs (``:meth:`...```) that the
  Evoto SDK uses; those refs are kept verbatim because the viewer
  surfaces them as plain text.
* Required parameters are encoded as ``default == "required"`` to
  match the legacy hand-curated data shape - the detail page draws a
  distinct "required" pill when it sees this string.
"""

from __future__ import annotations

import dataclasses
import enum
import importlib
import inspect
import re
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def introspect_module_functions(
    module_dotted: str,
    names: list[str],
    *,
    qualifier: str | None = None,
) -> list[dict]:
    """Build method-dicts for the named callables on a module.

    Args:
        module_dotted: dotted path to the module to import.
        names: explicit list of attribute names to surface.
        qualifier: optional dotted prefix for the rendered signature
            (e.g. ``"evoto"`` so the signature reads ``evoto.connect(...)``).
            Defaults to ``module_dotted`` when omitted.
    """
    mod = importlib.import_module(module_dotted)
    qual = qualifier or module_dotted
    out: list[dict] = []
    for name in names:
        try:
            obj = getattr(mod, name)
        except AttributeError:
            continue
        if not callable(obj):
            continue
        out.append(_method_dict(name, obj, qualifier=qual))
    return out


def introspect_class_methods(
    class_dotted: str,
    *,
    qualifier: str | None = None,
) -> list[dict]:
    """Build method-dicts for every public method of a class."""
    cls = _resolve(class_dotted)
    if not inspect.isclass(cls):
        raise TypeError(f"Expected a class at {class_dotted!r}, got {cls!r}")
    qual = qualifier or class_dotted.rsplit(".", 1)[0]
    out: list[dict] = []
    for name, fn in _public_callables_of_class(cls):
        out.append(_method_dict(name, fn, qualifier=qual, drop_self=True))
    out.sort(key=lambda m: m["name"])
    return out


def introspect_instance_methods(
    instance_dotted: str,
    *,
    qualifier: str | None = None,
) -> list[dict]:
    """Build method-dicts for the public methods of a singleton instance."""
    obj = _resolve(instance_dotted)
    cls = type(obj)
    qual = qualifier or instance_dotted
    out: list[dict] = []
    for name, fn in _public_callables_of_class(cls):
        out.append(_method_dict(name, fn, qualifier=qual, drop_self=True))
    out.sort(key=lambda m: m["name"])
    return out


def introspect_module(
    module_dotted: str,
    *,
    api_qualifier: str | None = None,
) -> list[dict]:
    """One-stop module introspection: API class methods + enums + dataclasses.

    Walks every public class declared in *module_dotted*:

    * **API / builder classes** (non-Enum, non-dataclass) get their
      public methods expanded one-per-entry, just like ``class_methods``
      does. The signature qualifier is *api_qualifier* if provided
      (typically the module's user-facing name, e.g. ``"evoto.project"``)
      otherwise the class's own name (``"ExportOptions"``).
    * **Enum subclasses** become one entry whose ``params`` list
      enumerates the members.
    * **Dataclasses** become one entry whose ``params`` lists the
      fields.

    Entries are sorted: API methods first (so the fluent API / class
    methods land first), then dataclasses, then enums alphabetically.
    """
    mod = importlib.import_module(module_dotted)
    out: list[dict] = []

    for name, obj in inspect.getmembers(mod):
        if name.startswith("_"):
            continue
        if not inspect.isclass(obj) or obj.__module__ != module_dotted:
            continue
        if issubclass(obj, enum.Enum) and obj is not enum.Enum:
            entry = _enum_dict(name, obj)
            entry["_sort"] = (2, name)
            out.append(entry)
        elif dataclasses.is_dataclass(obj):
            entry = _dataclass_dict(name, obj)
            entry["_sort"] = (1, name)
            out.append(entry)
        else:
            qualifier = api_qualifier or name
            for mname, fn in _public_callables_of_class(obj):
                method = _method_dict(
                    mname, fn, qualifier=qualifier, drop_self=True
                )
                method["_sort"] = (0, mname)
                out.append(method)

    out.sort(key=lambda m: m["_sort"])
    for m in out:
        m.pop("_sort", None)
    return out


# ---------------------------------------------------------------------------
# Method dict construction
# ---------------------------------------------------------------------------


def _method_dict(
    display_name: str,
    fn: Any,
    *,
    qualifier: str | None = None,
    drop_self: bool = False,
) -> dict:
    """Build the canonical viewer method dict for one callable."""
    sig_obj = _safe_signature(fn)
    parsed = _parse_docstring(inspect.getdoc(fn) or "")
    params = _params_from_signature(sig_obj, parsed.get("params_doc", {}))
    qualified_name = f"{qualifier}.{display_name}" if qualifier else display_name
    return {
        "kind": "method",
        "name": display_name,
        "signature": _format_signature(qualified_name, sig_obj, drop_self=drop_self),
        "brief": parsed.get("brief", ""),
        "params": params,
        "returns": parsed.get("returns", "None"),
        "example": parsed.get("example", ""),
    }


def _enum_dict(name: str, cls: type) -> dict:
    """Render an Enum subclass as a viewer module entry."""
    members: list[tuple[str, str, str, str]] = []
    for member in cls:
        value = _format_default(member.value)
        doc = (inspect.getdoc(member) or "").splitlines()[0:1]
        desc = doc[0] if doc and doc[0] != cls.__name__ else ""
        members.append((member.name, _enum_value_type(member.value), value, desc))

    brief = (inspect.getdoc(cls) or "").splitlines()[0:1]
    brief_text = brief[0] if brief else ""
    # Append a member preview so the overview page is readable without
    # drilling into the detail page.
    if members:
        names = ", ".join(m[0] for m in members)
        brief_text = (brief_text + f" Values: {names}").strip()

    return {
        "kind": "enum",
        "name": name,
        "signature": f"class {name}({cls.__bases__[0].__name__})",
        "brief": brief_text,
        "params": members,
        "returns": "",
        "example": "",
    }


def _dataclass_dict(name: str, cls: type) -> dict:
    """Render a dataclass as a viewer module entry."""
    doc = inspect.getdoc(cls) or ""
    parsed = _parse_docstring(doc)
    field_docs = parsed.get("params_doc", {})
    fields_out: list[tuple[str, str, str, str]] = []
    for f in dataclasses.fields(cls):
        ftype = _format_annotation(f.type)
        if f.default is not dataclasses.MISSING:
            default_str = _format_default(f.default)
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            default_str = "<factory>"
        else:
            default_str = "required"
        fields_out.append((f.name, ftype, default_str, field_docs.get(f.name, "")))

    brief_text = doc.splitlines()[0] if doc else ""
    if fields_out:
        names = ", ".join(f[0] for f in fields_out)
        brief_text = (brief_text + f" Fields: {names}").strip()

    return {
        "kind": "dataclass",
        "name": name,
        "signature": f"@dataclass\nclass {name}",
        "brief": brief_text,
        "params": fields_out,
        "returns": "",
        "example": "",
    }


def _class_summary_dict(name: str, cls: type) -> dict:
    """Render a non-dataclass non-enum class (e.g. ``ExportOptions``)."""
    parsed = _parse_docstring(inspect.getdoc(cls) or "")
    return {
        "kind": "class",
        "name": name,
        "signature": f"class {name}",
        "brief": parsed.get("brief", ""),
        "params": [],
        "returns": parsed.get("returns", ""),
        "example": parsed.get("example", ""),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve(dotted: str) -> Any:
    """Resolve ``"pkg.module.attr.attr"`` to the actual object.

    Imports the longest possible module prefix first, then walks the
    remaining components as attribute lookups. This is necessary because
    ``evoto/__init__.py`` shadows the ``evoto.project`` submodule with a
    ``ProjectAPI`` *instance*, so naive ``getattr(evoto, "project")``
    returns the instance and the next attribute lookup fails.
    """
    parts = dotted.split(".")
    module: Any = None
    boundary = 0
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        try:
            module = importlib.import_module(candidate)
            boundary = i
            break
        except ImportError:
            continue
    if module is None:
        raise ImportError(f"Cannot resolve any module prefix of {dotted!r}")
    obj: Any = module
    for name in parts[boundary:]:
        obj = getattr(obj, name)
    return obj


def _public_callables_of_class(cls: type) -> Iterable[tuple[str, Any]]:
    """Yield ``(name, function)`` pairs for public callables on a class.

    Treats ``staticmethod`` / ``classmethod`` / regular methods uniformly.
    Skips properties, dunders, and class attributes.
    """
    for name in sorted(set(vars(cls)) | set(dir(cls))):
        if name.startswith("_"):
            continue
        if name == "__init__":
            continue
        raw = inspect.getattr_static(cls, name, None)
        if raw is None or isinstance(raw, property):
            continue
        if isinstance(raw, (staticmethod, classmethod)):
            fn = raw.__func__
        elif inspect.isfunction(raw):
            fn = raw
        else:
            # Class attributes (sdk_version str, etc.) skipped.
            continue
        yield name, fn


def _display_name(_module, name: str) -> str:
    return name


def _safe_signature(fn: Any) -> inspect.Signature | None:
    try:
        return inspect.signature(fn)
    except (TypeError, ValueError):
        return None


def _format_signature(
    name: str,
    sig: inspect.Signature | None,
    *,
    drop_self: bool = False,
) -> str:
    """Render a signature without the ``self``-style first param and with
    annotations unquoted (the SDK uses ``from __future__ import annotations``
    so :func:`inspect.signature` would otherwise stringify them with quotes).
    """
    if sig is None:
        return f"{name}(...)"

    rendered_params: list[str] = []
    seen_kw_only_marker = False
    for p in sig.parameters.values():
        if drop_self and p.name in {"self", "cls"}:
            continue

        # Insert ``*`` to separate keyword-only params, mirroring the
        # canonical Python signature when introspect would have added it.
        if (
            p.kind is inspect.Parameter.KEYWORD_ONLY
            and not seen_kw_only_marker
            and not any(
                q.kind is inspect.Parameter.VAR_POSITIONAL for q in sig.parameters.values()
            )
        ):
            rendered_params.append("*")
            seen_kw_only_marker = True

        rendered_params.append(_render_parameter(p))

    args = ", ".join(rendered_params)
    ret = ""
    if sig.return_annotation is not inspect._empty:
        ret = f" -> {_format_annotation(sig.return_annotation)}"
    return f"{name}({args}){ret}"


def _render_parameter(p: inspect.Parameter) -> str:
    """Format a single Parameter for display in the signature line."""
    if p.kind is inspect.Parameter.VAR_POSITIONAL:
        prefix = "*"
    elif p.kind is inspect.Parameter.VAR_KEYWORD:
        prefix = "**"
    else:
        prefix = ""

    parts = [f"{prefix}{p.name}"]
    if p.annotation is not inspect._empty:
        parts.append(f": {_format_annotation(p.annotation)}")
    if p.default is not inspect.Parameter.empty:
        parts.append(f" = {_format_default(p.default)}")
    return "".join(parts)


def _format_default(value: Any) -> str:
    """Render a default value for display in a signature.

    Enum members render as ``ClassName.MEMBER`` instead of the noisy
    ``repr()`` form ``<ClassName.MEMBER: 'value'>`` so signatures stay
    readable.
    """
    if isinstance(value, enum.Enum):
        return f"{type(value).__name__}.{value.name}"
    return repr(value)


_TYPE_RE_TUPLE = re.compile(r"^(.*?)\s*[:|-]\s*(.*)$")


def _params_from_signature(
    sig: inspect.Signature | None,
    params_doc: dict[str, str],
) -> list[tuple[str, str, str, str]]:
    """Return (name, type, default, desc) tuples for each non-self param."""
    if sig is None:
        return []
    out: list[tuple[str, str, str, str]] = []
    for p in sig.parameters.values():
        if p.name in {"self", "cls"}:
            continue
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        ptype = _format_annotation(p.annotation) if p.annotation is not inspect._empty else ""
        if p.default is inspect.Parameter.empty:
            default = "required"
        else:
            default = _format_default(p.default)
        desc = params_doc.get(p.name, "")
        out.append((p.name, ptype, default, desc))
    return out


def _format_annotation(ann: Any) -> str:
    """Render an annotation for display.

    Modules that opt into PEP 563 (``from __future__ import annotations``)
    deliver annotations as already-evaluated string literals. Modules
    that do not deliver real type objects. ``inspect.formatannotation``
    handles both shapes uniformly while preserving syntax like
    ``str | None`` and ``list[int]`` - the same form a developer would
    type by hand.
    """
    if ann is inspect._empty:
        return ""
    if isinstance(ann, str):
        # Already a string (PEP 563 / typing.get_type_hints not called).
        return ann
    return inspect.formatannotation(ann)


def _enum_value_type(value: Any) -> str:
    return type(value).__name__


# ---------------------------------------------------------------------------
# Google-style docstring parser (lenient)
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(
    r"^(Args|Arguments|Parameters|Attributes|Returns|Return|Raises|Yields|Example|Examples|Note|Notes)\s*:\s*$"
)
_PARAM_RE = re.compile(r"^\s*(\w+)\s*(?:\(([^)]+)\))?\s*:(?!:)\s*(.*)$")


def _parse_docstring(text: str) -> dict:
    """Parse a Google-style docstring into structured fields.

    Returns:
        dict with optional keys:
            - brief:      first paragraph (single line).
            - description: remaining paragraphs above the first section.
            - params_doc: {name: description} from Args/Parameters.
            - returns:    description string from Returns.
            - example:    raw text from Example/Examples.
    """
    if not text:
        return {"brief": "", "params_doc": {}, "returns": "None", "example": ""}

    lines = text.splitlines()
    section = "_intro"
    buckets: dict[str, list[str]] = {section: []}

    for raw in lines:
        stripped = raw.strip()
        m = _SECTION_RE.match(stripped)
        if m:
            section = m.group(1).lower()
            buckets[section] = []
            continue
        buckets.setdefault(section, []).append(raw)

    intro = "\n".join(buckets.get("_intro", [])).strip()
    if intro:
        first_para, _, _ = intro.partition("\n\n")
        brief = " ".join(first_para.split())
    else:
        brief = ""

    params_doc: dict[str, str] = {}
    args_block = (
        buckets.get("args")
        or buckets.get("arguments")
        or buckets.get("parameters")
        or buckets.get("attributes")
        or []
    )
    if args_block:
        for name, desc in _parse_param_block(args_block):
            params_doc[name] = desc

    returns_block = buckets.get("returns") or buckets.get("return") or []
    returns = " ".join(line.strip() for line in returns_block if line.strip())

    example_block = buckets.get("example") or buckets.get("examples") or []
    example = "\n".join(example_block).strip()

    return {
        "brief": brief,
        "params_doc": params_doc,
        "returns": returns or "None",
        "example": example,
    }


def _parse_param_block(lines: list[str]) -> list[tuple[str, str]]:
    """Extract ``(name, description)`` pairs from a Google-style Args block.

    Each parameter entry occupies the lowest-indent level inside the Args
    block; deeper-indented lines are continuation text for the previous
    parameter. Empty lines reset the continuation buffer.
    """
    if not lines:
        return []
    indents = [
        len(raw) - len(raw.lstrip())
        for raw in lines
        if raw.strip() and _PARAM_RE.match(raw.strip())
    ]
    if not indents:
        return []
    base_indent = min(indents)

    items: list[tuple[str, list[str]]] = []
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        leading = len(raw) - len(raw.lstrip())
        m = _PARAM_RE.match(stripped)
        # A new parameter entry: same base indent, name + colon shape.
        if m and leading == base_indent:
            items.append((m.group(1), [m.group(3).strip()]))
        elif items:
            items[-1][1].append(stripped)
    return [(name, " ".join(parts).strip()) for name, parts in items]
