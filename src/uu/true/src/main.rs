// This file is part of the uutils coreutils package.
//
// For the full copyright and license information, please view the LICENSE
// file that was distributed with this source code.

uucore::bin!(uu_true);

// Interpose only on the standalone C-ABI main entry. Help/version go through
// the compiler-generated main, including the normal Rust runtime setup.
#[cfg(all(
    feature = "startup-early-return",
    target_os = "linux",
    target_env = "musl",
    target_arch = "x86_64"
))]
mod early_return {
    use core::ffi::{CStr, c_char, c_int};

    unsafe extern "C" {
        fn __real_main(argc: c_int, argv: *const *const c_char) -> c_int;
    }

    /// Called by the musl CRT through the linker's --wrap=main mechanism.
    ///
    /// # Safety
    /// The CRT supplies argc valid argument pointers, each NUL-terminated.
    /// This function must use only operations that need no Rust runtime setup.
    #[unsafe(no_mangle)]
    pub unsafe extern "C" fn __wrap_main(argc: c_int, argv: *const *const c_char) -> c_int {
        if argc == 2 {
            // SAFETY: argc == 2 guarantees argv[1] is a valid C string. It is
            // borrowed only for this comparison; no allocation or std I/O occurs.
            let flag = unsafe { CStr::from_ptr(*argv.add(1)) }.to_bytes();
            if flag == b"--help" || flag == b"--version" {
                // SAFETY: forward the original CRT arguments to the original
                // compiler-generated main. That entry initializes Rust normally.
                return unsafe { __real_main(argc, argv) };
            }
        }
        // true ignores every other argument combination, including help or
        // version accompanied by another operand. There is no output to flush.
        0
    }
}

// This entry uses only the Linux x86-64 initial stack and a relative jump.
// In particular it accesses no GOT, TLS, heap, or unrelocated static pointers.
#[cfg(all(
    feature = "startup-raw-entry",
    target_os = "linux",
    target_env = "musl",
    target_arch = "x86_64"
))]
core::arch::global_asm!(include_str!("early_start.S"));
