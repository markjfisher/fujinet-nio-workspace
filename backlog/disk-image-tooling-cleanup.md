# Shared disk-image tooling cleanup

Status: `TODO`

## Goal

Reduce duplicated disk-image implementation code while preserving repository
independence and the current workspace targets, manifests, and artifact paths.

## Dependencies

- The Python workspace build front end and current disk ownership boundaries
  are complete and documented in `docs/build-orchestration.md` and
  `docs/disk-image-builds.md`.
- `repos/fujinet-qemu-msdos` must remain independently buildable and pushable;
  it cannot import code through workspace-relative paths.

## Work

- [ ] Compare the current `create_msdos_img.py` copies in `nio-apps`,
      `nio-core-apps`, `nio-config`, and `fujinet-qemu-msdos` and define the
      supported common behavior.
- [ ] Decide between a versioned shared Python package and deliberately
      retained repo-local copies with conformance tests.
- [ ] Provide one manifest loader contract with environment expansion,
      optional entries, filename rules, and deterministic output.
- [ ] Keep QEMU qcow manipulation in `fujinet-qemu-msdos`; expose only a thin
      shared boundary needed by workspace composition.
- [ ] Add golden/conformance tests proving existing MS-DOS raw images and
      workspace manifests retain their filenames, labels, geometry, and files.
- [ ] Review whether BBC SSD staging benefits from the same package or should
      remain a small wrapper around the owner repository's `create_ssd.py`.
- [ ] Remove compatibility target aliases only after callers and documentation
      no longer use them.
- [ ] Update current documentation and archive this task when all consumers use
      the selected boundary.

## Exit criteria

Disk-image builders share a documented and tested implementation boundary,
workspace and standalone repository builds remain independent, existing
public targets produce compatible artifacts, and duplicate code is either
removed or intentionally governed by conformance tests.
