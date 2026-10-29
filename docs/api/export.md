# `evoto.export`

## Preset preparation and task acceptance

`start_with_custom()` and `start_with_export_preset()` prepare all regular
effect presets required by the export before the host accepts the task. A
regular preset that is not available locally is downloaded and validated
automatically. Sentinel selections that do not represent a downloadable
effect are passed through unchanged.

For `start_with_export_preset()`, the host derives effect preset IDs from the
saved export configurations. If `preset_suit_ids` is supplied, those override
IDs are prepared instead. For `start_with_custom()`, the supplied
`preset_suit_ids` are prepared directly.

These Python methods wait for preset preparation and task acceptance, so a
call can take longer when downloads are required. After the acceptance
response is returned, the export itself is still asynchronous. Subscribe to
the existing export lifecycle events or call `query()` to track it; no event
names or payloads change.

If a required preset suit ID is unknown, the method raises `ApiError` with
code `404`. If required assets cannot be downloaded or validated, it raises
`ApiError` with code `503`. No export task is accepted in either case. Preset
suit IDs can change when presets are updated. Resolve a current ID with
`evoto.preset.find_by_name()` close to the export request instead of relying
on a long-lived stored ID.

## Cropping transparent margins

Both start methods can trim the fully transparent border around a cut-out
image so that the saved file tightly fits the visible subject. The option is
off by default.

- `start_with_custom()`: pass `ExportOptions().crop_transparent()` in
  `options` (wire key `crop_transparent` inside `options`).
- `start_with_export_preset()`: pass `crop_transparent=True` (top-level wire
  key `crop_transparent`). It applies to every selected export preset.

```python
from evoto.export_options import ExportOptions, FileFormat

opts = (ExportOptions()
    .file_format(FileFormat.PNG)
    .crop_transparent()
    .build())
evoto.export.start_with_custom(project_id, export_dir, suit_ids,
                               imageIds=image_ids, options=opts)

evoto.export.start_with_export_preset(project_id, [png_preset_uuid],
                                      imageIds=image_ids, crop_transparent=True)
```

Behaviour:

- The crop box is the smallest rectangle containing every pixel whose alpha
  is not zero. Semi-transparent pixels count as visible, so faint matting
  noise near the edge can make the box larger.
- Only formats with an alpha channel are cropped: PNG, 8-bit TIFF and 16-bit
  TIFF. When the effective output format is JPEG, the host rejects the
  request with `ApiError` code `400` and no task is accepted. This also
  applies when `start_with_custom()` omits `file_format` and the host's
  current export settings use JPEG, so set the format explicitly. With the
  original format, only sources that keep an alpha channel are cropped.
- Cropping is the last step, after watermarking and scaling. The output can
  be smaller than the configured scale size, and a watermark that overlaps a
  transparent area can be cropped away.
- The image is saved uncropped when it has no alpha channel, when it is fully
  transparent, or when the crop box already covers the whole image.
- Image sizes reported in export events are the pre-crop sizes. Read the
  output file to get the final width and height.
- The option is applied to the export task, so it is kept when the task is
  paused, resumed or retried.

!!! note "Host version"
    `crop_transparent` requires Evoto 8.1.0 or later. Earlier Evoto versions
    ignore the key without an error and export the image uncropped, so check
    the host version before relying on it.

::: evoto.export.ExportAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true
