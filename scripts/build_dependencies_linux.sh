#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS_DIR="$ROOT_DIR/dependencies"
STATIC_DIR="$DEPS_DIR/static_bin"
ABC_CC=g++
ABC_CXX=g++
UNIQUE_GIT_REV=""

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required (sudo apt-get install cmake)"
  exit 1
fi

if ! command -v gcc >/dev/null 2>&1; then
  echo "gcc is required (sudo apt-get install build-essential)"
  exit 1
fi

if command -v pkg-config >/dev/null 2>&1; then
  if ! pkg-config --exists gmpxx 2>/dev/null; then
    if ! pkg-config --exists gmp 2>/dev/null; then
      echo "gmpxx/gmp not found via pkg-config. Set GMP_DIR or install libgmp-dev."
      exit 1
    fi
  fi
else
  if [ ! -f /usr/include/gmpxx.h ] && [ ! -f /usr/local/include/gmpxx.h ] && [ -z "${GMP_DIR:-}" ]; then
    echo "gmpxx.h is required. Set GMP_DIR or install libgmp-dev."
    exit 1
  fi
fi

if [ -z "${BOOST_ROOT:-}" ] && [ -z "${Boost_ROOT:-}" ] && [ -z "${CMAKE_PREFIX_PATH:-}" ]; then
  if command -v pkg-config >/dev/null 2>&1; then
    if ! pkg-config --exists boost 2>/dev/null; then
      if [ ! -f /usr/include/boost/program_options.hpp ] && [ ! -f /usr/local/include/boost/program_options.hpp ]; then
        echo "Boost headers not found. Set BOOST_ROOT/Boost_ROOT or install libboost-program-options-dev."
        exit 1
      fi
    fi
  else
    if [ ! -f /usr/include/boost/program_options.hpp ] && [ ! -f /usr/local/include/boost/program_options.hpp ]; then
      echo "Boost program_options headers are required. Set BOOST_ROOT/Boost_ROOT or install libboost-program-options-dev."
      exit 1
    fi
  fi
fi

mkdir -p "$STATIC_DIR"

echo "c building preprocess"
(
  cd "$DEPS_DIR/manthan-preprocess"
  echo "c building cryptominisat (shared)"
  (
    cd "$DEPS_DIR/manthan-preprocess/cryptominisat"
    rm -rf build
    mkdir -p build
    cd build
    cmake .. -DBUILD_SHARED_LIBS=ON -DENABLE_PYTHON_INTERFACE=OFF -DMANPAGE=OFF -DCMAKE_DISABLE_FIND_PACKAGE_breakid=ON -DBREAKID_FOUND=OFF -DBREAKID_LIBRARIES= -DBREAKID_INCLUDE_DIRS= -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    make -j8
  )
  echo "c building louvain-community (shared)"
  (
    cd "$DEPS_DIR/manthan-preprocess/louvain-community"
    rm -rf build
    mkdir -p build
    cd build
    cmake .. -DBUILD_SHARED_LIBS=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    make -j8
  )
  rm -rf build
  mkdir -p build
  cd build
  cmake .. -DSTATICCOMPILE=OFF -DNOM4RI=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -Dcryptominisat5_DIR="$DEPS_DIR/manthan-preprocess/cryptominisat/build" \
    -Dlouvain_communities_DIR="$DEPS_DIR/manthan-preprocess/louvain-community/build"
  make -j8
  cp preprocess "$STATIC_DIR/preprocess"
  # Bundle shared libs alongside preprocess and make it load from $ORIGIN.
  if command -v patchelf >/dev/null 2>&1; then
    patchelf --set-rpath '$ORIGIN' "$STATIC_DIR/preprocess" || true
  fi
  if [ -d "$DEPS_DIR/manthan-preprocess/cryptominisat/build/lib" ]; then
    cp -f "$DEPS_DIR/manthan-preprocess/cryptominisat/build/lib/"*.so* "$STATIC_DIR/" 2>/dev/null || true
  fi
  if [ -d "$DEPS_DIR/manthan-preprocess/louvain-community/build/lib" ]; then
    cp -f "$DEPS_DIR/manthan-preprocess/louvain-community/build/lib/"*.so* "$STATIC_DIR/" 2>/dev/null || true
  fi
)

echo "c building unique (itp)"
(
  cd "$DEPS_DIR/unique"
  if [ -z "$UNIQUE_GIT_REV" ] && [ -f "$DEPS_DIR/dependency_pins.json" ]; then
    UNIQUE_GIT_REV="$(
      DEPS_DIR="$DEPS_DIR" python3 - <<'PY'
import json
import os

pins_path = os.path.join(os.environ["DEPS_DIR"], "dependency_pins.json")
with open(pins_path, "r") as f:
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
  if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
  else
    PYTHON_BIN="$(python3 -c 'import sys; print(sys.executable)')"
  fi
  PYTHON_SOABI="$("$PYTHON_BIN" -c 'import sysconfig; print(sysconfig.get_config_var("SOABI") or "")')"
  PYBIND11_DIR="$("$PYTHON_BIN" -m pybind11 --cmakedir 2>/dev/null || true)"
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
  if [ -n "$PYTHON_SOABI" ]; then
    UNIQUE_CMAKE_FLAGS+=("-DPYTHON_MODULE_EXTENSION=.${PYTHON_SOABI}.so")
  fi
  rm -rf build
  cmake -S . -B build "${UNIQUE_CMAKE_FLAGS[@]}"
  UNIQUE_BUILD_TARGET=unique
  if [ -n "$PYBIND11_DIR" ]; then
    UNIQUE_BUILD_TARGET=itp
  fi
  cmake --build build --target "$UNIQUE_BUILD_TARGET" -- -j2
  if [ "$UNIQUE_BUILD_TARGET" = "itp" ]; then
    ITP_DIR="$DEPS_DIR/unique/build/interpolatingsolver/src"
    ITP_SO="$(ls "$ITP_DIR"/itp.cpython-*.so 2>/dev/null | head -n 1 || true)"
    if [ -n "$ITP_SO" ]; then
      if [ -f "$ITP_DIR/libinterpolating_minisat.so" ]; then
        cp -f "$ITP_DIR/libinterpolating_minisat.so"* "$ITP_DIR/" 2>/dev/null || true
      elif [ -f "$DEPS_DIR/unique/build/avy/src/libinterpolating_minisat.so" ]; then
        cp -f "$DEPS_DIR/unique/build/avy/src/libinterpolating_minisat.so"* "$ITP_DIR/" 2>/dev/null || true
      fi
      if [ ! -f "$ITP_DIR/libAvyDebug.so" ] && [ -f "$DEPS_DIR/unique/build/avy/src/libAvyDebug.so" ]; then
        cp -f "$DEPS_DIR/unique/build/avy/src/libAvyDebug.so"* "$ITP_DIR/" 2>/dev/null || true
      fi
      if command -v patchelf >/dev/null 2>&1; then
        patchelf --set-rpath '$ORIGIN' "$ITP_SO" || true
      fi
    fi
  fi
)

echo "c building abc helpers"
(
  cd "$DEPS_DIR/abc"
  make clean || true
  ABC_CXXFLAGS="${ABC_CXXFLAGS:-} -Wno-narrowing"
  ABC_CFLAGS="${ABC_CFLAGS:-} -Wno-narrowing"
  CC="$ABC_CC" CXX="$ABC_CXX" CXXFLAGS="$ABC_CXXFLAGS" CFLAGS="$ABC_CFLAGS" make libabc.a
  if [ -f file_generation_cex.c ] && [ -f file_generation_cnf.c ] && [ -f file_write_verilog.c ]; then
    "$ABC_CC" -Wall -g $ABC_CFLAGS -c file_generation_cex.c -o file_generation_cex.o
    "$ABC_CXX" -g -o file_generation_cex file_generation_cex.o libabc.a -lm -ldl -lreadline -lpthread
    "$ABC_CC" -Wall -g $ABC_CFLAGS -c file_generation_cnf.c -o file_generation_cnf.o
    "$ABC_CXX" -g -o file_generation_cnf file_generation_cnf.o libabc.a -lm -ldl -lreadline -lpthread
    "$ABC_CC" -Wall -g $ABC_CFLAGS -c file_write_verilog.c -o file_write_verilog.o
    "$ABC_CXX" -g -o file_write_verilog file_write_verilog.o libabc.a -lm -ldl -lreadline -lpthread
    cp file_generation_cex file_generation_cnf file_write_verilog "$STATIC_DIR/"
  else
    echo "c missing abc helper sources (file_generation_*.c not found)"
    exit 1
  fi
)

echo "c building cmsgen"
(
  cd "$DEPS_DIR/cmsgen"
  rm -rf build
  mkdir -p build
  cd build
  CC=cc CXX=c++ cmake ..
  make -j8
  cp cmsgen "$STATIC_DIR/cmsgen"
)

echo "c building picosat"
(
  cd "$DEPS_DIR/picosat-src"
  make clean || true
  ./configure.sh
  make -j8
  cp picosat "$STATIC_DIR/picosat"
)

echo "c building open-wbo"
(
  cd "$DEPS_DIR/open-wbo"
  make clean || true
  make -j8 \
    CFLAGS="-O3 -Wall -Wno-parentheses -std=c++11 -DNSPACE=Glucose -DSOLVERNAME=\\\"Glucose4.1\\\" -DVERSION=core -I$DEPS_DIR/open-wbo/solvers/glucose4.1" \
    LFLAGS="-lgmpxx -lgmp -lz"
  cp open-wbo "$STATIC_DIR/open-wbo"
)

echo "c done"
