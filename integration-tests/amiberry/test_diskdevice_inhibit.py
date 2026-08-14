def test_inhibit_media_replacement(run_amiga_case):
    results = run_amiga_case("diskdevice-inhibit-poc")

    assert "INHIBIT VOLUME A" in results["inhibit-a.result"]
    assert "INHIBIT=TRUE RETURN=-1 IOERR=0" in results["inhibit-true.result"]
    assert "REPLACEMENT RC=0" in results["inhibit-true.result"]
    assert "INHIBIT VOLUME B" in results["inhibit-b.result"]
    assert "INHIBIT=FALSE RETURN=-1 IOERR=0" in results["inhibit-false.result"]
    assert "REPLACEMENT RC=0" in results["inhibit-false.result"]
    assert "INHIBIT VOLUME A" in results["inhibit-a-again.result"]
    assert "INHIBIT VOLUME B" in results["inhibit-final.result"]
