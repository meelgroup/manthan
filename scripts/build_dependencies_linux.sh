#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS_DIR="$ROOT_DIR/dependencies"
STATIC_DIR="$DEPS_DIR/static_bin"

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required (sudo apt-get install cmake)"
  exit 1
fi

if ! command -v gcc >/dev/null 2>&1; then
  echo "gcc is required (sudo apt-get install build-essential)"
  exit 1
fi

if [ ! -f /usr/include/gmpxx.h ] && [ ! -f /usr/local/include/gmpxx.h ]; then
  echo "gmpxx.h is required (sudo apt-get install libgmp-dev)"
  exit 1
fi

if [ ! -f /usr/include/boost/program_options.hpp ] && [ ! -f /usr/local/include/boost/program_options.hpp ]; then
  echo "Boost program_options headers are required (sudo apt-get install libboost-program-options-dev)"
  exit 1
fi

mkdir -p "$STATIC_DIR"

echo "c building abc helpers"
(
  cd "$DEPS_DIR/abc"
  make libabc.a
  gcc -Wall -g -c file_generation_cex.c -o file_generation_cex.o
  g++ -g -o file_generation_cex file_generation_cex.o libabc.a -lm -ldl -lreadline -lpthread
  gcc -Wall -g -c file_generation_cnf.c -o file_generation_cnf.o
  g++ -g -o file_generation_cnf file_generation_cnf.o libabc.a -lm -ldl -lreadline -lpthread
  gcc -Wall -g -c file_write_verilog.c -o file_write_verilog.o
  g++ -g -o file_write_verilog file_write_verilog.o libabc.a -lm -ldl -lreadline -lpthread
  cp file_generation_cex file_generation_cnf file_write_verilog "$STATIC_DIR/"
)

echo "c building cmsgen"
(
  cd "$DEPS_DIR/cmsgen"
  mkdir -p build
  cd build
  cmake ..
  make -j8
  cp cmsgen "$STATIC_DIR/cmsgen"
)

echo "c building picosat"
(
  cd "$DEPS_DIR/picosat-src"
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

echo "c building unique (itp)"
(
  cd "$DEPS_DIR/unique"
  PYTHON_BIN="$(python3 -c 'import sys; print(sys.executable)')"
  PYTHON_SOABI="$(python3 -c 'import sysconfig; print(sysconfig.get_config_var("SOABI") or "")')"
  PYBIND11_DIR="$(python3 -m pybind11 --cmakedir 2>/dev/null || true)"
  UNIQUE_CMAKE_FLAGS=(
    -DABC_FORCE_CXX=OFF
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
  mkdir -p build
  cd build
  cmake .. "${UNIQUE_CMAKE_FLAGS[@]}"
  cmake --build . --target itp -- -j8
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
    cmake .. -DBUILD_SHARED_LIBS=OFF -DBREAKID_FOUND=OFF -DBREAKID_LIBRARIES= -DBREAKID_INCLUDE_DIRS=
    make -j8
  )
  echo "c building louvain-community (static)"
  (
    cd "$DEPS_DIR/manthan-preprocess/louvain-community"
    rm -rf build
    mkdir -p build
    cd build
    cmake .. -DBUILD_SHARED_LIBS=OFF
    make -j8
  )
  mkdir -p build
  cd build
  cmake .. -DSTATICCOMPILE=ON \
    -Dcryptominisat5_DIR="$DEPS_DIR/manthan-preprocess/cryptominisat/build" \
    -Dlouvain_communities_DIR="$DEPS_DIR/manthan-preprocess/louvain-community/build"
  make -j8
  cp preprocess "$STATIC_DIR/preprocess"
)

echo "c done"
