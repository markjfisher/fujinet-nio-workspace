def test_standard_adf_mount_info_read_dir_and_type(run_amiga_case):
    results = run_amiga_case("diskdevice-adf")

    assert "MOUNTED drive=0 slot=1 readonly=1 sectorSize=512 sectorCount=1760" in results["disk-mount.result"]
    assert "EXEC BOUNDARY PASS commands=5 notifications=2 remove=1" in results["disk-exec-boundary.result"]
    assert "KNOWN.TXT" in results["disk-dir.result"].upper()
    assert "FUJINET ADF READ PASSED" in results["disk-type.result"]
    assert "READ OK lba=0 actual=512" in results["disk-read-a.result"]
    assert "READ OK lba=880 actual=512" in results["disk-read-b.result"]
    assert "MOUNTED drive=1 slot=2 readonly=1" in results["disk-mount-1.result"]
    assert "DOS MOUNT 1 RC=0" in results["disk-dos-mount-1.result"]
    assert "FUJINET SECOND DRIVE PASSED" in results["disk-type-1.result"]
    assert "STATUS drive=1 change=1 absent=0 protected=1" in results["disk-status-1-early.result"]
    assert results["_mappings"] == "010000030c010d00000000000000000000"
    assert "MOUNTED drive=2 slot=3 readonly=0" in results["disk-mount-rw.result"]
    assert "UPDATED drive=2 slot=3" in results["disk-update.result"]
    assert "EJECTED drive=3 slot=4" in results["disk-eject.result"]
    assert "MOUNTED drive=2 slot=3 readonly=0" in results["disk-remount-rw.result"]
    assert "DOS REMOUNT 2 RC=0" in results["disk-dos-remount-2.result"]
    assert "FUJINET WRITE PERSISTED" in results["disk-persist.result"]
    assert "STATUS drive=0 change=1 absent=0 protected=1" in results["disk-status-0.result"]
    assert "STATUS drive=1 change=1 absent=0 protected=1" in results["disk-status-1.result"]
    assert "STATUS drive=2 change=3 absent=0 protected=0" in results["disk-status-2.result"]
    assert "STATUS drive=3 change=2 absent=1 protected=1" in results["disk-status-3.result"]
    assert "MOUNTED drive=7 slot=8 readonly=1" in results["disk-mount-direct.result"]
    assert "DIRECT MOUNT RC=0" in results["disk-mount-direct-rc.result"]
    assert "FAILED REPLACEMENT RC=20" in results["disk-failed-replacement.result"]
    assert "STATUS drive=7 change=1 absent=0 protected=1" in results["disk-status-7.result"]
