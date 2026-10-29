# Changelog

All notable changes to the Evoto Python SDK are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Starting with 3.0.1, each release names the Evoto desktop version it is built
for.

## [3.0.1] - 2026-10-29

Evoto version: 8.1.0

### Added

- `crop_transparent` export option, which trims fully transparent margins
  from exported images that have an alpha channel, such as PNG and TIFF.
  Enable it with `ExportOptions.crop_transparent()` for
  `evoto.export.start_with_custom()`, or with `crop_transparent=True` for
  `evoto.export.start_with_export_preset()`. Off by default. Requires Evoto
  8.1.0 or later; earlier versions silently ignore it. With JPEG output the
  host rejects the request with `ApiError` code `400`.

### Fixed

- The export example in `README.md` called `ExportOptions.to_dict()`, which
  does not exist. It now calls `ExportOptions.build()`.

## [3.0.0] - 2026-09-02

First public release.

### Added

- Python APIs for the Evoto plugin host: `evoto.project`, `evoto.image`,
  `evoto.preset`, `evoto.export` with `evoto.export_options`,
  `evoto.watcher`, `evoto.user`, `evoto.metadata`, `evoto.library`,
  `evoto.culling`, `evoto.edit`, `evoto.face` and `evoto.host`.
- Example plugins under `demo/`.
- Guides on the threading model, connection handshake, silent mode, plugin
  manifest, error handling and IPC protocol, plus the generated Python API
  reference.
