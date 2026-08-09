def test_wifi_configuration_set_get_status_and_scan(run_amiga_case):
    result = run_amiga_case("wifi-config")["wificonfigtest.result"]
    assert "WIFICFGTEST START" in result
    assert "SET OK" in result
    assert "GET OK" in result
    assert "STATUS OK" in result
    assert "SCAN OK" in result
    assert "WIFICFGTEST PASS=1 FAIL=0" in result
