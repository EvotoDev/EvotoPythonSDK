# `evoto.face`

Use `evoto.face` to run the host's standalone face detector over library
images. For every detected face it reports the bounding box, age, gender and
whether the person wears glasses.

This detector is independent from AI culling: it does not need a culling run,
it does not write to the culling tables, and results are returned to the plugin
rather than persisted.

```python
import evoto
from evoto.core.api_fields import FaceField

evoto.connect()

# 1. Load the model. Hundreds of megabytes, so this is asynchronous.
evoto.face.wait_for_model()

# 2. Start a detect task. Returns immediately with a task ID.
started = evoto.face.detect(image_ids=[101, 202, 303])
task_id = started[FaceField.TASK_ID]

# 3. Follow it, then read the final state.
final = evoto.face.wait_for_detect(
    task_id,
    on_progress=lambda d: print(d[FaceField.COMPLETED_COUNT], "/", d[FaceField.TOTAL]),
)
print(final[FaceField.STATUS], final[FaceField.FAILED_COUNT], "failed")

# 4. Read per-image outcomes.
for row in final[FaceField.RESULTS]:
    print(row[FaceField.IMAGE_ID], row[FaceField.STATUS], row.get(FaceField.FACE_COUNT))
    for face in row.get(FaceField.FACES, []):
        print("   ", face[FaceField.AGE], face[FaceField.GENDER], face[FaceField.WEAR_GLASSES])
```

Steps 2 and 3 collapse into `detect_and_wait()` when the calling thread has
nothing else to do, but a UI plugin should keep them apart and drive the UI from
the events instead of blocking.

To handle images one by one as they come in, rather than in a batch at the end,
pass `on_image`:

```python
def show(row):
    print(row[FaceField.IMAGE_ID], row[FaceField.STATUS], row.get(FaceField.FACE_COUNT))

evoto.face.wait_for_detect(task_id, on_image=show)
```

`on_image` receives one `FaceImageResult` per image the moment that image is
detected - the same row that later shows up in the task's `results`.

## Model lifecycle

The model is expensive to load and stays resident in the host process, so
loading is separate from detection.

`load_model()` returns as soon as the host accepts the request; it does not
wait for the load to finish. Track the outcome in one of three ways:

- listen to `face.model.loaded` / `face.model.failed`
- poll `model_status()` or `is_model_ready()`
- call `wait_for_model()`, which loads and blocks until ready

`wait_for_model()` is the convenient choice for scripts. It subscribes before
issuing the request, so a fast load cannot be missed, and it returns
immediately when the model is already loaded.

`load_model()` is idempotent. Calling it when the same folder is already loaded
returns `accepted=False` with `status="ready"` instead of paying the load cost
again. Calling it while another load is in flight also returns
`accepted=False`.

`model_status()` never blocks on the host side, so it stays responsive even
while a long detect task is running. Its `status` is one of `unloaded`,
`loading`, `ready` or `failed`; on `failed`, `error_message` explains why.

`unload_model()` frees the memory. The host rejects it with a 409 error while a
load or detect task is running.

Omit `model_folder` in production - the host falls back to its own model
resource path, and it knows whether those resources are a plain directory or a
packed bundle. Pass it explicitly only to point at custom resources during
development.

## Detecting faces

Choose the images either by `image_ids` or by project:

```python
# Explicit IDs, may span multiple projects.
evoto.face.detect(image_ids=[101, 202])

# Every non-deleted image of a project.
evoto.face.detect(project_id=7)

# The project currently open in the host UI.
evoto.face.detect(use_current_project=True)
```

`image_ids` takes priority when both are supplied.

`detect()` does not wait. It returns `task_id`, `accepted`, `status` and
`requested_count` as soon as the host queues the task, and the actual work
happens in the background. When the request resolves to zero images you get
`accepted=False` and `status="completed"` right away, and no events follow.

By default the model is loaded on demand when it is not ready yet. Pass
`auto_load_model=False` to fail fast with a 412 error instead, which is useful
when you want to control load timing yourself. Note that an on-demand load
happens *inside* the task, so its cost counts towards the task rather than
towards the `detect()` call.

### One task at a time

The detector is a single host-wide instance, so only one detect task exists at
any moment - it makes no difference whether it was started from an ID list or
from a project. A second `detect()` while one is running is rejected with a 409
error whose message names the running `task_id`, so you can decide whether to
wait for it or cancel it:

```python
from evoto.core._internal.exceptions import ApiError

try:
    started = evoto.face.detect(project_id=7)
except ApiError as exc:
    print("busy:", exc)          # message contains the running task_id
    running = evoto.face.detect_status()   # omit task_id to get the running one
    print(running[FaceField.PROGRESS], "% done")
```

### Tracking a task

Three ways, all keyed by `task_id`:

- **Events** - `face.detect.progress` per image, then exactly one of
  `face.detect.completed`, `face.detect.failed` or `face.detect.canceled`. The
  terminal event is how you know the whole batch is done. Each progress payload
  carries that image's full result under `result`, so you can consume outcomes
  as they are produced rather than waiting for the end.
- **Polling** - `detect_status(task_id)` returns `status`, `total`,
  `completed_count`, `success_count`, `failed_count`, `progress`,
  `cancel_requested` and `elapsed_ms`. Add `include_results=True` for the
  per-image rows, which are excluded by default because a large project yields
  thousands of them. Omit `task_id` to ask about whatever is running now.
- **Blocking** - `wait_for_detect(task_id)` returns the final state. It
  subscribes before checking status, so a task that ends during startup is not
  missed, and it raises `RuntimeError` only on a task-level failure.

Task snapshots outlive the task, so you can query one after it finished. The
host keeps the 16 most recent.

### Cancelling

`cancel_detect()` stops the running task. The image being detected cannot be
interrupted, so the task stops at the next image boundary rather than instantly.
Everything already detected is kept and stays readable through
`detect_status(task_id, include_results=True)`.

```python
evoto.face.cancel_detect()            # or cancel_detect(task_id)
final = evoto.face.wait_for_detect(task_id)
assert final[FaceField.STATUS] == "canceled"
print("kept", final[FaceField.COMPLETED_COUNT], "of", final[FaceField.TOTAL])
```

A cancelled task is not an error: `wait_for_detect()` returns normally with
`status="canceled"` and the partial results. `cancel_detect()` on an
already-finished task returns `accepted=False`, which is also not an error.

## Reading the results

Each row in `results` describes one image and carries `image_id`,
`project_id`, `absolute_path` and `status`. There are only two outcomes:

| `status` | Meaning |
| --- | --- |
| `success` | Detection ran. `face_count`, `faces` and `elapsed_ms` are present. |
| `failed` | The image was not detected. `reason` says why. |

`failed` covers every way one image can go wrong, and `reason` distinguishes
them: `file_not_found` when the original is gone, `path_empty` when the library
row has no path, and `detect_failed` when the detector itself raised, in which
case `error_message` carries the detail. **A failed image never stops the task** -
it is recorded, skipped, and the task moves to the next image. That is why a
task can finish with `status="completed"` while `failed_count` is non-zero.

The two values are the shared batch constants
`evoto.core.api_fields.BatchItemStatus.SUCCESS` and `.FAILED`; the reasons are in
`evoto.core.api_fields.FaceFailReasonValue`.

An image with `status="success"` and `face_count=0` is a **successful**
detection that simply found nobody. Do not treat it as a failure. Be aware that
the detector also returns an empty face list for an image it cannot decode,
without raising, so such a row is indistinguishable from a photo with no people
in it; only an outright detector error becomes `detect_failed`.

Every entry of `faces` has `box_x`, `box_y`, `box_width` and `box_height` in
original-image pixel coordinates, plus `age` (`-1` when unknown), `gender`
(`male` / `female` / `unidentified`) and `wear_glasses`.

Detection itself runs on a thumbnail whose longest edge is 2048 px and the
coordinates are scaled back to original-image pixels, so a very small face in a
high-resolution photo may be missed.

!!! note "Glasses, not closed eyes"
    The detector reports `wear_glasses`. It does not report an open/closed eye
    state. If you need closed-eye detection, use the culling result field
    `closed_eyes` from [`evoto.culling`](culling.md) instead.

## Events

| Event | Fires when |
| --- | --- |
| `face.model.loading` | A load task has started |
| `face.model.loaded` | The model became ready |
| `face.model.failed` | Loading failed; payload has `error_message` |
| `face.detect.started` | A detect task started; payload has `total` |
| `face.detect.progress` | One image finished; payload has that image's `result` plus `image_id`, `progress`, `completed_count`, `success_count`, `failed_count`, `total` |
| `face.detect.completed` | Every image was processed; payload is the full task state including `results` |
| `face.detect.failed` | The task failed as a whole, e.g. the model could not be loaded |
| `face.detect.canceled` | The task was stopped by `cancel_detect()`; payload holds the partial `results` |

`face.detect.completed`, `face.detect.failed` and `face.detect.canceled` are
terminal and mutually exclusive: exactly one fires per task. Waiting for one of
the three is how you learn that detection is really over.

Every `face.detect.*` payload carries the same `task_id` that `detect()`
returns, so a listener can tell tasks apart.

Subscribe with `evoto.on("face.detect.progress", handler)` or with the
convenience helpers below.

::: evoto.face.FaceAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true

## Payload Shapes

::: evoto.face.FaceModelState
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.face.FaceTaskState
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.face.FaceImageResult
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.face.DetectedFace
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

## Field Constants

::: evoto.core.api_fields.FaceField
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.FaceModelStatusValue
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.FaceGenderValue
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.FaceFailReasonValue
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.FaceTaskStateValue
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true
