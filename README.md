# Evoto Python SDK

The Evoto Python SDK helps you build Python plugins that communicate with the
Evoto desktop app. It provides a small, Pythonic API for common plugin tasks
such as reading the current project, importing images, applying presets,
starting exports, and listening for host events.

## Install

Install the SDK package in your plugin environment:

```bash
pip install -e .
```

If your plugin provides its own user interface, install the UI framework you
use separately.

## Quick Start

Create a Python plugin entry file and connect to the running Evoto host:

```python
import evoto


def main() -> None:
    evoto.connect()

    project = evoto.project.current()
    print(f"Current project: {project['name']}")

    evoto.shutdown()


if __name__ == "__main__":
    main()
```

In normal plugin usage, `evoto.connect()` discovers the host automatically.

## Plugin Manifest

Each plugin should include a `plugin.json` manifest next to its entry script.
The manifest identifies the plugin and tells Evoto how to launch it.

```json
{
  "id": "com.example.evoto-plugin",
  "name": "Example Plugin",
  "entry": "main.py"
}
```

## Common Tasks

### Read Project Information

```python
import evoto

evoto.connect()
project = evoto.project.current()
images = evoto.image.list(project_id=project["id"])
evoto.shutdown()
```

### Import Images

```python
import evoto

evoto.connect()
result = evoto.image.import_files(
    ["/path/to/image.jpg"],
    project_id=123,
)
print(result)
evoto.shutdown()
```

### Export Images

```python
import evoto
from evoto.export_options import ExportOptions, FileFormat

evoto.connect()

options = (
    ExportOptions()
    .file_format(FileFormat.JPEG)
    .quality(90)
    .build()
)

task = evoto.export.start_with_custom(
    project_id=123,
    export_dir="/path/to/output",
    imageIds=[456],
    preset_suit_ids=["-1"],
    options=options,
)

final_state = evoto.export.wait_for_completion(task["export_dir_id"])
print(final_state)

evoto.shutdown()
```

## Documentation

This repository includes:

- `docs/` for guides and reference pages
- `docs-data/python_api_reference.json` for structured API reference data
- `demo/` for example plugins

To preview the documentation locally:

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Then open `http://127.0.0.1:8000/`.

To build a static documentation site:

```bash
mkdocs build --clean
```

The generated site is written to `site/`. To preview the built output:

```bash
python -m http.server 8000 -d site
```

Then open `http://127.0.0.1:8000/`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for what changed in each release and the
Evoto version it is built for.

## License

Released under the [MIT License](LICENSE).
