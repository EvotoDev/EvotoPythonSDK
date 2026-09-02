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

::: evoto.export.ExportAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true
