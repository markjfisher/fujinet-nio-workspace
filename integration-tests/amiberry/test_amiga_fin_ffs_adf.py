def test_fin_mounts_and_reads_ffs_adf(run_amiga_case):
    results = run_amiga_case("amiga-fin-ffs-adf")

    assert "LOAD RC=0" in results["ffs-load.result"]
    assert "FHOST RC=0" in results["ffs-host.result"]
    assert "FIN RC=0" in results["ffs-fin.result"]
    assert "FMOUNT RC=0" in results["ffs-mount.result"]
    assert "KNOWN.TXT" in results["ffs-dir.result"].upper()
    assert "DIR RC=0" in results["ffs-dir.result"]
