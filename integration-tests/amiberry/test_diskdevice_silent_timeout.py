def test_mount_times_out_against_stalled_external_peer(run_amiga_case):
    results = run_amiga_case("diskdevice-stalled-external-peer")

    assert "STALLED PEER TIMEOUT RC=20" in results["stalled-peer-timeout.result"]
    assert results["fmount.result"].strip() == ""
