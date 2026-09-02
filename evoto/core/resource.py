"""Resource handles for returning large/binary-friendly results."""

import os
from dataclasses import dataclass

from .api_fields import ResourceField, ResourceType


@dataclass
class FileResource:
    """Handle referencing a file on disk."""
    path: str
    mime_type: str | None = None

    def __post_init__(self):
        if not os.path.isabs(self.path):
            self.path = os.path.abspath(self.path)

    def exists(self) -> bool:
        """Return True if the path exists."""
        return os.path.exists(self.path)

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict."""
        return {
            ResourceField.TYPE: ResourceType.FILE,
            ResourceField.PATH: self.path,
            ResourceField.MIME_TYPE: self.mime_type,
        }


@dataclass
class ImageResource(FileResource):
    """Handle referencing an image file plus optional dimensions."""
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict."""
        return {
            ResourceField.TYPE: ResourceType.IMAGE,
            ResourceField.PATH: self.path,
            ResourceField.MIME_TYPE: self.mime_type,
            ResourceField.WIDTH: self.width,
            ResourceField.HEIGHT: self.height,
        }


def file(path: str, mime_type: str | None = None) -> FileResource:
    """Factory for FileResource."""
    return FileResource(path=path, mime_type=mime_type)


def image(path: str, width: int | None = None, height: int | None = None) -> ImageResource:
    """Factory for ImageResource."""
    return ImageResource(path=path, width=width, height=height)
