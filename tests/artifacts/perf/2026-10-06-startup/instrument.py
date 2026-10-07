#!/usr/bin/env python3
"""Apply measurement-only probes to the disposable remote source copy."""
from pathlib import Path
import subprocess

BASE = Path('/home/callen/work/coreutils-startup-8cf2e4f4')
SOURCE = BASE / 'source'
ART = BASE / 'artifacts'

def replace(path, old, new):
    target = SOURCE / path
    original = target.read_text()
    assert original.count(old) == 1, (path, old, original.count(old))
    backup = ART / ('original-' + path.replace('/', '_'))
    if not backup.exists():
        backup.write_text(original)
    target.write_text(original.replace(old, new))

replace('src/bin/coreutils.rs', 'fn main() {\n    let utils', '''fn main() {
    let startup_profile = std::env::var_os("UUTILS_STARTUP_PROFILE").is_some();
    let startup_begin = std::time::Instant::now();
    let utils''')
replace('src/bin/coreutils.rs', '''            validation::setup_localization_or_exit(util);
            exit(uumain(vec![util_os].into_iter().chain(args)));''', '''            let dispatch_done = std::time::Instant::now();
            validation::setup_localization_or_exit(util);
            let locale_done = std::time::Instant::now();
            let code = uumain(vec![util_os].into_iter().chain(args));
            let utility_done = std::time::Instant::now();
            if startup_profile {
                eprintln!("STARTUP dispatch_ns={} localization_ns={} utility_ns={}",
                    dispatch_done.duration_since(startup_begin).as_nanos(),
                    locale_done.duration_since(dispatch_done).as_nanos(),
                    utility_done.duration_since(locale_done).as_nanos());
            }
            exit(code);''')
replace('src/uucore/src/lib/lib.rs', '''        pub fn main() {
            use std::io::Write;''', '''        pub fn main() {
            let startup_profile = std::env::var_os("UUTILS_STARTUP_PROFILE").is_some();
            let startup_begin = std::time::Instant::now();
            use std::io::Write;''')
replace('src/uucore/src/lib/lib.rs', '''            locale::setup_localization(uucore::get_canonical_util_name(stringify!($util)))''', '''            let dispatch_done = std::time::Instant::now();
            locale::setup_localization(uucore::get_canonical_util_name(stringify!($util)))''')
replace('src/uucore/src/lib/lib.rs', '''            // execute utility code
            let code = $util::uumain(uucore::args_os());
            $post

            std::process::exit(code);''', '''            // Measurement only; retain the utility's normal work and exit.
            let locale_done = std::time::Instant::now();
            let code = $util::uumain(uucore::args_os());
            let utility_done = std::time::Instant::now();
            $post
            let flush_done = std::time::Instant::now();
            if startup_profile {
                eprintln!("STARTUP dispatch_ns={} localization_ns={} utility_ns={} flush_ns={}",
                    dispatch_done.duration_since(startup_begin).as_nanos(),
                    locale_done.duration_since(dispatch_done).as_nanos(),
                    utility_done.duration_since(locale_done).as_nanos(),
                    flush_done.duration_since(utility_done).as_nanos());
            }
            std::process::exit(code);''')
with (ART / 'instrumentation.patch').open('w') as diff:
    for path in ['src/bin/coreutils.rs', 'src/uucore/src/lib/lib.rs']:
        subprocess.run(['diff', '-u', str(ART / ('original-' + path.replace('/', '_'))),
                        str(SOURCE / path)], stdout=diff, check=False)
