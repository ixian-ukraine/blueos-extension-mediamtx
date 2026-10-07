# Maintenance notes

Decisions and gotchas for this BlueOS MediaMTX extension. Full system-level
architecture lives in the `ugv-stuff` repo:
`docs/architecture/mediamtx-streaming-and-discovery.md`.

## MediaMTX version
- Pinned to **v1.19.2**, built from **`bluenviron/mediamtx`** (the old `aler9/mediamtx`
  URL is a rename). v1.19.2 requires **Go ≥ 1.26** → builder base `golang:1.26.5-alpine3.24`.
- To bump: change the `git checkout` tag in the Dockerfile, check the tag's `go.mod`
  for the required Go version, and re-check config-key compatibility (below).

## Config-key compatibility (MediaMTX errors on unknown keys)
When bumping across versions, verify renamed keys against the tag's stock `mediamtx.yml`:
- `sourceProtocol` → `rtspTransport` (per-path)
- `webrtcICEServers` → `webrtcICEServers2` (list of `{ url: … }`)

## Build
- **Multi-stage**: Go toolchain builds the static (`CGO_ENABLED=0`) binary; runtime is
  bare `alpine` + `ffmpeg`, `gettext` (envsubst), `python3`, `py3-yaml`. Keeps the image
  ~240–307 MB instead of ~1.2 GB.
- arm64 tar for BlueOS "upload tar" install:
  `docker buildx build --platform linux/arm64 -o type=docker,dest=out.tar .`
  (needs a `docker-container` buildx builder for the tar export).

## Web UI
- `webserver.py` serves the config editor (`/`) and WHEP grid viewer (`/webrtc`), and
  runs/monitors the `mediamtx` binary.
- `/api/paths` parses `mediamtx.yml` (PyYAML) for the grid's source list — deliberately
  independent of MediaMTX's control API, so the grid works with `api: false`.
- The grid plays all configured paths; single-view closes the other WHEP sessions
  (`reader.js` `close()`) to save Pi egress.

## Upgrade gotcha (config persistence)
`start.sh` writes the template config to the persistent bind mount **only if it doesn't
already exist**. Upgrading the image does **not** migrate an old config. An old-syntax
config (`sourceProtocol`/`webrtcICEServers`) crashes v1.19.2 on startup — edit it via the
Configuration page, or delete `/usr/blueos/extensions/mediamtx/mediamtx.yml` to regenerate.

## Version label
- Keep `Dockerfile` `LABEL version` and `register_service` `"version"` in sync
  (currently **2.1.0**).

## Ixian release distribution
- Publish version tags to `ixian-ukraine/blueos-extension-mediamtx` (local remote
  `ixian`); `origin` continues to point at the original upstream repository.
- The release workflow builds Linux ARM64 on a native GitHub runner, smoke-tests
  the HTTP service, then publishes to
  `ghcr.io/ixian-ukraine/blueos-extension-mediamtx`.
- The shared release workflow and catalog generator live in
  `ixian-ukraine/blueos-extensions`. Each release includes a
  `blueos-manifest.json` asset containing its image digest and permissions.
- For a manual workflow retry, select the version tag as the workflow ref.
- First-time GHCR packages must be set to Public in GitHub package settings.
