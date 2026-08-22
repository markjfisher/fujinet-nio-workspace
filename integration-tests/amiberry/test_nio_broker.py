def test_isolated_exchange(run_amiga_case):
    results = run_amiga_case("nio-broker-isolated")

    assert "LOAD RC=0" in results["nio-load.result"]
    exchange = results["nio-exchange.result"]
    assert "ISOLATED disk.device=absent FLS=absent serial-free-before=1" in exchange
    assert "EXCHANGE io=0 nio=0" in exchange
    assert "REUSE io=0 nio=0" in exchange
    assert "RESIDENT serial-busy-after-opencnt0=1" in exchange
    assert "AFTER_OPENCNT0 io=0 nio=0" in exchange
    assert "TIMEOUT io=0 nio=6 len=0" in exchange
    assert "TIMEOUT_KEPT_SERIAL busy=1" in exchange
    assert "RECOVERY io=0 nio=0" in exchange
    assert "CONCURRENT a_io=0 a_nio=0" in exchange
    assert "b_io=0 b_nio=0" in exchange
    assert "CONCURRENT serial-busy-after-concurrent=1" in exchange
    assert "PASS isolated-exchange" in exchange
    assert "TOOL RC=0" in results["nio-tool-rc.result"]
    assert "fujinet-disk.device" not in exchange
    assert "FLS=present" not in exchange
