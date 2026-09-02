"""RPC command names shared between host and plugin.

Single source of truth for the command strings the SDK and host agree on.
"""


class HostCmd:
    """Commands the plugin calls on the host."""
    PING = "host.ping"
    LOG = "host.log"
    GET_VERSION = "host.getVersion"
    VERSION = "host.version"
    CAPABILITIES = "host.capabilities"
    API_DOC = "host.apiDoc"
    SUBSCRIBE = "host.subscribe"
    UNSUBSCRIBE = "host.unsubscribe"
    QUIT = "host.quit"
    SILENT_TIMEOUT = "host.silentTimeout"


class PluginCmd:
    """Commands the host calls on the plugin."""
    HELLO = "plugin.hello"
    SHUTDOWN = "plugin.shutdown"
    PING = "plugin.ping"
    EVENT = "plugin.event"

    TASK_PREFIX = "task."


class ProjectCmd:
    """project.* domain commands."""
    LIST = "project.list"
    INFO = "project.info"
    CURRENT = "project.current"
    CREATE = "project.create"
    RENAME = "project.rename"
    DELETE = "project.delete"
    SWITCH = "project.switch"
    CONVERT_TO_CLOUD = "project.convertToCloud"
    STOP_CLOUD_LOADING = "project.stopCloudLoading"
    CLOUD_STATUS = "project.cloudStatus"
    GROUP_LIST = "project.group.list"
    GROUP_GET = "project.group.get"
    GROUP_CREATE = "project.group.create"
    GROUP_RENAME = "project.group.rename"
    GROUP_DELETE = "project.group.delete"

    # Lifecycle events broadcast by host (no explicit host.subscribe needed).
    # Delivered to every connected plugin after the mutation commits.
    CREATED_EVENT = "project.created"
    RENAMED_EVENT = "project.renamed"
    DELETED_EVENT = "project.deleted"
    GROUP_CREATED_EVENT = "project.group.created"
    GROUP_RENAMED_EVENT = "project.group.renamed"
    GROUP_DELETED_EVENT = "project.group.deleted"
    SWITCH_COMPLETED = "project.switch.completed"
    SWITCH_FAILED = "project.switch.failed"
    CONVERT_TO_CLOUD_COMPLETED = "project.convertToCloud.completed"
    CONVERT_TO_CLOUD_FAILED = "project.convertToCloud.failed"
    CLOUD_UPLOAD_COMPLETED = "project.cloudUpload.completed"
    CLOUD_UPLOAD_FAILED = "project.cloudUpload.failed"
    CLOUD_UPLOAD_PROGRESS = "project.cloudUpload.progress"
    CLOUD_DOWNLOAD_PROGRESS = "project.cloudDownload.progress"
    CLOUD_DOWNLOAD_COMPLETED = "project.cloudDownload.completed"
    CLOUD_DOWNLOAD_FAILED = "project.cloudDownload.failed"
    CLOUD_DOWNLOAD_PAUSED = "project.cloudDownload.paused"
    CLOUD_IMAGE_UPLOAD_FAILED = "project.cloudImageUpload.failed"
    CLOUD_IMAGE_DOWNLOAD_FAILED = "project.cloudImageDownload.failed"

    #: Event names the host broadcasts unconditionally; plugins simply attach
    #: listeners via :func:`evoto.host.on` - no subscribe handshake required.
    LIFECYCLE_EVENTS = (
        CREATED_EVENT,
        RENAMED_EVENT,
        DELETED_EVENT,
        SWITCH_COMPLETED,
        SWITCH_FAILED,
        CONVERT_TO_CLOUD_COMPLETED,
        CONVERT_TO_CLOUD_FAILED,
        CLOUD_UPLOAD_COMPLETED,
        CLOUD_UPLOAD_FAILED,
        CLOUD_UPLOAD_PROGRESS,
        CLOUD_DOWNLOAD_PROGRESS,
        CLOUD_DOWNLOAD_COMPLETED,
        CLOUD_DOWNLOAD_FAILED,
        CLOUD_DOWNLOAD_PAUSED,
        CLOUD_IMAGE_UPLOAD_FAILED,
        CLOUD_IMAGE_DOWNLOAD_FAILED,
        GROUP_CREATED_EVENT,
        GROUP_RENAMED_EVENT,
        GROUP_DELETED_EVENT,
    )


class PresetCmd:
    """preset.* domain commands."""
    LIST = "preset.list"
    APPLY_TO_IMAGE = "preset.applyToImage"
    APPLY_TO_IMAGE_ASYNC = "preset.applyToImageAsync"
    RESET = "preset.reset"
    ENSURE_READY = "preset.ensureReady"


class ImageCmd:
    """image.* domain commands."""
    IMPORT = "image.import"
    IMPORT_ASYNC = "image.importAsync"
    SUBSCRIBE = "image.importSubscribe"
    UNSUBSCRIBE = "image.importUnsubscribe"
    LIST = "image.list"
    INFO = "image.info"
    DELETE = "image.delete"
    STARTED = "import.started"
    PROGRESS = "import.progress"
    COMPLETED = "import.completed"
    FAILED = "import.failed"


class ExportCmd:
    """export.* domain commands and event names."""
    LIST_EXPORT_PRESETS = "export.listExportPresets"
    START_WITH_CUSTOM = "export.startWithCustom"
    START_WITH_EXPORT_PRESET = "export.startWithExportPreset"
    SUBSCRIBE = "export.subscribe"
    UNSUBSCRIBE = "export.unsubscribe"
    QUERY = "export.query"
    PAUSE = "export.pause"
    RESUME = "export.resume"
    RETRY = "export.retry"
    DELETE = "export.delete"

    STARTED = "export.started"
    PROGRESS = "export.progress"
    ITEM_FINISHED = "export.item_finished"
    COMPLETED = "export.completed"
    FAILED = "export.failed"


class UserCmd:
    """user.* domain commands."""
    INFO = "user.info"


class WatchCmd:
    """watch.* folder watching commands."""
    START = "watch.start"
    STOP = "watch.stop"
    LIST = "watch.list"

    FILES_ADDED = "watch.files.added"

    EXPORT_MONITOR_START = "watch.exportMonitor.start"
    EXPORT_MONITOR_STOP = "watch.exportMonitor.stop"
    EXPORT_MONITOR_QUERY = "watch.exportMonitor.query"
    LIST_UNEXPORTED = "watch.listUnexported"
    MARK_EXPORTED = "watch.markExported"

    UNEXPORTED_FOUND = "watch.unexported.found"


class MetadataCmd:
    """metadata.* domain commands."""
    READ = "metadata.read"
    WRITE = "metadata.write"
    READ_FROM_FILE = "metadata.readFromFile"
    SAVE_TO_FILE = "metadata.saveToFile"


class LibraryCmd:
    """library.* domain commands."""
    LIST_IMAGES = "library.listImages"
    GET_SELECTION = "library.getSelection"
    SET_SELECTION = "library.setSelection"
    ADD_SELECTION = "library.addSelection"
    CLEAR_SELECTION = "library.clearSelection"
    UPDATE_LABELS = "library.updateLabels"
    LIST_SPACES = "library.listSpaces"
    CURRENT_SPACE = "library.currentSpace"
    SWITCH_SPACE = "library.switchSpace"
    SWITCH_SPACE_COMPLETED = "library.switchSpace.completed"
    SWITCH_SPACE_FAILED = "library.switchSpace.failed"


class CullingCmd:
    """culling.* domain commands."""
    STATUS = "culling.status"
    START = "culling.start"
    RESTART = "culling.restart"
    STOP = "culling.stop"
    LIST_RESULTS = "culling.listResults"
    LIST_FACES = "culling.listFaces"
    LIST_CLUSTERS = "culling.listClusters"
    STARTED = "culling.started"
    PROGRESS = "culling.progress"
    COMPLETED = "culling.completed"
    FAILED = "culling.failed"
    CANCELED = "culling.canceled"
    QR_CODE_SCAN = "culling.qrCode.scan"
    QR_CODE_LIST_RESULTS = "culling.qrCode.listResults"
    QR_CODE_STARTED = "culling.qrCode.started"
    QR_CODE_PROGRESS = "culling.qrCode.progress"
    QR_CODE_COMPLETED = "culling.qrCode.completed"
    QR_CODE_FAILED = "culling.qrCode.failed"


class FaceCmd:
    """face.* domain commands and event names.

    Wraps the host-side standalone face detector. Both model loading and
    detection are asynchronous: the command returns as soon as the host accepts
    the request, and the real outcome arrives through events.

    Model side: :attr:`LOAD_MODEL` is confirmed by :attr:`MODEL_LOADED` /
    :attr:`MODEL_FAILED`, and :attr:`MODEL_STATUS` can be polled at any time.

    Detect side: :attr:`DETECT` returns a ``task_id`` and finishes with
    :attr:`DETECT_COMPLETED`, :attr:`DETECT_FAILED` or :attr:`DETECT_CANCELED`.
    Use :attr:`DETECT_STATUS` to query a task and :attr:`CANCEL_DETECT` to stop
    it. Only one detect task runs at a time.
    """
    LOAD_MODEL = "face.loadModel"
    MODEL_STATUS = "face.modelStatus"
    UNLOAD_MODEL = "face.unloadModel"
    DETECT = "face.detect"
    DETECT_STATUS = "face.detectStatus"
    CANCEL_DETECT = "face.cancelDetect"

    MODEL_LOADING = "face.model.loading"
    MODEL_LOADED = "face.model.loaded"
    MODEL_FAILED = "face.model.failed"
    DETECT_STARTED = "face.detect.started"
    DETECT_PROGRESS = "face.detect.progress"
    DETECT_COMPLETED = "face.detect.completed"
    DETECT_FAILED = "face.detect.failed"
    DETECT_CANCELED = "face.detect.canceled"


class EditCmd:
    """edit.* domain commands."""
    STATUS = "edit.status"
    SYNC_FROM = "edit.syncFrom"
    RESET = "edit.reset"
    CREATE_VIRTUAL_COPY = "edit.createVirtualCopy"
