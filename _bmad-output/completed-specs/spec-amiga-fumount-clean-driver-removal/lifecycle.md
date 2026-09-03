# Lifecycle diagrams

## Mount stack (current product)

```text
FMOUNT slot DNx: RW
        │
        ▼
┌──────────────────┐
│ DOS handler DNx: │
└────────┬─────────┘
         │ OpenDevice
         ▼
┌────────────────────────┐
│ fujinet-disk.device    │
│ unit n                 │
└────────┬───────────────┘
         │ fn_transport (broker client)
         ▼
┌────────────────────────┐
│ fujinet-nio.device     │
└────────────────────────┘
```

## FUMOUNT required for unload (CAP-1)

```text
FUMOUNT DNx:
        │
        ▼
ACTION_FLUSH ──fail──► stop; no DIE; no eject
        │ ok
        ▼
ACTION_DIE ──fail──► handler busy; no eject
        │ ok
        ▼
TD_EJECT / disk eject on unit n
        │
        ▼
CloseDevice (FUMOUNT's temporary open)
        │
        ▼
disk.device OpenCnt == 0 if no other clients
```

Handler terminated (`dol_Task` null). Do not `DeviceProc`/`Dir` `DNx:` to observe that, or DOS may start a new handler.

## Developer reload (CAP-4–CAP-7)

```text
FUMOUNT all used DNx:
        │
        ▼
RemDevice fujinet-disk.device
        │
        ▼
RemDevice fujinet-nio.device
        │
        ▼
fujinet-load-resident … fujinet-nio.device
        │
        ▼
fujinet-load-resident … fujinet-disk.device
```
