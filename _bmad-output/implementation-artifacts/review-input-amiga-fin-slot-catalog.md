# Review input: Amiga FIN Slot Catalog change

Baseline: `30bb7f42fe72b682b0b7b342a926c64a7be7431a`

## Intent and constraints

`FIN 0 filename.adf` must resolve the filename through the current HostService
path and persist a canonical Slot Catalog URI. FIN and FOUT command syntax,
Slot Catalog/Host/AppStore/DiskDevice wire contracts, and FMOUNT ownership are
unchanged. The unrelated writable-media `CMD_UPDATE` / `Assign DN2: DISMOUNT`
requester regression is expressly out of scope.

## Production diff

`repos/nio-core-apps/src/common/fnsvc.c`

```diff
-static fn_appstore_io_t appstore_io = { req_buf, sizeof(req_buf) };
-static char slot_key_buf[9];
+static fn_slot_catalog_io_t slot_catalog_io = { req_buf, sizeof(req_buf) };
@@ fnsvc_get_mount(uint8_t slot, fnsvc_mount_t *mount)
-  fn_appstore_read_t rr;
+  fn_slot_catalog_entry_t entry;
-  result = fn_appstore_read(&appstore_io, "config-nio", slot_key_buf, 0,
-                            resp_buf, sizeof(resp_buf), &rr);
+  result = fn_slot_catalog_get(&slot_catalog_io, slot, &entry);
+  if (result == FN_ERR_NOT_FOUND)
+    return 1;
   if (result != FN_OK)
     return fail(FNSVC_ERR_TRANSPORT);
-  if ((rr.flags & FN_APPSTORE_READ_EXISTS) == 0)
+  if (!(entry.flags & FN_SLOT_CATALOG_ENTRY_VALID) || entry.uri_len == 0)
     return 1;
-  uri_len = (uint16_t) (rr.bytes_read - 2);
+  uri_len = entry.uri_len;
   mount->enabled = 1;
-  strcpy(mount->mode, (resp_buf[1] & 0x01) ? "r" : "rw");
-  memcpy(mount->uri, resp_buf + 2, uri_len);
+  strcpy(mount->mode, (entry.flags & FN_SLOT_CATALOG_ENTRY_READ_ONLY) ? "r" : "rw");
+  memcpy(mount->uri, entry.uri, uri_len);
@@ fnsvc_set_mount(uint8_t slot, const char *uri, const char *mode, uint8_t enabled)
-  fn_appstore_delete_t dr;
-  fn_appstore_write_t wr;
+  fn_slot_catalog_entry_t entry;
+  uint8_t deleted;
-  if (fn_appstore_delete(&appstore_io, "config-nio", slot_key_buf, &dr) != FN_OK)
-    return fail(FNSVC_ERR_TRANSPORT);
-  if (!enabled)
+  if (!enabled) {
+    if (fn_slot_catalog_delete(&slot_catalog_io, slot, &deleted) != FN_OK)
+      return fail(FNSVC_ERR_TRANSPORT);
     return 1;
+  }
   if (!uri || !uri[0])
     return fail(FNSVC_ERR_INVALID_ARG);
   uri_len = (uint16_t) strlen(uri);
-  if (uri_len > FNSVC_MAX_URI || (size_t) uri_len + 2 > sizeof(resp_buf))
+  if (uri_len > FNSVC_MAX_URI || (size_t) uri_len + 5 > sizeof(req_buf))
     return fail(FNSVC_ERR_REQUEST_TOO_LARGE);
-  /* directly encode v1 AppStore record and write config-nio/slot-NNN */
+  if (fn_slot_catalog_put(&slot_catalog_io, slot,
+                          (uint8_t) (mode && strcmp(mode, "r") == 0
+                                     ? FN_SLOT_CATALOG_ENTRY_READ_ONLY : 0),
+                          uri, &entry) != FN_OK)
     return fail(FNSVC_ERR_TRANSPORT);
```

All manual private `slot-NNN` construction and AppStore record encoding was
removed from the two shared helper functions. `apps/fin.c` and `apps/fout.c`
remain unchanged callers of these helpers.

## Test diff

- New Amiberry case `amiga-fin-slot-catalog` uses a driver-loaded WB3.2 A1200
  environment and this sequence:

```text
FHOST host:/
FIN 0 standard.adf
FMOUNT 0 DN0: RO
Dir DN0:
FIN 1 host:/second.adf
FMOUNT 1 DN1: RO
Dir DN1:
FOUT 0
FMOUNT 0 DN2: RO
```

- Its pytest assertions require:
  - `Slot 0: host:/standard.adf`, a successful `FMOUNT`, and `KNOWN.TXT`;
  - `Slot 1: host:/second.adf`, a successful `FMOUNT`, and `SECOND.TXT`;
  - `FOUT` says slot cleared and a subsequent mount returns RC 10.
- Before the production change, this test failed with
  `Slot 0: standard.adf`; after the change it passes.
- `repos/fujinet-nio/tests/test_slot_catalog_service.cpp` adds a host-side
  regression: after storing `host:/known.adf` in slot 7, a relative Put with
  no current host returns `DeviceNotFound`, and Get still returns the prior
  canonical URI.

## Documentation/artifacts diff

- New `backlog/amiga-fin-slot-catalog.md` records the problem, intended
  `FHOST` → relative `FIN` → `FMOUNT` flow, scope, non-goals, and acceptance
  criteria.
- New BMad spec `spec-amiga-fin-slot-catalog.md` is status `in-review`; its
  frozen intent requires typed Slot Catalog use and excludes any FMOUNT
  fallback for bare paths.

## Verification

- `source scripts/env.sh && make -C repos/nio-core-apps TARGET=amiga` — pass.
- `source ../../scripts/env.sh && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug --output-on-failure` from `repos/fujinet-nio` — pass: 291 doctest cases / 5806 assertions and 23 Python tests.
- `source scripts/env.sh && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_amiga_fin_slot_catalog.py::test_fin_uses_slot_catalog_for_relative_and_full_targets` — pass (1 case; 16 existing Pillow deprecation warnings).
