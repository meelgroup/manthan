#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS_DIR="$ROOT_DIR/dependencies"

usage() {
  cat <<'EOF'
Usage: ./scripts/setup.sh [--build] [--force] [--repo owner/name]

Default: download prebuilt dependency binaries from the latest GitHub release
and extract them into dependencies/.

Options:
  --build   Build from source instead of downloading artifacts.
  --force   Re-download even if dependencies/static_bin already exists.
  --repo    Override GitHub repo in owner/name form.
EOF
}

want_build=0
force_download=0
repo_override=""

while [ $# -gt 0 ]; do
  case "$1" in
    --build)
      want_build=1
      ;;
    --force)
      force_download=1
      ;;
    --repo)
      repo_override="${2:-}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

detect_os() {
  local uname_out
  uname_out="$(uname -s)"
  case "$uname_out" in
    Linux*) echo "linux" ;;
    Darwin*) echo "macos" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

resolve_repo() {
  if [ -n "$repo_override" ]; then
    echo "$repo_override"
    return
  fi
  if [ -n "${MANTHAN_REPO:-}" ]; then
    echo "$MANTHAN_REPO"
    return
  fi
  local origin_url
  origin_url="$(git -C "$ROOT_DIR" config --get remote.origin.url || true)"
  if [ -z "$origin_url" ]; then
    echo ""
    return
  fi
  if [[ "$origin_url" == git@github.com:* ]]; then
    echo "$origin_url" | sed -E 's#git@github.com:([^/]+/[^.]+)(\.git)?#\1#'
    return
  fi
  if [[ "$origin_url" == https://github.com/* ]]; then
    echo "$origin_url" | sed -E 's#https://github.com/([^/]+/[^.]+)(\.git)?#\1#'
    return
  fi
  echo ""
}

update_itp_path() {
  python3 - <<'PY'
import configparser
from pathlib import Path

cfg_path = Path("manthan_dependencies.cfg")
config = configparser.ConfigParser()
config.read(cfg_path)
if "ITP-Path" not in config:
    config["ITP-Path"] = {}
config["ITP-Path"]["itp_path"] = "dependencies/unique/build/interpolatingsolver/src"
with open(cfg_path, "w") as f:
    config.write(f)
PY
}

download_release() {
  local os_slug="$1"
  local repo
  repo="$(resolve_repo)"
  if [ -z "$repo" ]; then
    echo "Unable to determine GitHub repo. Use --repo owner/name or set MANTHAN_REPO."
    return 1
  fi

  local asset_name="manthan-deps-${os_slug}.tar.gz"
  local api_url="https://api.github.com/repos/${repo}/releases/latest"
  local tmp_json tmp_tar
  tmp_json="$(mktemp)"
  tmp_tar="$(mktemp)"

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to download release artifacts"
    return 1
  fi

  curl -sL "$api_url" -o "$tmp_json"

  local asset_url
  asset_url="$(python3 - "$tmp_json" "$asset_name" <<'PY'
import json
import sys

path = sys.argv[1]
asset_name = sys.argv[2]
with open(path, "r") as f:
    data = json.load(f)
for asset in data.get("assets", []):
    if asset.get("name") == asset_name:
        print(asset.get("browser_download_url", ""))
        break
PY
)"

  if [ -z "$asset_url" ]; then
    echo "No release asset named $asset_name found in $repo."
    return 1
  fi

  echo "Downloading $asset_name from $repo..."
  curl -L "$asset_url" -o "$tmp_tar"
  tar -xzf "$tmp_tar" -C "$ROOT_DIR"
  rm -f "$tmp_json" "$tmp_tar"
  return 0
}

build_from_source() {
  ./scripts/clone_dependencies.sh
  case "$(detect_os)" in
    linux)
      ./scripts/build_dependencies_linux.sh
      ;;
    macos)
      ./scripts/build_dependencies_macos.sh
      ;;
    windows)
      bash ./scripts/build_dependencies_windows.sh
      ;;
    *)
      echo "Unsupported OS for build."
      return 1
      ;;
  esac
}

os_slug="$(detect_os)"
if [ "$os_slug" = "unknown" ]; then
  echo "Unsupported OS."
  exit 1
fi

if [ $want_build -eq 0 ]; then
  if [ -d "$DEPS_DIR/static_bin" ] && [ $force_download -eq 0 ]; then
    echo "dependencies/static_bin already exists; use --force to re-download or --build to rebuild."
  else
    if ! download_release "$os_slug"; then
      echo "Falling back to building from source."
      want_build=1
    fi
  fi
fi

if [ $want_build -eq 1 ]; then
  build_from_source
fi

update_itp_path
echo "Setup complete."
