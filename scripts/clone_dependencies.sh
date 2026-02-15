#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PINS_FILE="$ROOT_DIR/dependencies/dependency_pins.json"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required"
  exit 1
fi

if [ ! -f "$PINS_FILE" ]; then
  echo "Missing $PINS_FILE"
  exit 1
fi

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python is required"
  exit 1
fi

checkout_pin() {
  local path="$1"
  local url="$2"
  local rev="$3"
  if [ -e "$path/.git" ]; then
    git -C "$path" remote set-url origin "$url" || true
    git -C "$path" fetch --all --tags || true
    git -C "$path" checkout "$rev"
    case "$path" in
      */dependencies/unique|*/dependencies/bfss)
        git -C "$path" submodule update --init --recursive
        ;;
    esac
    return
  fi
  if [ -e "$path" ]; then
    if [ -d "$path" ] && [ -z "$(ls -A "$path")" ]; then
      rmdir "$path"
    else
      echo "Skipping $path (exists but is not a git repo)"
      return
    fi
  fi
  git clone "$url" "$path"
  git -C "$path" checkout "$rev"
  case "$path" in
    */dependencies/unique|*/dependencies/bfss)
      git -C "$path" submodule update --init --recursive
      ;;
  esac
}

if [ -f "$ROOT_DIR/.gitmodules" ]; then
  echo "c skipping root submodule init; dependencies are pinned in dependency_pins.json"
  git -C "$ROOT_DIR" submodule sync --recursive
fi

while IFS= read -r line; do
  if [ -z "$line" ]; then
    continue
  fi
  path="$(echo "$line" | cut -d'|' -f1)"
  url="$(echo "$line" | cut -d'|' -f2)"
  rev="$(echo "$line" | cut -d'|' -f3)"
  echo "c pinning $path @ $rev"
  checkout_pin "$ROOT_DIR/$path" "$url" "$rev"
done < <(
  "$PYTHON_BIN" - <<'PY'
import json
with open("dependencies/dependency_pins.json", "r") as f:
    pins = json.load(f)
for entry in pins:
    print(f"{entry['path']}|{entry['url']}|{entry['rev']}")
PY
)

echo "c done"
