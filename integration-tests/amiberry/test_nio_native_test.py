from pathlib import Path

from conftest import native_test_map_omits_serial_session_slip

ROOT = Path(__file__).resolve().parents[2]


def test_native_test_clock_exchange(run_amiga_case):
    results = run_amiga_case("nio-native-test")

    assert "LOAD RC=0" in results["nio-load.result"]
    probe = results["nio-native-test.result"]
    assert "IDENTITY=native-test" in probe
    assert "SET_BAUD io=0 nio=8" in probe
    assert "EXCHANGE io=0 nio=0" in probe
    assert "CLOCK cmd=1" in probe
    assert "PASS native-test-clock" in probe
    assert "TOOL RC=0" in results["nio-tool-rc.result"]
    map_path = ROOT / (
        "repos/fujinet-nio-driver/build/amiga/"
        "fujinet-nio-native-test.device.map"
    )
    assert map_path.is_file()
    assert native_test_map_omits_serial_session_slip(
        map_path.read_text(encoding="ascii", errors="ignore")
    )
