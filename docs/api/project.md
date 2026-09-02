# `evoto.project`

Use `project.switch(project_id)` to ask the host UI to open a project in the
Library. The host rejects the request if a modal dialog or popup is open. The
call returns `status="pending"` after the host accepts the request; listen to
`project.switch.completed` and `project.switch.failed` for the final result.
Both events include `project_id`.

Use `project.convert_to_cloud(project_id)` to convert a local project into a
cloud-synced project. `project_id` is required; the host does not default to
the current project. The call returns when the host accepts the request;
listen to `project.convertToCloud.completed` and
`project.convertToCloud.failed` for the conversion result. After conversion,
listen to `project.cloudUpload.progress`, `project.cloudUpload.completed` and
`project.cloudUpload.failed` to track image upload progress and failures. Single
image upload failures are reported through `project.cloudImageUpload.failed`.

Use `project.stop_cloud_loading(project_id)` to cancel an in-progress cloud
project load when it takes too long, instead of waiting for it to finish.

Use `project.cloud_status(project_id)` to read only the current active cloud
transfer state. The payload includes `project_id`, `status`, `upload_progress`
and `download_progress`. `status` is `uploading`, `downloading`, or `idle`.
Completed, failed, paused and persisted cloud sync states are not returned by
this query; subscribe to cloud events to receive those notifications.

For cloud project image downloads, subscribe to
`project.cloudDownload.progress`, `project.cloudDownload.completed`,
`project.cloudDownload.failed` and `project.cloudDownload.paused`. Single image
download failures are reported through `project.cloudImageDownload.failed`.

## Convert to cloud errors

`project.convert_to_cloud(project_id)` validates cloud availability before it
starts. These problems are returned synchronously as errors (the call raises
`ApiError`), so the conversion never starts:

| Condition | `code` | Message |
| --- | --- | --- |
| `project_id` missing / invalid | 400 | `project_id is required` / `project_id must be a positive integer` |
| Project not found or disabled | 404 | `Project not found: <id>` |
| Project is already a cloud project | 409 | `Project is already cloud-synced` |
| Account has no cloud space | 403 | `Cloud space is not enabled for this account. Open Evoto to check cloud space access, then try again.` |
| Cloud storage turned off in Evoto settings | 403 | `Cloud storage is disabled in Evoto. Open Evoto Settings to enable cloud storage, then try again.` |
| Target space permission unavailable | 403 | `Cloud space permission is unavailable. Open Evoto to check cloud space access, then try again.` |

Problems that only surface after upload starts are reported asynchronously
through `project.convertToCloud.failed` and `project.cloudUpload.failed`. Their
payload carries `project_id`, `message` and `internal_error_code`:

| Condition | `message` |
| --- | --- |
| Cloud storage is full | `Cloud storage is full. Open Evoto to upgrade or free cloud storage, then try again.` |
| Cloud space permission revoked / insufficient | `Cloud space permission is unavailable. Open Evoto to check cloud space access, then try again.` |
| Other server-side errors | `Cloud operation failed. Open Evoto to check details, then try again.` |

All `message` values are host-owned, language-neutral English strings; the
host's localized text is never forwarded. Successful events
(`project.cloudUpload.completed`, `project.cloudDownload.completed`) carry no
`message` field. `internal_error_code` is the raw host/server code. Download and
local file errors can additionally include `local_error_code` and `debug_code`,
so plugins can branch on them when they need finer handling than the message.

::: evoto.project.ProjectAPI
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true
