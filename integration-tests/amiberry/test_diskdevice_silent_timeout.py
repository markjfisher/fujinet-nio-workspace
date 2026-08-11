def test_native_transport_times_out_against_silent_peer(run_amiga_case):
    results = run_amiga_case("diskdevice-silent-timeout")

    assert "SILENT TIMEOUT RC=20" in results["silent-timeout.result"]
