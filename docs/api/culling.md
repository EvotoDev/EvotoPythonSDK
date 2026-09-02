# `evoto.culling`

Use `evoto.culling` to inspect culling state and read culling result data from
the host. Start and restart requests use the host UI workflow and only run when
the target project is currently loaded; other projects are rejected by the host.

```python
import evoto
from evoto.core.api_fields import CullingField

evoto.connect()

def on_progress(data):
    print(
        data.get("progress"),
        data.get("completed_count"),
        data.get("total"),
        data.get(CullingField.SECONDS_REMAINING),
    )

evoto.on("culling.progress", on_progress)

image_ids = [101, 202]

status = evoto.culling.status(use_current_project=True, image_ids=image_ids)
results = evoto.culling.list_results(
    use_current_project=True,
    image_ids=image_ids,
    filters={CullingField.AI_SELECTED: True},
)
faces = evoto.culling.list_faces(use_current_project=True, image_ids=image_ids)
for face in faces:
    print(face.get(CullingField.FACE_ID), face.get(CullingField.ICON))
similar_clusters = evoto.culling.list_clusters(
    use_current_project=True,
    image_ids=image_ids,
    cluster_type="similar",
)
person_clusters = evoto.culling.list_clusters(
    use_current_project=True,
    image_ids=image_ids,
    cluster_type="person",
)
```

Pass `image_ids` to limit read queries to specific images. Omit it or pass an
empty list to query all images in the current project.

Result read APIs (`list_results()`, `list_faces()` and `list_clusters()`) are
available after culling finishes. While culling is running, use `status()` or
the progress events instead.

`list_results()` returns image-level culling labels such as `ai_selected`,
`candidate`, `blurry`, `closed_eyes`, `overexposed`, `underexposed`,
and `similar`. Its `filters` argument accepts a
`CullingResultFilters` dictionary. Use `CullingField` constants as keys, for
example `{CullingField.AI_SELECTED: True, CullingField.SHARP: True,
CullingField.SIMILAR: True}`.
Rows that belong to a similar group include `similar_image_ids`, which contains
the other image IDs in the same group.

`list_faces()` returns face records from the host face data, such as `face_id`,
`image_id`, `person_id`, `icon`, `roi` and `cluster_id`.

`start()` and `restart()` return after the host accepts or skips the request.
They do not wait for culling to finish. Subscribe to `culling.started`,
`culling.progress`, `culling.completed`, `culling.failed` and
`culling.canceled` to display live progress. Progress payloads include
`project_id`, `status`, `progress`, `seconds_remaining`, `completed_count`
and `total`.

`stop()` requests cancellation for the current project's running culling task.
It returns after the stop request is accepted; the final cancellation state is
delivered through `culling.canceled`.

`scan_qr_codes()` scans project images for QR Codes on the host side. Pass
`force=True` to re-check images that already have persisted QR results. Listen
to `culling.qrCode.started`, `culling.qrCode.completed` and
`culling.qrCode.failed` for lifecycle events. The return payload contains
`task_id`, `project_id`, `status`, `success` and `results`. The `results`
array only includes images where QR codes were found; each row has `image_id`,
`absolute_path`, `qr_code_checked`, `has_qr_code` and `qr_code_content`
(a list of decoded QR code strings). Use `list_qr_code_results()` to read
persisted result rows without scanning; it also returns only rows with QR
codes.

`list_clusters()` supports `cluster_type="similar"` and
`cluster_type="person"` (the host also accepts `"face"` as an alias for
`"person"`). Cluster rows include `cluster_id`, `cluster_type`, `image_ids`
and, when available, `recommended_image_id`.

::: evoto.culling.CullingAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true

## Field Constants

::: evoto.culling.CullingResultFilters
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.CullingField
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.CullingStatusValue
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true
