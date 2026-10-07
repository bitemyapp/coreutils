#!/usr/bin/env python3
"""Instruction and syscall profiles, separate from timing measurements."""
import json
import os
from pathlib import Path
import subprocess

BASE = Path('/home/callen/work/coreutils-startup-8cf2e4f4')
ART = BASE / 'artifacts'
os.chdir(BASE / 'run')
os.sched_setaffinity(0, {4})
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'
os.environ.pop('LANGUAGE', None)
VG = BASE / 'tools/valgrind/usr'
os.environ['VALGRIND_LIB'] = str(VG / 'libexec/valgrind')
cases = json.loads((ART / 'cases.json').read_text())
for name, cmd in cases.items():
    with (ART / f'{name}.callgrind.log').open('w') as log:
        subprocess.run([str(VG / 'bin/valgrind'), '--tool=callgrind',
            '--callgrind-out-file=' + str(ART / f'{name}.callgrind'), *cmd],
            stdout=log, stderr=subprocess.STDOUT, check=True)
    for inclusive in ['yes', 'no']:
        with (ART / f'{name}.instructions-{inclusive}.txt').open('w') as out:
            subprocess.run([str(VG / 'bin/callgrind_annotate'), '--auto=no',
                '--inclusive=' + inclusive, '--threshold=99', str(ART / f'{name}.callgrind')],
                stdout=out, stderr=subprocess.STDOUT, check=True)
    subprocess.run(['strace', '-qq', '-T', '-o', str(ART / f'{name}.strace'), *cmd], check=True)
    subprocess.run(['strace', '-qq', '-c', '-o', str(ART / f'{name}.syscalls'), *cmd], check=True)
    loader = []
    for _ in range(100):
        result = subprocess.run(cmd, env={**os.environ, 'LD_DEBUG': 'statistics'},
                                capture_output=True, text=True, check=True)
        loader.append(result.stderr)
    (ART / f'{name}.loader.json').write_text(json.dumps(loader, indent=2))
    with (ART / f'{name}.time-v.txt').open('w') as out:
        subprocess.run(['/usr/bin/time', '-v', *cmd], stdout=out, stderr=subprocess.STDOUT, check=True)
    with (ART / f'{name}.elf.txt').open('w') as out:
        for tool in [['stat', '-Lc', '%n %s bytes'], ['size'], ['readelf', '-dW'], ['readelf', '-lW']]:
            subprocess.run([*tool, cmd[0]], stdout=out, stderr=subprocess.STDOUT, check=True)
    print(name + ' profiled', flush=True)
