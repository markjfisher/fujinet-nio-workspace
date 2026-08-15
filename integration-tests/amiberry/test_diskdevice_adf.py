def test_standard_adf_mount_info_read_dir_and_type(run_amiga_case):
    results = run_amiga_case("diskdevice-adf")

    assert "MOUNTED drive=0 slot=1 readonly=1 sectorSize=512 sectorCount=1760" in results["disk-mount.result"]
    assert "EXEC BOUNDARY PASS commands=5 notifications=4 remove=1 queue=1 multi=2 cause=3" in results["disk-exec-boundary.result"]
    assert "KNOWN.TXT" in results["disk-dir.result"].upper()
    assert "ENV name=DN0 table=19 sizeBlock=128 secOrg=0 surfaces=2 sectorPerBlock=1 blocksPerTrack=11 reserved=2 preAlloc=0 interleave=0 lowCyl=0 highCyl=79 buffers=5 bufMemType=1 maxTransfer=7fffffff mask=fffffffe bootPri=0 dosType=444f5300 baud=1200 control=0 bootBlocks=0 stack=32768 priority=5 globVec=ffffffff" in results["disk-dos-envec.result"]
    assert "FUJINET ADF READ PASSED" in results["disk-type.result"]
    assert "READ OK lba=0 actual=512" in results["disk-read-a.result"]
    assert "READ OK lba=880 actual=512" in results["disk-read-b.result"]
    assert "MOUNTED drive=1 slot=2 readonly=1" in results["disk-mount-1.result"]
    assert "DOS MOUNT 1 RC=0" in results["disk-dos-mount-1.result"]
    assert "FUJINET SECOND DRIVE PASSED" in results["disk-type-1.result"]
    assert "STATUS drive=1 change=1 absent=0 protected=1" in results["disk-status-1-early.result"]
    assert results["_mappings"] == "010000030c010d00000000000000000000"
    assert "MOUNTED drive=2 slot=3 readonly=0" in results["disk-mount-rw.result"]
    assert "COPY RC=0" in results["disk-copy-rw.result"]
    assert "UPDATED drive=2 slot=3" in results["disk-update.result"]
    assert "EJECTED drive=3 slot=4" in results["disk-eject.result"]
    assert "MOUNTED drive=2 slot=3 readonly=0" in results["disk-remount-rw.result"]
    assert "DOS REMOUNT 2 RC=0" in results["disk-dos-remount-2.result"]
    assert "FUJINET WRITE PERSISTED" in results["disk-persist.result"]
    assert "STATUS drive=0 change=1 absent=0 protected=1" in results["disk-status-0.result"]
    assert "STATUS drive=1 change=1 absent=0 protected=1" in results["disk-status-1.result"]
    assert "STATUS drive=2 change=3 absent=0 protected=0" in results["disk-status-2.result"]
    assert "STATUS drive=3 change=2 absent=1 protected=1" in results["disk-status-3.result"]
    assert "MALFORMED URI REJECTED" in results["disk-malformed.result"]
    assert "MOUNTED drive=7 slot=8 readonly=1" in results["disk-mount-direct.result"]
    assert "DIRECT MOUNT RC=0" in results["disk-mount-direct-rc.result"]
    assert "FAILED REPLACEMENT RC=20" in results["disk-failed-replacement.result"]
    assert "STATUS drive=7 change=1 absent=0 protected=1" in results["disk-status-7.result"]


def test_native_floppy_adf_dir_and_type(run_amiga_case):
    results = run_amiga_case("diskdevice-adf-native-floppy")

    assert "DIR RC=0" in results["df0-dir-rc.result"]
    assert "KNOWN.TXT" in results["df0-dir.result"].upper()
    assert "FUJINET ADF READ PASSED" in results["df0-type.result"]
    assert "COPY RC=0" in results["df0-copy.result"]


def test_hd_adf_mount_geometry_dir_and_type(run_amiga_case):
    results = run_amiga_case("diskdevice-hd-adf")

    assert "LOAD RC=0" in results["hd-load.result"]
    assert "sectorCount=3520" in results["hd-mount.result"]
    assert "HD MOUNT RC=0" in results["hd-mount.result"]
    assert "HD.TXT" in results["hd-dir.result"].upper()
    assert "DIR RC=0" in results["hd-dir.result"]
    assert "FUJINET HD ADF READ PASSED" in results["hd-type.result"]
    assert "STATUS drive=0 change=1 absent=0 protected=1" in results["hd-status.result"]
