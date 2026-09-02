"""Hand-written code examples for individual API methods.

Looked up by ``(module_key, method_name)`` from the facade.
Each value is rendered as the Detail page's ``Example`` block.

These examples were preserved from the original hand-curated
``api_reference_data.py``. To add or update an example:
  1. Add a new ``(module_key, method_name): "<code>"`` entry.
  2. The viewer picks it up at next start.
"""

from __future__ import annotations

EXAMPLES: dict[tuple[str, str], str] = {
    ('CullingAPI', 'list_clusters'): (
        'clusters = evoto.culling.list_clusters(\n'
        '    use_current_project=True,\n'
        '    image_ids=[101, 202],\n'
        '    cluster_type="similar",\n'
        ')\n'
        "print('clusters:', len(clusters), clusters[0].get('image_ids') if clusters else [])"
    ),
    ('CullingAPI', 'list_faces'): (
        'from evoto.core.api_fields import CullingField\n'
        '\n'
        'faces = evoto.culling.list_faces(\n'
        '    use_current_project=True,\n'
        '    image_ids=[101, 202],\n'
        ')\n'
        "print('faces:', len(faces), faces[0].get(CullingField.FACE_ID) if faces else None)"
    ),
    ('CullingAPI', 'list_results'): (
        'from evoto.core.api_fields import CullingField\n'
        '\n'
        'results = evoto.culling.list_results(\n'
        '    use_current_project=True,\n'
        '    image_ids=[101, 202],\n'
        '    filters={CullingField.AI_SELECTED: True},\n'
        ')\n'
        "print('selected:', len(results))"
    ),
    ('CullingAPI', 'restart'): (
        'result = evoto.culling.restart(\n'
        '    use_current_project=True,\n'
        ')\n'
        "print(result.get('status'), result.get('reason'))"
    ),
    ('CullingAPI', 'start'): (
        'result = evoto.culling.start(\n'
        '    use_current_project=True,\n'
        ')\n'
        "print(result.get('status'), result.get('reason'))"
    ),
    ('CullingAPI', 'status'): (
        'status = evoto.culling.status(\n'
        '    use_current_project=True,\n'
        ')\n'
        "print(status.get('status'))"
    ),
    ('EditAPI', 'create_virtual_copy'): (
        'result = evoto.edit.create_virtual_copy(101)\n'
        "print(result.get('status'), result.get('reason'))"
    ),
    ('EditAPI', 'reset'): (
        'from evoto.core.api_fields import EditModuleValue\n'
        '\n'
        'result = evoto.edit.reset(\n'
        '    [101, 202],\n'
        '    modules=[EditModuleValue.BACKGROUND],\n'
        ')\n'
        "print(result.get('status'), result.get('accepted_count'), result.get('skipped_count'))"
    ),
    ('EditAPI', 'status'): (
        'summaries = evoto.edit.status(12345, image_ids=[101, 202])\n'
        'for item in summaries:\n'
        "    print(item['image_id'], item.get('has_edit'), item.get('has_color'), item.get('has_crop'))"
    ),
    ('EditAPI', 'sync_from'): (
        'from evoto.core.api_fields import EditModuleValue\n'
        '\n'
        'result = evoto.edit.sync_from(\n'
        '    101,\n'
        '    [202, 303],\n'
        '    modules=[EditModuleValue.COLOR, EditModuleValue.PORTRAIT],\n'
        ')\n'
        "print(result.get('status'), result.get('reason'), result.get('skipped_count'))"
    ),
    ('ExportAPI', 'delete'): (
        'evoto.export.delete(42)'
    ),
    ('ExportAPI', 'list_export_presets'): (
        'presets = evoto.export.list_export_presets()\n'
        'for p in presets:\n'
        "    print(p['name'], p['uuid'])"
    ),
    ('ExportAPI', 'off_completed'): (
        'evoto.export.off_completed()'
    ),
    ('ExportAPI', 'off_failed'): (
        'evoto.export.off_failed()'
    ),
    ('ExportAPI', 'off_item_finished'): (
        'evoto.export.off_item_finished()'
    ),
    ('ExportAPI', 'off_progress'): (
        'evoto.export.off_progress()'
    ),
    ('ExportAPI', 'off_started'): (
        'evoto.export.off_started()'
    ),
    ('ExportAPI', 'on_completed'): (
        "evoto.export.on_completed(lambda d: print('All done!'))"
    ),
    ('ExportAPI', 'on_failed'): (
        'def on_failed(data):\n'
        "    print('Export failed:', data.get('message'))\n"
        '\n'
        'evoto.export.on_failed(on_failed)'
    ),
    ('ExportAPI', 'on_item_finished'): (
        'def on_item(data):\n'
        "    print('Item done:', data.get('output_path'))\n"
        '\n'
        'evoto.export.on_item_finished(on_item)'
    ),
    ('ExportAPI', 'on_progress'): (
        'def on_progress(data):\n'
        '    print(f"Progress: {data[\'progress\']}%")\n'
        '\n'
        'evoto.export.on_progress(on_progress)'
    ),
    ('ExportAPI', 'on_started'): (
        'def on_started(data):\n'
        "    print('Export started:', data)\n"
        '\n'
        'evoto.export.on_started(on_started)'
    ),
    ('ExportAPI', 'pause'): (
        'evoto.export.pause(42)'
    ),
    ('ExportAPI', 'query'): (
        'status = evoto.export.query(export_dir_id=42)'
    ),
    ('ExportAPI', 'resume'): (
        'evoto.export.resume(42)'
    ),
    ('ExportAPI', 'retry'): (
        'evoto.export.retry(42)'
    ),
    ('ExportAPI', 'start_with_custom'): (
        'from evoto.export_options import ExportOptions, FileFormat\n'
        '\n'
        'matches = evoto.preset.find_by_name("Soft Light")\n'
        'suit_id = next(\n'
        '    item["id"] for item in matches\n'
        '    if item["className"] == "Portrait"\n'
        ')\n'
        '\n'
        'opts = (ExportOptions()\n'
        '    .file_format(FileFormat.JPEG)\n'
        '    .quality(90)\n'
        '    .build())\n'
        '\n'
        'result = evoto.export.start_with_custom(\n'
        '    project_id=12345,\n'
        '    export_dir="/output",\n'
        '    preset_suit_ids=[suit_id],\n'
        '    imageIds=[101, 202],\n'
        '    options=opts,\n'
        ')\n'
        'print("Export accepted:", result)'
    ),
    ('ExportAPI', 'start_with_export_preset'): (
        'result = evoto.export.start_with_export_preset(\n'
        '    project_id=12345,\n'
        '    export_preset_ids=["preset_uuid_1"],\n'
        '    imageIds=[101, 202],\n'
        ')\n'
        'print("Export accepted:", result)'
    ),
    ('ExportAPI', 'subscribe'): (
        'evoto.export.subscribe()'
    ),
    ('ExportAPI', 'unsubscribe'): (
        'evoto.export.unsubscribe()'
    ),
    ('ExportAPI', 'wait_for_completion'): (
        'result = evoto.export.wait_for_completion(\n'
        '    export_dir_id=42,\n'
        "    on_progress=lambda p: print(f'{p:.0f}%'),\n"
        '    timeout=300,\n'
        ')'
    ),
    ('ExportOptions', 'build'): (
        'opts = (ExportOptions()\n'
        '    .file_format(FileFormat.JPEG)\n'
        '    .quality(90)\n'
        '    .scale_long_edge(3000)\n'
        '    .dpi(300)\n'
        '    .sharpen(SharpenType.SCREEN, SharpenAmount.STANDARD)\n'
        '    .naming(NamingFormat.ORIGINAL_CUSTOM, suffix="_edited")\n'
        '    .exist_format(ExistFormat.ADD_SUFFIX)\n'
        '    .build())'
    ),
    ('ExportOptions', 'create_subdir'): (
        '.create_subdir("batch_01")'
    ),
    ('ExportOptions', 'dpi'): (
        '.dpi(300)'
    ),
    ('ExportOptions', 'dpi_unit'): (
        '.dpi(300).dpi_unit(DpiUnit.CM)'
    ),
    ('ExportOptions', 'exist_format'): (
        '.exist_format(ExistFormat.ADD_SUFFIX)'
    ),
    ('ExportOptions', 'file_format'): (
        '.file_format(FileFormat.JPEG)'
    ),
    ('ExportOptions', 'limit_size'): (
        '.limit_size(5.0)'
    ),
    ('ExportOptions', 'naming'): (
        '.naming(NamingFormat.ORIGINAL_CUSTOM, suffix="_edited")'
    ),
    ('ExportOptions', 'quality'): (
        '.quality(90)'
    ),
    ('ExportOptions', 'scale_long_edge'): (
        '.scale_long_edge(3000)'
    ),
    ('ExportOptions', 'scale_percent'): (
        '.scale_percent(0.5)'
    ),
    ('ExportOptions', 'scale_short_edge'): (
        '.scale_short_edge(1080)'
    ),
    ('ExportOptions', 'scale_unit'): (
        '.scale_unit(ScaleUnit.INCH).scale_long_edge(10)'
    ),
    ('ExportOptions', 'scale_width_height'): (
        '.scale_width_height(1920, 1080)'
    ),
    ('ExportOptions', 'sharpen'): (
        '.sharpen(SharpenType.SCREEN, SharpenAmount.STANDARD)'
    ),
    ('ExportOptions', 'watermark'): (
        '.watermark("/logo.png", position=WatermarkPosition.BOTTOM_RIGHT)'
    ),
    ('ImageAPI', 'delete'): (
        'from evoto.core.api_fields import ImageField, DeleteMode\n'
        'result = evoto.image.delete([101, 102], delete_mode=DeleteMode.RECYCLE)\n'
        'if result[ImageField.ACCEPTED]:\n'
        "    print('delete task accepted')"
    ),
    ('ImageAPI', 'import_files'): (
        'result = evoto.image.import_files(\n'
        '    ["/photos/batch_01"],\n'
        '    use_current_project=True,\n'
        ')\n'
        'print(result)'
    ),
    ('ImageAPI', 'import_files_async'): (
        'ack = evoto.image.import_files_async(\n'
        '    ["/photos/batch_01"],\n'
        '    project_name="Auto Import",\n'
        '    allow_cross_cloud_sync=True,\n'
        ')\n'
        "print('Import ID:', ack['import_id'])"
    ),
    ('ImageAPI', 'info'): (
        'from evoto.core.api_fields import ImageMetadataGroup\n'
        'info = evoto.image.info(101)\n'
        'exposure = info.metadata.get(ImageMetadataGroup.EXIF_EXPOSURE, {})\n'
        "iso = exposure.get('isoSpeedRatings')\n"
        "shutter = exposure.get('shutterSpeedValue')"
    ),
    ('ImageAPI', 'list'): (
        'images = evoto.image.list(use_current_project=True)\n'
        'for img in images:\n'
        "    print(img['id'], img['filename'])"
    ),
    ('ImageAPI', 'off_completed'): (
        'evoto.image.off_completed()'
    ),
    ('ImageAPI', 'off_failed'): (
        'evoto.image.off_failed()'
    ),
    ('ImageAPI', 'off_progress'): (
        'evoto.image.off_progress()'
    ),
    ('ImageAPI', 'off_started'): (
        'evoto.image.off_started()'
    ),
    ('ImageAPI', 'on_completed'): (
        'def on_completed(data):\n'
        "    print('Import completed:', data)\n"
        '\n'
        'evoto.image.on_completed(on_completed)'
    ),
    ('ImageAPI', 'on_failed'): (
        'def on_failed(data):\n'
        "    print('Import failed:', data.get('message'))\n"
        '\n'
        'evoto.image.on_failed(on_failed)'
    ),
    ('ImageAPI', 'on_progress'): (
        'def on_progress(data):\n'
        "    print('Import progress:', data.get('progress', 0))\n"
        '\n'
        'evoto.image.on_progress(on_progress)'
    ),
    ('ImageAPI', 'on_started'): (
        'def on_started(data):\n'
        "    print('Import started:', data)\n"
        '\n'
        'evoto.image.on_started(on_started)'
    ),
    ('ImageAPI', 'subscribe'): (
        "evoto.image.subscribe(import_listener_uuid='listener-001')"
    ),
    ('ImageAPI', 'unsubscribe'): (
        'evoto.image.unsubscribe()'
    ),
    ('LibraryAPI', 'add_selection'): (
        'result = evoto.library.add_selection([101, 202])\n'
        "print(result.get('status'), result.get('reason'))"
    ),
    ('LibraryAPI', 'clear_selection'): (
        'result = evoto.library.clear_selection([202])\n'
        '# Omit image_ids to clear all non-primary selected images.\n'
        'result = evoto.library.clear_selection()\n'
        "print(result.get('status'), result.get('reason'))"
    ),
    ('LibraryAPI', 'get_selection'): (
        'selection = evoto.library.get_selection()\n'
        "print(selection.get('project_id'), selection.get('selected_count'), selection.get('primary_image_id'))\n"
        "print(selection.get('images', []))"
    ),
    ('LibraryAPI', 'list_images'): (
        'from evoto.core.api_fields import LibraryField, MetadataFlag\n'
        '\n'
        'images = evoto.library.list_images(\n'
        '    project_id=123,\n'
        '    filters={\n'
        '        LibraryField.RATING: [2, 3],\n'
        '        LibraryField.FLAG: [MetadataFlag.PICK, MetadataFlag.REJECT],\n'
        '        LibraryField.EXPORT_STATUS: ["unexported", "failed"],\n'
        '        LibraryField.FORMAT: ["RAW", "JPG"],\n'
        '        LibraryField.ORIENTATION: ["landscape", "portrait"],\n'
        '        LibraryField.FILE_NAME: ["IMG", "DSC"],\n'
        '    },\n'
        '    sort=LibraryField.CAPTURE_TIME,\n'
        '    sort_desc=True,\n'
        ')\n'
        'for img in images[:10]:\n'
        "    print(img['id'], img.get('filename'))"
    ),
    ('LibraryAPI', 'list_spaces'): (
        'spaces = evoto.library.list_spaces()\n'
        'for space in spaces:\n'
        "    print(space['space_id'], space['name'], space['type'])"
    ),
    ('LibraryAPI', 'current_space'): (
        'space = evoto.library.current_space()\n'
        "print(space.get('space_id'), space.get('name'), space.get('type'))"
    ),
    ('LibraryAPI', 'set_selection'): (
        'result = evoto.library.set_selection(\n'
        '    [101, 202],\n'
        '    primary_image_id=101,\n'
        ')\n'
        "print(result.get('status'), result.get('reason'))"
    ),
    ('LibraryAPI', 'update_labels'): (
        'from evoto.core.api_fields import MetadataColorLabel\n'
        '\n'
        'evoto.library.update_labels(\n'
        '    [101, 202],\n'
        '    rating=5,\n'
        '    color_label=MetadataColorLabel.GREEN,\n'
        ')'
    ),
    ('LibraryAPI', 'switch_space'): (
        'result = evoto.library.switch_space(123)\n'
        "print(result.get('success'), result.get('space', {}).get('name'))"
    ),
    ('MetadataAPI', 'read'): (
        'items = evoto.metadata.read([101, 202])\n'
        'for item in items:\n'
        '    print(item["image_id"], item["filename"], item["absolute_path"])\n'
        '    print(item["metadata"].keys())'
    ),
    ('MetadataAPI', 'read_from_file'): (
        'result = evoto.metadata.read_from_file([101, 202])\n'
        "print(result.get('success_count'), result.get('failed_count'))"
    ),
    ('MetadataAPI', 'save_to_file'): (
        'from evoto.core.api_fields import MetadataField\n'
        '\n'
        'result = evoto.metadata.save_to_file(\n'
        '    [101, 202],\n'
        '    sidecar=True,\n'
        '    fields={MetadataField.TITLE: "Title for sidecar only"},\n'
        ')\n'
        "print(result.get('success_count'), result.get('failed_count'))"
    ),
    ('MetadataAPI', 'write'): (
        'from evoto.core.api_fields import MetadataField\n'
        '\n'
        'result = evoto.metadata.write(\n'
        '    [101, 202],\n'
        '    {\n'
        '        MetadataField.TITLE: "Client selects",\n'
        '        MetadataField.RATING: 5,\n'
        '    },\n'
        ')\n'
        "print(result.get('success_count'), result.get('failed_count'))"
    ),
    ('PresetAPI', 'apply_to_image'): (
        'matches = evoto.preset.find_by_name("Soft Light")\n'
        'suit_id = next(\n'
        '    item["id"] for item in matches\n'
        '    if item["className"] == "Portrait"\n'
        ')\n'
        '\n'
        '# Prepare this ID with ensure_ready_async() and wait for success\n'
        '# before using the synchronous apply method.\n'
        'evoto.preset.apply_to_image(\n'
        '    suit_id,\n'
        '    imageIds=[101, 202],\n'
        ')'
    ),
    ('PresetAPI', 'apply_to_image_async'): (
        'matches = evoto.preset.find_by_name("Soft Light")\n'
        'suit_id = next(\n'
        '    item["id"] for item in matches\n'
        '    if item["className"] == "Portrait"\n'
        ')\n'
        '\n'
        'def on_applied(result, status):\n'
        '    if not status.is_success:\n'
        '        print(status.error_code, status.error_message)\n'
        '        return\n'
        '    print(result["appliedCount"], result["downloaded"])\n'
        '\n'
        'request_id = evoto.preset.apply_to_image_async(\n'
        '    suit_id,\n'
        '    imageIds=[101, 202],\n'
        '    callback=on_applied,\n'
        ')'
    ),
    ('PresetAPI', 'ensure_ready_async'): (
        'matches = evoto.preset.find_by_name("Soft Light")\n'
        'suit_id = next(\n'
        '    item["id"] for item in matches\n'
        '    if item["className"] == "Portrait"\n'
        ')\n'
        '\n'
        'def on_ready(result, status):\n'
        '    if not status.is_success:\n'
        '        print(status.error_code, status.error_message)\n'
        '        return\n'
        '    print(result["readySuitIds"], result["downloaded"])\n'
        '\n'
        'request_id = evoto.preset.ensure_ready_async(\n'
        '    [suit_id],\n'
        '    callback=on_ready,\n'
        ')'
    ),
    ('PresetAPI', 'find_by_name'): (
        'matches = evoto.preset.find_by_name("Soft Light")\n'
        'for m in matches:\n'
        "    print(m['className'], m['classType'], m['id'])\n"
        '\n'
        '# Names repeat across classes, so select the intended current ID.\n'
        'suit_id = next(\n'
        '    item["id"] for item in matches\n'
        '    if item["className"] == "Portrait"\n'
        ')'
    ),
    ('PresetAPI', 'list'): (
        'categories = evoto.preset.list()\n'
        'for cat in categories:\n'
        "    print(cat['name'], len(cat['presets']), 'presets')"
    ),
    ('PresetAPI', 'reset'): (
        'evoto.preset.reset(imageIds=[101, 202])'
    ),
    ('ProjectAPI', 'create'): (
        'import evoto\n'
        '\n'
        'evoto.connect()\n'
        '\n'
        'result = evoto.project.create(\n'
        '    "My Portrait Project",\n'
        '    use_current_group=True,\n'
        '    allow_cross_cloud_sync=True,\n'
        ')\n'
        'print(result)'
    ),
    ('ProjectAPI', 'current'): (
        'try:\n'
        '    proj = evoto.project.current()\n'
        "    print('Active project:', proj['name'])\n"
        'except ApiError as e:\n'
        '    if e.code == 404:\n'
        "        print('No project is open')"
    ),
    ('ProjectAPI', 'convert_to_cloud'): (
        "evoto.project.on_convert_to_cloud_completed(lambda d: print('converted:', d))\n"
        "evoto.project.on_convert_to_cloud_failed(lambda d: print('failed:', d.get('message')))\n"
        "evoto.project.on_cloud_upload_completed(lambda d: print('all uploaded:', d.get('project_id')))\n"
        "evoto.project.on_cloud_upload_failed(lambda d: print('upload failed:', d.get('message')))\n"
        "evoto.project.on_cloud_download_failed(lambda d: print('download failed:', d.get('message')))\n"
        '\n'
        'result = evoto.project.convert_to_cloud(12345)\n'
        "print('accepted:', result.get('accepted'))"
    ),
    ('ProjectAPI', 'cloud_status'): (
        'status = evoto.project.cloud_status(12345)\n'
        "print(status.get('status'), status.get('upload_progress'), status.get('download_progress'))"
    ),
    ('ProjectAPI', 'stop_cloud_loading'): (
        'result = evoto.project.stop_cloud_loading(12345)\n'
        "print('stopped:', result.get('stopped'))"
    ),
    ('ProjectAPI', 'delete'): (
        'evoto.project.delete(use_current_project=True)'
    ),
    ('ProjectAPI', 'group_create'): (
        'group = evoto.project.group_create("Retouching Queue")'
    ),
    ('ProjectAPI', 'group_delete'): (
        'evoto.project.group_delete(use_current_group=True)'
    ),
    ('ProjectAPI', 'group_get'): (
        'group = evoto.project.group_get(use_current_group=True)'
    ),
    ('ProjectAPI', 'group_list'): (
        'groups = evoto.project.group_list()\n'
        'for group in groups:\n'
        "    print(group['id'], group['name'])"
    ),
    ('ProjectAPI', 'group_rename'): (
        'evoto.project.group_rename(None, "Client Delivery", use_current_group=True)'
    ),
    ('ProjectAPI', 'info'): (
        'proj = evoto.project.info(use_current_project=True)'
    ),
    ('ProjectAPI', 'list'): (
        'projects = evoto.project.list(use_current_group=True)\n'
        'for p in projects:\n'
        "    print(p['name'])"
    ),
    ('ProjectAPI', 'rename'): (
        'evoto.project.rename(None, "New Name", use_current_project=True)'
    ),
    ('ProjectAPI', 'switch'): (
        "evoto.project.on_switch_completed(lambda d: print('switched:', d))\n"
        "evoto.project.on_switch_failed(lambda d: print('failed:', d.get('message')))\n"
        '\n'
        'result = evoto.project.switch(12345)\n'
        "print(result.get('status'))"
    ),
    ('UserAPI', 'UserInfo (dataclass)'): (
        'from evoto import UserInfo\n'
        '\n'
        'def is_running_low(me: UserInfo, threshold: float = 50) -> bool:\n'
        '    return me.credits_remaining < threshold\n'
        '\n'
        'me = evoto.user.info()\n'
        'if is_running_low(me):\n'
        "    evoto.log('Credits running low!', level='warning')"
    ),
    ('UserAPI', 'info'): (
        'import evoto\n'
        '\n'
        'evoto.connect()\n'
        'me = evoto.user.info()\n'
        'print(me.display_name, me.email)\n'
        'print(f"credits: {me.credits_remaining}/{me.credits_total}")\n'
        'if me.has_cloud_space:\n'
        '    print(f"cloud: {me.cloud_used_space} / {me.cloud_total_space}")\n'
        'if me.is_subscribed:\n'
        "    print('next bill:', me.next_bill_date)"
    ),
    ('WatcherAPI', 'list'): (
        'watchers = evoto.watcher.list()'
    ),
    ('WatcherAPI', 'list_unexported'): (
        'images = evoto.watcher.list_unexported(12345)\n'
        'for img in images:\n'
        "    print(img['filename'])"
    ),
    ('WatcherAPI', 'mark_exported'): (
        'evoto.watcher.mark_exported(image_ids=[101, 202])'
    ),
    ('WatcherAPI', 'off_files_added'): (
        'evoto.watcher.off_files_added()'
    ),
    ('WatcherAPI', 'off_unexported_found'): (
        'evoto.watcher.off_unexported_found()'
    ),
    ('WatcherAPI', 'on_files_added'): (
        'def on_new(data):\n'
        "    for f in data['files']:\n"
        "        print('New file:', f)\n"
        '\n'
        'evoto.watcher.on_files_added(on_new)'
    ),
    ('WatcherAPI', 'on_unexported_found'): (
        'def on_unexported(data):\n'
        '    print(f"{data[\'total\']} unexported images")\n'
        '\n'
        'evoto.watcher.on_unexported_found(on_unexported)'
    ),
    ('WatcherAPI', 'query_export_monitor'): (
        'config = evoto.watcher.query_export_monitor()'
    ),
    ('WatcherAPI', 'start'): (
        'from evoto.watcher import WatchFilterType\n'
        'result = evoto.watcher.start(\n'
        '    ["/watch/incoming"],\n'
        '    filters=[WatchFilterType.JPG, WatchFilterType.RAW],\n'
        '    include_sub_dir=True,\n'
        ')'
    ),
    ('WatcherAPI', 'start_export_monitor'): (
        'evoto.watcher.start_export_monitor(12345, interval=60)'
    ),
    ('WatcherAPI', 'stop'): (
        'evoto.watcher.stop()'
    ),
    ('WatcherAPI', 'stop_export_monitor'): (
        'evoto.watcher.stop_export_monitor()'
    ),
    ('evoto', 'connect'): (
        'import evoto\n'
        '\n'
        'evoto.connect()\n'
        "print('Connected:', evoto.host.is_connected)"
    ),
    ('evoto', 'disconnect'): (
        'evoto.disconnect()'
    ),
    ('evoto', 'log'): (
        "evoto.log('Processing started', level='info')"
    ),
    ('evoto', 'off'): (
        "evoto.off('export.completed', on_export_done)"
    ),
    ('evoto', 'on'): (
        'def on_export_done(data):\n'
        "    print('Export completed:', data)\n"
        '\n'
        "evoto.on('export.completed', on_export_done)"
    ),
    ('evoto', 'on_shutdown'): (
        'def cleanup():\n'
        "    print('Shutting down...')\n"
        '\n'
        'evoto.on_shutdown(cleanup)'
    ),
    ('evoto', 'project / image / preset / export / watcher / user'): (
        'proj = evoto.project.current()\n'
        'images = evoto.image.list(use_current_project=True)\n'
        "evoto.preset.apply_to_image('suit-1', imageIds=[img.id for img in images])\n"
        'me = evoto.user.info()\n'
        'print(me.display_name, me.credits_remaining)'
    ),
    ('evoto', 'run'): (
        'import evoto\n'
        '\n'
        '@evoto.task\n'
        'def hello(name: str) -> str:\n'
        '    return f"Hello, {name}!"\n'
        '\n'
        'evoto.run()'
    ),
    ('evoto', 'shutdown'): (
        'evoto.shutdown()'
    ),
    ('evoto', 'task (decorator)'): (
        '@evoto.task\n'
        'def my_task(x: int, y: int) -> dict:\n'
        '    return {"sum": x + y}\n'
        '\n'
        '@evoto.task(name="custom.name")\n'
        'def another_task(data: str) -> str:\n'
        '    return data.upper()'
    ),
    ('host', 'call'): (
        "result = evoto.host.call('image.list', {'project_id': 42})"
    ),
    ('host', 'call_async'): (
        'def done(result, status):\n'
        "    print('async result:', result)\n"
        '\n'
        "req_id = evoto.host.call_async('image.list', {}, done)"
    ),
    ('host', 'cancel_request'): (
        'evoto.host.cancel_request(req_id)'
    ),
    ('host', 'configure_silent_timeout'): (
        'import evoto\n'
        '\n'
        '# Requires a background host: Evoto -silent\n'
        'evoto.connect()\n'
        '\n'
        '# Keep the silent host alive indefinitely\n'
        'evoto.host.configure_silent_timeout(timeout_seconds=0)\n'
        '\n'
        '# Show the UI instead of quitting when nobody attaches\n'
        '# within 10 minutes (default action is quit)\n'
        "evoto.host.configure_silent_timeout(600, 'show')"
    ),
    ('host', 'discover_host'): (
        'path = evoto.host.discover_host()'
    ),
    ('host', 'is_available'): (
        'print(evoto.host.is_available())'
    ),
    ('host', 'is_connected (property)'): (
        'if evoto.host.is_connected:\n'
        "    print('Ready')"
    ),
    ('host', 'quit'): (
        'import evoto\n'
        '\n'
        'evoto.connect()\n'
        'evoto.host.quit()              # clean shutdown\n'
        'evoto.host.quit(relaunch=True) # restart after quitting'
    ),
    ('host', 'reconnect'): (
        'evoto.host.reconnect()'
    ),
    ('host', 'wait_for_host'): (
        'if evoto.host.wait_for_host(timeout=60):\n'
        '    evoto.connect()'
    ),
}
