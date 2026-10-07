# MediaMTX BlueOS Extension

A BlueOS extension that provides RTSP relay functionality using [MediaMTX](https://github.com/aler9/mediamtx), enabling you to proxy, view, and redistribute RTSP video streams through various protocols including WebRTC.

## Features

- **RTSP Stream Relay**: Proxy and redistribute RTSP streams from IP cameras or other sources
- **WebRTC Support**: View streams directly in your browser with low latency
- **Web-based Configuration**: Easy-to-use interface for editing MediaMTX configuration
- **Real-time Management**: Start, stop, and restart the MediaMTX service through the web 

## Ixian Ukraine distribution

This repository maintains an ARM64 build based on
[Willian Galvani's extension](https://github.com/Williangalvani/blueos-extension-MediaMTX).
Extension version **2.1.0** includes MediaMTX **1.19.2** and the multi-camera viewer.

### Install in BlueOS

Open **Extensions → Settings (gear) → Extensions Manifest → +** and add:

```text
https://raw.githubusercontent.com/ixian-ukraine/blueos-extensions/main/manifest.json
```

Enable the source and install **MediaMTX (Ixian)**. The extension identifier is
`ixian-ukraine.mediamtx`; the image is
`ghcr.io/ixian-ukraine/blueos-extension-mediamtx:2.1.0`.

The current published platform is **Linux ARM64**. The UI uses port **8908**,
relayed RTSP uses **8555**, and WebRTC signaling uses **8889**.
Configuration persists in `/usr/blueos/extensions/mediamtx/mediamtx.yml`.
Stop an existing MediaMTX extension before switching to this build because it
uses the same ports and persistent configuration. Existing configurations are
not automatically migrated; see [MAINTENANCE.md](MAINTENANCE.md).

### Publishing

Push a SemVer tag to build, smoke-test, and publish the image to GHCR. The workflow
also attaches `blueos-manifest.json` to the GitHub release. The
[Ixian catalog](https://github.com/ixian-ukraine/blueos-extensions) picks up releases
hourly, or when its **Refresh catalog** workflow is run manually.
