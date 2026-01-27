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

export CPATH="$GMP_PREFIX/include${CPATH:+:$CPATH}"
export CPLUS_INCLUDE_PATH="$GMP_PREFIX/include${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
export LIBRARY_PATH="$GMP_PREFIX/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"

mkdir -p "$STATIC_DIR"

echo "c building abc helpers"
(
  cd "$DEPS_DIR/abc"
  make libabc.a
  if [ -f file_generation_cex.c ] && [ -f file_generation_cnf.c ] && [ -f file_write_verilog.c ]; then
    gcc -Wall -g -c file_generation_cex.c -o file_generation_cex.o
    g++ -g -o file_generation_cex file_generation_cex.o libabc.a -lm -ldl -lreadline -lpthread
    gcc -Wall -g -c file_generation_cnf.c -o file_generation_cnf.o
    g++ -g -o file_generation_cnf file_generation_cnf.o libabc.a -lm -ldl -lreadline -lpthread
    gcc -Wall -g -c file_write_verilog.c -o file_write_verilog.o
    g++ -g -o file_write_verilog file_write_verilog.o libabc.a -lm -ldl -lreadline -lpthread
    cp file_generation_cex file_generation_cnf file_write_verilog "$STATIC_DIR/"
  else
    echo "c skipping abc helpers (file_generation_*.c not found)"
  fi
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
    CXXFLAGS="-O3 -Wall -Wno-parentheses -std=c++11 -DNSPACE=Glucose -DSOLVERNAME=\\\"Glucose4.1\\\" -DVERSION=core -I$DEPS_DIR/open-wbo/solvers/glucose4.1 -I$GMP_PREFIX/include" \
    LFLAGS="-lgmpxx -lgmp -L$GMP_PREFIX/lib -lz"
  cp open-wbo "$STATIC_DIR/open-wbo"
)

echo "c building unique (itp)"
(
  cd "$DEPS_DIR/unique"
  python3 - <<'PY'
from pathlib import Path

path = Path("avy/src/CMakeLists.txt")
text = path.read_text()
marker = "add_library (AbcCpp"
link_line = "target_link_libraries(AbcCpp ${ABC_LIBRARY} ClauseItpSeq AvyDebug ${MINISAT_LIBRARY})"
if link_line not in text and marker in text:
    lines = text.splitlines()
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if line.strip().startswith(marker):
            out.append(link_line)
            inserted = True
    if inserted:
        path.write_text("\n".join(out) + "\n")
PY
  if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
  else
    PYTHON_BIN="$(python3 -c 'import sys; print(sys.executable)')"
  fi
  PYTHON_SOABI="$("$PYTHON_BIN" -c 'import sysconfig; print(sysconfig.get_config_var("SOABI") or "")')"
  PYBIND11_DIR="$("$PYTHON_BIN" -m pybind11 --cmakedir 2>/dev/null || true)"
  BOOST_PREFIX="$(brew --prefix boost 2>/dev/null || true)"
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
  if [ -n "$BOOST_PREFIX" ]; then
    UNIQUE_CMAKE_FLAGS+=("-DBoost_ROOT=$BOOST_PREFIX" "-DCMAKE_CXX_FLAGS=-I$BOOST_PREFIX/include")
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
    cmake .. -DBUILD_SHARED_LIBS=OFF -DCMAKE_DISABLE_FIND_PACKAGE_breakid=ON -DBREAKID_FOUND=OFF -DBREAKID_LIBRARIES= -DBREAKID_INCLUDE_DIRS= -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    make -j8
  )
  echo "c building louvain-community (static)"
  (
    cd "$DEPS_DIR/manthan-preprocess/louvain-community"
    rm -rf build
    mkdir -p build
    cd build
    cmake .. -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    make -j8
  )
  mkdir -p build
  cd build
  cmake .. -DSTATICCOMPILE=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -Dcryptominisat5_DIR="$DEPS_DIR/manthan-preprocess/cryptominisat/build" \
    -Dlouvain_communities_DIR="$DEPS_DIR/manthan-preprocess/louvain-community/build"
  make -j8
  cp preprocess "$STATIC_DIR/preprocess"
)

echo "c done"
