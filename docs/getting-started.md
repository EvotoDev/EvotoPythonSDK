# Getting Started

This page walks you from a clean checkout to a running plugin that talks to a
local Evoto host.

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Runs your plugin and the SDK |
| Evoto desktop | Any recent build | The JSON-RPC host that the SDK connects to |
| `pip` | Bundled with Python | Install the SDK in editable mode |
| PySide6 | 6.5+ (optional) | Only if you want a GUI plugin (most demos use it) |

The SDK has no hard dependency on Qt; you only need PySide6 if your plugin
shows UI. CLI / headless plugins work fine without it.

Evoto itself can run either normally (with its UI) or in the background:
launching the executable with `-silent` starts a headless host that the
SDK still connects to through `evoto.connect()`. See the
[Silent mode guide](guides/silent-mode.md).

## Install the SDK

The SDK is currently distributed as a source checkout. From the repo root:

```bash
pip install -e .
```

That installs `evoto` as an editable package: changes you make in
`evoto/` are reflected the next time you `import evoto`, no reinstall
needed.

To install the documentation toolchain (only needed if you intend to
build / preview this site):

```bash
pip install -r requirements-docs.txt
```

## Hello world plugin

Create `hello.py`:

```python
import evoto

evoto.connect(timeout=15.0)

project = evoto.project.current()
print(f"Active project: {project.get('name')!r}")

# Subscribe to project rename events; the disposer is returned for cleanup.
dispose = evoto.project.on_renamed(
    lambda name, payload: print(f"  -> renamed to {payload.get('name')!r}")
)

try:
    input("Hit Enter to disconnect...")
finally:
    dispose()
    evoto.shutdown()
```

Run it:

```bash
python hello.py
```

If the Evoto host is running, you should see the active project name and
any rename events fire while the script blocks on `input()`.

## Run the bundled demos

Each demo in `demo/<name>/` has its own `plugin.json` and `main.py` and
can be run directly:

```bash
python demo/runtime_demo/main.py
python demo/preset_demo/main.py
python demo/hot_folder_demo/main.py
```

If a connect call hangs, walk through the
[Connection handshake guide](guides/connection-handshake.md) - it
covers the six steps `evoto.connect()` performs and ships a small
troubleshooting snippet.

## What to read next

- [Threading model](guides/threading-model.md) - which thread your
  `on_*` callback runs on, and why you must marshal Qt updates with
  a queued signal.
- [Connection handshake](guides/connection-handshake.md) - the six
  internal steps `evoto.connect()` performs, and how to debug a
  connection issue.
- [Plugin manifest](guides/plugin-manifest.md) - every key in
  `plugin.json`.
- [Error handling](guides/error-handling.md) - exception hierarchy and
  HTTP-style error codes.
- [IPC protocol](guides/ipc-protocol.md) - wire format, transport,
  authentication.
- [Python API reference](api/index.md) - method-by-method docs
  auto-generated from the SDK's docstrings.
