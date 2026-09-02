# `evoto.host`

The `evoto.host` namespace exposes low-level handles onto the connected
Evoto host: raw JSON-RPC, host-process discovery, and host lifecycle
control. Plugin authors should normally prefer the domain APIs
(`evoto.project`, `evoto.image`, etc.); reach for this namespace when
those are not enough.

`configure_silent_timeout` only applies when Evoto was launched with
`-silent`; against a normally launched host it raises `ApiError` with
`code=412`. The [Silent mode guide](../guides/silent-mode.md) covers how
to launch the background host and what the watcher does.

::: evoto._Host
    options:
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: true
      members:
        - call
        - call_async
        - cancel_request
        - discover_host
        - wait_for_host
        - is_available
        - reconnect
        - quit
        - configure_silent_timeout
        - is_connected
