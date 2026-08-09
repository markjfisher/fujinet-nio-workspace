def test_cli_arguments_and_persistent_state(run_amiga_case):
    results = run_amiga_case("cli-stateful")
    assert "HOST:" in results["cli-fhost-set.result"]
    assert "HOST: host:/" in results["cli-fhost-get.result"]
    assert "entries" in results["cli-fls.result"] or "entry" in results["cli-fls.result"]
    assert "Wrote 5 bytes" in results["cli-fapp-put.result"]
    assert "hello" in results["cli-fapp-get.result"]
    assert "value" in results["cli-fapp-list.result"]
    assert "Deleted: yes" in results["cli-fapp-delete.result"]
