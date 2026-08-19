# AmigaOS Environment Setup

This document covers the full lifecycle for AmigaOS test environments: configuring
licensed media paths, creating machine profiles, building environments, and running tests.

## Architecture overview

```
local/amiga.env          ← licensed media paths (gitignored, never committed)
       │
       ▼
configs/amiga/environments/*.yaml   ← OS installation recipe (no local paths)
configs/amiga/machines/*.yaml       ← machine hardware profile (UAE settings)
       │
       ▼
scripts/amiga-env build <env_id> [--machine <machine_id>]
       │
       ▼
build/amiga-envs/<env_id>/[<machine_id>/]
       ├── base.hdf         ← assembled from licensed media; gitignored
       └── manifest.json    ← build fingerprint and resolved paths
       │
       ▼
scripts/amiga-tests --amiga-env <env_id> [--amiga-machine <machine_id>]
```

Licensed AmigaOS data is not committed to git. `build/amiga-envs/` is gitignored.
The `manifest.json` records absolute paths and a SHA-256 content hash used for
cache invalidation.

---

## Step 1 — Populate `local/amiga.env`

Copy the example file and fill in your local paths:

```bash
cp local/amiga.env.example local/amiga.env
$EDITOR local/amiga.env
```

`local/amiga.env` is gitignored and must never be committed. It contains only
paths to licensed media — nothing derivable from recipes or builds.

### Variables by OS version

**WB3.1 (Amiga Forever or original disks):**

```bash
AMIGA_WB31_KICKSTART=/path/to/kick40063.A1200.rom
AMIGA_WB31_ROM_KEY=/path/to/rom.key          # omit if not needed
AMIGA_WB31_ADF_INSTALL=/path/to/amiga-os-310-install.adf
AMIGA_WB31_ADF_WORKBENCH=/path/to/amiga-os-310-workbench.adf
AMIGA_WB31_ADF_EXTRAS=/path/to/amiga-os-310-extras.adf
AMIGA_WB31_ADF_STORAGE=/path/to/amiga-os-310-storage.adf
AMIGA_WB31_ADF_LOCALE=/path/to/amiga-os-310-locale.adf
AMIGA_WB31_ADF_FONTS=/path/to/amiga-os-310-fonts.adf
```

**WB3.2 (generic media, shared across machines):**

```bash
AMIGA_WB32_KICKSTART=/path/to/kickCDTVa1000a500a2000a600.rom
AMIGA_WB32_ADF_WORKBENCH=/path/to/Workbench3.2.adf
AMIGA_WB32_ADF_EXTRAS=/path/to/Extras3.2.adf
```

**WB3.2 (machine-specific Modules ADF — one per hardware family):**

```bash
AMIGA_WB32_ADF_MODULES_A1200=/path/to/ModulesA1200_3.2.adf
AMIGA_WB32_ADF_MODULES_A500=/path/to/ModulesA500_3.2.adf
# add AMIGA_WB32_ADF_MODULES_A2000 etc. when needed
```

The Modules ADF is machine-specific because it contains chipset drivers. The generic
Workbench and Extras ADFs are shared; only the Modules ADF differs per machine family.

---

## Step 2 — Understand environment recipes

Environment recipes live in `configs/amiga/environments/*.yaml`. They contain no
local paths — only the names of `local/amiga.env` variables to resolve at build time.

### Machine-agnostic environments (e.g. `wb31`)

Build output goes to `build/amiga-envs/<env_id>/base.hdf`.

```bash
scripts/amiga-env build wb31
```

### Machine-keyed environments (e.g. `wb32`)

`wb32` uses `machine_modules: required`. The environment recipe only describes
generic Workbench and Extras content; the machine-specific Modules ADF is declared
by the machine profile. You must always supply `--machine`:

```bash
scripts/amiga-env build wb32 --machine a1200-030
scripts/amiga-env build wb32 --machine a500-030
```

Build output: `build/amiga-envs/wb32/a1200-030/base.hdf`, etc.

---

## Step 3 — Machine profiles

Machine profiles live in `configs/amiga/machines/*.yaml`. They are committed to git
(they contain no licensed data — only hardware configuration).

### Profile structure

```yaml
id: a500-030
display_name: "Amiga 500 (68030)"

# Base UAE config file, relative to configs/amiga/.
# Defines cpu_model, fpu_model, and other invariants for this CPU class.
uae_config: base-68030.uae

# UAE/Amiberry key=value overrides, applied as -s flags after uae_config.
# Use actual UAE setting names — not invented abstractions.
settings:
  chipset: ecs
  chipmem_size: 2
  fastmem_size: 2
  cpu_speed: max

# For environments with machine_modules: required, declare the env variable
# name that points to the machine-specific Modules ADF.
os_modules:
  wb32: AMIGA_WB32_ADF_MODULES_A500
```

The `uae_config` file (e.g. `base-68030.uae`) sets CPU model and FPU model. The
`settings:` dict overrides chipset, RAM, and speed — only what differs per machine.

### Creating a new machine profile

1. Create `configs/amiga/machines/<machine_id>.yaml` following the structure above.
2. Choose a `uae_config` base file from `configs/amiga/` that matches the CPU class:
   - `base.uae` — 68000
   - `base-68030.uae` — 68030/68882
3. Set `settings:` with UAE keys for this machine's chipset, RAM, and speed.
4. If you need `wb32`, add `os_modules.wb32: AMIGA_WB32_ADF_MODULES_<FAMILY>` and
   ensure that variable is set in `local/amiga.env`.

### Existing machine profiles

| Profile ID   | CPU    | Chipset | Chip RAM | Fast RAM | `uae_config`    |
|-------------|--------|---------|----------|----------|-----------------|
| `a1200-030` | 68030  | AGA     | 4M       | 8M       | base-68030.uae  |
| `a500-000`  | 68000  | OCS     | 1M       | 0        | base.uae        |
| `a500-030`  | 68030  | ECS     | 2M       | 2M       | base-68030.uae  |

---

## Step 4 — Build environments

```bash
# Machine-agnostic
scripts/amiga-env build wb31

# Machine-keyed (required for wb32)
scripts/amiga-env build wb32 --machine a1200-030
scripts/amiga-env build wb32 --machine a500-030

# Force rebuild even if inputs are unchanged
scripts/amiga-env build wb32 --machine a1200-030 --force
```

The builder reads `local/amiga.env`, resolves all variable references from the recipe
and machine profile, unpacks ADFs using `xdftool`, overlays them in the order defined
by the method, and packs the result into an HDF. Build artifacts:

```
build/amiga-envs/
  wb31/
    base.hdf
    manifest.json
  wb32/
    a1200-030/
      base.hdf
      manifest.json
    a500-030/
      base.hdf
      manifest.json
```

### Check build status

```bash
scripts/amiga-env status
```

This lists all built environments and whether their inputs are still current (content
hash matches the manifest's `input_hash`).

### Inspect a built environment

```bash
scripts/amiga-env show wb31
scripts/amiga-env show wb32 --machine a1200-030
scripts/amiga-env show wb32 --machine a1200-030 kickstart
```

---

## Step 5 — Run tests

```bash
# Run full suite against a machine-agnostic environment
scripts/amiga-tests --amiga-env wb31 --run-amiga

# Run full suite against a machine-keyed environment
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 --run-amiga

# Run a focused test
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 \
  --run-amiga -k test_fmount_fumount_standard_adf

# Verbose output
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 --run-amiga -v
```

`scripts/amiga-tests` is a thin wrapper around `uv run pytest`. Any pytest arguments
can follow the `--amiga-env`/`--amiga-machine` flags.

---

## Example: building and testing `wb32/a500-030`

Given that `configs/amiga/machines/a500-030.yaml` exists (it does) and
`AMIGA_WB32_ADF_MODULES_A500` is set in `local/amiga.env`:

```bash
# 1. Build the environment
scripts/amiga-env build wb32 --machine a500-030

# 2. Verify it was built
scripts/amiga-env status

# 3. Run tests
scripts/amiga-tests --amiga-env wb32 --amiga-machine a500-030 --run-amiga
```

If `AMIGA_WB32_ADF_MODULES_A500` is not set in `local/amiga.env`, the build step
will print a clear error naming the missing variable.

---

## Troubleshooting

**"AmigaOS environment 'wb32/a500-030' has not been built"**
Run `scripts/amiga-env build wb32 --machine a500-030`.

**"Variable AMIGA_WB32_ADF_MODULES_A500 is not set"**
Add that variable to `local/amiga.env` pointing to your local Modules ADF for the A500.

**"Amiberry UAE configuration not found: base-68030.uae"**
The `uae_config` in the machine profile is resolved relative to `configs/amiga/`. Check
that the file exists at `configs/amiga/base-68030.uae`.

**Build output is stale / using old media**
Run `scripts/amiga-env build wb32 --machine a500-030 --force` to bypass the content-hash
cache and rebuild unconditionally.
