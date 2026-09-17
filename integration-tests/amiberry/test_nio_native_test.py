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
