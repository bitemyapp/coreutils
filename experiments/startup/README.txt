Four-way startup experiment
===========================
Base revision: 8cf2e4f4ab613947b955f442c750df9d53d17b08.
All builds, tests, timings, and profiles run on ssh wx-workstation.
The variant file selects baseline, lazy, musl, or lazy-musl.
Run bash experiments/startup/build.sh from the corresponding remote worktree.
The default experiment root is /home/callen/work/coreutils-startup-factorial.
The musl compiler wrapper for native C dependencies lives at tools/musl-gcc.
It uses privately extracted Ubuntu musl development packages; no system packages
were replaced. rustc supplies the target's static Rust runtime and libc.

Controlled inputs
- Rust 1.94.1; locked dependencies; release opt-level 3, fat LTO, one codegen unit,
  panic=abort; debug=1 and force-frame-pointers=yes for all four variants.
- Standalone true and ln built in separate Cargo invocations, without multicall
  feature unification. The copied binaries are measured, not overwritten outputs.
- Multicall has the same feat_os_unix_musl feature set in every variant. This
  excludes stdbuf, which cannot be built for static musl. All other source changes
  are confined to the lazy variants. ASLR remains enabled (PIE/static PIE).
- No PGO, CPU tuning, cache dropping, or privileged profiling.
- Warm-cache hyperfine -N; CPU 4; LANG=LC_ALL=C; 8 randomized blocks, 1000 launches
  per case per block, 20 warmups. GNU true/ln are included in each block.
- true: no arguments. ln: -s -f src.txt dst.txt, replacing the same symlink.
- The machine is shared. Keep builds/tests/profiles separate from timings.

Lazy variant scope and behavior
Only true/ln entry points defer localization. ln constructs the same argument
schema without translated help strings; on any parse error/help/version request,
it reparses with the original complete metadata before filesystem effects.
Normal success paths use the original utility implementations. No syscall fast
path, custom runtime, changed overwrite algorithm, or GNU source is involved.

Ordering and compatibility
Argument ordering, overrides, tie breaking, filenames, filesystem operations,
exit statuses, and rendered messages are unchanged for valid locale assets.
Floating-point and RNG behavior are not involved. The caller's original
localization error handler is retained. Locale environment/files are observed
when first needed, so concurrent changes to locale assets can be observed at a
different point in execution. A fatal initialization error, if any, is likewise
deferred. An additional damaged-external-locale check matched baseline: the
existing implementation already falls back to embedded English for that case.
This is an experimental branch, not a claim of suite-wide or cross-platform
compatibility beyond the tested true/ln paths.

Validation
42 locale unit tests pass on GNU and musl targets, including deferred setup,
alias preservation, and switching utility contexts on one thread. 69 true/ln
integration tests pass against each standalone and multicall variant. Golden
comparison covers 528 cases per experimental variant, checking exit code,
stdout, stderr, and filesystem state with identical argv[0]. It includes C,
French, invalid locale selection, embedded/external assets, invalid UTF-8 names,
help/version, invalid/abbreviated options, backups, prompts, and parse-before-I/O.
All 528 match baseline in each of lazy, musl, lazy-musl; SHA-256 verifies the
baseline golden file. cargo fmt --all --check and targeted clippy complete;
this installed compiler warns about the repository's unknown assert_is_empty lint.

Scripts
build.sh is the build recipe. golden.py captures/compares behavior. measure.py
runs timings and block bootstrap. profile.py gathers Callgrind, strace, ELF,
and resource data without source annotation. Scripts intentionally use the
remote experiment root. Results and raw artifacts are stored outside sources
at that root's artifacts directory and synced to the original checkout under
tests/artifacts/perf/2026-10-06-factorial.

Rollback: these are isolated experiment branches; main is unchanged. Revert
the lazy-initialization commit to remove the source experiment.
