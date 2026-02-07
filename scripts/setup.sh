#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS_DIR="$ROOT_DIR/dependencies"

usage() {
  cat <<'EOF'
Usage: ./scripts/setup.sh [--build] [--clean] [--update]

Default: build dependencies from source.

Options:
  --build   Build from source (default behavior).
  --clean   Remove built dependency artifacts.
  --update  Fetch/pull dependency repos before building.
EOF
}

want_build=0
want_clean=0
want_update=0

while [ $# -gt 0 ]; do
  case "$1" in
    --build)
      want_build=1
      ;;
    --clean)
      want_clean=1
      ;;
    --update)
      want_update=1
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

clean_dependencies() {
  rm -rf \
    "$DEPS_DIR/static_bin" \
    "$DEPS_DIR/unique/build" \
    "$DEPS_DIR/manthan-preprocess/build" \
    "$DEPS_DIR/manthan-preprocess/cryptominisat/build" \
    "$DEPS_DIR/manthan-preprocess/louvain-community/build" \
    "$DEPS_DIR/abc/build" \
    "$DEPS_DIR/cmsgen/build" \
    "$DEPS_DIR/open-wbo/build" \
    "$DEPS_DIR/picosat-src/build"
}

update_dependencies() {
  if [ ! -f "$DEPS_DIR/dependency_pins.json" ]; then
    echo "Missing $DEPS_DIR/dependency_pins.json"
    return 1
  fi
  local repos
  repos="$(python3 - <<'PY'
import json
with open("dependencies/dependency_pins.json", "r") as f:
    pins = json.load(f)
for entry in pins:
    print(entry["path"])
PY
)"
  local path branch
  while IFS= read -r path; do
    [ -z "$path" ] && continue
    if [ -d "$ROOT_DIR/$path/.git" ]; then
      git -C "$ROOT_DIR/$path" fetch --all --tags || true
      branch="$(git -C "$ROOT_DIR/$path" symbolic-ref --short -q HEAD || true)"
      if [ -n "$branch" ]; then
        git -C "$ROOT_DIR/$path" pull --ff-only origin "$branch" || true
      fi
      case "$path" in
        dependencies/unique|dependencies/manthan-preprocess)
          git -C "$ROOT_DIR/$path" submodule update --init --recursive --remote || true
          ;;
      esac
    fi
  done <<< "$repos"
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

if [ "$want_clean" -eq 1 ]; then
  clean_dependencies
fi

if [ "$want_update" -eq 1 ]; then
  update_dependencies
fi

if [ $want_build -eq 1 ] || [ "$want_clean" -eq 0 ]; then
  build_from_source
fi

update_itp_path
echo "Setup complete."
