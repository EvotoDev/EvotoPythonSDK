"""JSON field name constants shared between host and plugin.

Eliminates hand-typed string literals when constructing or parsing the
JSON payloads the SDK exchanges with the host.
"""

from enum import IntEnum


class Field:
    """Common fields."""
    ID = "id"
    NAME = "name"
    STATUS = "status"
    SUCCESS = "success"
    RESULT = "result"
    ERROR = "error"
    ERROR_CODE = "error_code"
    INTERNAL_ERROR_CODE = "internal_error_code"
    CODE = "code"
    MESSAGE = "message"
    REASON = "reason"


class VersionField:
    """Version-related fields."""
    VERSION = "version"
    API_VERSION = "api_version"
    HOST_VERSION = "host_version"
    SDK_VERSION = "sdk_version"
    MIN_SDK_VERSION = "min_sdk_version"
    MIN_API_VERSION = "min_api_version"
    APP = "app"


class PluginField:
    """Plugin handshake / lifecycle fields."""
    PLUGIN_ID = "plugin_id"
    AUTH_TOKEN = "auth_token"
    TASKS = "tasks"
    COMMANDS = "commands"
    PONG = "pong"
    LOGGED = "logged"
    ACKNOWLEDGED = "acknowledged"
    HANDLED = "handled"


class ResourceField:
    """Resource handle serialization keys returned from plugin tasks."""
    TYPE = "type"
    PATH = "path"
    MIME_TYPE = "mime_type"
    WIDTH = "width"
    HEIGHT = "height"


class ResourceType:
    """Values for :attr:`ResourceField.TYPE`."""
    FILE = "file"
    IMAGE = "image"


class LogField:
    """host.log fields."""
    LEVEL = "level"
    MESSAGE = "message"


class LogLevel:
    """host.log ``level`` field values."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class HostField:
    """``host.*`` command fields."""

    RELAUNCH = "relaunch"
    ACCEPTED = "accepted"
    #: ``host.silentTimeout`` fields.
    TIMEOUT_SECONDS = "timeout_seconds"
    ACTION = "action"
    ENABLED = "enabled"
    CONNECTED_PLUGIN_COUNT = "connected_plugin_count"
    IS_LOGGED_IN = "is_logged_in"


class SilentActionValue:
    """``host.silentTimeout`` ``action`` field values.

    - ``QUIT``: the host quits when the silent timer fires.
    - ``SHOW``: the host exits silent mode and shows the main window.
    """

    QUIT = "quit"
    SHOW = "show"


class HostDocField:
    """host.apiDoc filter and response schema fields.

    The leaf ``name``/``type``/``required``/``default``/``description``
    keys are part of the host RPC schema returned by ``host.apiDoc``.
    """
    COMMAND = "command"
    DOMAIN = "domain"
    DESCRIPTION = "description"
    PARAMS = "params"
    RETURNS = "returns"
    EVENTS = "events"
    COMMANDS = "commands"
    NAME = "name"
    TYPE = "type"
    REQUIRED = "required"
    DEFAULT = "default"


class HostDocTypeValue:
    """Values allowed for :attr:`HostDocField.TYPE`."""
    INT = "int"
    STRING = "string"
    BOOL = "bool"
    NUMBER = "number"
    ARRAY = "array"
    OBJECT = "object"


class EventField:
    """Event subscription fields."""
    EVENTS = "events"
    EVENT = "event"
    DATA = "data"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"


class MetaField:
    """_meta envelope fields."""
    META = "_meta"
    TIMESTAMP = "timestamp"
    TASK_ID = "task_id"


class ProjectField:
    """project.* fields."""
    PROJECT_ID = "project_id"
    GROUP_ID = "group_id"
    USE_CURRENT_PROJECT = "use_current_project"
    USE_CURRENT_GROUP = "use_current_group"
    ALLOW_CROSS_CLOUD_SYNC = "allow_cross_cloud_sync"
    TEAM_ID = "team_id"
    STORAGE_PATH = "storage_path"
    STOPPED = "stopped"
    PROCESS_ID = "process_id"
    FILE_ID = "file_id"
    DOWNLOAD_TYPE = "download_type"
    UPLOAD_PROGRESS = "upload_progress"
    DOWNLOAD_PROGRESS = "download_progress"
    CLOUD_SYNC_STATUS = "cloud_sync_status"
    LOCAL_ERROR_CODE = "local_error_code"
    DEBUG_CODE = "debug_code"
    TYPE = "type"
    POSITION = "position"
    PROJECT_COUNT = "project_count"
    NAME_DUPLICATED = "name_duplicated"
    CREATED_TIME = "created_time"
    UPDATE_TIME = "update_time"
    VISIT_TIME = "visit_time"
    IS_CATALOG = "is_catalog"
    IS_CLOUD = "is_cloud"
    DISABLED = "disabled"
    INCLUDE_DISABLED = "include_disabled"
    DATA_MODE = "data_mode"
    PROJECT = "project"
    PROJECTS = "projects"
    GROUP = "group"
    GROUPS = "groups"


class ImageField:
    """image.* fields."""
    PROJECT_ID = "project_id"
    PROJECT_NAME = "project_name"
    PROJECT_GROUP_ID = "project_group_id"
    USE_CURRENT_PROJECT = "use_current_project"
    ALLOW_CROSS_CLOUD_SYNC = "allow_cross_cloud_sync"
    PATHS = "paths"
    TIMEOUT_MS = "timeout_ms"
    IMPORT_ID = "import_id"
    IMPORT_LISTENER_UUID = "import_listener_uuid"
    ADDED_COUNT = "added_count"
    REPEAT_COUNT = "repeat_count"
    DATA_MODE = "data_mode"
    IMAGES = "images"
    IMAGE_ID = "image_id"
    IMAGE_IDS = "imageIds"
    IMAGE_IDS_INPUT = "image_ids"
    DELETE_MODE = "delete_mode"
    ACCEPTED = "accepted"
    STATUS = "status"
    REQUESTED_COUNT = "requested_count"
    DELETED_COUNT = "deleted_count"
    FAILED_ITEMS = "failed_items"
    UUIDS = "uuids"
    FILENAME = "filename"
    ORIGIN_PATH = "origin_path"
    FORMAT = "format"
    WIDTH = "width"
    HEIGHT = "height"
    FILE_SIZE = "file_size"
    INCLUDE_METADATA = "include_metadata"
    METADATA = "metadata"


class ImageMetadataGroup:
    """Top-level group keys in the ``image.info`` metadata payload.

    Empty metadata groups are omitted from the payload.
    """

    EXIF_EXPOSURE   = "LibraryExifExposure"
    EXIF_CAMERA     = "LibraryExifCamera"
    EXIF_GPS        = "LibraryExifGps"
    IPTC_METADATA   = "LibraryIptcMetaData"
    IPTC_STATUS     = "LibraryIptcStatus"
    IPTC_COPYRIGHT  = "LibraryIptcCopyright"
    IPTC_CONTENT    = "LibraryIptcContent"
    IPTC_CONTACT    = "LibraryIptcContact"


class DeleteMode:
    """image.delete supported mode values."""
    RECYCLE = "recycle"
    REMOVE = "remove"
    TRASH = "trash"


class PresetField:
    """preset.* fields."""
    CLASS_ID = "classId"
    SUIT_ID = "suitId"
    SUIT_IDS = "suitIds"
    PRESETS = "presets"
    CLASSES = "classes"
    PRESET_ID = "presetId"
    PRESET_NAME = "presetName"
    CLASS_NAME = "className"
    CLASS_TYPE = "classType"
    TYPE = "type"
    IS_TEAM = "isTeam"
    COLOR_WEIGHT = "colorWeight"
    IMAGE_IDS = "imageIds"
    APPLIED_COUNT = "appliedCount"
    RENDER = "render"
    READY_SUIT_IDS = "readySuitIds"
    DOWNLOADED = "downloaded"


class PresetType:
    """preset.list ``type`` field values."""
    SYSTEM = "system"
    USER = "user"
    TEAM = "team"
    UNKNOWN = "unknown"


class ExportField:
    """export.* fields."""
    PROJECT_ID = "project_id"
    IMAGE_IDS = "imageIds"
    EXPORT_DIR = "export_dir"
    OPTIONS = "options"
    PRESET_SUIT_IDS = "preset_suit_ids"
    EXPORT_PRESET_IDS = "export_preset_ids"
    EXPORT_PRESETS = "export_presets"
    EXPORT_LISTENER_UUID = "export_listener_uuid"
    CROP_TRANSPARENT = "crop_transparent"
    EXPORT_NAME = "export_name"
    EXPORT_DIR_ID = "export_dir_id"
    STATE = "state"
    INCLUDE_ITEMS = "include_items"
    PROGRESS = "progress"
    REQUESTED_COUNT = "requested_count"
    COMPLETED_COUNT = "completed_count"
    SUCCESS_COUNT = "success_count"
    FAILED_COUNT = "failed_count"
    ITEMS = "items"
    ITEM = "item"
    IMAGE_ID = "image_id"
    UUID = "uuid"
    OUTPUT_PATH = "output_path"
    ORIGIN_PATH = "origin_path"
    ORIGIN_DIR = "origin_dir"
    FILENAME = "filename"
    IMG_FORMAT = "img_format"
    PRESET_SUIT_ID = "preset_suit_id"
    PRESET_SUIT_NAME = "preset_suit_name"
    MESSAGE = "message"
    REASON = "reason"
    ERROR_MESSAGE = "error_message"
    ERROR_CODE = "error_code"
    INTERNAL_ERROR_CODE = "internal_error_code"
    FAILED_ITEMS = "failed_items"


class ExportOption:
    """``export.startWithCustom`` options dict keys."""

    FILE_FORMAT = "file_format"
    QUALITY_TYPE = "quality_type"
    QUALITY = "quality"
    LIMIT_SIZE = "limit_size"
    SCALE_TYPE = "scale_type"
    SCALE_UNIT = "scale_unit"
    SCALE_PERCENT = "scale_percent"
    SCALE_WIDTH = "scale_width"
    SCALE_HEIGHT = "scale_height"
    SCALE_LONG_EDGE = "scale_long_edge"
    SCALE_SHORT_EDGE = "scale_short_edge"
    SCALE_NEVER_UPSCALE = "scale_never_upscale"
    DPI = "dpi"
    DPI_UNIT = "dpi_unit"
    RESOLUTION_UNIT = "resolution_unit"
    SHARPEN_TYPE = "sharpen_type"
    SHARPEN_AMOUNT = "sharpen_amount"
    NAMING_FORMAT = "naming_format"
    NAMING_PREFIX = "naming_prefix"
    NAMING_START = "naming_start"
    NAMING_SUFFIX = "naming_suffix"
    EXIST_FORMAT = "exist_format"
    CREATE_SUBDIR = "create_subdir"
    SUBDIR_NAME = "subdir_name"
    WATERMARK_ENABLE = "watermark_enable"
    WATERMARK_PATH = "watermark_path"
    WATERMARK_POSITION = "watermark_position"
    WATERMARK_ROTATION = "watermark_rotation"
    WATERMARK_SIZE = "watermark_size"
    WATERMARK_OPACITY = "watermark_opacity"
    WATERMARK_H_OFFSET = "watermark_h_offset"
    WATERMARK_V_OFFSET = "watermark_v_offset"
    CROP_TRANSPARENT = "crop_transparent"


# ---------------------------------------------------------------------------
# Allowed values for the enum-style fields inside ``export.startWithCustom``'s
# ``options`` payload live as user-facing enums in :mod:`evoto.export_options`
# (``FileFormat`` / ``QualityType`` / ``ScaleType`` / ``ScaleUnit`` /
# ``DpiUnit`` / ``SharpenType`` / ``SharpenAmount`` / ``NamingFormat`` /
# ``ExistFormat``). The user-facing enum is the single Python definition of
# the wire value.
# ---------------------------------------------------------------------------


class ExportState:
    """export.* event ``state`` field values."""
    PENDING = "pending"
    STARTED = "started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ITEM_FINISHED = "item_finished"


class ImportItemStatus:
    """Allowed values for per-item ``status`` in an ``image.import`` result."""

    IMPORTED = "imported"
    DUPLICATE = "duplicate"
    IMPORTING = "importing"


class DeleteFailReason:
    """Allowed values for the ``reason`` field of a failed ``image.delete`` entry."""

    IMAGE_NOT_FOUND = "image_not_found"
    CLOUD_DELETE_FAILED = "cloud_delete_failed"
    CLOUD_ONLY_RECYCLE = "cloud_image_only_supports_recycle"


class ExportFailReason:
    """Allowed values for the ``reason`` field of failed export items."""

    API_ERROR = "api_error"
    NATIVE_ERROR = "native_error"
    EXPORT_ERROR = "export_error"
    UNKNOWN = "unknown"


class ShutdownReasonValue:
    """Allowed values for the ``reason`` field in a ``plugin.shutdown`` request."""

    HOST_REQUESTED = "host_requested"
    UNLOAD_REQUESTED = "unload_requested"


class ImportState:
    """image.import event ``state`` field values."""
    STARTED = "started"
    REQUESTING = "requesting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EMPTY = "empty"
    DUPLICATE = "duplicate"
    UNKNOWN = "unknown"


class ExportItemStatus:
    """Per-item export ``status`` field values."""
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class BatchField:
    """Common per-item batch response fields."""
    REQUESTED_COUNT = "requested_count"
    ACCEPTED_COUNT = "accepted_count"
    SUCCESS_COUNT = "success_count"
    SKIPPED_COUNT = "skipped_count"
    FAILED_COUNT = "failed_count"
    ITEMS = "items"
    IMAGE_ID = "image_id"
    STATUS = "status"
    SKIPPED_REASON = "skipped_reason"
    ERROR_MESSAGE = "error_message"


class BatchItemStatus:
    """Per-item batch status values."""
    SUCCESS = "success"
    ACCEPTED = "accepted"
    SKIPPED = "skipped"
    FAILED = "failed"


class MetadataField:
    """metadata.* fields."""
    IMAGE_IDS = "image_ids"
    SOURCE = "source"
    FIELDS = "fields"
    SIDECAR = "sidecar"
    METADATA = "metadata"
    TITLE = "title"
    CAPTION = "caption"
    CREATOR = "creator"
    COPYRIGHT = "copyright"
    SUPPLEMENTAL_CATEGORIES = "supplemental_categories"
    RATING = "rating"
    COLOR_LABEL = "color_label"
    FLAG = "flag"


class MetadataColorLabel(IntEnum):
    """Valid values for :attr:`MetadataField.COLOR_LABEL`.

    An ``IntEnum`` so it can be used directly as an integer in payloads while
    still constraining callers to the accepted set at type-check time.

    ``Gray`` (1) and ``Orange`` (7) exist in the host engine but are
    intentionally NOT exposed here: ``Gray`` is treated as "no color"
    internally, so neither is a valid user-facing color label. The members
    below are therefore the full set of accepted color labels.
    """
    NONE = 0
    GREEN = 2
    PURPLE = 3
    BLUE = 4
    YELLOW = 5
    RED = 6


class MetadataFlag(IntEnum):
    """Valid values for :attr:`MetadataField.FLAG`.

    An ``IntEnum`` so it can be used directly as an integer in payloads while
    still constraining callers to the accepted set at type-check time.
    """
    REJECT = -1
    NONE = 0
    PICK = 1


class MetadataSourceValue:
    """metadata.read source values."""
    EVOTO = "evoto"


class LibraryField:
    """library.* fields."""
    ID = "id"
    NAME = "name"
    PROJECT_ID = "project_id"
    USE_CURRENT_PROJECT = "use_current_project"
    DATA_MODE = "data_mode"
    FILTERS = "filters"
    SORT = "sort"
    PAGE = "page"
    PAGE_SIZE = "page_size"
    IMAGES = "images"
    IMAGE_IDS = "image_ids"
    RATING = "rating"
    COLOR_LABEL = "color_label"
    FLAG = "flag"
    EDIT_STATUS = "edit_status"
    EXPORT_STATUS = "export_status"
    HIDDEN = "hidden"
    REJECTED = "rejected"
    FORMAT = "format"
    ORIENTATION = "orientation"
    FILE_NAME = "file_name"
    FILENAME = "filename"
    ORIGIN_PATH = "origin_path"
    WIDTH = "width"
    HEIGHT = "height"
    FILE_SIZE = "file_size"
    HAS_CROP = "has_crop"
    CAPTURE_TIME = "capture_time"
    DIMENSIONS = "dimensions"
    SELECTED_COUNT = "selected_count"
    PRIMARY_IMAGE_ID = "primary_image_id"
    PRIMARY = "primary"
    SPACE_ID = "space_id"
    SPACE = "space"
    SPACES = "spaces"
    TYPE = "type"


class CullingField:
    """culling.* fields."""
    PROJECT_ID = "project_id"
    IMAGE_ID = "image_id"
    IMAGE_IDS = "image_ids"
    FORCE = "force"
    FILTERS = "filters"
    MODE = "mode"
    CLUSTER_TYPE = "cluster_type"
    PROGRESS = "progress"
    SECONDS_REMAINING = "seconds_remaining"
    REQUESTED_COUNT = "requested_count"
    COMPLETED_COUNT = "completed_count"
    SUCCESS_COUNT = "success_count"
    SKIPPED_COUNT = "skipped_count"
    FAILED_COUNT = "failed_count"
    ABSOLUTE_PATH = "absolute_path"
    QR_CODE_CHECKED = "qr_code_checked"
    HAS_QR_CODE = "has_qr_code"
    QR_CODE_CONTENT = "qr_code_content"
    RESULTS = "results"
    FACES = "faces"
    CLUSTERS = "clusters"
    UPDATED_TIME = "updated_time"
    AI_SELECTED = "ai_selected"
    CANDIDATE = "candidate"
    BLURRY = "blurry"
    SHARP = "sharp"
    CLOSED_EYES = "closed_eyes"
    OVEREXPOSED = "overexposed"
    UNDEREXPOSED = "underexposed"
    SIMILAR = "similar"
    SIMILAR_IMAGE_IDS = "similar_image_ids"
    FACE_ID = "face_id"
    PERSON_ID = "person_id"
    GROUP_ID = "group_id"
    CLUSTER_ID = "cluster_id"
    RECOMMENDED_IMAGE_ID = "recommended_image_id"
    ICON = "icon"
    ROI = "roi"


class CullingStatusValue:
    """culling.status values."""
    NOT_STARTED = "not_started"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class FaceField:
    """face.* fields."""
    PROJECT_ID = "project_id"
    IMAGE_ID = "image_id"
    IMAGE_IDS = "image_ids"
    USE_CURRENT_PROJECT = "use_current_project"
    MODEL_FOLDER = "model_folder"
    AUTO_LOAD_MODEL = "auto_load_model"
    TASK_ID = "task_id"
    ACCEPTED = "accepted"
    READY = "ready"
    STATUS = "status"
    SUCCESS = "success"
    REASON = "reason"
    ERROR_MESSAGE = "error_message"
    ABSOLUTE_PATH = "absolute_path"
    RESULT = "result"
    RESULTS = "results"
    FACES = "faces"
    FACE_COUNT = "face_count"
    BOX_X = "box_x"
    BOX_Y = "box_y"
    BOX_WIDTH = "box_width"
    BOX_HEIGHT = "box_height"
    AGE = "age"
    GENDER = "gender"
    WEAR_GLASSES = "wear_glasses"
    ELAPSED_MS = "elapsed_ms"
    PROGRESS = "progress"
    TOTAL = "total"
    COMPLETED_COUNT = "completed_count"
    REQUESTED_COUNT = "requested_count"
    SUCCESS_COUNT = "success_count"
    FAILED_COUNT = "failed_count"
    INCLUDE_RESULTS = "include_results"
    CANCEL_REQUESTED = "cancel_requested"


class FaceModelStatusValue:
    """face.modelStatus / face.model.* ``status`` values."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"


class FaceTaskStateValue:
    """face.detect task-level ``status`` values."""
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class FaceGenderValue:
    """face.detect per-face ``gender`` values."""
    MALE = "male"
    FEMALE = "female"
    UNIDENTIFIED = "unidentified"


class FaceFailReasonValue:
    """face.detect per-image ``reason`` values on a failed row.

    A missing original file, an empty path and a detector error are all
    reported as ``status="failed"`` on that image; the task skips it and
    carries on. ``reason`` tells the three cases apart.
    """
    PATH_EMPTY = "path_empty"
    FILE_NOT_FOUND = "file_not_found"
    DETECT_FAILED = "detect_failed"


class EditField:
    """edit.* fields."""
    IMAGE_ID = "image_id"
    IMAGE_IDS = "image_ids"
    SOURCE_IMAGE_ID = "source_image_id"
    TARGET_IMAGE_IDS = "target_image_ids"
    MODULES = "modules"
    STATUS = "status"
    NAME = "name"
    NEW_IMAGE_ID = "new_image_id"
    HAS_EDIT = "has_edit"
    HAS_COLOR = "has_color"
    HAS_AI_COLOR = "has_ai_color"
    HAS_PORTRAIT = "has_portrait"
    HAS_BACKGROUND = "has_background"
    HAS_CROP = "has_crop"
    HAS_CLOTHES = "has_clothes"
    HAS_PET = "has_pet"
    HAS_PRESET = "has_preset"


class EditModuleValue:
    """Supported edit module names."""
    COLOR = "color"
    AI_COLOR = "ai_color"
    PORTRAIT = "portrait"
    BACKGROUND = "background"
    CROP = "crop"
    CLOTHES = "clothes"
    PET = "pet"


class RpcField:
    """JSON-RPC envelope fields."""
    TYPE = "type"
    ID = "id"
    METHOD = "method"
    PARAMS = "params"
    STATUS = "status"
    RESULT = "result"
    ERROR = "error"
    CODE = "code"
    MESSAGE = "message"
    EVENT = "event"
    DATA = "data"
    META = "_meta"
    TASK_ID = "task_id"
    SDK_VERSION = "sdk_version"
    TIMESTAMP = "timestamp"
    HOST_VERSION = "host_version"
    API_VERSION = "api_version"


class RpcType:
    """JSON-RPC message type values."""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"


class RpcStatus:
    """JSON-RPC status values."""
    OK = "ok"
    ERROR = "error"


class UserField:
    """user.* fields."""
    USER_ID = "user_id"
    DISPLAY_NAME = "display_name"
    EMAIL = "email"
    CREDITS_TOTAL = "credits_total"
    CREDITS_USED = "credits_used"
    CREDITS_REMAINING = "credits_remaining"
    HAS_CLOUD_SPACE = "has_cloud_space"
    CLOUD_USED_SPACE = "cloud_used_space"
    CLOUD_TOTAL_SPACE = "cloud_total_space"
    NEXT_BILL_DATE = "next_bill_date"
    IS_SUBSCRIBED = "is_subscribed"
    IS_VIP = "is_vip"


class WatchField:
    """watch.* fields."""
    WATCH_ID = "watchId"
    PATHS = "paths"
    FILTERS = "filters"
    INCLUDE_SUB_DIR = "includeSubDir"
    FILES = "files"
    WATCHERS = "watchers"
    RUNNING = "running"

    PROJECT_ID = "project_id"
    IMAGES = "images"
    IMAGE_IDS = "imageIds"
    ABSOLUTE_PATH = "absolute_path"
    EXPORT_STATUS = "export_status"
    UPDATED_COUNT = "updated_count"
    INTERVAL = "interval"
    UNIT = "unit"
    ENABLED = "enabled"
    TOTAL = "total"
    TOTAL_MONITORS = "total_monitors"
    STOPPED_COUNT = "stopped_count"
    PROJECT_IDS = "project_ids"


# Wire values for ``watch.exportMonitor`` ``unit`` and ``watch.start``
# ``filters`` live as user-facing enums in :mod:`evoto.watcher` (``TimeUnit``
# / ``WatchFilterType``). The user-facing enum is the single Python
# definition of the wire value.
