"""IPC-level constants shared with the host.

These values are part of the plugin <-> host contract; any change here
must be mirrored on the host side simultaneously.
"""

import logging
import os
import sys
import tempfile

logger = logging.getLogger(__name__)

#: Base socket name, without environment prefix.
SOCKET_BASE_NAME = "evoto_plugin_host"

#: Valid environment prefixes:
#:
#: - ``"pro"``      - production / default fallback
#: - ``"pro_pre"``  - pre-release
#: - ``"test"``     - test build
#: - ``"dev"``      - development build
ENV_PREFIXES = ("pro", "pro_pre", "test", "dev")

#: Production environment prefix. Used as the SDK default when no
#: explicit environment is configured.
DEFAULT_ENV_PREFIX = "pro"


def socket_name_for_env(env: str | None) -> str:
    """Return the fully-qualified socket name for ``env``.

    Args:
        env: one of :data:`ENV_PREFIXES`. ``None`` / unknown value falls
            back to :data:`DEFAULT_ENV_PREFIX` (``pro``) with a warning.

    Returns:
        ``"{env}_{SOCKET_BASE_NAME}"``.
    """
    if env not in ENV_PREFIXES:
        if env is not None:
            logger.warning(
                "Unknown Evoto env prefix %r, falling back to %r",
                env, DEFAULT_ENV_PREFIX,
            )
        env = DEFAULT_ENV_PREFIX
    return f"{env}_{SOCKET_BASE_NAME}"


#: Unix / local socket name used for the plugin <-> host IPC endpoint.
#: Defaults to the production-prefixed name; the Evoto host listens on
#: ``{env}_{SOCKET_BASE_NAME}`` where ``env`` is the host build flavour.
SOCKET_NAME = socket_name_for_env(DEFAULT_ENV_PREFIX)

#: ``True`` when running on Windows. On Windows the IPC endpoint is a
#: **Named Pipe** (``\\.\pipe\<name>``); on POSIX it is a Unix Domain
#: Socket file (``$TMPDIR/<name>``).
IS_WINDOWS = sys.platform == "win32"

#: Windows named-pipe address prefix. Literal form: ``\\.\pipe\``.
WIN_PIPE_PREFIX = "\\\\.\\pipe\\"


def default_socket_path(env: str | None = None) -> str:
    """Return the platform-correct IPC endpoint for ``env``.

    The same logical socket name maps to two different transports
    depending on platform:

    - **Windows** -> named pipe ``\\\\.\\pipe\\<name>``
    - **POSIX**   -> Unix Domain Socket at ``<tmpdir>/<name>``

    Args:
        env: one of :data:`ENV_PREFIXES` (``pro`` / ``pro_pre`` /
            ``test`` / ``dev``). ``None`` falls back to
            :data:`DEFAULT_ENV_PREFIX`.

    Returns:
        Fully-qualified address string suitable for passing to
        :meth:`evoto.connect` / :meth:`evoto.run`.
    """
    name = socket_name_for_env(env)
    if IS_WINDOWS:
        return WIN_PIPE_PREFIX + name
    return os.path.join(tempfile.gettempdir(), name)


def is_windows_pipe_path(path: str) -> bool:
    """True when ``path`` looks like a Windows named-pipe address.

    Used by the transport layer to decide whether to speak Win32 named
    pipes instead of ``AF_UNIX`` - lets an override via
    ``EVOTO_PLUGIN_SOCKET`` still pick the right transport regardless
    of the host platform default. Accepts forward slashes too since
    Windows APIs treat them interchangeably.
    """
    if not path:
        return False
    normalized = path.replace("/", "\\")
    return normalized.startswith(WIN_PIPE_PREFIX)

#: Plugin manifest filename expected inside each plugin directory.
MANIFEST_FILENAME = "plugin.json"

#: Environment variable carrying the auth token injected by the host
#: into each spawned plugin subprocess.
ENV_AUTH_TOKEN = "EVOTO_PLUGIN_AUTH_TOKEN"

#: Environment variable allowing an explicit host socket path override
#: for externally launched plugins (e.g. during development).
ENV_SOCKET_PATH = "EVOTO_PLUGIN_SOCKET"


class PluginManifestKey:
    """``plugin.json`` schema key names (the host <-> plugin contract).

    Plugin authors write these keys in their ``plugin.json``; the host
    parses them when spawning the plugin process.
    """

    ID = "id"
    NAME = "name"
    VERSION = "version"
    DESCRIPTION = "description"
    ENTRY = "entry"
    PYTHON = "python"
    DEPENDENCIES = "dependencies"

    #: Default Python entry script name when ``entry`` is omitted.
    DEFAULT_ENTRY = "main.py"
    #: Default manifest version when ``version`` is omitted.
    DEFAULT_VERSION = "0.0.0"
