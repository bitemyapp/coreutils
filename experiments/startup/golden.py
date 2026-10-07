#!/usr/bin/env python3
"""Behavior comparisons; run only on wx-workstation."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path('/home/callen/work/coreutils-startup-factorial')
ART = ROOT / 'artifacts'
WORK = ROOT / 'run/golden'
VARIANTS = ['baseline', 'lazy', 'musl', 'lazy-musl']
CASES = []
for args in [[], ['--help'], ['--version'], ['-h'], ['--bogus'],
             ['--help', 'extra'], ['--version', 'extra'],
             ['--help', '--version'], [b'\xff']]:
    CASES.append(('true', args, b'', {}))
for args in [
    ['src', 'new'], ['-s', 'src', 'new'], ['-sf', 'src', 'dst'],
    ['--sym', '--for', 'src', 'dst'], ['-svf', 'src', 'dst'],
    ['-srv', 'src', 'new'], ['-sfT', 'src', 'dst'],
    ['--backup=numbered', '-sf', 'src', 'dst'],
    ['--backup=simple', '--suffix=.bak', '-sf', 'src', 'dst'],
    ['-s', '-t', 'directory', 'src', 'other'],
    ['-s', 'src', 'directory'], ['-s', 'missing', 'new'],
    ['missing', 'new'], ['src', 'dst'], [], ['-T', 'src'],
    ['-T', 'src', 'other', 'new'], ['-r', 'src', 'new'],
    ['-t', 'missing', 'src'], ['-t', 'directory', '-T', 'src'],
    ['--definitely-invalid'], ['-s', 'src', 'new', '--definitely-invalid'],
    ['--help'], ['--he', 'src', 'new'], ['--version'],
    ['--backup=bad', 'src', 'new'], ['--s', 'src', 'new'],
    ['-s', '--', '-dash', 'new'], ['-s', b'\xff-source', 'new'],
    ['-sf', 'src', 'directory-link'], ['-sfn', 'src', 'directory-link'],
]:
    CASES.append(('ln', args, b'', {}))
CASES += [('ln', ['-si', 'src', 'dst'], answer, {}) for answer in [b'y\n', b'n\n']]
CASES += [('ln', ['-sf', 'src', 'dst'], b'', {'VERSION_CONTROL': 'bad'}),
          ('ln', ['--help'], b'', {'CLICOLOR_FORCE': '1'})]

def snapshot():
    result = {}
    for path in sorted(WORK.rglob('*')):
        name = str(path.relative_to(WORK))
        if path.is_symlink():
            result[name] = ['symlink', os.readlink(path)]
        elif path.is_dir():
            result[name] = ['dir']
        else:
            stat = path.stat()
            result[name] = ['file', hashlib.sha256(path.read_bytes()).hexdigest(),
                            stat.st_nlink, stat.st_mode & 0o777]
    return result

def run(variant, form, phase, lang, case):
    util, args, stdin, extra = case
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    for name in ['src', 'other', 'dst', '-dash', os.fsdecode(b'\xff-source')]:
        (WORK / name).write_text(name.encode('utf-8', 'backslashreplace').decode() + '\n')
    (WORK / 'directory').mkdir()
    (WORK / 'directory-link').symlink_to('directory')
    env = dict(os.environ, LANG=lang, LC_ALL='C', TZ='UTC', TERM='dumb')
    for name in ['LANGUAGE', 'VERSION_CONTROL', 'SIMPLE_BACKUP_SUFFIX',
                 'NO_COLOR', 'CLICOLOR_FORCE', 'FORCE_COLOR', 'LD_PRELOAD']:
        env.pop(name, None)
    env.update(extra)
    executable = ROOT / 'bin' / variant / form / util
    # Keep argv[0] identical: some diagnostics print the invocation verbatim.
    result = subprocess.run([util, *args], executable=executable,
                            cwd=WORK, env=env, input=stdin, capture_output=True)
    return dict(code=result.returncode,
                stdout=base64.b64encode(result.stdout).decode(),
                stderr=base64.b64encode(result.stderr).decode(), files=snapshot())

def collect(variant):
    records = {}
    for phase in ['embedded', 'external']:
        for form in ['single', 'multi']:
            locales = ROOT / 'bin' / variant / form / 'locales'
            assert not locales.exists(), locales
            if phase == 'external':
                locales.mkdir()
                for util in ['true', 'ln', 'uucore']:
                    src = ROOT / 'baseline/src' / ('uucore' if util == 'uucore' else f'uu/{util}') / 'locales'
                    (locales / util).symlink_to(src)
            try:
                for lang in ['C', 'fr-FR.UTF-8', 'invalid_locale']:
                    for index, case in enumerate(CASES):
                        key = f'{form}/{phase}/{lang}/{index}'
                        records[key] = run(variant, form, phase, lang, case)
            finally:
                if phase == 'external':
                    shutil.rmtree(locales)
    return records

if sys.argv[1] == 'capture':
    records = collect('baseline')
    (ART / 'golden-baseline.json').write_text(json.dumps(records, indent=2))
    (ART / 'golden-cases.json').write_text(json.dumps(
        [(u, [os.fsdecode(a) for a in args], stdin.decode(), env)
         for u, args, stdin, env in CASES], indent=2))
    digest = hashlib.sha256((ART / 'golden-baseline.json').read_bytes()).hexdigest()
    (ART / 'golden.sha256').write_text(digest + '  golden-baseline.json\n')
    print(f'Captured {len(records)} baseline behavior cases.', flush=True)
else:
    baseline = json.loads((ART / 'golden-baseline.json').read_text())
    failures = {}
    for variant in VARIANTS[1:]:
        records = collect(variant)
        mismatches = {k: {'baseline': baseline[k], 'actual': v}
                      for k, v in records.items() if v != baseline[k]}
        failures[variant] = mismatches
        print(f'{variant}: {len(records) - len(mismatches)}/{len(records)} equal', flush=True)
    (ART / 'golden-comparison.json').write_text(json.dumps(failures, indent=2))
    sys.exit(any(failures.values()))
