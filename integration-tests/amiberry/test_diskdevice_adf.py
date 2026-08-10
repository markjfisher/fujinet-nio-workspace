def test_standard_adf_mount_info_read_dir_and_type(run_amiga_case):
    results = run_amiga_case("diskdevice-adf")

    assert "MOUNTED slot=1 readonly=1 sectorSize=512 sectorCount=1760" in results["disk-mount.result"]
    assert "KNOWN.TXT" in results["disk-dir.result"].upper()
    assert "FUJINET ADF READ PASSED" in results["disk-type.result"]
