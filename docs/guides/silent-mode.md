# Silent Mode

Evoto can be launched in silent mode by starting the Evoto executable
with the `-silent` argument. In this mode Evoto runs in the background
with no main window, and the Python SDK connects through
`evoto.connect()` to call supported functions exactly as it would
against a normally launched host.

This is the mode to use for headless workers, scheduled jobs, and
hot-folder style automation where nobody is sitting in front of the UI.

## Launching

```bash
# macOS - point at the binary inside the bundle
/Applications/Evoto.app/Contents/MacOS/Evoto -silent

# Windows
"C:\Program Files\Evoto\Evoto.exe" -silent

# Linux / other
/opt/evoto/Evoto -silent
```

On macOS the `.app` bundle root is not executable itself. Resolve it to
`Contents/MacOS/<bundle stem>`; dev builds whose binary name does not
match the bundle folder can be resolved by taking the first executable
file under `Contents/MacOS`. That is what
`demo/hot_folder_demo/launcher.py` does.

## Showing the UI

To show the UI, start Evoto normally without `-silent`, or configure
silent mode to show the main window after the SDK disconnects:

```python
evoto.host.configure_silent_timeout(timeout_seconds=600, action="show")
```

By default, if the SDK disconnects, Evoto will **not** automatically
open the UI. The silent host exits after the default timeout unless the
timeout action is explicitly set to `"show"`.

## The silent-mode watcher

`-silent` arms a background watcher that fires an action after
`timeout_seconds` with no plugin connected. `connected_plugin_count > 0`
pauses the timer, so the countdown only runs while nothing is attached.

| Setting | Default | Effect |
|---|---|---|
| `timeout_seconds` | `300` | Seconds without a connected plugin before the action fires. |
| `timeout_seconds <= 0` | - | Disables auto-exit; the host stays silent indefinitely. |
| `action="quit"` | default | The host quits when the timer fires. |
| `action="show"` | - | The host leaves silent mode and shows the main window. |

Unspecified parameters keep their current value, and the call returns a
snapshot after the update:

```python
import evoto

evoto.connect(timeout=15.0)

# Daemon plugin: never let the host time out from under us
state = evoto.host.configure_silent_timeout(timeout_seconds=0)
print(state)
# {'timeout_seconds': 0, 'action': 'quit', 'enabled': False,
#  'connected_plugin_count': 1}
```

`configure_silent_timeout()` is silent-mode-only. When the host was
launched **without** `-silent` there is no watcher to configure and the
call raises `ApiError` with `code=412`
(`ApiErrorCode.PRECONDITION_FAILED`) - see
[Error handling](error-handling.md).

```python
from evoto.core.api_error_code import ApiErrorCode
from evoto.core._internal.exceptions import ApiError

try:
    evoto.host.configure_silent_timeout(timeout_seconds=0)
except ApiError as e:
    if e.code == ApiErrorCode.PRECONDITION_FAILED:
        print("Host is not running with -silent; nothing to configure.")
    else:
        raise
```

## Spawning the host from Python

A plugin that wants a one-step local workflow can spawn the silent host
itself, wait for the endpoint to appear, then connect:

```python
import subprocess
import sys

import evoto

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

evoto_binary = "/Applications/Evoto.app/Contents/MacOS/Evoto"

kwargs = dict(
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
if sys.platform == "win32":
    kwargs["creationflags"] = CREATE_NO_WINDOW | DETACHED_PROCESS
else:
    # Detach from the controlling terminal so Ctrl+C on the plugin
    # does not also kill Evoto.
    kwargs["start_new_session"] = True

proc = subprocess.Popen([evoto_binary, "-silent"], **kwargs)

# The host needs a moment to boot before the endpoint is listening.
if evoto.host.wait_for_host(timeout=60.0, poll_interval=1.0) is None:
    raise RuntimeError("Evoto did not come up within 60s")

evoto.connect(timeout=15.0)
```

`evoto.host.wait_for_host()` polls discovery and returns the endpoint
path, or `None` on timeout; `evoto.host.is_available()` is the
one-shot variant. Cold starts from disk can take tens of seconds, so
give the wait a generous budget.

## Shutting down

`evoto.host.quit()` works in both normal UI mode and `-silent`
background mode:

```python
evoto.host.quit()               # close the host
evoto.host.quit(relaunch=True)  # restart it
```

The host flushes the reply before quitting, so the returned
`{"accepted": True, "relaunch": bool}` is an acknowledgement - the IPC
channel drops shortly after. If you spawned the process yourself, keep
the `Popen` handle around as a fallback: terminate it, and SIGKILL as a
last resort.

## Checklist

- Pass `-silent` to the executable, not to the macOS `.app` bundle root.
- Expect `412` from `configure_silent_timeout()` when the host is not
  silent - that is the reliable way to detect the mode.
- Set `timeout_seconds=0` for long-running daemons, otherwise the host
  quits 300 s after your plugin disconnects.
- Use `action="show"` only when a human is meant to take over the
  session; the default is to quit.
