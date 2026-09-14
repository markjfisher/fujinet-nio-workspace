# Epic 1 Context: Developers can prove native FujiBus service parity before hardware exists

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Establish a genuinely SLIP-free packet path through production FujiBus code and real services, then prove the Amiga broker and exchange tool can use a test-only native backend while preserving existing service and media behavior. Separate serial deployments supply compatibility evidence. This epic needs no Zorro, RP2350B or ESP32-S3 hardware; actual Amiga guest execution still requires its emulator and toolchains. Feature requirements come from the approved epic and canonical spec package; there is no separate feature PRD or UI design requirement.

## Stories

- Story 1.1: Establish independent FujiBus wire-format regression fixtures
- Story 1.2: Expose the canonical raw FujiBus codec without breaking serial callers
- Story 1.3: Make framer composition use raw FujiBus packets consistently
- Story 1.4: Provide a bounded native packet adapter and deterministic I/O double
- Story 1.5: Prove native broker ownership and recovery against existing retry callers
- Story 1.6: Accept the canonical software packet contract for bridge design
- Story 1.7: Prove file-list and clock parity through the real core
- Story 1.8: Prove disk read/write parity with independently checked backing storage
- Story 1.9: Add a host-side native packet test endpoint for guest integration
- Story 1.10: Build an Amiga native-test broker binary using the host endpoint
- Story 1.11: Let exchange-tool read-only operations run without serial setup
- Story 1.12: Add safe ordinary disk operations to the exchange tool
- Story 1.13: Extend host parity to catalogue and media lifecycle contracts
- Story 1.14: Accept end-to-end native guest parity and fault isolation

## Requirements & Constraints

Preserve FujiBus IDs, commands, field widths, byte order, packet lengths, checksums, status mapping and service payloads. Preserve the public Amiga exchange ABI, caller buffer ownership, distinct Exec/FN errors and exactly one reply per request. Initially retain observable ordering and ownership without permanently requiring one particular worker implementation. Local queueing is allowed, but at most one exchange may be remotely in flight because the protocol has no safe response correlation identifier.

A native installation has only its installed backend: no assumed serial hardware, runtime physical selection, fallback or automatic failover. Serial tests run in separate configurations. Keep standard DD/HD ADF support, independent drive mappings, catalogue selection and media lifecycle behavior unchanged. Do not reopen accepted broker/media work or add HDF/RDB support.

Use literal wire vectors independent of production serialization, including SLIP-reserved bytes and boundary sizes. Parity tests must exercise production codecs, transports and real handlers, with independent backing-storage and time expectations. Use disposable writable media, controlled clocks and deterministic fault schedules. Canned replies cannot establish service parity. Host evidence cannot substitute for exercising the actual Amiga tool, and neither host nor guest evidence establishes physical hardware correctness.

Run each changed owner's cheapest sufficient verification after sourcing the workspace environment. Any library change requires complete `make check`; guest-visible changes require focused guest evidence. Record unavailable toolchains or environments explicitly.

## Technical Decisions

Keep service interpretation above the physical transport. Reuse the existing internal Amiga backend contract and C++ framer/transport seams; justify any additional packet-I/O interface with explicit boundary or error requirements. Native traffic carries complete raw FujiBus packets, with no SLIP wrapping. Packet boundaries must never be inferred from arbitrary byte reads or poll timing. Specify bounded ownership, capacities, truncation, send failure, backpressure and reset behavior; raw, SLIP-expanded and eventual hardware transfer lengths are distinct limits.

Physical backend choice is a build/install decision using separate binaries with an identical public ABI. Preserve current serial-control command and diagnostic compatibility; do not overwrite it with older architecture assumptions or invent native meanings for serial diagnostics. Exchange-tool `--backend cold|warm` retains lifecycle semantics, distinct from physical backend choice. Ordinary native operations must not require serial setup or serial provocation controls.

Abort does not roll back remote effects, and local timeout or reopen does not prove remote quiescence. Test existing retry callers against ambiguous completion and late replies. Recovery must prevent stale responses completing later requests and must not hide duplicate writes. If unchanged callers cannot be safely contained, request a scope decision rather than expanding into service or library redesign.

Test endpoints and packet doubles are software harnesses, not proposed bridge protocols. Defer registers, mailbox layouts, PIO organization, bridge-to-ESP link choices and performance targets until their evidence gates.

## Cross-Story Dependencies

The initial sequence is independent fixtures, raw codec, framer composition, packet adapter, broker recovery, then software-contract acceptance (1.1–1.6). Under the user's 2026-09-14 amendment, 1.5/1.6 require evidence-backed agent technical acceptance, not routine human checkpoints; unresolved limitations, scope decisions and meaningful tradeoffs go to the user. The evidence criteria remain unchanged. Service parity, guest endpoint, broker binary, exchange-tool and media work converge at 1.14; each dispatch entry defines its exact prerequisites.

Epic 1 has no hardware-epic dependency. Bridge setup and feasibility may proceed independently, but hardware ABI approval requires accepted 1.6 plus positive physical feasibility evidence. Physical endpoint implementation additionally requires accepted 1.14. Passing codec fixtures alone does not release those gates.

Current 2026-09-14 audit: 1.6 is held because 1.5's recorded tests do not
establish the full both-caller ambiguity/remote-effect contract. Historical
completion is preserved, but 1-8/1-10 and downstream work cannot use it as
current safety acceptance. Consult the active execution-gates.md and 1.6
decision record before dispatch; 1-7 and independent feasibility remain eligible
subject to their own prerequisites.
