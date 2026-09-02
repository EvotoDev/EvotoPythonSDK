"""Demo-side Evoto environment resolver.

This module is intentionally kept for local development demos. Public docs
should present the simple ``evoto.connect()`` path, but developers running
multiple local Evoto builds can still point demos at the desired host here.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from evoto.core.ipc_constants import (
    DEFAULT_ENV_PREFIX,
    ENV_PREFIXES,
    ENV_SOCKET_PATH,
    default_socket_path,
)

logger = logging.getLogger(__name__)

#: Path of the demo-local environment config file. Sits next to this
#: module so all demos share a single copy.
CONFIG_PATH: Path = Path(__file__).resolve().parent / "evoto_env.json"


def load_env() -> str:
    """Return the configured Evoto env prefix, or ``"pro"`` as fallback."""
    if not CONFIG_PATH.is_file():
        return DEFAULT_ENV_PREFIX

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "Failed to read %s (%s); falling back to %r",
            CONFIG_PATH, exc, DEFAULT_ENV_PREFIX,
        )
        return DEFAULT_ENV_PREFIX

    env = data.get("environment") if isinstance(data, dict) else None
    if env not in ENV_PREFIXES:
        if env is not None:
            logger.warning(
                "Invalid 'environment' %r in %s; falling back to %r",
                env, CONFIG_PATH, DEFAULT_ENV_PREFIX,
            )
        return DEFAULT_ENV_PREFIX

    return env


def resolve_socket_path() -> str:
    r"""Return the full local IPC endpoint path to connect to."""
    env_override = os.environ.get(ENV_SOCKET_PATH)
    if env_override:
        return env_override

    return default_socket_path(load_env())


def load_env_info() -> dict:
    r"""Return diagnostic info about the resolved demo environment."""
    env_override = os.environ.get(ENV_SOCKET_PATH)
    if env_override:
        return {
            "env": None,
            "source": "env_var",
            "socket_path": env_override,
        }

    source = "config" if CONFIG_PATH.is_file() else "default"
    env = load_env()
    return {
        "env": env,
        "source": source,
        "socket_path": default_socket_path(env),
    }


__all__ = [
    "CONFIG_PATH",
    "load_env",
    "resolve_socket_path",
    "load_env_info",
]
