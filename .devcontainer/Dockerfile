FROM ghcr.io/astral-sh/uv:0.6.6 AS uv

FROM fedora:latest

RUN dnf install -y \
    gcc \
    gobject-introspection-devel \
    cairo-gobject-devel \
    pkg-config \
    python3-devel \
    gtk4 \
    libadwaita-devel \
    mesa-libEGL-devel \
    meson \
    desktop-file-utils \
    && dnf clean all

COPY --from=uv /uv /uvx /bin/
