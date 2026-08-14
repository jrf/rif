default: install

# Build in debug mode
build:
    cargo build

# Build in release mode
release:
    cargo build --release

# Run the app
run:
    cargo run

# Install to the cargo bin path (~/.cargo/bin by default)
install:
    cargo install --path . --force
    codesign -s - "{{ env('CARGO_HOME', env('HOME') / '.cargo') }}/bin/rift"

# Uninstall from the cargo bin path
uninstall:
    cargo uninstall rift

# Remove build artifacts
clean:
    cargo clean
