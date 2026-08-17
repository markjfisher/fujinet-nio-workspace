# Disk-image build reference

Disk recipes follow one ownership rule: repository-local images belong to the
repository that owns their contents; images composed from multiple
repositories are workspace artifacts.

## Common workspace targets

| Command | Output/purpose |
| --- | --- |
| `./scripts/build.sh boot-disks` | Build and install platform boot images into `repos/fujinet-nio/distfiles/boot` and `distfiles/esp32-data/boot` |
| `./scripts/build.sh bbc-boot-disk` | Build/install BBC `FN-BOOT.ssd` from `fn-rom`, including configured workspace utilities |
| `./scripts/build.sh master-boot-disk` | Build/install Master `FN-BOOT-M.ssd` |
| `./scripts/build.sh confnio-bbc-disk` | Build standalone BBC `CONFNIO`/diagnostic SSD under `build/images` |
| `./scripts/build.sh confnio-master-disk` | Build the corresponding Master SSD |
| `./scripts/build.sh msdos-apps-image` | Build the workspace raw FAT application image |
| `./scripts/build.sh msdos-boot-config-image` | Build a raw FAT image combining `FUJINET.SYS` with standard config/utilities |
| `./scripts/build.sh qemu-msdos-image` | Build the bootable QEMU MS-DOS qcow2 image |
| `./scripts/build.sh bounce-world-disk` | Build the standalone Bounce World MS-DOS image |

Use `./scripts/build.sh --explain TARGET` for the authoritative dependency and
output description. Exact output paths are also written to
`build/manifest.txt`.

## Workspace manifests

Cross-repository MS-DOS composition is defined under:

```text
manifests/disks/
  msdos-apps.yaml
  msdos-boot-config.yaml
  qemu-msdos-apps.yaml
```

`scripts/build-msdos-manifest-img` supplies those manifests to the raw FAT
image tooling. The QEMU repository retains its own standalone manifest and
must not depend on workspace-relative paths.

## Platform distinctions

- BBC and Master firmware utility disks are owned by `fn-rom`, because their
  transient binaries target the resident ROM ABI. BBC uses `FN-BOOT.ssd` and
  load address `$1900`; Master uses `FN-BOOT-M.ssd` and load address `$0E00`.
- MS-DOS raw FAT images composed from driver, config, and core-utility repos
  are workspace-owned.
- The bootable QEMU hard disk remains owned by `fujinet-qemu-msdos` and is
  orchestrated by the workspace.
- Atari and repository-local application disks remain with their owning app
  repository.

The build-interface rules are documented in
[`build-orchestration.md`](build-orchestration.md). Consolidation of duplicate
disk-image implementation scripts is active work in
[`../backlog/disk-image-tooling-cleanup.md`](../backlog/disk-image-tooling-cleanup.md).
