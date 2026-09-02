# Python API Reference

These pages are auto-generated from the docstrings in the `evoto` package source. Each
page documents one cohesive surface of the SDK; pick the area you need
and dive in.

## Module map

| Module | What it covers | Typical entry |
|---|---|---|
| [`evoto.project`](project.md) | Projects and project groups | `evoto.project.create()`, `evoto.project.list()` |
| [`evoto.image`](image.md) | Image import, listing, deletion, lifecycle events | `evoto.image.import_files()`, `evoto.image.on_completed()` |
| [`evoto.preset`](preset.md) | Apply / reset preset suits on images | `evoto.preset.apply_to_image()` |
| [`evoto.export`](export.md) | Run exports, follow lifecycle, retry / pause / resume | `evoto.export.start_with_custom()` |
| [`evoto.export_options`](export-options.md) | Builder + enums for export options | `evoto.ExportOptions(...)` |
| [`evoto.watcher`](watcher.md) | Folder watching and per-project export monitor | `evoto.watcher.start()`, `evoto.watcher.start_export_monitor()` |
| [`evoto.user`](user.md) | Current user / subscription / credits info | `evoto.user.info()` |
| [`evoto.metadata`](metadata.md) | Metadata read/write and file sync helpers | `evoto.metadata.read()`, `evoto.metadata.write()` |
| [`evoto.library`](library.md) | Data-only library queries and lightweight labels | `evoto.library.list_images()`, `evoto.library.update_labels()` |
| [`evoto.culling`](culling.md) | Culling status, results, faces, and clusters | `evoto.culling.status()`, `evoto.culling.list_results()` |
| [`evoto.edit`](edit.md) | Edit summaries and guarded workflows | `evoto.edit.status(project_id)`, `evoto.edit.sync_from()` |
| [`evoto.face`](face.md) | Standalone face detection: box, age, gender, glasses | `evoto.face.wait_for_model()`, `evoto.face.detect()` |
| [`evoto.host`](host.md) | Low-level RPC, host-process discovery, host-process control | `evoto.host.call()`, `evoto.host.discover_host()`, `evoto.host.quit()` |

## Top-level façade

The bare `evoto` module is itself a façade that ties the pieces together.
The most common entry points:

::: evoto
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - connect
        - run
        - disconnect
        - shutdown
        - on_shutdown
        - on
        - off
        - log
        - task
