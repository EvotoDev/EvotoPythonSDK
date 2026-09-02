# `evoto.metadata`

Use `evoto.metadata` to read and update image metadata through the host. Batch
write-style calls return per-image item statuses so one missing or unsupported
image does not hide the rest of the result.

```python
import evoto
from evoto.core.api_fields import MetadataColorLabel, MetadataField, MetadataFlag

evoto.connect()

image_ids = [101, 202]
items = evoto.metadata.read(image_ids)
for item in items:
    print(item["image_id"], item["filename"], item["absolute_path"])
    print(item["metadata"])

result = evoto.metadata.write(
    image_ids,
    {
        MetadataField.TITLE: "Client selects",
        MetadataField.RATING: 5,
        MetadataField.COLOR_LABEL: MetadataColorLabel.GREEN,
        MetadataField.FLAG: MetadataFlag.PICK,
    },
)
```

To show file read/save progress, subscribe to metadata file events. Use
`completed_count` and `requested_count` to display progress like `2/10`:

```python
for event_name in (
    "metadata.readFromFile.started",
    "metadata.readFromFile.progress",
    "metadata.readFromFile.completed",
    "metadata.readFromFile.failed",
    "metadata.saveToFile.started",
    "metadata.saveToFile.progress",
    "metadata.saveToFile.completed",
    "metadata.saveToFile.failed",
):
    evoto.on(
        event_name,
        lambda data, name=event_name: print(
            name,
            data.get("completed_count"),
            "/",
            data.get("requested_count"),
        ),
    )

result = evoto.metadata.read_from_file(image_ids)
result = evoto.metadata.save_to_file(
    image_ids,
    sidecar=True,
    fields={
        MetadataField.TITLE: "Title for sidecar only",
        MetadataField.COLOR_LABEL: MetadataColorLabel.RED,
    },
)
```

::: evoto.metadata.MetadataAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true

## Field Constants

::: evoto.metadata.MetadataEditableFields
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.MetadataField
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.MetadataColorLabel
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.MetadataFlag
    options:
      heading_level: 3
      show_root_heading: true
      show_root_toc_entry: true

::: evoto.core.api_fields.MetadataSourceValue
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
