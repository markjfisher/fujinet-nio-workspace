#!/usr/bin/env python3
"""MyDOS BASIC reset check: the user initiates Reset in Altirra."""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import run_boot_acceptance as boot

READY = bytes.fromhex('3225212439')


def run(evidence_dir, wait_seconds):
    run_dir = evidence_dir.resolve() / 'netsio'
    observed = {}

    def drive(token, path):
        sys.path.insert(0, str(boot.SDK))
        from altirra_bridge import AltirraBridge
        with AltirraBridge.from_token_file(token) as b:
            module = (boot.ROOT / 'integration-tests/atari-sio/boot-app/build/nio.o65').read_bytes()
            code_len, initialized = boot._u16(module, 32), boot._u16(module, 16)

            def snapshot(name):
                install = b.peek(0x9380, 40)
                start, end = boot._u16(install, 12), boot._u16(install, 14)
                state = {'regs': b.regs(), 'warmst': b.peek(8)[0],
                         'memlo': b.peek16(0x2e7), 'memtop': b.peek16(0x2e5),
                         'hatabs': b.peek(boot.HATABS_ADDR, boot.HATABS_TOTAL_BYTES).hex(),
                         'iocb1': b.peek(0x350, 16).hex(),
                         'owners': b.peek(start + initialized, 32).hex(),
                         'resident_start': start, 'resident_end': end,
                         'resident_code_sha256': hashlib.sha256(b.memdump(start, code_len)).hexdigest()}
                (path / (name + '.json')).write_text(json.dumps(state, indent=2) + '\n')
                (path / (name + '.png')).write_bytes(b.screenshot())
                observed[name] = state
                return state

            for _ in range(160):
                b.frame(50)
                if READY in b.peek(b.peek16(0x58), 960) and b.peek(0x9380, 6) == b'NRI!\x02\x00':
                    break
            else:
                raise RuntimeError('MyDOS did not reach BASIC READY with N: installed')
            before = snapshot('manual-before')
            keys = boot._type_atari_command(b, 'LOAD "D:FNRESET.BAS"')
            (path / 'manual-load-keys.json').write_text(json.dumps(keys, indent=2) + '\n')
            fixture = (boot.ROOT / 'integration-tests/atari-sio/boot-app/build/fnreset.bas').read_bytes()
            offset = 14 + boot._u16(fixture, 8) - boot._u16(fixture, 2)
            size = boot._u16(fixture, 10) - boot._u16(fixture, 8)
            program = fixture[offset:offset + size]
            for _ in range(60):
                b.frame(20)
                if program and b.memdump(b.peek16(0x88), size) == program:
                    break
            else:
                raise RuntimeError('BASIC did not load the exact FNRESET.BAS program')
            (path / 'manual-loaded.png').write_bytes(b.screenshot())
            hub_offset = (path / 'hub.log').stat().st_size
            nio_offset = (path / 'nio.log').stat().st_size
            b.poke(0x6e4, 0)
            keys = boot._type_atari_command(b, 'RUN')
            (path / 'manual-run-keys.json').write_text(json.dumps(keys, indent=2) + '\n')
            for _ in range(60):
                b.frame(30)
                marker = b.peek(0x6e4)[0]
                if marker in (0xad, 0xee):
                    break
            else:
                raise RuntimeError('FNRESET.BAS did not reach its reset prompt')
            if marker != 0xad:
                raise RuntimeError('FNRESET.BAS could not open N:')
            prompt = snapshot('manual-prompt')
            if 0x10 not in bytes.fromhex(prompt['owners'])[::16] or bytes.fromhex(prompt['iocb1'])[0] == 0xff:
                raise RuntimeError('FNRESET.BAS did not leave IOCB #1 open')
            print('Atari is ready: use Altirra System > Warm Reset (or its Warm Reset shortcut).',
                  file=sys.stderr, flush=True)
            print(f'Evidence: {evidence_dir}', file=sys.stderr, flush=True)
            b.resume()
            deadline = time.monotonic() + wait_seconds if wait_seconds else None
            event = None
            while deadline is None or time.monotonic() < deadline:
                with (path / 'hub.log').open('rb') as log:
                    log.seek(hub_offset)
                    tail = log.read().decode(errors='replace')
                reset = re.search(r'HOST (WARM|COLD) RESET', tail)
                if reset:
                    event = reset.group(1).lower() + '_reset'
                    break
                time.sleep(0.25)
            if not event:
                b.pause()
                snapshot('manual-timeout')
                raise TimeoutError(f'No user reset was observed in {wait_seconds:g} seconds')
            observed['reset_event'] = event
            # FNRESET clears the screen before printing the prompt, so READY
            # here must have appeared after the observed reset, not before RUN.
            for _ in range(200):
                b.frame(50)
                if READY in b.peek(b.peek16(0x58), 960) and b.peek(0x9380, 5) == b'NRI!\x02':
                    break
            else:
                raise RuntimeError('Reset did not return to MyDOS BASIC READY')
            after = snapshot('manual-after')
            trace = (path / 'nio.log').read_bytes()[nio_offset:].decode(errors='replace')
            observed['network_reclaimed'] = ('Atari host reset reclaiming NetworkDevice sessions' in trace and
                                             'Network fixture close count=1' in trace)
            observed['output_written'] = ('Network fixture write count=' in trace or
                                          'fixture committed body' in trace)
            observed['integrity'] = (after['memlo'] == before['memlo'] and
                                     after['hatabs'] == before['hatabs'] and
                                     after['resident_code_sha256'] == before['resident_code_sha256'])
            owners = bytes.fromhex(after['owners'])[::16]
            observed['ownership_consistent'] = ((0x10 in owners) ==
                                                (bytes.fromhex(after['iocb1'])[0] != 0xff))
            observed['os_start'] = 'warm' if after['warmst'] else 'cold'
            if observed['integrity'] and observed['ownership_consistent']:
                if 0x10 in owners:
                    boot._type_atari_command(b, 'CLOSE #1')
                    b.frame(100)
                b.poke(0x6e0, 0)
                boot._type_atari_command(b, 'OPEN #1,4,0,"N1:fixture://resident-open"')
                b.frame(100)
                boot._type_atari_command(b, 'GET #1,A')
                boot._type_atari_command(b, 'POKE 1760,A')
                boot._type_atari_command(b, 'CLOSE #1')
                b.frame(100)
                observed['reopened_byte'] = b.peek(0x6e0)[0]
                recovered = snapshot('manual-recovered')
                trace = (path / 'nio.log').read_bytes()[nio_offset:].decode(errors='replace')
                commands = tuple(int(value) for value in re.findall(
                    r'NetworkDevice routed request \d+ command=(\d+)', trace))
                expected = (1, 4, 1, 2, 4) if 0x10 in owners else (1, 1, 2, 4)
                observed['network_commands'] = commands
                observed['reopened_cleanly'] = (observed['reopened_byte'] == ord('N') and
                    commands == expected and
                    bytes.fromhex(recovered['owners'])[::16] == b'\xff\xff' and
                    recovered['resident_code_sha256'] == before['resident_code_sha256'] and
                    recovered['hatabs'] == before['hatabs'] and recovered['memlo'] == before['memlo'])
            else:
                observed['reopened_cleanly'] = False

    result = boot.run_netsio(0.1, evidence_dir=evidence_dir, trace_serial=True, basic=True,
        explicit_cold_reset=True, boot_atr=boot.RESIDENT_O65_MYDOS_BASIC_ATR,
        sidecar=boot.PUBLIC_API_CLOCK_ENDPOINT,
        sidecar_args=('--host', '127.0.0.1', '--port', '9997', '--storage-root',
                      str(run_dir / 'fujinet-data'), '--boot-atr'),
        sidecar_ready='Atari public-API Clock/File/Network/Disk acceptance initialized',
        after_launch=drive, inspector=lambda token, path: {'manual_reset': observed})
    result['outcome'] = ('pass' if observed['reset_event'] == 'warm_reset' and
                         observed['os_start'] == 'warm' and observed['integrity'] and
                         observed['ownership_consistent'] and observed['network_reclaimed'] and
                         observed['reopened_cleanly'] and not observed['output_written'] else 'incomplete')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-seconds', type=float, default=300,
                        help='time to wait for your reset; 0 waits indefinitely (default: 300)')
    parser.add_argument('--evidence-dir', type=Path, default=Path('test-evidence/atari-sio-manual-warm-reset'))
    args = parser.parse_args()
    if args.wait_seconds < 0:
        parser.error('--wait-seconds must be nonnegative')
    evidence = boot.make_evidence_dir(args.evidence_dir)
    try:
        result = run(evidence, args.wait_seconds)
    except Exception as exc:
        result = {'outcome': 'failure', 'error': str(exc), 'evidence_dir': str(evidence)}
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['outcome'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
