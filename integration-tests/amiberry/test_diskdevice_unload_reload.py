def test_unload_reload_without_reboot(run_amiga_case):
    results = run_amiga_case("diskdevice-unload-reload")

    # Initial mount and I/O - DN0:
    assert "FMOUNT DN0 RC=0" in results["initial-fmount-dn0.result"]
    assert "DIR DN0 RC=0" in results["initial-dir-dn0.result"]
    assert "KNOWN.TXT" in results["initial-dir-dn0.result"].upper()
    assert "TYPE DN0 RC=0" in results["initial-type-dn0.result"]
    assert "FUJINET ADF READ PASSED" in results["initial-type-dn0.result"]

    # Initial mount and I/O - DN1:
    assert "FMOUNT DN1 RC=0" in results["initial-fmount-dn1.result"]
    assert "DIR DN1 RC=0" in results["initial-dir-dn1.result"]
    assert "SECOND.TXT" in results["initial-dir-dn1.result"].upper()
    assert "TYPE DN1 RC=0" in results["initial-type-dn1.result"]
    assert "FUJINET SECOND DRIVE PASSED" in results["initial-type-dn1.result"]

    # FUMOUNT both drives
    assert "Ejected DN0:" in results["fumount-dn0.result"]
    assert "FUMOUNT DN0 RC=0" in results["fumount-dn0.result"]
    assert "Ejected DN1:" in results["fumount-dn1.result"]
    assert "FUMOUNT DN1 RC=0" in results["fumount-dn1.result"]

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
