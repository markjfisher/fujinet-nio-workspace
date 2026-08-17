# Amiga nio-config port

Status: `TODO`

## Goal

Add an Amiga port to `repos/nio-config` before work on faster Amiga backends.
It must use the same FujiBus service contracts and persistent state as other
platforms, so software written against RS-232 continues to work unchanged on
later packet-native transports.

## Dependencies

- Amiga DiskDevice Phase 2 is complete: `fujinet-disk.device` exposes units
  0–7 as `DN0:`–`DN7:`, supported media geometry is not silently fixed to the
  Stage 8 DD-ADF profile, and standard `FMOUNT`/`FUMOUNT` own all normal
  catalogue-slot-to-drive operations.
- `FMOUNT` implements catalogue-slot-to-drive mappings using the shared
  `config-nio/mappings` contract through the resident driver.
- The existing Amiga `fujinet-nio-lib` application target remains usable
  independently of the resident driver target.
- The supported-media and standard-command contract is documented in
  `docs/amiga/disk-media-architecture.md`.

## Work

- [ ] Define the Amiga UI and input conventions without changing Slot Catalog,
      HostService, AppStore, or DiskDevice wire contracts.
- [ ] Port host/path selection and sparse catalogue browsing/editing.
- [ ] Display catalogue slots separately from active `DNx:` device state and
      saved mappings.
- [ ] Read the version-1 eight-entry `config-nio/mappings` value for display,
      but do not mutate it independently of the resident device lifecycle.
- [ ] Mount, replace, and eject selected catalogue media on drives 0–7 with
      explicit RO/RW mode through the same public resident-device operations
      used by `FMOUNT`/`FUMOUNT`.
- [ ] Prove UI actions update live device state, change counters, protection,
      and saved mappings atomically; use `FMOUNTRESTORE` semantics for startup
      restoration rather than creating a second restore path.
- [ ] Surface unsupported-media and stale-mapping failures without creating a
      DOS node or desynchronising the displayed state.
- [ ] Add native builds, deterministic host tests, and Amiberry interaction
      coverage for configuration persistence and remount after restart.
- [ ] Document installation, keys, limitations, and compatible revisions.

## Exit criteria

An Amiga user can configure hosts and catalogue URIs, assign any populated
catalogue slot to any `DN0:`–`DN7:` drive, persist those assignments, and use
the resulting disks through normal AmigaDOS commands over the RS-232 backend.
The UI must remain a client of the established mount lifecycle, not an
independent writer of mapping state.
