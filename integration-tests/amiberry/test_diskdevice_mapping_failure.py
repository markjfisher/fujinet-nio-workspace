def test_mapping_write_failure_preserves_active_media(run_amiga_case):
    results = run_amiga_case("diskdevice-mapping-failure")

    assert "MOUNTED drive=0 slot=1 readonly=1" in results["map-direct.result"]
    assert "MAPPING FAILURE RC=20" in results["map-failure.result"]
    assert "STATUS drive=0 change=1 absent=0 protected=1" in results["map-status.result"]
