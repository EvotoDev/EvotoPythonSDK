"""Standalone face detection helpers.

The host wraps a dedicated face detector that is independent from the culling
pipeline. It reports, per face, the bounding box, age, gender and whether the
person wears glasses.

Both halves of the workflow are asynchronous. The model is expensive (hundreds
of megabytes) and stays resident in the host process once loaded, so loading is
a separate step from detection. Detection itself is a task: :meth:`FaceAPI.detect`
returns a ``task_id`` right away, progress and completion arrive as events, and
the task can be polled with :meth:`FaceAPI.detect_status` or stopped with
:meth:`FaceAPI.cancel_detect`. Only one detect task runs at a time.
"""

from __future__ import annotations

import threading
from typing import Callable, TypedDict

from .core.api_commands import FaceCmd
from .core.api_fields import (
    FaceField,
    FaceModelStatusValue,
    FaceTaskStateValue,
    ProjectField,
)


class FaceModelState(TypedDict, total=False):
    """Payload shape returned by :meth:`FaceAPI.model_status`."""

    status: str
    """``unloaded``, ``loading``, ``ready`` or ``failed``; the constants live in
    ``evoto.core.api_fields.FaceModelStatusValue``."""

    ready: bool
    """True only while ``status`` is ``ready``, which is when ``detect()`` can
    run without an on-demand load."""

    model_folder: str
    """Folder the model was loaded from. Empty until a load has been requested.
    """

    error_message: str
    """Why the load failed. Present only when ``status`` is ``failed``."""

    accepted: bool
    """Whether this specific call started a new load task. Present in
    ``load_model()`` and ``unload_model()`` replies, absent from
    ``model_status()``. False means the request was a no-op, either because the
    same folder was already loaded or because another load was in flight."""


class DetectedFace(TypedDict, total=False):
    """One detected face. Coordinates are pixels in the original image."""

    box_x: float
    """Left edge of the face box."""

    box_y: float
    """Top edge of the face box."""

    box_width: float
    """Width of the face box."""

    box_height: float
    """Height of the face box."""

    age: int
    """Estimated age, or ``-1`` when the detector could not tell. ``-1`` is a
    sentinel, not an age."""

    gender: str
    """``male``, ``female`` or ``unidentified``; the constants live in
    ``evoto.core.api_fields.FaceGenderValue``."""

    wear_glasses: bool
    """Whether the person wears glasses. This is not an open/closed eye state -
    for closed eyes use ``closed_eyes`` from ``evoto.culling``."""


class FaceImageResult(TypedDict, total=False):
    """Detect outcome for a single image.

    ``status`` is ``success`` or ``failed``. A ``success`` row with
    ``face_count == 0`` means the detector found nobody, which is also what an
    image it cannot decode looks like - only an outright detector error is
    reported as ``failed``.
    """

    image_id: int
    """Library image this row describes."""

    project_id: int
    """Project the image belongs to. Rows in one task may span several projects
    when ``detect()`` was called with an explicit ``image_ids`` list."""

    absolute_path: str
    """Path of the original file that was read."""

    status: str
    """``success`` or ``failed`` - the shared batch constants
    ``evoto.core.api_fields.BatchItemStatus.SUCCESS`` and ``.FAILED``."""

    reason: str
    """Why this image failed: ``file_not_found``, ``path_empty`` or
    ``detect_failed``. Present only when ``status`` is ``failed``; the constants
    live in ``evoto.core.api_fields.FaceFailReasonValue``."""

    error_message: str
    """Detector error detail. Present only when ``reason`` is
    ``detect_failed``."""

    face_count: int
    """Number of faces found, i.e. the length of ``faces``. Present only when
    ``status`` is ``success``, where ``0`` is a valid result meaning nobody was
    found."""

    faces: list[DetectedFace]
    """One entry per detected face, empty when none were found. Present only
    when ``status`` is ``success``."""

    elapsed_ms: int
    """Milliseconds spent detecting this one image. Present only when ``status``
    is ``success``."""


class FaceTaskState(TypedDict, total=False):
    """Progress and results of one detect task.

    Returned by :meth:`FaceAPI.detect_status` and carried by the terminal
    ``face.detect.*`` events. ``results`` is only present when explicitly
    requested, since a large project produces thousands of rows.
    """

    task_id: str
    """Identifier returned by ``detect()``. Every ``face.detect.*`` event
    carries the same value, so a listener can tell tasks apart."""

    project_id: int
    """Project the task was started for, or ``0`` when it was started from an
    explicit ``image_ids`` list."""

    status: str
    """``running``, ``completed``, ``failed`` or ``canceled``; the constants live
    in ``evoto.core.api_fields.FaceTaskStateValue``. ``completed`` only means
    every image was processed - some of them may have failed."""

    success: bool
    """True when the task itself ran to the end, which is ``status ==
    "completed"``. Independent of whether individual images failed, so check
    ``failed_count`` as well."""

    total: int
    """Number of images the task will actually process."""

    requested_count: int
    """Number of images the request resolved to before the task started. Differs
    from ``total`` only when the host dropped unusable rows."""

    completed_count: int
    """Images processed so far, i.e. ``success_count + failed_count``."""

    success_count: int
    """Images that were detected successfully, counting those where no face was
    found."""

    failed_count: int
    """Images that could not be detected. Non-zero is compatible with
    ``status == "completed"``, because one failed image never stops the task."""

    progress: int
    """Percent complete, ``0`` to ``100``, as an integer."""

    cancel_requested: bool
    """True once ``cancel_detect()`` has been accepted. The task keeps running
    until the current image finishes, so this can be True while ``status`` is
    still ``running``."""

    elapsed_ms: int
    """Milliseconds since the task started, frozen once it reaches a terminal
    status."""

    error_message: str
    """Why the whole task failed, for example because the model could not be
    loaded. Present only when ``status`` is ``failed``."""

    results: list[FaceImageResult]
    """One row per processed image, including partial results for a canceled
    task. Present only when explicitly requested with
    ``detect_status(include_results=True)`` or carried by a terminal event,
    because a large project produces thousands of rows."""


class FaceAPI:
    """Load the face detect model and run face detection on library images."""

    def __init__(self, client):
        self._client = client

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def load_model(
        self,
        *,
        model_folder: str | None = None,
        timeout: float = 30.0,
    ) -> FaceModelState:
        """Request an asynchronous model load.

        Returns as soon as the host accepts the request - it does not wait for
        the model to finish loading. Track the outcome through the
        ``face.model.loaded`` / ``face.model.failed`` events, by polling
        :meth:`model_status`, or by calling :meth:`wait_for_model`.

        Calling this while the model is already loaded from the same folder is
        a no-op and returns ``accepted=False`` with ``status="ready"``. Calling
        it while another load is in flight also returns ``accepted=False``.

        Args:
            model_folder: Resource path holding the detection model. Omit to
                use the host's own resource path, which is what production
                plugins want - the host knows whether its resources are a
                directory or a packed bundle.
            timeout: RPC timeout in seconds for the acceptance reply only.

        Returns:
            A :class:`FaceModelState` whose ``status`` reflects the state at
            reply time - usually ``loading``, or ``ready`` when the same folder
            was already loaded. ``accepted`` tells whether this specific call
            started a new load task; ``error_message`` is set only when the host
            rejected the request outright.
        """
        payload: dict = {}
        if model_folder is not None:
            payload[FaceField.MODEL_FOLDER] = model_folder
        return self._client.call(FaceCmd.LOAD_MODEL, payload, timeout)

    def model_status(self, *, timeout: float = 10.0) -> FaceModelState:
        """Return the current model state.

        Never blocks on the host side, so it stays responsive even while a
        detect task is running.

        Args:
            timeout: RPC timeout in seconds.

        Returns:
            Payload with ``status`` (one of
            :class:`evoto.core.api_fields.FaceModelStatusValue`), ``ready``,
            ``model_folder`` and ``error_message``.
        """
        return self._client.call(FaceCmd.MODEL_STATUS, {}, timeout)

    def is_model_ready(self, *, timeout: float = 10.0) -> bool:
        """Return True when the model is loaded and can serve :meth:`detect`.

        Args:
            timeout: RPC timeout in seconds.

        Returns:
            The ``ready`` flag of :meth:`model_status`, so False covers
            ``unloaded``, ``loading`` and ``failed`` alike.
        """
        return bool(self.model_status(timeout=timeout).get(FaceField.READY, False))

    def unload_model(self, *, timeout: float = 30.0) -> FaceModelState:
        """Release the model and free its memory.

        The host rejects this while a load or detect task is running.

        Args:
            timeout: RPC timeout in seconds.

        Returns:
            A :class:`FaceModelState` with ``status`` back to ``unloaded``,
            ``ready`` False and ``accepted`` True when this call performed the
            release.
        """
        return self._client.call(FaceCmd.UNLOAD_MODEL, {}, timeout)

    def wait_for_model(
        self,
        *,
        model_folder: str | None = None,
        timeout: float = 300.0,
    ) -> FaceModelState:
        """Load the model if needed and block until it is ready.

        Subscribes to ``face.model.loaded`` / ``face.model.failed`` before
        issuing the load request, so a fast load cannot slip through between
        the request and the subscription.

        Args:
            model_folder: Model resource path. Omit to use the host default.
            timeout: Maximum seconds to wait for the load to finish.

        Returns:
            A :class:`FaceModelState` with ``status`` ``ready`` and ``ready``
            True, since any other outcome raises instead of returning.

        Raises:
            RuntimeError: If the host reports that loading failed.
            TimeoutError: If *timeout* is exceeded.
        """
        done = threading.Event()
        result_box: list[dict] = []
        error_box: list[dict] = []

        def _on_loaded(data: dict) -> None:
            result_box.append(data)
            done.set()

        def _on_failed(data: dict) -> None:
            error_box.append(data)
            done.set()

        self._client.on(FaceCmd.MODEL_LOADED, _on_loaded)
        self._client.on(FaceCmd.MODEL_FAILED, _on_failed)
        try:
            accepted = self.load_model(model_folder=model_folder)
            # Already loaded: no event will ever arrive, so return right away.
            if accepted.get(FaceField.READY, False):
                return accepted
            if accepted.get(FaceField.STATUS) == FaceModelStatusValue.FAILED:
                raise RuntimeError(
                    "Face model load failed: "
                    f"{accepted.get(FaceField.ERROR_MESSAGE, 'unknown error')}"
                )
            if not done.wait(timeout):
                raise TimeoutError(f"Face model load timed out after {timeout}s")
        finally:
            self._client.off(FaceCmd.MODEL_LOADED, _on_loaded)
            self._client.off(FaceCmd.MODEL_FAILED, _on_failed)

        if error_box:
            payload = error_box[0]
            raise RuntimeError(
                "Face model load failed: "
                f"{payload.get(FaceField.ERROR_MESSAGE, 'unknown error')}"
            )
        return result_box[0]

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(
        self,
        *,
        image_ids: list[int] | None = None,
        project_id: int | None = None,
        use_current_project: bool = False,
        auto_load_model: bool = True,
        timeout: float = 30.0,
    ) -> FaceTaskState:
        """Start a detect task and return immediately with its ``task_id``.

        Pick the images either by ``image_ids`` or by project. ``image_ids``
        wins when both are given, and may span multiple projects.

        This does **not** wait for detection to finish. Track the task in any
        of three ways: subscribe to ``face.detect.progress`` and
        ``face.detect.completed`` via :meth:`on_detect_progress` /
        :meth:`on_detect_completed`, poll :meth:`detect_status` with the
        returned ``task_id``, or call :meth:`wait_for_detect` to block until
        the task ends. :meth:`cancel_detect` stops it early.

        Only one detect task runs at a time, no matter whether it was started
        from an ID list or from a project. A second call while one is running
        is rejected with a 409 error that names the running ``task_id``.

        Args:
            image_ids: Image IDs to detect. Takes priority over the project
                arguments.
            project_id: Detect every non-deleted image of this project. Used
                only when ``image_ids`` is empty.
            use_current_project: Resolve the project from the host UI instead
                of passing ``project_id``.
            auto_load_model: Load the model on demand when it is not ready.
                Pass False to fail fast with a 412 error instead. Note the
                on-demand load happens inside the task, so the model load time
                counts towards the task, not towards this call.
            timeout: RPC timeout in seconds for the acceptance reply only.

        Returns:
            Payload with ``task_id``, ``accepted``, ``project_id``, ``status``
            and ``requested_count``. ``accepted`` is False when the request
            resolved to zero images, in which case ``status`` is already
            ``completed`` and no events will follow.

        Raises:
            evoto.core._internal.exceptions.ApiError: If the host rejects the
                request, for example when the model is not loaded and
                ``auto_load_model`` is False, or when another detect task is
                already running.
        """
        payload: dict = {
            FaceField.AUTO_LOAD_MODEL: auto_load_model,
        }
        if image_ids is not None:
            payload[FaceField.IMAGE_IDS] = image_ids
        if use_current_project:
            payload[ProjectField.USE_CURRENT_PROJECT] = True
        elif project_id is not None:
            payload[FaceField.PROJECT_ID] = project_id
        return self._client.call(FaceCmd.DETECT, payload, timeout)

    def detect_status(
        self,
        task_id: str | None = None,
        *,
        include_results: bool = False,
        timeout: float = 10.0,
    ) -> FaceTaskState:
        """Return the overall state of a detect task.

        Answers "is it done, how far along, and how many images failed" without
        waiting. Stays responsive while detection is running.

        Args:
            task_id: Task to query. Omit to query the task the host is running
                right now, or the most recent one if none is running.
            include_results: Also return the per-image rows detected so far.
                Off by default because a large project yields thousands of rows.
            timeout: RPC timeout in seconds.

        Returns:
            A :class:`FaceTaskState`. ``status`` is one of
            :class:`evoto.core.api_fields.FaceTaskStateValue`, and ``results`` is
            present only when ``include_results`` was True.

        Raises:
            evoto.core._internal.exceptions.ApiError: 404 when ``task_id`` is
                unknown, or when no task has ever been started.
        """
        payload: dict = {FaceField.INCLUDE_RESULTS: include_results}
        if task_id is not None:
            payload[FaceField.TASK_ID] = task_id
        return self._client.call(FaceCmd.DETECT_STATUS, payload, timeout)

    def cancel_detect(
        self,
        task_id: str | None = None,
        *,
        timeout: float = 10.0,
    ) -> FaceTaskState:
        """Ask the running detect task to stop.

        The image currently being detected still finishes, so the task stops on
        the next image boundary rather than instantly. Results for images
        already detected are kept and remain readable through
        :meth:`detect_status`. The task ends with a ``face.detect.canceled``
        event and final status ``canceled``.

        Args:
            task_id: Task to cancel. Omit to cancel whatever is running.
            timeout: RPC timeout in seconds.

        Returns:
            Payload with ``task_id``, ``accepted`` and ``status``. ``accepted``
            is False when the task had already finished, which is not an error.

        Raises:
            evoto.core._internal.exceptions.ApiError: 404 when ``task_id`` is
                unknown, or when no task has ever been started.
        """
        payload: dict = {}
        if task_id is not None:
            payload[FaceField.TASK_ID] = task_id
        return self._client.call(FaceCmd.CANCEL_DETECT, payload, timeout)

    def wait_for_detect(
        self,
        task_id: str,
        *,
        include_results: bool = True,
        on_image: Callable[[FaceImageResult], None] | None = None,
        on_progress: Callable[[dict], None] | None = None,
        timeout: float = 3600.0,
    ) -> FaceTaskState:
        """Block until the given detect task ends, then return its final state.

        Waits for the task's terminal event - ``completed``, ``failed`` or
        ``canceled``. A cancelled task is *not* an error here: it returns
        normally with ``status="canceled"`` and whatever results it managed to
        produce, so partial work is never lost.

        Subscribes before checking the current status, so a task that finishes
        while this method is starting up cannot be missed.

        Args:
            task_id: Task returned by :meth:`detect`.
            include_results: Fetch the per-image rows for the returned state.
            on_image: Optional callback invoked with each image's
                :class:`FaceImageResult` the moment that image is detected, so
                results can be consumed while the task is still running. Only
                rows of *this* task are delivered. Runs on the SDK event
                thread, so keep it cheap.
            on_progress: Optional callback invoked with the raw
                ``face.detect.progress`` payload, which also carries the
                counters. Use :paramref:`on_image` when you only want results.
            timeout: Maximum seconds to wait. Detection cost scales with image
                count, so raise this for large projects.

        Returns:
            The :class:`FaceTaskState` in its terminal form, so ``status`` is
            ``completed`` or ``canceled`` - a whole-task failure raises instead.
            A ``canceled`` task still carries everything detected before the
            stop.

        Raises:
            RuntimeError: If the task failed as a whole, for example because
                the model could not be loaded. Per-image failures do not raise;
                they are reported as failed rows inside ``results``.
            TimeoutError: If *timeout* is exceeded. The task keeps running on
                the host; use :meth:`cancel_detect` to stop it.
        """
        done = threading.Event()

        def _on_terminal(data: dict) -> None:
            if data.get(FaceField.TASK_ID) == task_id:
                done.set()

        def _on_image_progress(data: dict) -> None:
            if data.get(FaceField.TASK_ID) != task_id:
                return
            row = data.get(FaceField.RESULT)
            if row is not None:
                on_image(row)

        self._client.on(FaceCmd.DETECT_COMPLETED, _on_terminal)
        self._client.on(FaceCmd.DETECT_FAILED, _on_terminal)
        self._client.on(FaceCmd.DETECT_CANCELED, _on_terminal)
        if on_image is not None:
            self._client.on(FaceCmd.DETECT_PROGRESS, _on_image_progress)
        if on_progress is not None:
            self._client.on(FaceCmd.DETECT_PROGRESS, on_progress)
        try:
            # The task may already be over; the events above would never fire.
            current = self.detect_status(task_id, include_results=False)
            if current.get(FaceField.STATUS) != FaceTaskStateValue.RUNNING:
                done.set()
            if not done.wait(timeout):
                raise TimeoutError(
                    f"Face detect task {task_id} did not finish within {timeout}s"
                )
        finally:
            self._client.off(FaceCmd.DETECT_COMPLETED, _on_terminal)
            self._client.off(FaceCmd.DETECT_FAILED, _on_terminal)
            self._client.off(FaceCmd.DETECT_CANCELED, _on_terminal)
            if on_image is not None:
                self._client.off(FaceCmd.DETECT_PROGRESS, _on_image_progress)
            if on_progress is not None:
                self._client.off(FaceCmd.DETECT_PROGRESS, on_progress)

        # Read the authoritative state from the host rather than trusting the
        # event payload, so the caller always sees consistent counters.
        final = self.detect_status(task_id, include_results=include_results)
        if final.get(FaceField.STATUS) == FaceTaskStateValue.FAILED:
            raise RuntimeError(
                "Face detect task failed: "
                f"{final.get(FaceField.ERROR_MESSAGE, 'unknown error')}"
            )
        return final

    def detect_and_wait(
        self,
        *,
        image_ids: list[int] | None = None,
        project_id: int | None = None,
        use_current_project: bool = False,
        auto_load_model: bool = True,
        include_results: bool = True,
        on_image: Callable[[FaceImageResult], None] | None = None,
        on_progress: Callable[[dict], None] | None = None,
        timeout: float = 3600.0,
    ) -> FaceTaskState:
        """Start a detect task and block until it ends.

        Convenience wrapper over :meth:`detect` plus :meth:`wait_for_detect`
        for scripts that have nothing else to do while detecting. Prefer the
        two-step form in a UI plugin, where blocking the calling thread is not
        acceptable.

        Args:
            image_ids: Image IDs to detect. Takes priority over the project
                arguments.
            project_id: Detect every non-deleted image of this project.
            use_current_project: Resolve the project from the host UI.
            auto_load_model: Load the model on demand when it is not ready.
            include_results: Fetch the per-image rows for the returned state.
            on_image: Optional per-image :class:`FaceImageResult` callback,
                invoked as each image is detected.
            on_progress: Optional ``face.detect.progress`` callback.
            timeout: Maximum seconds to wait for the task to finish.

        Returns:
            The final :class:`FaceTaskState`.

        Raises:
            RuntimeError: If the task failed as a whole.
            TimeoutError: If *timeout* is exceeded.
        """
        started = self.detect(
            image_ids=image_ids,
            project_id=project_id,
            use_current_project=use_current_project,
            auto_load_model=auto_load_model,
        )
        task_id = started.get(FaceField.TASK_ID, "")
        # Zero images resolved: the host already marked the task completed.
        if not started.get(FaceField.ACCEPTED, False):
            return self.detect_status(task_id, include_results=include_results)
        return self.wait_for_detect(
            task_id,
            include_results=include_results,
            on_image=on_image,
            on_progress=on_progress,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def on_model_loaded(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``face.model.loaded``."""
        self._client.on(FaceCmd.MODEL_LOADED, callback)

    def on_model_failed(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``face.model.failed``."""
        self._client.on(FaceCmd.MODEL_FAILED, callback)

    def on_detect_progress(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``face.detect.progress``.

        Fires once per image, as soon as that image is detected. The payload's
        ``result`` field holds that image's :class:`FaceImageResult` - the exact
        row that will also appear in the task's final ``results`` - so a plugin
        can render outcomes while the task is still running instead of waiting
        for it to end.
        """
        self._client.on(FaceCmd.DETECT_PROGRESS, callback)

    def on_detect_completed(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``face.detect.completed``."""
        self._client.on(FaceCmd.DETECT_COMPLETED, callback)

    def on_detect_failed(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``face.detect.failed``."""
        self._client.on(FaceCmd.DETECT_FAILED, callback)

    def on_detect_canceled(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``face.detect.canceled``."""
        self._client.on(FaceCmd.DETECT_CANCELED, callback)
