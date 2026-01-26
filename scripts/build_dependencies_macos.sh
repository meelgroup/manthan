#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS_DIR="$ROOT_DIR/dependencies"
STATIC_DIR="$DEPS_DIR/static_bin"

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required (brew install cmake)"
  exit 1
fi

GMP_PREFIX="$(brew --prefix gmp 2>/dev/null || true)"
if [ -z "$GMP_PREFIX" ]; then
  echo "gmp is required (brew install gmp)"
  exit 1
fi

mkdir -p "$STATIC_DIR"

echo "c building abc helpers"
(
  cd "$DEPS_DIR/abc"
  gcc -Wall -g -c file_generation_cex.c -o file_generation_cex.o
  g++ -g -o file_generation_cex file_generation_cex.o libabc.a -lm -ldl -lreadline -lpthread
  gcc -Wall -g -c file_generation_cnf.c -o file_generation_cnf.o
  g++ -g -o file_generation_cnf file_generation_cnf.o libabc.a -lm -ldl -lreadline -lpthread
  gcc -Wall -g -c file_write_verilog.c -o file_write_verilog.o
  g++ -g -o file_write_verilog file_write_verilog.o libabc.a -lm -ldl -lreadline -lpthread
  cp file_generation_cex file_generation_cnf file_write_verilog "$DEPS_DIR/"
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
    CFLAGS="-O3 -Wall -Wno-parentheses -std=c++11 -DNSPACE=Glucose -DSOLVERNAME=\\\"Glucose4.1\\\" -DVERSION=core -I$DEPS_DIR/open-wbo/solvers/glucose4.1 -I$GMP_PREFIX/include" \
    LFLAGS="-lgmpxx -lgmp -L$GMP_PREFIX/lib -lz"
  cp open-wbo "$STATIC_DIR/open-wbo"
)

echo "c building unique (itp)"
(
  cd "$DEPS_DIR/unique"
  mkdir -p build
  cd build
  cmake .. -DCMAKE_CXX_STANDARD=14
  cmake --build . --target itp -- -j8
)

echo "c building preprocess"
(
  cd "$DEPS_DIR/manthan-preprocess"
  mkdir -p build
  cd build
  cmake ..
  make -j8
  cp preprocess "$STATIC_DIR/preprocess"
)

echo "c done"
