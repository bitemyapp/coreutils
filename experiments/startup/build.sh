#!/usr/bin/env bash
# Run via ssh wx-workstation, from this worktree.
set -euo pipefail
cd "$(dirname "$0")/../.."
variant=$(cat experiments/startup/variant)
if [[ "$variant" == aggressive ]]; then
    exec bash experiments/startup/build-aggressive.sh aggressive
fi
base=${STARTUP_EXPERIMENT_ROOT:-/home/callen/work/coreutils-startup-factorial}
target=x86_64-unknown-linux-gnu
if [[ "$variant" == *musl ]]; then
    target=x86_64-unknown-linux-musl
    export CC_x86_64_unknown_linux_musl="$base/tools/musl-gcc"
fi
export CARGO_TARGET_DIR="$base/target-$variant"
export LANG=en_US.UTF-8
export CARGO_PROFILE_RELEASE_DEBUG=1
export CARGO_BUILD_JOBS=24
export RUSTFLAGS="-C force-frame-pointers=yes"
mkdir -p "$base/bin/$variant/single" "$base/bin/$variant/multi"
# Separate invocations keep standalone dependency features isolated.
for util in true ln; do
    cargo build --locked --release --target "$target" -p "uu_$util" --bin "$util"
    cp "$CARGO_TARGET_DIR/$target/release/$util" "$base/bin/$variant/single/$util"
done
# Identical utility set for both libc targets: excludes unsupported musl stdbuf.
cargo build --locked --release --target "$target" --features feat_os_unix_musl --bin coreutils
cp "$CARGO_TARGET_DIR/$target/release/coreutils" "$base/bin/$variant/multi/coreutils"
for util in true ln; do ln -sfn coreutils "$base/bin/$variant/multi/$util"; done
sha256sum "$base/bin/$variant/single/"* "$base/bin/$variant/multi/coreutils"
