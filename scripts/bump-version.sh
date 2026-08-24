#!/usr/bin/env bash
# Bump rift's version across the crate and packaging metadata, then (optionally)
# refresh the Homebrew formula checksums from a published GitHub release.
#
# Usage:
#   scripts/bump-version.sh 0.2.0            # set version everywhere
#   scripts/bump-version.sh 0.2.0 --shasums  # also pull release .sha256 files
#
# The `--shasums` step requires the `v<version>` release to already be published
# (i.e. run it after the release workflow finishes) and `curl` on PATH.
set -euo pipefail

version="${1:-}"
if [[ -z "$version" ]]; then
  echo "usage: $0 <version> [--shasums]" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

# In-place edit helper that works on both GNU and BSD sed.
sed_i() {
  if sed --version >/dev/null 2>&1; then
    sed -i "$@"
  else
    sed -i '' "$@"
  fi
}

echo "Setting version to $version"

# Cargo.toml: the first `version = "..."` under [package].
sed_i "s/^version = \".*\"/version = \"$version\"/" Cargo.toml

# Keep Cargo.lock's own rift entry in sync.
cargo update -p rift --precise "$version" >/dev/null 2>&1 || cargo build >/dev/null

# Homebrew formula version line.
sed_i "s/^  version \".*\"/  version \"$version\"/" packaging/homebrew/rift.rb

echo "Updated Cargo.toml, Cargo.lock, packaging/homebrew/rift.rb"

if [[ "${2:-}" == "--shasums" ]]; then
  base="https://github.com/jrf/rift/releases/download/v${version}"
  declare -A targets=(
    [aarch64-apple-darwin]="on_arm.*apple-darwin"
    [x86_64-apple-darwin]="on_intel.*apple-darwin"
    [aarch64-unknown-linux-gnu]="on_arm.*linux-gnu"
    [x86_64-unknown-linux-gnu]="on_intel.*linux-gnu"
  )
  for target in "${!targets[@]}"; do
    file="rift-${version}-${target}.tar.gz"
    echo "Fetching checksum for $file"
    sum="$(curl -fsSL "${base}/${file}.sha256" | awk '{print $1}')"
    if [[ -z "$sum" ]]; then
      echo "warning: no checksum for $target" >&2
      continue
    fi
    # Replace the sha256 line that follows this target's url line.
    awk -v tgt="$target" -v sum="$sum" '
      $0 ~ tgt "\\.tar\\.gz\"" { print; getline; sub(/"[0-9a-f]+"/, "\"" sum "\""); print; next }
      { print }
    ' packaging/homebrew/rift.rb > packaging/homebrew/rift.rb.tmp
    mv packaging/homebrew/rift.rb.tmp packaging/homebrew/rift.rb
  done
  echo "Refreshed Homebrew checksums"
fi

echo "Done. Review changes, commit, then tag: git tag v${version} && git push --tags"
