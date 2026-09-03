def test_unload_reload_without_reboot(run_amiga_case):
    results = run_amiga_case("diskdevice-unload-reload")

    # Initial mount and I/O
    assert "FMOUNT RC=0" in results["initial-fmount.result"]
    assert "DIR RC=0" in results["initial-dir.result"]
    assert "KNOWN.TXT" in results["initial-dir.result"].upper()
    assert "TYPE RC=0" in results["initial-type.result"]
    assert "FUJINET ADF READ PASSED" in results["initial-type.result"]

    # FUMOUNT success
    assert "Ejected DN0:" in results["fumount.result"]
    assert "FUMOUNT RC=0" in results["fumount.result"]

    # Unload disk device
    assert "Unloaded: fujinet-disk.device" in results["unload-disk.result"]
    assert "UNLOAD DISK RC=0" in results["unload-disk.result"]

    # Unload nio device
    assert "Unloaded: fujinet-nio.device" in results["unload-nio.result"]
    assert "UNLOAD NIO RC=0" in results["unload-nio.result"]

    # Reload nio device
    assert "Resident loaded: fujinet-nio.device" in results["reload-nio.result"]
    assert "LOAD NIO RC=0" in results["reload-nio.result"]

    # Reload disk device
    assert "Resident loaded: fujinet-disk.device" in results["reload-disk.result"]
    assert "LOAD DISK RC=0" in results["reload-disk.result"]

    # Post-reload mount and I/O
    assert "FMOUNT RC=0" in results["post-fmount.result"]
    assert "DIR RC=0" in results["post-dir.result"]
    assert "KNOWN.TXT" in results["post-dir.result"].upper()
    assert "TYPE RC=0" in results["post-type.result"]
    assert "FUJINET ADF READ PASSED" in results["post-type.result"]
