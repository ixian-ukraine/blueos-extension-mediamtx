# ---- Build stage: compile the mediamtx binary ----
# mediamtx v1.19.2 requires Go >= 1.26
FROM golang:1.26.5-alpine3.24 AS builder

RUN apk add --no-cache \
    gcc \
    musl-dev \
    git

WORKDIR /build

# Clone and build mediamtx with a specific version.
# CGO_ENABLED=0 produces a static binary that runs on a bare Alpine runtime.
RUN git clone https://github.com/bluenviron/mediamtx.git . && \
    git checkout v1.19.2 && \
    go generate ./... && \
    CGO_ENABLED=0 go build -o /mediamtx .

# ---- Runtime stage: slim image with just the binary + web server ----
FROM alpine:3.24

# Runtime dependencies only (no Go toolchain):
#  - ffmpeg:  optional path sources / runOnDemand hooks
#  - gettext: provides envsubst, used by start.sh to render the config template
#  - python3 + py3-yaml: the web server and its /api/paths config parsing
RUN apk add --no-cache \
    ffmpeg \
    gettext \
    python3 \
    py3-yaml

# Set working directory
WORKDIR /app

# Copy the compiled mediamtx binary from the build stage
COPY --from=builder /mediamtx /app/mediamtx

# Create config directory and the BlueOS extension mount point
RUN mkdir -p /app/config /usr/blueos/extensions/mediamtx

# Copy configuration file and start script
COPY mediamtx.yml /app/config/mediamtx.yml.template
COPY start.sh /app/start.sh
COPY reader.js /app/reader.js
COPY index.html /app/index.html
COPY webrtc.html /app/webrtc.html
COPY webserver.py /app/webserver.py
COPY register_service /app/register_service
RUN chmod +x /app/start.sh /app/webserver.py /app/mediamtx

# Expose RTSP, WebRTC, and web server ports
EXPOSE 8554
EXPOSE 8889
EXPOSE 8908

# Docker labels for BlueOS
LABEL version="2.1.0"
LABEL org.opencontainers.image.source="https://github.com/ixian-ukraine/blueos-extension-mediamtx"
LABEL permissions='{\
  "HostConfig": {\
    "Privileged": true,\
    "NetworkMode": "host",\
    "Binds":[\
      "/usr/blueos/extensions/mediamtx:/usr/blueos/extensions/mediamtx"\
    ]\
  }\
}'

LABEL authors='[\
    {\
        "name": "Willian Galvani",\
        "email": "willian@bluerobotics.com"\
    }\
]'
LABEL company='{\
        "about": "Ixian-maintained build of the BlueOS MediaMTX extension",\
        "name": "Ixian Ukraine"\
    }'
LABEL type="other"
LABEL tags='[\
        "communication"\
    ]'
LABEL readme='https://raw.githubusercontent.com/ixian-ukraine/blueos-extension-mediamtx/{tag}/README.md'
LABEL links='{\
        "website": "https://github.com/ixian-ukraine/blueos-extension-mediamtx",\
        "support": "https://github.com/ixian-ukraine/blueos-extension-mediamtx/issues"\
    }'

# Use the start script as entrypoint
ENTRYPOINT ["/app/start.sh"]
