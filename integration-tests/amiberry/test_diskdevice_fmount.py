def test_fmount_fumount_standard_adf(run_amiga_case):
    results = run_amiga_case("diskdevice-fmount")

    assert "LOAD RC=0" in results["fmount-load.result"]
    assert "FMOUNT RC=0" in results["fmount-mount.result"]
    assert "Mounted slot 11 on DN0:" in results["fmount-mount.result"]
    assert "STATUS drive=0 change=1 absent=0 protected=1" in results["fmount-status.result"]
    assert "KNOWN.TXT" in results["fmount-dir.result"].upper()
    assert "DIR RC=0" in results["fmount-dir.result"]
    assert "FUJINET ADF READ PASSED" in results["fmount-type.result"]
    assert "Ejected DN0:" in results["fumount-eject.result"]
    assert "FUMOUNT RC=0" in results["fumount-eject.result"]
    assert "absent=1" in results["fumount-status.result"]
