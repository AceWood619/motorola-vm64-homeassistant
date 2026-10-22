#!/bin/sh
set -eu

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
RESEARCH_ROOT="${RESEARCH_ROOT:-/tmp/vm64-talkback-research}"
TOOLCHAIN_IMAGE="${TOOLCHAIN_IMAGE:-vm64-anyka-toolchain:local}"
CROSS_GCC="/work/toolchain/arm-anykav200-crosstool/usr/bin/arm-anykav200-linux-uclibcgnueabi-gcc"
SDK_ROOT="/work/ak3918ev300v18/platform/libplat"

if [ ! -x "$RESEARCH_ROOT/toolchain/arm-anykav200-crosstool/usr/bin/arm-anykav200-linux-uclibcgnueabi-gcc" ]; then
  echo "Missing Anyka toolchain under $RESEARCH_ROOT/toolchain" >&2
  exit 2
fi
if [ ! -f "$RESEARCH_ROOT/ak3918ev300v18/platform/libplat/include/ak_ao.h" ] || [ ! -f "$RESEARCH_ROOT/ak3918ev300v18/platform/libplat/lib/libplat_ao.a" ]; then
  echo "Missing Anyka SDK under $RESEARCH_ROOT/ak3918ev300v18" >&2
  exit 2
fi

if ! docker image inspect "$TOOLCHAIN_IMAGE" >/dev/null 2>&1; then
  docker build -t "$TOOLCHAIN_IMAGE" -f "$REPO_ROOT/scripts/talkback-toolchain.Dockerfile" "$REPO_ROOT"
fi

docker run --rm \
  -v "$REPO_ROOT:/src:ro" \
  -v "$RESEARCH_ROOT:/work" \
  -w /work "$TOOLCHAIN_IMAGE" \
  "$CROSS_GCC" -Os \
  -I"$SDK_ROOT/include" -L"$SDK_ROOT/lib" \
  -Wl,-rpath,/usr/lib \
  -o /work/vm64_talkback /src/scripts/talkback_player.c \
  -Wl,-Bstatic -lplat_ao -lplat_common -lplat_thread -lplat_ipcsrv \
  -Wl,-Bdynamic -lakaudiofilter -ldl -lm -lpthread

file "$RESEARCH_ROOT/vm64_talkback"
readelf -h "$RESEARCH_ROOT/vm64_talkback" | grep -E 'Class|Machine'
