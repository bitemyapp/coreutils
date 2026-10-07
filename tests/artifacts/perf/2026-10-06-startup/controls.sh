#!/bin/bash
# Invoke on wx-workstation after unprofiled baseline timing has finished.
set -euo pipefail
cd /home/callen/work/coreutils-startup-8cf2e4f4
mkdir -p bin/controls
cat > artifacts/empty.c <<'C'
int main(void) { return 0; }
C
cat > artifacts/empty.rs <<'RUST'
fn main() {}
RUST
gcc -O3 -g -fno-omit-frame-pointer artifacts/empty.c -o bin/controls/empty-c
rustc -O -C panic=abort -C lto=fat -C codegen-units=1 -C force-frame-pointers=yes -g artifacts/empty.rs -o bin/controls/empty-rust
cat > artifacts/calibrate-tsc.c <<'C'
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <x86intrin.h>
static uint64_t ns(struct timespec t) {
    return (uint64_t)t.tv_sec * 1000000000u + t.tv_nsec;
}
int main(void) {
    struct timespec a, b, delay = { .tv_sec = 0, .tv_nsec = 20000000 };
    for (int i = 0; i < 10; i++) {
        clock_gettime(CLOCK_MONOTONIC_RAW, &a);
        _mm_lfence();
        uint64_t x = __rdtsc();
        nanosleep(&delay, 0);
        _mm_lfence();
        uint64_t y = __rdtsc();
        clock_gettime(CLOCK_MONOTONIC_RAW, &b);
        printf("%.6f\n", (double)(y - x) / (double)(ns(b) - ns(a)));
    }
}
C
gcc -O2 artifacts/calibrate-tsc.c -o bin/controls/calibrate-tsc
taskset -c 4 bin/controls/calibrate-tsc > artifacts/tsc-cycles-per-ns.txt
cd run
LC_ALL=C taskset -c 4 hyperfine -N --warmup 10 --runs 2000 \
  --export-json ../artifacts/empty-controls.json \
  --command-name empty-c ../bin/controls/empty-c \
  --command-name empty-rust ../bin/controls/empty-rust \
  --command-name gnu-true /usr/bin/true \
  --command-name rust-single-true ../bin/single/true \
  > ../artifacts/empty-controls.log 2>&1
