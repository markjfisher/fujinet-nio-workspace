import re


def _status(result):
    match = re.search(
        r"STATUS drive=(\d+) change=(\d+) absent=(\d+) protected=(\d+)",
        result,
    )
    assert match, result
    return tuple(int(value) for value in match.groups())


def test_fmount_fumount_standard_adf(run_amiga_case):
    results = run_amiga_case("diskdevice-fmount")

    assert "LOAD RC=0" in results["fmount-load.result"]
    assert "FMOUNT RC=0" in results["fmount-mount.result"]
    assert "Mounted slot 11 on DN0:" in results["fmount-mount.result"]
    assert "STATUS drive=0 change=1 absent=0 protected=1" in results["fmount-status.result"]
    assert "KNOWN.TXT" in results["fmount-dir.result"].upper()
    assert "DIR RC=0" in results["fmount-dir.result"]
    assert "FUJINET ADF READ PASSED" in results["fmount-type.result"]
    assert "Ejected DN0:" in results["fmount-replace-eject.result"]
    replace_before = _status(results["fmount-status.result"])
    replace_absent = _status(results["fmount-replace-absent.result"])
    replace_present = _status(results["fmount-replace-present.result"])
    assert replace_absent[0] == replace_before[0] == replace_present[0] == 0
    assert replace_absent[2:] == (1, 1)
    assert replace_present[2:] == (0, 1)
    assert replace_before[1] < replace_absent[1] < replace_present[1]
    assert "Mounted slot 12 on DN0:" in results["fmount-replace-mount.result"]
    assert "FUJINET SECOND DRIVE PASSED" in results["fmount-replace-type.result"]
    assert "FMOUNT RW RC=0" in results["fmount-rw-mount.result"]
    assert "Mounted slot 13 on DN2:" in results["fmount-rw-mount.result"]
    assert "DOS MOUNT 2 RC=0" in results["fmount-rw-dos-mount.result"]
    assert "COPY RC=0" in results["fmount-rw-copy.result"]
    assert "Ejected DN2:" in results["fmount-rw-fumount.result"]
    assert "FUMOUNT RW RC=0" in results["fmount-rw-fumount.result"]
    rw_before = _status(results["fmount-rw-status.result"])
    rw_absent = _status(results["fmount-rw-absent.result"])
    rw_present = _status(results["fmount-rw-present.result"])
    assert rw_before[0] == rw_absent[0] == rw_present[0] == 2
    assert rw_absent[2:] == (1, 1)
    assert rw_present[2:] == (0, 0)
    assert rw_before[1] < rw_absent[1] < rw_present[1]
    assert "Mounted slot 13 on DN2:" in results["fmount-rw-remount.result"]
    assert "FMOUNT RW REMOUNT RC=0" in results["fmount-rw-remount.result"]
    assert "DOS REMOUNT 2 RC=0" in results["fmount-rw-remount.result"]
    assert "FUJINET WRITE PERSISTED" in results["fmount-rw-persist.result"]
    assert "Ejected DN0:" in results["fumount-eject.result"]
    assert "FUMOUNT RC=0" in results["fumount-eject.result"]
    assert "absent=1" in results["fumount-status.result"]
    assert results["_mappings"] == "0100000000010d00000000000000000000"
