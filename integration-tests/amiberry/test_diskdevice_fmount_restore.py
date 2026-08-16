def test_fmount_fumount_persisted_dd_hd_restore(run_amiga_case):
    results = run_amiga_case("diskdevice-fmount-restore")

    assert "DD FMOUNT RC=0" in results["restore-dd-mount.result"]
    assert "KNOWN.TXT" in results["restore-dd-before-dir.result"].upper()
    assert "DD DIR BEFORE RC=0" in results["restore-dd-before-dir.result"]
    assert "FUJINET ADF READ PASSED" in results["restore-dd-before-type.result"]
    assert "DD TYPE BEFORE RC=0" in results["restore-dd-before-type.result"]

    assert "HD FMOUNT RC=0" in results["restore-hd-mount.result"]
    assert "HD.TXT" in results["restore-hd-before-dir.result"].upper()
    assert "HD DIR BEFORE RC=0" in results["restore-hd-before-dir.result"]
    assert "FUJINET HD ADF READ PASSED" in results["restore-hd-before-type.result"]
    assert "HD TYPE BEFORE RC=0" in results["restore-hd-before-type.result"]

    assert "FMOUNTRESTORE unit=0 slot=11 mode=RO" in results["restore-startup.result"]
    assert "FMOUNTRESTORE unit=1 slot=14 mode=RO" in results["restore-startup.result"]
    assert "FMOUNTRESTORE restored=2" in results["restore-startup.result"]
    assert "RESTORE RC=0" in results["restore-startup.result"]

    assert "KNOWN.TXT" in results["restore-dd-after-dir.result"].upper()
    assert "DD DIR AFTER RC=0" in results["restore-dd-after-dir.result"]
    assert "FUJINET ADF READ PASSED" in results["restore-dd-after-type.result"]
    assert "DD TYPE AFTER RC=0" in results["restore-dd-after-type.result"]
    assert "HD.TXT" in results["restore-hd-after-dir.result"].upper()
    assert "HD DIR AFTER RC=0" in results["restore-hd-after-dir.result"]
    assert "FUJINET HD ADF READ PASSED" in results["restore-hd-after-type.result"]
    assert "HD TYPE AFTER RC=0" in results["restore-hd-after-type.result"]

    assert "DD FUMOUNT RC=0" in results["restore-dd-fumount.result"]
    assert "DD SECOND FUMOUNT RC=0" not in results["restore-dd-absent.result"]
    assert "HD FUMOUNT RC=0" in results["restore-hd-fumount.result"]
    assert "HD SECOND FUMOUNT RC=0" not in results["restore-hd-absent.result"]
    assert results["_mappings"] == "01" + "00" * 16


def test_invalid_persisted_mapping_fails_without_creating_node(run_amiga_case):
    results = run_amiga_case("diskdevice-fmount-restore-invalid")

    assert "FMOUNTRESTORE unit=0 slot=99 rc=" in results["restore-invalid.result"]
    assert "RESTORE INVALID RC=0" not in results["restore-invalid.result"]
    assert "DN0 type=0" not in results["restore-invalid-dos.result"]
