# `evoto.library`

Use `evoto.library` to query project image rows, update lightweight labels,
manage the current UI selection, and read or switch the active personal/team
space.

Filtering is a data API only: it returns matching rows and does not change the
visible library filter state in the host UI.

```python
import evoto
from evoto.core.api_fields import LibraryField, MetadataColorLabel, MetadataFlag

evoto.connect()

images = evoto.library.list_images(
    project_id=123,
    filters={
        LibraryField.RATING: [2, 3],
        LibraryField.FLAG: [MetadataFlag.PICK, MetadataFlag.REJECT],
        LibraryField.EXPORT_STATUS: ["unexported", "failed"],
        LibraryField.FORMAT: ["RAW", "JPG"],
        LibraryField.ORIENTATION: ["landscape", "portrait"],
        LibraryField.FILE_NAME: ["IMG", "DSC"],
    },
    sort=LibraryField.CAPTURE_TIME,
    sort_desc=True,
    page=1,
    page_size=50,
)

selected_ids = [img[LibraryField.ID] for img in images[:3]]
evoto.library.update_labels(selected_ids, color_label=MetadataColorLabel.GREEN)

selection = evoto.library.get_selection()
print(selection["project_id"], selection["selected_count"], selection.get("primary_image_id"))
for img in selection.get("images", []):
    print(img[LibraryField.ID], img[LibraryField.ORIGIN_PATH], img[LibraryField.PRIMARY])

evoto.library.set_selection([101], primary_image_id=101)
evoto.library.add_selection([202, 303])
evoto.library.clear_selection([202])
evoto.library.clear_selection()

spaces = evoto.library.list_spaces()
team_spaces = evoto.library.list_spaces("team")
current_space = evoto.library.current_space()
evoto.library.switch_space(team_spaces[0]["space_id"])
```

`list_images(filters=...)` accepts lists for every filter. Multiple values in
one field use OR matching, while different filter fields are combined together.

Supported filter keys:

- `LibraryField.RATING`: star levels, e.g. `[2, 3]`.
- `LibraryField.COLOR_LABEL`: `MetadataColorLabel` members, e.g. `[MetadataColorLabel.GREEN, MetadataColorLabel.RED]`.
- `LibraryField.FLAG`: `MetadataFlag` members, e.g. `[MetadataFlag.PICK, MetadataFlag.REJECT]` (legacy strings `"flagged"`, `"rejected"`, `"unflagged"` still accepted).
- `LibraryField.EDIT_STATUS`: `"unedited"`, `"edited"`.
- `LibraryField.EXPORT_STATUS`: `"unexported"`, `"exported"`, `"failed"`.
- `LibraryField.FORMAT`: `"RAW"`, `"JPG"`, `"PNG"`, `"TIFF"`, `"HEIC"`, `"BMP"`, `"TSQ"`.
- `LibraryField.ORIENTATION`: `"landscape"`, `"portrait"`, `"square"`; computed from width and height.
- `LibraryField.FILE_NAME`: filename keywords, e.g. `["IMG", "DSC"]`.

Image payloads include `id`, `origin_path`, `filename`, `project_id`, `rating`,
`color_label`, `flag`, `edit_status`, `export_status`, `hidden`, `rejected`,
`capture_time`, `format`, `dimensions`, and `orientation`.

`update_labels(image_ids, rating=..., color_label=..., flag=...)` updates
lightweight labels. `color_label` takes a `MetadataColorLabel` member and
`flag` a `MetadataFlag` member; `rating` is `0`-`5`. Out-of-range values raise
`ApiError` (`BAD_REQUEST`) before the request is sent. `Gray` and `Orange` are
not valid color labels and are intentionally absent from `MetadataColorLabel`.

`list_images(sort=...)` supports `LibraryField.CAPTURE_TIME`,
`LibraryField.FILENAME`, `LibraryField.RATING`, and
`LibraryField.COLOR_LABEL`. Pass one sort key per request. Use `sort_desc=True`
for descending order; the default is ascending.

`get_selection()` returns the active UI project selection. The payload includes
`project_id`, `selected_count`, `primary_image_id` when present, and `images`.
Each image item contains `id`, `origin_path`, and `primary`; the primary image
is returned first.

`set_selection(image_ids, primary_image_id=...)` replaces the current UI
selection, clears the previous primary flag, and marks the requested primary
image as `primary`. `add_selection(image_ids)` adds images as normal selected
items only; it does not change the current primary image. `clear_selection()`
clears all non-primary selected images. `clear_selection(image_ids)` clears only
the requested non-primary selected images. The primary image cannot be cleared
with `clear_selection`; use `set_selection` to move the primary flag to another
image.

`list_spaces("all" | "personal" | "team")` returns available personal and team
spaces. `current_space()` returns the active host space. `switch_space(space_id)`
returns `status="pending"` after the host accepts the request; listen to
`library.switchSpace.completed` and `library.switchSpace.failed` for the final
result. Both events include `space_id`.

::: evoto.library.LibraryAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true

## Field Constants

::: evoto.core.api_fields.LibraryField
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.BatchField
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.BatchItemStatus
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true
