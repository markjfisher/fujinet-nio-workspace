def test_inhibit_experiment_a(run_amiga_case):
    results = run_amiga_case("diskdevice-inhibit-exp-a")
    assert "INHIBIT=TRUE RETURN=-1 IOERR=0" in results["exp-a-true.result"]
    assert "REPLACEMENT RC=0" in results["exp-a-true.result"]
    assert "INHIBIT=FALSE RETURN=-1 IOERR=0" in results["exp-a-false.result"]
    assert "FUJINET SECOND DRIVE PASSED" in results["exp-a-type.result"]


def test_inhibit_experiment_b(run_amiga_case):
    results = run_amiga_case("diskdevice-inhibit-exp-b")
    assert "INHIBIT=TRUE RETURN=-1 IOERR=0" in results["exp-b-true.result"]
    assert "REPLACEMENT RC=0" in results["exp-b-true.result"]
    assert "INHIBIT=FALSE RETURN=-1 IOERR=0" in results["exp-b-true.result"]
    assert "FUJINET SECOND DRIVE PASSED" in results["exp-b-type.result"]
