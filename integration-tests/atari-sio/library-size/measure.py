#!/usr/bin/env python3
"""Rebuild identical Atari clients against a chosen archive and retain maps.

Source scripts/env.sh first. Output directories must be different for each
backend. Attribution comes from linked archive members, not archive file size.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LIB = ROOT / 'repos/fujinet-nio-lib'
APPS = ROOT / 'repos/nio-core-apps'
sys.path.insert(0, str(HERE.parent))
from fnaccept_memory_layout import parse_map, validate_link_layout
spec = importlib.util.spec_from_file_location('map_analysis', LIB / 'scripts/app_map_analysis.py')
analysis = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analysis
spec.loader.exec_module(analysis)


def measure(name, output, archive):
    stem = output / name
    source = APPS / 'apps/platform/atari/fnaccept.c' if name == 'fnaccept' else HERE / (name + '.c')
    subprocess.run(['cl65', '-t', 'atari', '-c', '-Osir', '-O', '-I', str(LIB / 'include'),
                    '-o', str(stem.with_suffix('.o')), str(source)], check=True)
    subprocess.run(['cl65', '-t', 'atari', '--config', str(APPS / 'makefiles/cc65-atari-nio.cfg'),
                    '--start-addr', '0x0D00', '-m', str(stem.with_suffix('.map')),
                    '-Ln', str(stem.with_suffix('.lbl')), '-o', str(stem.with_suffix('.xex')),
                    str(stem.with_suffix('.o')), str(archive)], check=True)
    segments = parse_map(stem.with_suffix('.map'))
    modules = analysis.parse_modules(stem.with_suffix('.map'))
    groups = {key: {} for key in ('app', 'library', 'runtime', 'other')}
    for module in modules:
        category = ('library' if str(archive) + '(' in module.name else
                    'runtime' if '.lib(' in module.name else
                    'app' if Path(module.name).name == name + '.o' else 'other')
        for segment, size in module.segments.items():
            groups[category][segment] = groups[category].get(segment, 0) + size
    for segment, (start, end) in segments.items():
        attributed = sum(group.get(segment, 0) for group in groups.values())
        if attributed != end - start:
            raise RuntimeError(f'{name}: {segment} attribution {attributed} != {end-start}')
    main_start = segments['STARTUP'][0]
    main_end = segments['BSS'][1]
    fixed_application = 384 if name == 'fnaccept' else 0
    result = {
        'xex_bytes': stem.with_suffix('.xex').stat().st_size,
        'xex_sha256': hashlib.sha256(stem.with_suffix('.xex').read_bytes()).hexdigest(),
        'segments': {key: {'start': start, 'end_exclusive': end, 'bytes': end-start}
                     for key, (start, end) in segments.items()},
        'linked_code_data_bytes': sum(end-start for key, (start, end) in segments.items()
                                      if key in ('CODE', 'RODATA', 'DATA')),
        'main_occupied_range': [main_start, main_end],
        'main_footprint_bytes': main_end-main_start,
        'zero_page_bytes': segments['ZEROPAGE'][1]-segments['ZEROPAGE'][0],
        'software_stack_reserved_bytes': 2048,
        'fixed_application_workspace_bytes': fixed_application,
        'total_ram_bytes': main_end-main_start + segments['ZEROPAGE'][1]-segments['ZEROPAGE'][0] + 2048 + fixed_application,
        'attribution': groups,
        'modules': [{'name': module.name, 'segments': module.segments} for module in modules],
    }
    if name == 'fnaccept':
        validate_link_layout(stem.with_suffix('.map'), stem.with_suffix('.xex'))
    return result


def provenance():
    """Identify dirty inputs separately from the repositories' committed HEADs."""
    repositories = {}
    for repo in ('.', 'repos/fujinet-nio-lib', 'repos/nio-core-apps', 'repos/cc65'):
        command = ['git', '-C', str(ROOT / repo)]
        repositories[repo] = {
            'head': subprocess.check_output(command + ['rev-parse', 'HEAD'], text=True).strip(),
            'status_porcelain': subprocess.check_output(
                command + ['status', '--porcelain=v1', '--untracked-files=all'], text=True),
            'tracked_diff_sha256': hashlib.sha256(subprocess.check_output(
                command + ['diff', '--binary', 'HEAD', '--'])).hexdigest(),
        }
    inputs = {Path(__file__).resolve(), HERE / 'clock.c', HERE / 'empty.c',
              HERE.parent / 'fnaccept_memory_layout.py',
              LIB / 'scripts/app_map_analysis.py', LIB / 'Makefile',
              APPS / 'apps/platform/atari/fnaccept.c',
              APPS / 'makefiles/cc65-atari-nio.cfg',
              ROOT / 'repos/cc65/lib/atari.lib'}
    for directory in (LIB / 'include', LIB / 'src', LIB / 'makefiles'):
        inputs.update(path for path in directory.rglob('*') if path.is_file())
    for executable in ('cl65', 'cc65', 'ca65', 'ld65'):
        path = shutil.which(executable)
        if path:
            inputs.add(Path(path).resolve())
    hashes = {}
    for path in sorted(inputs):
        label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        hashes[label] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'repositories': repositories, 'input_sha256': hashes,
            'input_manifest_sha256': hashlib.sha256(
                json.dumps(hashes, sort_keys=True).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    archive, output = args.archive.resolve(), args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('--output must be absent or an empty directory; existing evidence is never overwritten')
    archive_bytes = archive.read_bytes()
    output.mkdir(parents=True, exist_ok=True)
    preserved_archive = output / 'selected-archive.lib'
    preserved_archive.write_bytes(archive_bytes)
    report = {'archive_source': str(archive), 'archive': str(preserved_archive),
              'archive_sha256': hashlib.sha256(archive_bytes).hexdigest(),
              'cc65': subprocess.check_output(['cl65', '--version'], stderr=subprocess.STDOUT, text=True).strip(),
              'provenance': provenance(),
              'clients': {name: measure(name, output, preserved_archive) for name in ('empty', 'clock', 'fnaccept')}}
    empty = report['clients']['empty']
    for name in ('clock', 'fnaccept'):
        client = report['clients'][name]
        client['incremental_over_empty'] = {key: client[key]-empty[key] for key in ('xex_bytes', 'linked_code_data_bytes', 'total_ram_bytes')}
        # Exact linked library cost, plus additional runtime linked beyond empty.
        client['incremental_nio_library_bytes'] = sum(client['attribution']['library'].values())
        client['extra_runtime_over_empty_bytes'] = sum(client['attribution']['runtime'].values()) - sum(empty['attribution']['runtime'].values())
    (output / 'measurement.json').write_text(json.dumps(report, indent=2) + '\n')
    print(output / 'measurement.json')

if __name__ == '__main__':
    main()
