alias test := tests

# Build the app using flatpak-builder
build:
    flatpak-builder --force-clean --build-only build-dir de.flokoe.Whisper.json

# Build and run the app using flatpak-builder
dev: build
    flatpak-builder --run build-dir de.flokoe.Whisper.json whisper --debug

# Install the app using flatpak-builder
install:
    flatpak-builder --user --force-clean --install build-dir de.flokoe.Whisper.json

# Execute all tests
tests:
    uv run pytest tests/
