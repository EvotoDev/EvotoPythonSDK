# `evoto.edit`

Use `evoto.edit` to inspect image edit summaries, sync effects, and reset effects.
Mutating workflows are executed through host UI
workflows when safe; unsupported workflows return an explicit skipped payload
instead of performing partial database-only changes.

```python
import evoto
from evoto.core.api_fields import EditModuleValue

evoto.connect()

status = evoto.edit.status(12345, image_ids=[101, 202])
project_status = evoto.edit.status(12345)

sync_result = evoto.edit.sync_from(
    101,
    [202, 303],
    modules=[EditModuleValue.COLOR, EditModuleValue.PORTRAIT],
)
reset_result = evoto.edit.reset(
    [202, 303],
    modules=[EditModuleValue.BACKGROUND],
)
copy_result = evoto.edit.create_virtual_copy(101)
```

`status(project_id, image_ids=None)` returns edit summaries for testing whether
images have edits, module-level effects, crop, and preset/look state.
Pass image IDs to inspect a subset; omit `image_ids` to inspect all non-recycled
images in the project. The host runs this query in a background task because it
may read local edit configuration files; if another status query is still
running, the host rejects the new request with a conflict error.

`sync_from` uses the host's existing effect sync workflow and returns an
accepted payload with batch counts and per-image items after the request is
queued. When `modules` is provided, the host maps those module names to
syncable edit settings and overrides saved/default sync settings; when omitted,
it uses saved or default sync settings.

`reset` applies the host default parameters for the requested modules and
leaves other edit modules unchanged. Omitting `modules` resets all effects.

`create_virtual_copy` queues the host's existing virtual-copy workflow for one
current-project image. The copy uses the product default name such as
`Copy 1`; the SDK does not accept or send a copy name.

This module covers:

- Read whether an image has edits.
- Read module-level effect booleans such as `has_color`, `has_crop`, and
  `has_portrait`.
- Sync all or selected modules from one source image to target images.
- Reset selected modules for a batch of images.
- Create a virtual copy through the product workflow.
- Return clear skipped reasons for source-without-module and restricted
  scenarios such as multi-person, collection, or virtual-copy limitations.

::: evoto.edit.EditAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true

## Field Constants

::: evoto.core.api_fields.EditField
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.EditModuleValue
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true
