# `evoto.preset`

## Preset ID lifecycle

Preset suit IDs can change when a preset is updated. Treat a stored `suit_id`
as refreshable rather than permanent. Before calling either
`apply_to_image_async()` or `apply_to_image()`, resolve the current ID with
`find_by_name()` close to the time of application:

```python
matches = evoto.preset.find_by_name("Soft Light")

# Preset names are not unique across classes. Select the intended class when
# find_by_name() returns more than one match.
match = next(item for item in matches if item["className"] == "Portrait")
suit_id = match["id"]
```

`apply_to_image_async()` validates the resolved ID and downloads missing
preset details automatically before applying. The synchronous
`apply_to_image()` method does not perform that preparation. Before using the
synchronous method, call `ensure_ready_async([suit_id], callback)` and wait for
its callback to report `status.is_success=True`.

Successful async replies are normally delivered on the SDK receiver thread.
Do not call the blocking `apply_to_image()` method directly inside the
`ensure_ready_async()` callback. Return control to the application thread or
dispatch the synchronous call to a separate worker thread first.

Use `preset.apply_to_image_async(suit_id, imageIds, callback, timeout=120.0)`
when a preset may not be downloaded yet. The call returns a request ID
immediately. The host validates the current suit ID, downloads missing preset
details, verifies local files, and applies the preset before invoking the
callback.

The method return value and callback values have separate meanings:

- The method immediately returns a string `request_id`. The callback's
  `status.request_id` contains the same value.
- On success, `result` is a dict. `result["success"]` is `True`,
  `result["appliedCount"]` is the number of images actually updated and may be
  `0` when none of the supplied image IDs resolve to an applicable image, and
  `result["downloaded"]` reports whether this request downloaded missing
  preset details. `downloaded=False` means the preset was already ready
  locally; it does not indicate failure.
- On success, `status.is_success` is `True`, `status.is_timeout` is `False`,
  `status.error_code` is `0`, and `status.error_message` is empty.

Images in the current project trigger an automatic gallery refresh; images
outside the current project are updated without refreshing the current
gallery.

Missing suit IDs and download failures arrive as normal RPC errors. An unknown
or stale `suit_id` returns error code `404`. For a host error, `result` is
`None`, `status.is_success` and `status.is_timeout` are `False`, and
`status.error_code` / `status.error_message` describe the error. For a timeout,
`result` is `None`, `status.is_success` is `False`, and `status.is_timeout` is
`True`. In every callback, `status.elapsed_ms` is the elapsed time until the
reply or timeout.

Do not assume that callbacks run on a fixed thread. Successful host replies
and host errors usually invoke the callback on the SDK receiver thread, while
timeouts use the SDK timer thread. A local send failure invokes the callback
immediately on the thread calling `apply_to_image_async()`, potentially before
the method returns. Marshal to the appropriate application thread before
touching thread-affine state such as GUI objects.

If `evoto.host.cancel_request(request_id)` returns `True`, the callback runs
locally with `result=None`, `status.is_success=False`,
`status.is_timeout=False`, and cancellation described by
`status.error_message`. The callback runs synchronously on the thread calling
`cancel_request()`. A later host reply is ignored. Cancellation does not stop
an in-progress host download or host-side application.

```python
import evoto


def on_preset_applied(result, status):
    if not status.is_success:
        print(f"Preset application failed: {status.error_message}")
        return
    print(
        f"Applied to {result['appliedCount']} images; "
        f"downloaded={result['downloaded']}"
    )


matches = evoto.preset.find_by_name("Soft Light")
suit_id = next(
    item["id"] for item in matches if item["className"] == "Portrait"
)

request_id = evoto.preset.apply_to_image_async(
    suit_id,
    imageIds=[101, 102],
    callback=on_preset_applied,
)
```

Use `preset.ensure_ready_async(suit_ids, callback, timeout=120.0)` before a
workflow depends on preset assets that may still need downloading on the host.
Resolve current suit IDs with `find_by_name()` first; do not pass beautify or
palette preset IDs.

The method immediately returns a string `request_id`; the callback's
`status.request_id` contains the same value. On success, `result` is a dict:
`result["success"]` is `True`, `result["readySuitIds"]` lists every requested
suit ID confirmed ready after validation and any required download, and
`result["downloaded"]` reports whether this request downloaded missing preset
details. `downloaded=False` means every requested suit was already ready
locally; it does not indicate failure. `status.is_success` is `True`,
`status.is_timeout` is `False`, `status.error_code` is `0`, and
`status.error_message` is empty.

For a host error, `result` is `None`, `status.is_success` and
`status.is_timeout` are `False`, and `status.error_code` /
`status.error_message` describe the error. For a timeout, `result` is `None`,
`status.is_success` is `False`, and `status.is_timeout` is `True`. In every
callback, `status.elapsed_ms` is the elapsed time until the reply or timeout.
Unknown or stale suit IDs are reported as host errors with error code `404`.

Do not assume that callbacks run on a fixed thread. Successful host replies
and host errors usually invoke the callback on the SDK receiver thread, while
timeouts use the SDK timer thread. A local send failure invokes the callback
immediately on the thread calling `ensure_ready_async()`, potentially before
the method returns. Marshal to the appropriate application thread before
touching thread-affine state such as GUI objects.

If `evoto.host.cancel_request(request_id)` returns `True`, the callback runs
locally with `result=None`, `status.is_success=False`,
`status.is_timeout=False`, and cancellation described by
`status.error_message`. The callback runs synchronously on the thread calling
`cancel_request()`. A later host reply is ignored. Cancellation does not stop
an in-progress host download or host-side preset preparation.

```python
import evoto


def on_presets_ready(result, status):
    if not status.is_success:
        print(f"Preset preparation failed: {status.error_message}")
        return
    print(f"Ready preset suits: {result['readySuitIds']}")


matches = evoto.preset.find_by_name("Soft Light")
suit_id = next(
    item["id"] for item in matches if item["className"] == "Portrait"
)

request_id = evoto.preset.ensure_ready_async(
    [suit_id],
    on_presets_ready,
)
```

::: evoto.preset.PresetAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true
