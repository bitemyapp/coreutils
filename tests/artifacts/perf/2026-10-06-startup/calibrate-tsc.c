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
