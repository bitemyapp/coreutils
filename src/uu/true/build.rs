// This file is part of the uutils coreutils package.
//
// For the full copyright and license information, please view the LICENSE
// file that was distributed with this source code.

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    let early = std::env::var_os("CARGO_FEATURE_STARTUP_EARLY_RETURN").is_some();
    let raw = std::env::var_os("CARGO_FEATURE_STARTUP_RAW_ENTRY").is_some();
    assert!(!(early && raw), "select only one startup entry experiment");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("linux")
        && std::env::var("CARGO_CFG_TARGET_ENV").as_deref() == Ok("musl")
        && std::env::var("CARGO_CFG_TARGET_ARCH").as_deref() == Ok("x86_64")
    {
        if early {
            println!("cargo:rustc-link-arg-bin=true=-Wl,--wrap=main");
        }
        if raw {
            println!("cargo:rustc-link-arg-bin=true=-Wl,-e,uutils_true_start");
        }
    }
}
