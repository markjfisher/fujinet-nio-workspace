def test_checksumbench_c_and_asm_results(run_amiga_case):
    results = run_amiga_case("checksumbench")
    output = results["checksumbench.result"]
    rows = [line.split() for line in output.splitlines()
            if line and line.split()[0].isdigit()]

    assert [row[2] for row in rows] == ["C", "A", "B"] * 6
    assert [row[0] for row in rows] == ["16", "16", "16", "64", "64", "64", 
                                        "256", "256", "256", "512", "512", "512",
                                        "1024", "1024", "1024", "4096", "4096", "4096"]
