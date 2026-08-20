def test_diskdevice_loader(run_amiga_case):
    results = run_amiga_case("diskdevice-loader")
    assert "Resident loaded: fujinet-disk.device" in results["loader.result"]
    assert "segment released" not in results["loader.result"].lower()
    assert "FIRST RC=0" in results["loader.result"]
    assert "Resident device already loaded: fujinet-disk.device" in results["loader-second.result"]
    assert "SECOND RC=0" in results["loader-second.result"]
    assert "Resident segment released after scan failure" in results["loader-mismatch.result"]
    assert "MISMATCH RC=20" in results["loader-mismatch.result"]
    assert "Resident segment released after scan failure" in results["loader-invalid.result"]
    assert "INVALID RC=20" in results["loader-invalid.result"]
    assert "STATUS drive=0" in results["loader-status.result"]
    assert "absent=1" in results["loader-status.result"]
