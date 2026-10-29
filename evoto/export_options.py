"""Export options builder with typed constants.

Provides a fluent API for constructing the ``options`` dict passed to
``ExportAPI.start_with_custom``. All JSON key names and enumeration
values are defined as class-level constants so that plugin authors get
IDE auto-completion and avoid hand-typed string literals.
"""

from __future__ import annotations

from enum import Enum, IntEnum

from .core.api_fields import ExportOption


# ---------------------------------------------------------------------------
# Built-in preset suit IDs
# ---------------------------------------------------------------------------

class PresetSuitId:
    """Well-known preset suit IDs defined by the host.

    Real preset suit IDs are numeric strings obtained from
    ``PresetAPI.list()`` -> each preset's ``id`` field.
    These two are special built-in values.
    """
    NO_EFFECT = "-1"
    """Export with no beautify/palette effect applied (original image)."""


# ---------------------------------------------------------------------------
# Enumeration constants
# ---------------------------------------------------------------------------

class FileFormat(str, Enum):
    """Export image format.

    Values are strings and can be used directly in JSON payloads::

        FileFormat.JPEG          # "jpg"
        FileFormat.JPEG == "jpg" # True
    """
    ORIGINAL = "original"
    JPEG = "jpg"
    PNG = "png"
    TIFF_8BIT = "tiff_8bit"
    TIFF_16BIT = "tiff_16bit"


class QualityType(str, Enum):
    """Quality control mode."""
    SIZE = "size"
    PERCENT = "percent"


class ScaleType(str, Enum):
    """Scale mode."""
    NONE = "none"
    PERCENT = "percent"
    WIDTH_HEIGHT = "width_height"
    LONG_EDGE = "long_edge"
    SHORT_EDGE = "short_edge"


class ScaleUnit(str, Enum):
    """Scale display unit (width/height/long edge dimensions)."""
    PIXEL = "px"
    INCH = "in"
    CM = "cm"


class DpiUnit(str, Enum):
    """DPI / resolution metadata unit.

    UI labels: **px/in** (pixels per inch) vs **px/cm** (pixels per centimetre).
    """
    INCH = "in"
    CM = "cm"


class SharpenType(str, Enum):
    """Output sharpening mode."""
    NONE = "none"
    SCREEN = "screen"
    PRINT = "print"


class SharpenAmount(str, Enum):
    """Sharpening strength."""
    STANDARD = "standard"
    LOW = "low"
    HIGH = "high"


class ExistFormat(str, Enum):
    """Behaviour when the output file already exists."""
    ADD_SUFFIX = "add_suffix"
    SKIP = "skip"
    REPLACE = "replace"


class NamingFormat(str, Enum):
    """Output file naming pattern."""
    ORIGINAL = "original"
    CUSTOM_1OF2 = "custom_1of2"
    CAPTURE_DATE = "capture_date"
    CUSTOM_SEQUENCE = "custom_sequence"
    ORIGINAL_CUSTOM = "original_custom"


class WatermarkPosition(IntEnum):
    """Watermark anchor position (3 x 3 grid).

    Layout corresponds to a 3x3 grid::

        TOP_LEFT(1)      TOP_CENTER(2)      TOP_RIGHT(3)
        MIDDLE_LEFT(4)   MIDDLE_CENTER(5)   MIDDLE_RIGHT(6)
        BOTTOM_LEFT(7)   BOTTOM_CENTER(8)   BOTTOM_RIGHT(9)
    """
    TOP_LEFT = 1
    TOP_CENTER = 2
    TOP_RIGHT = 3
    MIDDLE_LEFT = 4
    MIDDLE_CENTER = 5
    MIDDLE_RIGHT = 6
    BOTTOM_LEFT = 7
    BOTTOM_CENTER = 8
    BOTTOM_RIGHT = 9


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class ExportOptions:
    """Fluent builder for the export ``options`` dict.

    Usage::

        from evoto.export_options import ExportOptions, FileFormat, SharpenType

        opts = (ExportOptions()
            .file_format(FileFormat.JPEG)
            .quality(90)
            .scale_long_edge(3000)
            .sharpen(SharpenType.SCREEN)
            .dpi(300)
            .build())
    """

    # -- JSON key constants for the export options dict --
    # Mirrored from :class:`evoto.core.api_fields.ExportOption` so the
    # SDK keeps a single source of truth.
    KEY_FILE_FORMAT = ExportOption.FILE_FORMAT
    KEY_QUALITY_TYPE = ExportOption.QUALITY_TYPE
    KEY_QUALITY = ExportOption.QUALITY
    KEY_LIMIT_SIZE = ExportOption.LIMIT_SIZE
    KEY_SCALE_TYPE = ExportOption.SCALE_TYPE
    KEY_SCALE_UNIT = ExportOption.SCALE_UNIT
    KEY_SCALE_PERCENT = ExportOption.SCALE_PERCENT
    KEY_SCALE_WIDTH = ExportOption.SCALE_WIDTH
    KEY_SCALE_HEIGHT = ExportOption.SCALE_HEIGHT
    KEY_SCALE_LONG_EDGE = ExportOption.SCALE_LONG_EDGE
    KEY_SCALE_SHORT_EDGE = ExportOption.SCALE_SHORT_EDGE
    KEY_SCALE_NEVER_UPSCALE = ExportOption.SCALE_NEVER_UPSCALE
    KEY_DPI = ExportOption.DPI
    KEY_DPI_UNIT = ExportOption.DPI_UNIT
    KEY_SHARPEN_TYPE = ExportOption.SHARPEN_TYPE
    KEY_SHARPEN_AMOUNT = ExportOption.SHARPEN_AMOUNT
    KEY_NAMING_FORMAT = ExportOption.NAMING_FORMAT
    KEY_NAMING_PREFIX = ExportOption.NAMING_PREFIX
    KEY_NAMING_START = ExportOption.NAMING_START
    KEY_NAMING_SUFFIX = ExportOption.NAMING_SUFFIX
    KEY_EXIST_FORMAT = ExportOption.EXIST_FORMAT
    KEY_WATERMARK_ENABLE = ExportOption.WATERMARK_ENABLE
    KEY_WATERMARK_PATH = ExportOption.WATERMARK_PATH
    KEY_WATERMARK_POSITION = ExportOption.WATERMARK_POSITION
    KEY_WATERMARK_ROTATION = ExportOption.WATERMARK_ROTATION
    KEY_WATERMARK_SIZE = ExportOption.WATERMARK_SIZE
    KEY_WATERMARK_OPACITY = ExportOption.WATERMARK_OPACITY
    KEY_WATERMARK_H_OFFSET = ExportOption.WATERMARK_H_OFFSET
    KEY_WATERMARK_V_OFFSET = ExportOption.WATERMARK_V_OFFSET
    KEY_CREATE_SUBDIR = ExportOption.CREATE_SUBDIR
    KEY_SUBDIR_NAME = ExportOption.SUBDIR_NAME
    KEY_CROP_TRANSPARENT = ExportOption.CROP_TRANSPARENT

    def __init__(self) -> None:
        self._data: dict = {}

    # -- File ----------------------------------------------------------

    def file_format(self, fmt: FileFormat | str) -> ExportOptions:
        """Set the output image format.

        Args:
            fmt: Target format, e.g. ``FileFormat.JPEG``.
        """
        self._data[self.KEY_FILE_FORMAT] = fmt
        return self

    def quality(self, percent: int) -> ExportOptions:
        """Set JPEG quality percentage.

        Args:
            percent: JPEG quality from ``1`` to ``100``. Higher values keep
                more detail and create larger files.
        """
        self._data[self.KEY_QUALITY_TYPE] = QualityType.PERCENT
        self._data[self.KEY_QUALITY] = percent
        return self

    def limit_size(self, mb: float) -> ExportOptions:
        """Limit output file size in megabytes.

        Args:
            mb: Target maximum file size in megabytes. Must be greater than
                zero.
        """
        self._data[self.KEY_QUALITY_TYPE] = QualityType.SIZE
        self._data[self.KEY_LIMIT_SIZE] = mb
        return self

    # -- Scale ---------------------------------------------------------

    def scale_percent(self, pct: float, *, never_upscale: bool = True) -> ExportOptions:
        """Scale by percentage.

        Args:
            pct: Scale ratio, for example ``0.5`` for 50% or ``1.0`` for
                original size.
            never_upscale: When true, do not enlarge images beyond their
                original pixel dimensions.
        """
        self._data[self.KEY_SCALE_TYPE] = ScaleType.PERCENT
        self._data[self.KEY_SCALE_PERCENT] = pct
        self._data[self.KEY_SCALE_NEVER_UPSCALE] = never_upscale
        return self

    def scale_long_edge(self, px: int, *, never_upscale: bool = True) -> ExportOptions:
        """Scale so the long edge equals ``px`` pixels.

        Args:
            px: Target long-edge length in pixels.
            never_upscale: When true, do not enlarge images beyond their
                original pixel dimensions.
        """
        self._data[self.KEY_SCALE_TYPE] = ScaleType.LONG_EDGE
        self._data[self.KEY_SCALE_LONG_EDGE] = px
        self._data[self.KEY_SCALE_NEVER_UPSCALE] = never_upscale
        return self

    def scale_short_edge(self, px: int, *, never_upscale: bool = True) -> ExportOptions:
        """Scale so the short edge equals ``px`` pixels.

        Args:
            px: Target short-edge length in pixels.
            never_upscale: When true, do not enlarge images beyond their
                original pixel dimensions.
        """
        self._data[self.KEY_SCALE_TYPE] = ScaleType.SHORT_EDGE
        self._data[self.KEY_SCALE_SHORT_EDGE] = px
        self._data[self.KEY_SCALE_NEVER_UPSCALE] = never_upscale
        return self

    def scale_width_height(self, w: int, h: int, *, never_upscale: bool = True) -> ExportOptions:
        """Scale to explicit width and height in pixels.

        Args:
            w: Target width in pixels.
            h: Target height in pixels.
            never_upscale: When true, do not enlarge images beyond their
                original pixel dimensions.
        """
        self._data[self.KEY_SCALE_TYPE] = ScaleType.WIDTH_HEIGHT
        self._data[self.KEY_SCALE_WIDTH] = w
        self._data[self.KEY_SCALE_HEIGHT] = h
        self._data[self.KEY_SCALE_NEVER_UPSCALE] = never_upscale
        return self

    def dpi(self, value: int) -> ExportOptions:
        """Set output DPI metadata.

        Args:
            value: Resolution value. ``300`` is a common print default.
        """
        self._data[self.KEY_DPI] = value
        return self

    def scale_unit(self, unit: ScaleUnit | str) -> ExportOptions:
        """Set dimension unit for width/height/long-edge/short-edge values.

        Use with :meth:`scale_long_edge` / :meth:`scale_short_edge` /
        :meth:`scale_width_height` when values are in inches or centimetres
        instead of pixels.

        Args:
            unit: ``ScaleUnit.PIXEL`` (``\"px\"``), ``ScaleUnit.INCH`` (``\"in\"``),
                or ``ScaleUnit.CM`` (``\"cm\"``).
        """
        self._data[self.KEY_SCALE_UNIT] = unit
        return self

    def dpi_unit(self, unit: DpiUnit | str) -> ExportOptions:
        """Set whether *dpi* is interpreted as pixels per inch or per cm.

        Args:
            unit: ``DpiUnit.INCH`` (``\"in\"``, px/in) or ``DpiUnit.CM`` (``\"cm\"``, px/cm).
        """
        self._data[self.KEY_DPI_UNIT] = unit
        return self

    # -- Sharpen -------------------------------------------------------

    def sharpen(
        self,
        stype: SharpenType | str,
        amount: SharpenAmount | str = SharpenAmount.STANDARD,
    ) -> ExportOptions:
        """Enable output sharpening.

        Args:
            stype: Sharpening mode, e.g. ``SharpenType.SCREEN``.
            amount: Sharpening strength, e.g. ``SharpenAmount.HIGH``.
        """
        self._data[self.KEY_SHARPEN_TYPE] = stype
        self._data[self.KEY_SHARPEN_AMOUNT] = amount
        return self

    # -- Naming --------------------------------------------------------

    def naming(
        self,
        fmt: NamingFormat | str,
        *,
        prefix: str = "",
        start: int = 1,
        suffix: str = "",
    ) -> ExportOptions:
        """Configure output file naming.

        Args:
            fmt: Naming pattern, e.g. ``NamingFormat.ORIGINAL``.
            prefix: Custom prefix string.
            start: Starting sequence number.
            suffix: Custom suffix string.
        """
        self._data[self.KEY_NAMING_FORMAT] = fmt
        if prefix:
            self._data[self.KEY_NAMING_PREFIX] = prefix
        if start != 1:
            self._data[self.KEY_NAMING_START] = start
        if suffix:
            self._data[self.KEY_NAMING_SUFFIX] = suffix
        return self

    # -- Path / exist --------------------------------------------------

    def exist_format(self, fmt: ExistFormat | str) -> ExportOptions:
        """Set behaviour when output file exists.

        Args:
            fmt: Conflict resolution strategy, e.g. ``ExistFormat.REPLACE``.
        """
        self._data[self.KEY_EXIST_FORMAT] = fmt
        return self

    def create_subdir(self, name: str) -> ExportOptions:
        """Create a sub-directory inside the export directory.

        Args:
            name: Sub-directory name to create under the selected export
                directory.
        """
        self._data[self.KEY_CREATE_SUBDIR] = True
        self._data[self.KEY_SUBDIR_NAME] = name
        return self

    # -- Watermark -----------------------------------------------------

    def watermark(
        self,
        path: str,
        *,
        position: WatermarkPosition | int = WatermarkPosition.BOTTOM_RIGHT,
        size: int = 10,
        opacity: int = 100,
        rotation: int = 0,
        h_offset: int = 3,
        v_offset: int = 3,
    ) -> ExportOptions:
        """Enable watermark overlay.

        Args:
            path: Absolute path to the watermark image file.
            position: Anchor position on a 3x3 grid,
                e.g. ``WatermarkPosition.BOTTOM_RIGHT``.
            size: Watermark size as percentage (0-100).
            opacity: Watermark opacity (0-100).
            rotation: Rotation angle in degrees.
            h_offset: Horizontal offset percentage.
            v_offset: Vertical offset percentage.
        """
        self._data[self.KEY_WATERMARK_ENABLE] = True
        self._data[self.KEY_WATERMARK_PATH] = path
        self._data[self.KEY_WATERMARK_POSITION] = position
        self._data[self.KEY_WATERMARK_SIZE] = size
        self._data[self.KEY_WATERMARK_OPACITY] = opacity
        self._data[self.KEY_WATERMARK_ROTATION] = rotation
        self._data[self.KEY_WATERMARK_H_OFFSET] = h_offset
        self._data[self.KEY_WATERMARK_V_OFFSET] = v_offset
        return self

    # -- Transparent crop ----------------------------------------------

    def crop_transparent(self, enable: bool = True) -> ExportOptions:
        """Crop transparent output to the bounding box of visible pixels.

        When enabled, the host trims every fully transparent row and column
        around the image before writing the file, so a cut-out subject is
        saved without empty margins. The option is off unless this method
        is called.

        Notes:
            * Only output formats with an alpha channel are cropped
              (``FileFormat.PNG``, ``FileFormat.TIFF_8BIT``,
              ``FileFormat.TIFF_16BIT``). With ``FileFormat.JPEG`` the host
              rejects the request with ``ApiError`` code ``400``. With
              ``FileFormat.ORIGINAL`` only sources that keep an alpha
              channel are cropped.
            * Cropping runs last, after watermarking and scaling. The file
              can therefore be smaller than the configured scale size, and
              a watermark placed over a transparent area can be cropped
              away.
            * Pixels with any non-zero alpha (including semi-transparent
              ones) count as visible, so faint matting noise near the edge
              can enlarge the crop box.
            * The image is saved uncropped when it has no alpha channel,
              when it is fully transparent, or when the bounding box already
              covers the whole image.
            * Image sizes reported by export events are the pre-crop sizes.
              Read the output file to get the final dimensions.
            * Requires Evoto 8.1.0 or later. Earlier versions ignore the key
              and export the image uncropped.

        Args:
            enable: ``True`` to crop transparent margins, ``False`` to keep
                the full canvas.
        """
        self._data[self.KEY_CROP_TRANSPARENT] = bool(enable)
        return self

    # -- Build ---------------------------------------------------------

    def build(self) -> dict:
        """Return the assembled options dict."""
        return dict(self._data)
