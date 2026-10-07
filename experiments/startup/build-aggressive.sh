#!/usr/bin/env bash
# Run on wx-workstation. Each stage snapshots binaries for an ablation comparison.
set -euo pipefail
cd "$(dirname "$0")/../.."
base=${STARTUP_EXPERIMENT_ROOT:-/home/callen/work/coreutils-startup-factorial}
stage=${1:?stage name required}
export LANG=en_US.UTF-8
export CARGO_TARGET_DIR="$base/target-aggressive"
export CARGO_PROFILE_RELEASE_DEBUG=1
export CARGO_BUILD_JOBS=24
export CC_x86_64_unknown_linux_musl="$base/tools/musl-gcc"
export RUSTFLAGS="-C force-frame-pointers=yes"
if [[ "${STARTUP_RELR:-0}" == 1 ]]; then
    RUSTFLAGS+=" -C link-arg=-Wl,-z,pack-relative-relocs"
fi
target=x86_64-unknown-linux-musl
mkdir -p "$base/bin/$stage/single" "$base/bin/$stage/multi"
for util in true ln; do
    extra=()
    if [[ "$util" == true && "$stage" == aggressive ]]; then
        extra+=(--features startup-early-return)
    fi
    cargo build --locked --release --target "$target" -p "uu_$util" --bin "$util" "${extra[@]}"
    cp "$CARGO_TARGET_DIR/$target/release/$util" "$base/bin/$stage/single/$util"
done
cargo build --locked --release --target "$target" --features feat_os_unix_musl --bin coreutils
cp "$CARGO_TARGET_DIR/$target/release/coreutils" "$base/bin/$stage/multi/coreutils"
for util in true ln; do ln -sfn coreutils "$base/bin/$stage/multi/$util"; done
sha256sum "$base/bin/$stage/single/"* "$base/bin/$stage/multi/coreutils"
