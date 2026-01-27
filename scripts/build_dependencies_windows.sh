#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS_DIR="$ROOT_DIR/dependencies"
STATIC_DIR="$DEPS_DIR/static_bin"
ABC_CC=g++
ABC_CXX=g++
UNIQUE_GIT_REV=""

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required (pacman -S mingw-w64-x86_64-cmake)"
  exit 1
fi

if ! command -v gcc >/dev/null 2>&1; then
  echo "gcc is required (pacman -S mingw-w64-x86_64-toolchain)"
  exit 1
fi

mkdir -p "$STATIC_DIR"

copy_bin() {
  local name="$1"
  if [ -f "$name.exe" ]; then
    cp "$name.exe" "$STATIC_DIR/$name.exe"
  elif [ -f "$name" ]; then
    cp "$name" "$STATIC_DIR/$name"
  fi
}

echo "c building unique (itp)"
(
  cd "$DEPS_DIR/unique"
  if [ -z "$UNIQUE_GIT_REV" ] && [ -f "$DEPS_DIR/dependency_pins.json" ]; then
    UNIQUE_GIT_REV="$(python3 - <<'PY'
import json
with open("dependencies/dependency_pins.json", "r") as f:
    pins = json.load(f)
for entry in pins:
    if entry.get("path") == "dependencies/unique":
        print(entry.get("rev", ""))
        break
PY
)"
  fi
  if command -v git >/dev/null 2>&1 && [ -e .git ]; then
    git fetch --all --tags || true
    if [ -n "$UNIQUE_GIT_REV" ]; then
      git checkout "$UNIQUE_GIT_REV"
    fi
  fi
  PYTHON_BIN="$(python3 -c 'import sys; print(sys.executable)')"
  PYTHON_EXT="$(python3 -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX") or ".pyd")')"
  PYBIND11_DIR="$(python3 -m pybind11 --cmakedir 2>/dev/null || true)"
  UNIQUE_CMAKE_FLAGS=(
    -DABC_FORCE_CXX=ON
    -DABC_NAMESPACE=abc
    -DPYBIND11_FINDPYTHON=ON
    "-DPython_EXECUTABLE=$PYTHON_BIN"
    -DCMAKE_CXX_STANDARD=14
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5
  )
  if [ -n "$PYBIND11_DIR" ]; then
    UNIQUE_CMAKE_FLAGS+=("-Dpybind11_DIR=$PYBIND11_DIR")
  fi
  if [ -n "$PYTHON_EXT" ]; then
    UNIQUE_CMAKE_FLAGS+=("-DPYTHON_MODULE_EXTENSION=$PYTHON_EXT")
  fi
  rm -rf build
  cmake -S . -B build "${UNIQUE_CMAKE_FLAGS[@]}"
  UNIQUE_BUILD_TARGET=unique
  if [ -n "$PYBIND11_DIR" ]; then
    UNIQUE_BUILD_TARGET=itp
  fi
  cmake --build build --config Release --target "$UNIQUE_BUILD_TARGET"
)

echo "c building abc helpers"
(
  cd "$DEPS_DIR/abc"
  ABC_CXXFLAGS="${ABC_CXXFLAGS:-} -Wno-narrowing"
  ABC_CFLAGS="${ABC_CFLAGS:-} -DABC_USE_STDINT -Wno-narrowing"
  CC="$ABC_CC" CXX="$ABC_CXX" CXXFLAGS="$ABC_CXXFLAGS" CFLAGS="$ABC_CFLAGS" make libabc.a
  if [ -f file_generation_cex.c ] && [ -f file_generation_cnf.c ] && [ -f file_write_verilog.c ]; then
    "$ABC_CC" -Wall -g $ABC_CFLAGS -c file_generation_cex.c -o file_generation_cex.o
    "$ABC_CXX" -g $ABC_CFLAGS -o file_generation_cex file_generation_cex.o libabc.a -lm -lreadline -lpthread
    "$ABC_CC" -Wall -g $ABC_CFLAGS -c file_generation_cnf.c -o file_generation_cnf.o
    "$ABC_CXX" -g $ABC_CFLAGS -o file_generation_cnf file_generation_cnf.o libabc.a -lm -lreadline -lpthread
    "$ABC_CC" -Wall -g $ABC_CFLAGS -c file_write_verilog.c -o file_write_verilog.o
    "$ABC_CXX" -g $ABC_CFLAGS -o file_write_verilog file_write_verilog.o libabc.a -lm -lreadline -lpthread
    copy_bin file_generation_cex
    copy_bin file_generation_cnf
    copy_bin file_write_verilog
  else
    echo "c skipping abc helpers (file_generation_*.c not found)"
  fi
)

echo "c building cmsgen"
(
  cd "$DEPS_DIR/cmsgen"
  mkdir -p build
  cd build
  CC=cc CXX=c++ cmake ..
  cmake --build . -- -j8
  copy_bin cmsgen
)

echo "c building picosat"
(
  cd "$DEPS_DIR/picosat-src"
  ./configure.sh
  make -j8
  copy_bin picosat
)

echo "c building open-wbo"
(
  cd "$DEPS_DIR/open-wbo"
  make clean || true
  make -j8 \
    CFLAGS="-O3 -Wall -Wno-parentheses -std=c++11 -DNSPACE=Glucose -DSOLVERNAME=\\\"Glucose4.1\\\" -DVERSION=core -I$DEPS_DIR/open-wbo/solvers/glucose4.1" \
    LFLAGS="-lgmpxx -lgmp -lz"
  copy_bin open-wbo
)

echo "c building preprocess"
(
  cd "$DEPS_DIR/manthan-preprocess"
  echo "c building cryptominisat (static)"
  (
    cd "$DEPS_DIR/manthan-preprocess/cryptominisat"
    rm -rf build
    mkdir -p build
    cd build
    cmake .. -DBUILD_SHARED_LIBS=OFF -DCMAKE_DISABLE_FIND_PACKAGE_breakid=ON -DBREAKID_FOUND=OFF -DBREAKID_LIBRARIES= -DBREAKID_INCLUDE_DIRS= -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    cmake --build . -- -j8
  )
  echo "c building louvain-community (static)"
  (
    cd "$DEPS_DIR/manthan-preprocess/louvain-community"
    rm -rf build
    mkdir -p build
    cd build
    cmake .. -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    cmake --build . -- -j8
  )
  mkdir -p build
  cd build
  cmake .. -DSTATICCOMPILE=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -Dcryptominisat5_DIR="$DEPS_DIR/manthan-preprocess/cryptominisat/build" \
    -Dlouvain_communities_DIR="$DEPS_DIR/manthan-preprocess/louvain-community/build"
  cmake --build . -- -j8
  copy_bin preprocess
)

echo "c done"
