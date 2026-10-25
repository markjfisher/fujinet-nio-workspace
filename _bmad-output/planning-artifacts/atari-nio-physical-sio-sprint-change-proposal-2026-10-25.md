# Atari physical SIO: Story 2.5 rebaseline

**Decision:** User-directed rebaseline, 2026-10-25. Scope is documentation and
planning only; the user explicitly requested and authorized these edits and a
commit. Story 2.5 remains **in progress**.

## Trigger and evidence

The original plan coupled the native BASIC handler to the configuration ATR and
linked it to the C public library. The implemented production path instead
installs a relocatable CA65 module during MyDOS 4.53/4 startup, with genuine
BASIC READ/PUT/POST passing against production NetworkDevice over NetSIO. Its
permanent allocation is 2,360 bytes. The configuration ATR is a transient
configuration and boot-selection environment; its existing boot contract stays
in force. The Story 2.5 implementation record contains the test commands and
evidence.

A NetSIO host-reset event reclaims its own remote sessions without flushing or
committing abandoned output. The observed emulator reset took the OS cold path,
so it does not demonstrate installed-driver persistence over a genuine OS warm
start. Physical SIO reset detection and embedded-adapter BASIC acceptance are
also unverified.

## Impact and path

- **Epic 2 / Story 2.5:** direct adjustment of FR11, acceptance and story
  record. The native protocol, I/O behavior, recovery, safe installation and
  RAM ceiling remain required. Genuine OS warm-start persistence is still a
  closure criterion; the story remains open.
- **Feature spec and architecture:** align CAP-6, companion wire/acceptance
  text and architecture AD-10 with DOS startup and the CA65 resident. The
  independent config ATR boot and public-API XEX contracts are unchanged.
- **Epic 1 and Epic 3:** no change to configuration boot/media or physical
  acceptance. Physical reset detection remains a physical verification gap.
- **Other DOS environments:** Atari DOS 2.0S/2.5, SpartaDOS and SpartaDOS X
  are unverified follow-on compatibility targets using the same module and
  DOS-appropriate installation. They do not block this MyDOS story.
- **Embedded adapter:** the BASIC lifecycle remains an explicit outstanding
  verification item; existing public-API adapter acceptance is not a substitute.
- **Deferred idea:** `config://` might eventually expose files from the
  original configuration/boot disk after a selected DOS replaces it. No API,
  implementation or current requirement is established.
- **UX, firmware, installer, test infrastructure and config ATR:** no changes
  in this increment. The Atari feature spec serves as the product contract; no
  separate Atari PRD or UX contract is identified in the feature artifacts.

Direct adjustment is low-effort documentation work with low risk to the
verified baseline. Rollback would discard working acceptance evidence and is
unnecessary; broader product replanning is not required. The calendar impact
of the remaining warm-start and physical verification is not yet estimated.

## Specific changes and handoff

| Artifact | Before | Rebaselined decision |
| --- | --- | --- |
| Story 2.5 / FR11 | Config ATR installs an N: handler linked to the public C library. | User DOS startup installs the relocatable CA65 native-protocol handler; retain MyDOS evidence and all safety and I/O requirements. |
| Feature spec / architecture AD-10 | BASIC path goes through the public library and config-ATR installer. | BASIC resident directly implements the existing native protocol; config ATR boot contract is unchanged. |
| Story evidence | Historical matrix treats config packaging and POST as missing, before subsequent POST and reset work. | Current matrix records verified MyDOS, POST, RAM and NetSIO evidence, genuine warm-start gap, physical detection gap and embedded-adapter question; history remains labeled historical. |

Handoff to the Atari development and verification owners: establish a genuine
OS warm start, verify retained HATABS/MEMLO/code and usable N: while abandoned
sessions are reclaimed without committing output, and separately resolve the
embedded-adapter BASIC and physical-reset evidence gaps. Reassess closure from
that evidence. No new implementation is authorized by this rebaseline.
