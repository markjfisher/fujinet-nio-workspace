# Amiga NIO broker Stage 4 — remove disk idle-close

Status: `ACCEPTED` (2026-08-23)

## Goal

Stop `fujinet-disk.device` from `fn_transport_close` when the worker FIFO
empties. Keep the broker client across ordinary idle. Close only from pending
`LIBF_DELEXP` teardown (safe expunge, last CloseDevice when that flag is set,
or worker idle with the flag already pending). Do not unload the disk resident.

## Acceptance

Parent gate `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-4.md`
Verification commands ran: `fn_transport_close` only in
`complete_pending_expunge`; native `make tests`; Amiberry
`test_hd_adf_mount_geometry_dir_and_type`; inspect-catalog twice.

## Durable contract

`docs/amiga/nio-broker-architecture.md` §4

Remaining work stays in `backlog/nio-broker.md`: Stage 5 extra backends.
Do not restore FIFO-empty idle-close unless a regression is found.
