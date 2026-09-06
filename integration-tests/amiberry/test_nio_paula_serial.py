def test_paula_serial_clock(run_amiga_case):
    results = run_amiga_case("nio-paula-serial")

    assert "SERIAL LOAD RC=0" in results["serial-load.result"]
    assert "LOAD RC=0" in results["nio-load.result"]
    exchange = results["nio-exchange.result"]
    assert "result=0" in exchange
    assert "backend=cold" in exchange
    assert "TOOL RC=0" in results["nio-tool-rc.result"]
