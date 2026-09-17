import pytest
from pathlib import Path
import re
import time

from conftest import native_test_map_omits_serial_session_slip

ROOT = Path(__file__).resolve().parents[2]


def test_native_test_clock_exchange(run_amiga_case):
    results = run_amiga_case("nio-native-test")

    assert "LOAD RC=0" in results["nio-load.result"].splitlines()
    probe = results["nio-native-test.result"]
    assert "IDENTITY=native-test" in probe
    assert "SET_BAUD io=0 nio=8" in probe
    assert "EXCHANGE io=0 nio=0" in probe
    assert "CLOCK cmd=1" in probe
    assert "PASS native-test-clock" in probe
    assert "TOOL RC=0" in results["nio-tool-rc.result"].splitlines()
    map_path = ROOT / (
        "repos/fujinet-nio-driver/build/amiga/"
        "fujinet-nio-native-test.device.map"
    )
    assert map_path.is_file()
    assert native_test_map_omits_serial_session_slip(
        map_path.read_text(encoding="ascii", errors="ignore")
    )


def test_native_exchange_tool_read_only(run_amiga_case, amiga_evidence_root):
    started = int(time.time())
    results = run_amiga_case("nio-native-exchange")
    finished = int(time.time())
    assert "SEED RC=0" in results["nio-seed.result"].splitlines()
    assert "LOAD RC=0" in results["nio-load.result"].splitlines()
    invalid = [text for name, text in results.items() if name.startswith("bad-")]
    assert len(invalid) == 13
    for text in invalid:
        # Usage returns 10; an attempted OpenDevice failure returns 20.
        # stderr is not redirected, so stdout absence alone proves nothing.
        assert "RC=10" in text.splitlines(), text
        assert "req_len=" not in text
    # Responses include the 6-byte FujiBus header and one U8 status parameter.
    # Each list has one full entry: 10-byte list
    # header, 2-byte flags/name length, name, and 16-byte size/mtime.
    for name, request_length, response_length in (
        ("nio-clock.result", 6, 6 + 1 + 12),
        ("nio-list.result", 19, 6 + 1 + 10 + 2 + len("native-exchange.txt") + 16),
    ):
        text = results[name]
        assert "installed_backend=native lifecycle=warm" in text
        assert "RC=0" in text.splitlines()
        trials = [line for line in text.splitlines() if line.startswith("req_len=")]
        assert len(trials) == 2, text
        for trial in trials:
            assert f"req_len={request_length} resp_len={response_length} " in trial
            assert "result=0 cause=0 native=0 status=0 backend=warm" in trial
        for failure in ("GET_BAUD", "SET_BAUD", "GET_SERIAL", "SET_SERIAL",
                        "WARMUP io=", "fujibus=bad", "Cannot open"):
            assert failure not in text
    records = amiga_evidence_root / "nio-native-exchange" / "native-test-records"
    assert (records / "host-fs/native-exchange.txt").read_text() == "seed\n"
    assert (records / "complete").read_text().strip() == "PASS"

    # Independently inspect real service payloads from the host endpoint log.
    # Six clocks include four warmups; two lists are measured operations.
    host_log = (records.parent / "fujinet-nio-native-test.log").read_text()
    receives = re.findall(r"fujibus: receive: .*dev=(0x[0-9A-Fa-f]+) cmd=(0x[0-9A-Fa-f]+)", host_log)
    assert receives == [("0x45", "0x01")] * 5 + [
        ("0xFE", "0x02"), ("0x45", "0x01"), ("0xFE", "0x02")]
    replies = re.findall(
        r"fujibus: send: dev=(0x[0-9A-Fa-f]+) status=(\d+) cmd=(0x[0-9A-Fa-f]+) payload=(\d+)(.*?)(?=fujibus: receive:|native-test: fujinet-nio-native-test exiting|\Z)",
        host_log, re.S,
    )
    assert len(replies) == 8
    for device, status, command, length, dump in replies:
        assert status == "0"
        payload = bytes.fromhex(" ".join(re.findall(r"fujibus:   [0-9a-f]{4}: ([0-9a-f ]+)\|", dump)))
        assert len(payload) == int(length)
        if device == "0x45":
            assert command == "0x01" and len(payload) == 12
            assert payload[:4] == bytes([1, 0, 0, 0])
            assert started <= int.from_bytes(payload[4:12], "little") <= finished
        else:
            assert device == "0xFE" and command == "0x02"
            filename = b"native-exchange.txt"
            entry_length = 2 + len(filename) + 16
            assert payload[:10] == bytes([1, 0, 0, 0, 0, 0, 1, 0, entry_length, 0])
            assert payload[10:12] == bytes([0, len(filename)])
            assert payload[12:12 + len(filename)] == filename
            assert int.from_bytes(payload[12 + len(filename):20 + len(filename)], "little") == 5
            assert len(payload) == 10 + entry_length


def test_native_exchange_tool_disk(run_amiga_case, amiga_evidence_root):
    results = run_amiga_case("nio-native-disk")
    for name, text in results.items():
        if name.startswith("bad-"):
            assert "RC=10" in text.splitlines(), (name, text)
            assert "ordinary" not in text
    for name in ("nio-load", "disk-load", "disk-unload", "disk-reload"):
        assert "RC=0" in results[f"{name}.result"].splitlines()
    for name, trials in (("disk-read", 2), ("disk-write", 3)):
        text = results[f"{name}.result"]
        assert "RC=0" in text.splitlines(), text
        assert f"ORDINARY PASS completed_trials={trials} failure=none" in text
        assert "FIXTURE LEFT MOUNTED" in text
        assert "result=0 cause=0 native=0 status=0" in text
        assert "io_Error=0 io_Actual=512" in text
        for serial in ("GET_BAUD", "SET_BAUD", "GET_SERIAL", "SET_SERIAL", "pacing="):
            assert serial not in text
    for name, failure in (("occupied-local", "local-slot-occupied"),
                          ("occupied-remote", "remote-slot-occupied"),
                          ("missing-fixture", "mount"),
                          ("bounds", "geometry-bounds")):
        text = results[f"{name}.result"]
        assert "RC=20" in text.splitlines(), text
        assert f"failure={failure}" in text
        assert "ordinary op=write " not in text
        assert ("FIXTURE LEFT MOUNTED" in text) == (name == "bounds")
    assert "ordinary op=local-state slot=1 lba=17 io_Error=0 io_Actual=1" in results["occupied-remote.result"]
    run = amiga_evidence_root / "nio-native-disk"
    host = run / "native-test-records" / "host-fs"
    read_bytes = (run / "read-original.adf").read_bytes()[17 * 512:18 * 512]
    expected_digest = 2166136261
    for value in read_bytes:
        expected_digest = ((expected_digest ^ value) * 16777619) & 0xffffffff
    actual_digests = re.findall(r"ordinary read trial=(\d+) checksum_fnv1a32=([0-9a-f]{8})", results["disk-read.result"])
    assert actual_digests == [(str(trial), f"{expected_digest:08x}") for trial in (1, 2)]
    assert "FIXTURE STATE UNKNOWN" in results["missing-fixture.result"]
    for fixture in ("read", "bounds"):
        assert (host / f"{fixture}.adf").read_bytes() == (run / f"{fixture}-original.adf").read_bytes()
    expected = bytearray((run / "write-original.adf").read_bytes())
    # Third (zero-based trial 2) pattern, independently specified here.
    expected[17 * 512:18 * 512] = bytes(
        ((i ^ 0x5a) ^ (2 >> ((i % 4) * 8))) & 255 for i in range(512)
    )
    assert (host / "write.adf").read_bytes() == expected
    assert sorted(p.name for p in host.iterdir()) == ["bounds.adf", "fujinet-runtime-mounts.tsv", "read.adf", "write.adf"]
    log = (run / "fujinet-nio-native-test.log").read_text()
    requests = re.findall(r"fujibus: receive: .*dev=(0x[0-9A-Fa-f]+) cmd=(0x[0-9A-Fa-f]+)", log)
    # Real host handler calls, not tool summaries: exactly three writes; no replay.
    disk = [(int(dev, 16), int(cmd, 16)) for dev, cmd in requests]
    assert all(dev == 0xfc for dev, _ in disk), disk
    assert sum(cmd == 4 for _, cmd in disk) == 3
    assert sum(cmd == 0x0e for _, cmd in disk) == 5  # two writable mounts + three trials
    commands = [cmd for _, cmd in disk]
    first_write = commands.index(4)
    assert commands[first_write:] == [4, 0x0e, 3] * 3
    assert sum(cmd == 3 for _, cmd in disk) == 5
    assert sum(cmd == 1 for _, cmd in disk) == 4
    assert not any(cmd == 2 for _, cmd in disk)  # no raw unmount/eject
    assert (run / "native-test-records" / "complete").read_text() == "PASS\n"


@pytest.mark.parametrize("fault", ["hold", "drop"])
def test_native_fault_isolation(run_amiga_case, amiga_evidence_root, fault):
    name = f"nio-native-fault-{fault}"
    results = run_amiga_case(name)
    if fault == "hold":
        assert "LATE actual-reply-visible=1" in results["nio-fault.result"]
    assert "QUEUED completions=2 isolated=1" in results["nio-fault.result"]
    assert "RETRY rc=16 length=0" in results["nio-fault.result"]
    assert "RECOVERY first-write-only=1" in results["nio-fault.result"]
    assert "FRESH same-command-lba18=1" in results["nio-fault.result"]
    assert re.search(r"RESIDENT retries=\d+ error=-?\d+ actual=0 isolated=1", results["nio-fault.result"])
    assert "RESIDENT recovered=1" in results["nio-fault.result"]
    assert "PASS native-fault" in results["nio-fault.result"]
    run = amiga_evidence_root / name
    expected = bytearray((run / "fault-original.adf").read_bytes())
    expected[17 * 512:18 * 512] = bytes((i + 0x31) & 255 for i in range(512))
    expected[18 * 512:19 * 512] = bytes((i + 0x71) & 255 for i in range(512))
    records = run / "native-test-records"
    assert (records / "host-fs/fault.adf").read_bytes() == expected
    log = (run / "fujinet-nio-native-test.log").read_text()
    requests = re.findall(r"fujibus: receive: .*dev=(0x[0-9A-Fa-f]+) cmd=(0x[0-9A-Fa-f]+)", log)
    assert requests[:7] == [("0xFC", "0x01"), ("0xFC", "0x04"), ("0xFC", "0x0E"), ("0xFC", "0x03"), ("0xFC", "0x04"), ("0xFC", "0x0E"), ("0xFC", "0x03")]
    assert requests[7:].count(("0xFC", "0x04")) == 1  # actual resident retry loop sent once
    resident = bytearray((run / "resident-original.adf").read_bytes())
    resident[17 * 512:18 * 512] = bytes((i + 0x91) & 255 for i in range(512))
    assert (records / "host-fs/resident.adf").read_bytes() == resident
    assert f"native-test actual reply {fault}" in log
    assert "native-test barrier drained" in log
    assert not (records / "AMBIGUOUS").exists()
    assert not (records / "RECOVER").exists()


@pytest.mark.parametrize("installation", ["serial", "native"])
def test_exchange_tool_installation_parity(run_amiga_case, amiga_evidence_root, installation):
    started = int(time.time())
    results = run_amiga_case("nio-tool-parity", installation=installation)
    finished = int(time.time())
    for name, text in results.items():
        assert "RC=0" in text.splitlines(), (name, text)
    for kind, response_length in (("clock", 19), ("list", 45)):
        text = results[f"parity-{kind}.result"]
        assert f"installed_backend={installation} lifecycle=warm" in text
        trials = [line for line in text.splitlines() if line.startswith("req_len=")]
        assert len(trials) == 2
        for trial in trials:
            assert f"resp_len={response_length} " in trial
            assert "result=0 cause=0 native=0 status=0" in trial
    for kind, trials in (("read", 2), ("write", 3)):
        assert f"ORDINARY PASS completed_trials={trials} failure=none" in results[f"parity-{kind}.result"]
    run = amiga_evidence_root / f"nio-tool-parity-{installation}"
    host = run / ("native-test-records/host-fs" if installation == "native" else "fujinet-data")
    seed = (run / "read-original.adf").read_bytes()
    assert (host / "read.adf").read_bytes() == seed
    assert (host / "bounds.adf").read_bytes() == (run / "bounds-original.adf").read_bytes()
    digest = 2166136261
    for value in seed[17 * 512:18 * 512]:
        digest = ((digest ^ value) * 16777619) & 0xffffffff
    assert re.findall(r"ordinary read trial=(\d+) checksum_fnv1a32=([0-9a-f]{8})", results["parity-read.result"]) == [(str(i), f"{digest:08x}") for i in (1, 2)]
    expected = bytearray((run / "write-original.adf").read_bytes())
    expected[17 * 512:18 * 512] = bytes(((i ^ 0x5a) ^ (2 >> ((i % 4) * 8))) & 255 for i in range(512))
    assert (host / "write.adf").read_bytes() == expected
    log = (run / ("fujinet-nio-native-test.log" if installation == "native" else "fujinet-nio.log")).read_text()
    assert len(re.findall(r"fujibus: receive: .*dev=0xFC cmd=0x04", log)) == 3
    # Independent real-service clock payload oracle, not parity equality alone.
    dumps = re.findall(r"fujibus: send: dev=0x45 status=0 cmd=0x01 payload=12(.*?)(?=fujibus: receive:|\Z)", log, re.S)
    assert len(dumps) >= 2
    for dump in dumps:
        data = bytes.fromhex(" ".join(re.findall(r"fujibus:   [0-9a-f]{4}: ([0-9a-f ]+)\|", dump)))[:12]
        assert data[:4] == b"\x01\0\0\0"
        assert started <= int.from_bytes(data[4:], "little") <= finished
    assert (host / "listing/parity.txt").read_bytes() == b"parity\n"

    lists = re.findall(r"fujibus: send: dev=0xFE status=0 cmd=0x02 payload=38(.*?)(?=fujibus: receive:|\Z)", log, re.S)
    assert len(lists) == 2
    for dump in lists:
        data = bytes.fromhex(" ".join(re.findall(r"fujibus:   [0-9a-f]{4}: ([0-9a-f ]+)\|", dump)))[:38]
        assert data[:12] == bytes([1, 0, 0, 0, 0, 0, 1, 0, 28, 0, 0, 10])
        assert data[12:22] == b"parity.txt"
        assert int.from_bytes(data[22:30], "little") == 7
        assert len(data) == 38
