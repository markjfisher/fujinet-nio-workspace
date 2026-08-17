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
    replace_before = _status(results["fmount-status.result"])
    replace_present = _status(results["fmount-ab-present.result"])
    assert replace_before[0] == replace_present[0] == 0
    assert replace_present[2:] == (0, 1)
    assert replace_before[1] < replace_present[1]
    assert "Mounted slot 12 on DN0:" in results["fmount-ab-mount.result"]
    assert "FUJINET SECOND DRIVE PASSED" in results["fmount-ab-type.result"]
    back_present = _status(results["fmount-ba-present.result"])
    assert back_present[0] == 0
    assert back_present[2:] == (0, 1)
    assert "Mounted slot 11 on DN0:" in results["fmount-ba-mount.result"]
    assert "FUJINET ADF READ PASSED" in results["fmount-ba-type.result"]
    assert "FMOUNT HD RC=0" in results["fmount-hd-mount.result"]
    assert "Mounted slot 14 on DN0:" in results["fmount-hd-mount.result"]
    assert "DIR HD RC=0" in results["fmount-hd-dir.result"]
    assert "HD.TXT" in results["fmount-hd-dir.result"].upper()
    assert "TYPE HD RC=0" in results["fmount-hd-type.result"]
    assert "FUJINET HD ADF READ PASSED" in results["fmount-hd-type.result"]
    assert "DN0 type=0 task=00000000" not in results["fmount-hd-dos.result"]
    assert "blocksPerTrack=22" in results["fmount-hd-dos.result"]
    assert "FMOUNT DD RETURN RC=0" in results["fmount-dd-return-mount.result"]
    assert "DIR DD RETURN RC=0" in results["fmount-dd-return-dir.result"]
    assert "KNOWN.TXT" in results["fmount-dd-return-dir.result"].upper()
    assert "TYPE DD RETURN RC=0" in results["fmount-dd-return-type.result"]
    assert "FUJINET ADF READ PASSED" in results["fmount-dd-return-type.result"]
    assert "DN0 type=0 task=00000000" not in results["fmount-dd-return-dos.result"]
    assert "blocksPerTrack=11" in results["fmount-dd-return-dos.result"]
    assert "FMOUNT FAILED RC=10" in results["fmount-failed-replace.result"]
    assert "FUJINET ADF READ PASSED" in results["fmount-fail-type.result"]
    assert "FMOUNT RW RC=0" in results["fmount-rw-mount.result"]
    assert "Mounted slot 13 on DN2:" in results["fmount-rw-mount.result"]
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
    assert "FUJINET WRITE PERSISTED" in results["fmount-rw-persist.result"]
    assert "Ejected DN0:" in results["fumount-eject.result"]
    assert "FUMOUNT RC=0" in results["fumount-eject.result"]
    assert "absent=1" in results["fumount-status.result"]
    assert results["_mappings"] == "0100000000010d00000000000000000000"


def test_hd_stage8_replacement_and_writable_durability(run_amiga_case):
    results = run_amiga_case("diskdevice-hd-stage8")

    a_status = _status(results["hd-stage8-a-status.result"])
    b_status = _status(results["hd-stage8-b-status.result"])
    a2_status = _status(results["hd-stage8-a2-status.result"])
    assert a_status[2:] == b_status[2:] == a2_status[2:] == (0, 1)
    assert a_status[1] < b_status[1] < a2_status[1]
    assert "FUJINET HD ADF READ PASSED" in results["hd-stage8-a-type.result"]
    assert "FUJINET SECOND HD PASSED" in results["hd-stage8-b-type.result"]
    assert "FUJINET HD ADF READ PASSED" in results["hd-stage8-a2-type.result"]

    assert "Mounted slot 18 on DN0:" in results["hd-stage8-rw-mount.result"]
    assert "COPY HD RC=0" in results["hd-stage8-rw-copy.result"]
    rw_status = _status(results["hd-stage8-rw-status.result"])
    absent_status = _status(results["hd-stage8-rw-absent.result"])
    present_status = _status(results["hd-stage8-rw-present.result"])
    assert rw_status[2:] == (0, 0)
    assert absent_status[2:] == (1, 1)
    assert present_status[2:] == (0, 0)
    assert rw_status[1] < absent_status[1] < present_status[1]
    assert "Ejected DN0:" in results["hd-stage8-rw-fumount.result"]
    assert "Mounted slot 18 on DN0:" in results["hd-stage8-rw-remount.result"]
    assert "FUJINET HD WRITE PERSISTED" in results["hd-stage8-rw-persist.result"]
