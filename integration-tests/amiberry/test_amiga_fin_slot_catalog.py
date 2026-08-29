def test_fin_uses_slot_catalog_for_relative_and_full_targets(run_amiga_case):
    results = run_amiga_case("amiga-fin-slot-catalog")

    assert "LOAD RC=0" in results["fin-load.result"]
    assert "FHOST RC=0" in results["fin-host.result"]

    assert "Slot 0: host:/standard.adf" in results["fin-relative.result"]
    assert "FIN RELATIVE RC=0" in results["fin-relative.result"]
    assert "Mounted slot 0 on DN0:" in results["fin-relative-mount.result"]
    assert "FMOUNT RELATIVE RC=0" in results["fin-relative-mount.result"]
    assert "KNOWN.TXT" in results["fin-relative-dir.result"].upper()
    assert "DIR RELATIVE RC=0" in results["fin-relative-dir.result"]

    assert "Slot 1: host:/second.adf" in results["fin-full.result"]
    assert "FIN FULL RC=0" in results["fin-full.result"]
    assert "Mounted slot 1 on DN1:" in results["fin-full-mount.result"]
    assert "FMOUNT FULL RC=0" in results["fin-full-mount.result"]
    assert "SECOND.TXT" in results["fin-full-dir.result"].upper()
    assert "DIR FULL RC=0" in results["fin-full-dir.result"]

    assert "Slot 0 cleared" in results["fin-clear.result"]
    assert "FOUT RC=0" in results["fin-clear.result"]
    assert "FMOUNT CLEAR RC=10" in results["fin-clear-mount.result"]
