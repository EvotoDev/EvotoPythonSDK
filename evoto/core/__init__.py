"""Evoto Plugin SDK - internal core subpackage.

Plugin authors should import from the top-level :mod:`evoto` namespace
(e.g. ``import evoto; evoto.connect()``) rather than reaching into
``evoto.core`` directly. The symbols re-exported here are kept for
internal use (tests, scripts, advanced integrations).
"""

from .resource import FileResource, ImageResource
from ._internal.exceptions import ReplyStatus
from .version import SDK_VERSION

__version__ = SDK_VERSION

__all__ = [
    "FileResource",
    "ImageResource",
    "ReplyStatus",
    "SDK_VERSION",
]
