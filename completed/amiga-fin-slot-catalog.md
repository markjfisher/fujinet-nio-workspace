# Amiga FIN must populate the Slot Catalog

Status: `DONE`

Accepted 2026-08-29 (`_bmad-output/implementation-artifacts/spec-amiga-fin-slot-catalog.md`).
The parked `diskdevice-adf` `CMD_UPDATE`/`Assign DISMOUNT` requester was
fixed separately in the Amiberry sequence (FUMOUNT then remount).

## Problem

The Amiga `FIN` command writes the private `config-nio/slot-NNN` AppStore
record directly.  A relative argument such as `FIN 0 amiga-wifitest.adf` is
therefore stored as a bare filename, even after `FHOST` has selected a TNFS
directory.  `FMOUNT` later resolves that record through the Slot Catalog and
cannot inspect the unqualified disk target.

`FIN` must be a Slot Catalog client, not a writer of the catalogue's private
AppStore schema.  This is the established FujiNet contract: Slot Catalog
`Put` resolves a relative target against the current HostService path and
stores a canonical URI.

## Intended user flow

```text
FHOST tnfs://192.168.1.101/amiga
FIN 0 amiga-wifitest.adf
FMOUNT 0 DN0: RO
Dir DN0:
```

The equivalent full URI form must work too:

```text
FIN 0 tnfs://192.168.1.101/amiga/amiga-wifitest.adf
```

## Scope

- Add focused, initially failing coverage for `FHOST` + relative `FIN` +
  `FMOUNT` on Amiga; prove that `DN0:` can be read.
- Change `FIN`/its shared service helper to use the typed Slot Catalog API for
  put, get, and delete semantics where appropriate, preserving the current
  `FIN` and `FOUT` command-line interface.
- Verify canonical URI persistence and a full URI input.
- Keep `FMOUNT` as the owner of the Amiga DOS-node and media lifecycle.

## Non-goals

- Do not change Slot Catalog, HostService, DiskDevice, or AppStore wire
  contracts.
- Do not work around the problem by teaching `FMOUNT` to interpret bare paths.
- Do not address the separate `CMD_UPDATE`/`Assign DN2: DISMOUNT` requester
  regression from `diskdevice-adf`; track and investigate it independently.

## Acceptance criteria

- Given a current TNFS host path, when an Amiga user runs `FIN 0 filename`,
  then Slot Catalog slot 0 contains the canonical TNFS URI and `FMOUNT 0
  DN0: RO` followed by `Dir DN0:` succeeds.
- Given a full canonical URI, when the user runs `FIN`, then the same mount
  flow succeeds.
- Given an unavailable/invalid target, when Slot Catalog rejects it, then
  `FIN` fails without creating or corrupting the existing slot.
- Focused host and single-node Amiberry coverage pass; no full suite is
  required for this change.
