ROOT := $(abspath ../../..)
APPS := $(ROOT)/repos/nio-core-apps
PICOBOOT := $(ROOT)/repos/MyPicoDOS/picobootcode-dd.bin
OUT := build
XEX := $(OUT)/boot-acceptance.xex
ATR := $(OUT)/boot-acceptance.atr
RESIDENT_O65_MODULE := $(APPS)/build/atari/bin/fnresident-asm.o65
RESIDENT_ASM_MODULE := $(APPS)/build/atari/bin/fnresident-asm.o65
RESIDENT_O65_LABELS := $(RESIDENT_O65_MODULE:.o65=.lbl)
RESIDENT_O65_STAGE := $(OUT)/fnresident-o65-stage.xex
RESIDENT_O65_LOADER := $(OUT)/fnresident-o65-loader.xex
RESIDENT_O65_PROBE := $(OUT)/fnresident-o65-probe.xex
RESIDENT_O65_XEX := $(OUT)/fnresident-o65-install.xex
RESIDENT_O65_ATR := $(OUT)/fnresident-o65-install.atr
RESIDENT_O65_ALTBASE_XEX := $(OUT)/fnresident-o65-altbase.xex
RESIDENT_O65_ALTBASE_ATR := $(OUT)/fnresident-o65-altbase.atr
RESIDENT_O65_OVERLAP_XEX := $(OUT)/fnresident-o65-overlap.xex
RESIDENT_O65_OVERLAP_ATR := $(OUT)/fnresident-o65-overlap.atr
RESIDENT_O65_FOREIGN_XEX := $(OUT)/fnresident-o65-foreign.xex
RESIDENT_O65_FOREIGN_ATR := $(OUT)/fnresident-o65-foreign.atr
RESIDENT_O65_OPEN_PROBE := $(OUT)/fnresident-o65-open-probe.xex
RESIDENT_O65_OPEN_XEX := $(OUT)/fnresident-o65-open.xex
RESIDENT_O65_OPEN_ATR := $(OUT)/fnresident-o65-open.atr
RESIDENT_O65_MYDOS_ATR := $(OUT)/fnresident-o65-mydos-basic.atr
RESIDENT_ASM_DISK_LOADER := $(OUT)/fnresident-asm-disk-loader.xex
RESIDENT_O65_DISK_IMAGE := $(OUT)/nio.o65
MYDOS_PLAIN_ATR := $(OUT)/mydos-4534-plain.atr
TBXL_PARSER := $(OUT)/tools/basicParser-v12-0-ga877718/basicParser
RESIDENT_O65_BASIC_SOURCE := fnresident_basic_read.bas
RESIDENT_O65_BASIC_PROGRAM := $(OUT)/fnread.bas
RESIDENT_O65_BASIC_WRITE := $(OUT)/fnwrite.bas
RESIDENT_O65_BASIC_POST := $(OUT)/fnpost.bas
RESIDENT_O65_BASIC_STALE := $(OUT)/fnstale.bas
RESIDENT_O65_BASIC_STALE_READ := $(OUT)/fnstread.bas
RESIDENT_O65_BASIC_MANUAL_RESET := $(OUT)/fnreset.bas
RESIDENT_O65_OPEN_CONTROL := $(OUT)/fnresident-o65-open-control.bin
RESIDENT_O65_OPEN_SIOV := $(OUT)/fnresident-o65-open-siov.xex
RESIDENT_O65_GET_CLOSE_CONTROL := $(OUT)/fnresident-o65-get-close-control.bin
RESIDENT_O65_GET_CLOSE_SIOV := $(OUT)/fnresident-o65-get-close-siov.xex
RESIDENT_O65_PUT_CONTROL := $(OUT)/fnresident-o65-put-control.bin
RESIDENT_O65_PUT_SIOV := $(OUT)/fnresident-o65-put-siov.xex

.PHONY: all resident-o65 resident-o65-altbase resident-o65-overlap resident-o65-foreign resident-o65-open resident-o65-mydos-basic mydos-plain test-resident-o65 clean
all: $(ATR)
resident-o65: $(RESIDENT_O65_ATR)
resident-o65-altbase: $(RESIDENT_O65_ALTBASE_ATR)
resident-o65-overlap: $(RESIDENT_O65_OVERLAP_ATR)
resident-o65-foreign: $(RESIDENT_O65_FOREIGN_ATR)
resident-o65-open: $(RESIDENT_O65_OPEN_ATR)
resident-o65-mydos-basic: $(RESIDENT_O65_MYDOS_ATR)
mydos-plain: $(MYDOS_PLAIN_ATR)

$(OUT):
	mkdir -p $@

$(XEX): boot_acceptance.s atari-xex.cfg | $(OUT)
	cl65 -t none -C atari-xex.cfg -o $@ $<

$(PICOBOOT):
	$(MAKE) -C $(ROOT)/repos/MyPicoDOS picobootcode-dd.bin

$(ATR): $(XEX) $(PICOBOOT) Makefile | $(OUT)
	rm -rf $(OUT)/stage
	mkdir -p $(OUT)/stage
	cp $(XEX) $(OUT)/stage/coltest.xex
	cd $(APPS) && dir2atr -m -D -B $(PICOBOOT) $(abspath $@) $(abspath $(OUT)/stage)

$(RESIDENT_O65_MODULE):
	$(MAKE) -C $(APPS) -f makefiles/build.mk TARGET=atari fnresident-asm

$(RESIDENT_O65_LABELS): $(RESIDENT_O65_MODULE)

$(RESIDENT_O65_STAGE): $(RESIDENT_O65_MODULE) $(RESIDENT_O65_LABELS) ../make_resident_o65_image.py Makefile | $(OUT)
	python3 ../make_resident_o65_image.py --module $(RESIDENT_O65_MODULE) --labels $(RESIDENT_O65_LABELS) --cstack 0 --stage 0x4900 --max-stage-end 0x9380 --output $@

$(RESIDENT_O65_LOADER): $(APPS)/apps/platform/atari/resident/fnresident_o65_loader.s fnresident-o65-loader.cfg Makefile | $(OUT)
	cl65 -t none --asm-define ASM_RESIDENT=1 -C fnresident-o65-loader.cfg -o $@ $(APPS)/apps/platform/atari/resident/fnresident_o65_loader.s

$(RESIDENT_O65_PROBE): fnresident_o65_probe.s fnresident-o65-probe.cfg | $(OUT)
	cl65 -t none -C fnresident-o65-probe.cfg -o $@ fnresident_o65_probe.s

$(RESIDENT_O65_XEX): $(RESIDENT_O65_LOADER) $(RESIDENT_O65_STAGE) $(RESIDENT_O65_PROBE) ../compose_resident_o65_xex.py | $(OUT)
	python3 ../compose_resident_o65_xex.py --loader $(RESIDENT_O65_LOADER) --staged $(RESIDENT_O65_STAGE) --probe $(RESIDENT_O65_PROBE) --output $@

$(RESIDENT_O65_ALTBASE_XEX): $(RESIDENT_O65_LOADER) $(RESIDENT_O65_STAGE) $(RESIDENT_O65_PROBE) ../compose_resident_o65_xex.py | $(OUT)
	python3 ../compose_resident_o65_xex.py --memlo 0x0702 --loader $(RESIDENT_O65_LOADER) --staged $(RESIDENT_O65_STAGE) --probe $(RESIDENT_O65_PROBE) --output $@

$(RESIDENT_O65_OVERLAP_XEX): $(RESIDENT_O65_LOADER) $(RESIDENT_O65_STAGE) $(RESIDENT_O65_PROBE) ../compose_resident_o65_xex.py | $(OUT)
	python3 ../compose_resident_o65_xex.py --repeat --loader $(RESIDENT_O65_LOADER) --staged $(RESIDENT_O65_STAGE) --probe $(RESIDENT_O65_PROBE) --output $@

$(RESIDENT_O65_FOREIGN_XEX): $(RESIDENT_O65_LOADER) $(RESIDENT_O65_STAGE) $(RESIDENT_O65_PROBE) ../compose_resident_o65_xex.py | $(OUT)
	python3 ../compose_resident_o65_xex.py --foreign --loader $(RESIDENT_O65_LOADER) --staged $(RESIDENT_O65_STAGE) --probe $(RESIDENT_O65_PROBE) --output $@

$(RESIDENT_O65_OPEN_PROBE): fnresident_o65_open_probe.s fnresident-o65-open-probe.cfg Makefile | $(OUT)
	cl65 -t none --start-addr 0x5800 -C fnresident-o65-open-probe.cfg -o $@ $<

$(RESIDENT_O65_OPEN_XEX): $(RESIDENT_O65_LOADER) $(RESIDENT_O65_STAGE) $(RESIDENT_O65_OPEN_PROBE) ../compose_resident_o65_xex.py | $(OUT)
	python3 ../compose_resident_o65_xex.py --loader $(RESIDENT_O65_LOADER) --staged $(RESIDENT_O65_STAGE) --probe $(RESIDENT_O65_OPEN_PROBE) --output $@

$(TBXL_PARSER): ../fetch_tbxl_parser.py | $(OUT)
ifeq ($(DOS25_OFFLINE),1)
	@echo 'BASIC parser missing; provision it before the offline build' >&2; exit 1
else
	python3 ../fetch_tbxl_parser.py --output $@
endif

$(RESIDENT_O65_BASIC_PROGRAM): $(RESIDENT_O65_BASIC_SOURCE) $(TBXL_PARSER) | $(OUT)
	$(TBXL_PARSER) -A -q -o $@ $<

$(RESIDENT_O65_BASIC_WRITE): fnresident_basic_write.bas $(TBXL_PARSER) | $(OUT)
	$(TBXL_PARSER) -A -q -o $@ $<

$(RESIDENT_O65_BASIC_POST): fnresident_basic_post.bas $(TBXL_PARSER) | $(OUT)
	$(TBXL_PARSER) -A -q -o $@ $<

$(RESIDENT_O65_BASIC_STALE): fnresident_basic_stale.bas $(TBXL_PARSER) | $(OUT)
	$(TBXL_PARSER) -A -q -o $@ $<

$(RESIDENT_O65_BASIC_STALE_READ): fnresident_basic_stale_read.bas $(TBXL_PARSER) | $(OUT)
	$(TBXL_PARSER) -A -q -o $@ $<

$(RESIDENT_O65_BASIC_MANUAL_RESET): fnresident_basic_manual_reset.bas $(TBXL_PARSER) | $(OUT)
	$(TBXL_PARSER) -A -q -o $@ $<

$(RESIDENT_O65_ATR): $(RESIDENT_O65_XEX) $(PICOBOOT) Makefile | $(OUT)
	rm -rf $(OUT)/resident-o65-stage
	mkdir -p $(OUT)/resident-o65-stage
	cp $(RESIDENT_O65_XEX) $(OUT)/resident-o65-stage/coltest.xex
	cd $(APPS) && dir2atr -m -D -B $(PICOBOOT) $(abspath $@) $(abspath $(OUT)/resident-o65-stage)

$(RESIDENT_O65_ALTBASE_ATR): $(RESIDENT_O65_ALTBASE_XEX) $(PICOBOOT) Makefile | $(OUT)
	rm -rf $(OUT)/resident-o65-altbase-stage
	mkdir -p $(OUT)/resident-o65-altbase-stage
	cp $(RESIDENT_O65_ALTBASE_XEX) $(OUT)/resident-o65-altbase-stage/coltest.xex
	cd $(APPS) && dir2atr -m -D -B $(PICOBOOT) $(abspath $@) $(abspath $(OUT)/resident-o65-altbase-stage)

$(RESIDENT_O65_OVERLAP_ATR): $(RESIDENT_O65_OVERLAP_XEX) $(PICOBOOT) Makefile | $(OUT)
	rm -rf $(OUT)/resident-o65-overlap-stage
	mkdir -p $(OUT)/resident-o65-overlap-stage
	cp $(RESIDENT_O65_OVERLAP_XEX) $(OUT)/resident-o65-overlap-stage/coltest.xex
	cd $(APPS) && dir2atr -m -D -B $(PICOBOOT) $(abspath $@) $(abspath $(OUT)/resident-o65-overlap-stage)

$(RESIDENT_O65_FOREIGN_ATR): $(RESIDENT_O65_FOREIGN_XEX) $(PICOBOOT) Makefile | $(OUT)
	rm -rf $(OUT)/resident-o65-foreign-stage
	mkdir -p $(OUT)/resident-o65-foreign-stage
	cp $(RESIDENT_O65_FOREIGN_XEX) $(OUT)/resident-o65-foreign-stage/coltest.xex
	cd $(APPS) && dir2atr -m -D -B $(PICOBOOT) $(abspath $@) $(abspath $(OUT)/resident-o65-foreign-stage)

$(RESIDENT_O65_OPEN_ATR): $(RESIDENT_O65_OPEN_XEX) $(PICOBOOT) Makefile | $(OUT)
	rm -rf $(OUT)/resident-o65-open-stage
	mkdir -p $(OUT)/resident-o65-open-stage
	cp $(RESIDENT_O65_OPEN_XEX) $(OUT)/resident-o65-open-stage/coltest.xex
	cd $(APPS) && dir2atr -m -D -B $(PICOBOOT) $(abspath $@) $(abspath $(OUT)/resident-o65-open-stage)

# MyDOS 4.53/4's checked-in DOS.SYS/DUP.SYS pair matches dir2atr's MyDos4534
# boot sectors. MyDOS natively auto-loads NIO.AR0 during normal startup.
$(RESIDENT_ASM_DISK_LOADER): $(APPS)/apps/platform/atari/resident/fnresident_o65_loader.s fnresident-o65-disk-loader.cfg | $(OUT)
	cl65 -t none --asm-define DISK_SOURCE=1 --asm-define ASM_RESIDENT=1 -C fnresident-o65-disk-loader.cfg -Ln $(@:.xex=.lbl) -o $@ $<

$(OUT)/fnresident-asm-loader.xex: $(APPS)/apps/platform/atari/resident/fnresident_o65_loader.s fnresident-o65-loader.cfg | $(OUT)
	cl65 -t none --asm-define ASM_RESIDENT=1 -C fnresident-o65-loader.cfg -o $@ $<

.PHONY: resident-asm-build
resident-asm-build:
	$(MAKE) -C $(APPS) -f makefiles/build.mk TARGET=atari fnresident-asm

$(RESIDENT_O65_DISK_IMAGE): resident-asm-build ../make_resident_o65_image.py | $(OUT)
	python3 ../make_resident_o65_image.py --module $(RESIDENT_ASM_MODULE) --labels $(RESIDENT_ASM_MODULE:.o65=.lbl) --cstack 0 --output $@

$(OUT)/fnresident-asm-stage.xex: $(RESIDENT_O65_DISK_IMAGE)
	python3 ../make_resident_o65_image.py --module $(RESIDENT_ASM_MODULE) --labels $(RESIDENT_ASM_MODULE:.o65=.lbl) --cstack 0 --stage 0x4900 --max-stage-end 0x9380 --output $@

.PHONY: test-resident-asm
test-resident-asm: $(OUT)/fnresident-asm-stage.xex $(OUT)/fnresident-asm-loader.xex $(RESIDENT_ASM_DISK_LOADER) $(RESIDENT_O65_OPEN_CONTROL) $(RESIDENT_O65_OPEN_SIOV) $(RESIDENT_O65_GET_CLOSE_CONTROL) $(RESIDENT_O65_GET_CLOSE_SIOV) $(RESIDENT_O65_PUT_CONTROL) $(RESIDENT_O65_PUT_SIOV) $(OUT)/fnresident-asm-open.xex
	python3 ../test_resident_asm.py

$(OUT)/fnresident-asm-open-probe.xex: fnresident_o65_open_probe.s fnresident-o65-open-probe.cfg | $(OUT)
	cl65 -t none --start-addr 0x5800 -C fnresident-o65-open-probe.cfg -o $@ $<

$(OUT)/fnresident-asm-open.xex: $(OUT)/fnresident-asm-stage.xex $(OUT)/fnresident-asm-loader.xex $(OUT)/fnresident-asm-open-probe.xex ../compose_resident_o65_xex.py
	python3 ../compose_resident_o65_xex.py --loader $(OUT)/fnresident-asm-loader.xex --staged $(OUT)/fnresident-asm-stage.xex --probe $(OUT)/fnresident-asm-open-probe.xex --output $@

$(RESIDENT_O65_MYDOS_ATR): $(RESIDENT_ASM_DISK_LOADER) $(RESIDENT_O65_DISK_IMAGE) $(RESIDENT_O65_BASIC_PROGRAM) $(RESIDENT_O65_BASIC_WRITE) $(RESIDENT_O65_BASIC_POST) $(RESIDENT_O65_BASIC_STALE) $(RESIDENT_O65_BASIC_STALE_READ) $(RESIDENT_O65_BASIC_MANUAL_RESET) Makefile | $(OUT)
	rm -rf $(OUT)/resident-o65-mydos-stage
	mkdir -p $(OUT)/resident-o65-mydos-stage
	cp $(ROOT)/repos/MyPicoDOS/mydos-dos.sys $(OUT)/resident-o65-mydos-stage/DOS.SYS
	cp $(ROOT)/repos/MyPicoDOS/mydos-dup.sys $(OUT)/resident-o65-mydos-stage/DUP.SYS
	cp $(RESIDENT_ASM_DISK_LOADER) $(OUT)/resident-o65-mydos-stage/NIO.AR0
	cp $(RESIDENT_O65_DISK_IMAGE) $(OUT)/resident-o65-mydos-stage/NIO.O65
	cp $(RESIDENT_O65_BASIC_PROGRAM) $(OUT)/resident-o65-mydos-stage/fnread.bas
	cp $(RESIDENT_O65_BASIC_WRITE) $(OUT)/resident-o65-mydos-stage/fnwrite.bas
	cp $(RESIDENT_O65_BASIC_POST) $(OUT)/resident-o65-mydos-stage/fnpost.bas
	cp $(RESIDENT_O65_BASIC_STALE) $(OUT)/resident-o65-mydos-stage/fnstale.bas
	cp $(RESIDENT_O65_BASIC_STALE_READ) $(OUT)/resident-o65-mydos-stage/fnstread.bas
	cp $(RESIDENT_O65_BASIC_MANUAL_RESET) $(OUT)/resident-o65-mydos-stage/fnreset.bas
	cd $(APPS) && dir2atr -m -S -b MyDos4534 $(abspath $@) $(abspath $(OUT)/resident-o65-mydos-stage)

# Baseline for the virtual-D1 diagnosis: the matching checked-in MyDOS 4.53/4
# files only, deliberately no AR0 startup payload, NIO image, or BASIC program.
$(MYDOS_PLAIN_ATR): Makefile | $(OUT)
	rm -rf $(OUT)/mydos-plain-stage
	mkdir -p $(OUT)/mydos-plain-stage
	cp $(ROOT)/repos/MyPicoDOS/mydos-dos.sys $(OUT)/mydos-plain-stage/DOS.SYS
	cp $(ROOT)/repos/MyPicoDOS/mydos-dup.sys $(OUT)/mydos-plain-stage/DUP.SYS
	cd $(APPS) && dir2atr -m -S -b MyDos4534 $(abspath $@) $(abspath $(OUT)/mydos-plain-stage)

$(RESIDENT_O65_OPEN_CONTROL): fnresident_o65_open_control.s fnresident-o65-loader-control.cfg | $(OUT)
	cl65 -t none -C fnresident-o65-loader-control.cfg -o $@ fnresident_o65_open_control.s

$(RESIDENT_O65_OPEN_SIOV): fnresident_o65_open_siov.s fnresident-o65-open-siov.cfg | $(OUT)
	cl65 -t none -C fnresident-o65-open-siov.cfg -o $@ fnresident_o65_open_siov.s

$(RESIDENT_O65_GET_CLOSE_CONTROL): fnresident_o65_get_close_control.s fnresident-o65-loader-control.cfg | $(OUT)
	cl65 -t none -C fnresident-o65-loader-control.cfg -o $@ fnresident_o65_get_close_control.s

$(RESIDENT_O65_GET_CLOSE_SIOV): fnresident_o65_get_close_siov.s fnresident-o65-open-siov.cfg | $(OUT)
	cl65 -t none -C fnresident-o65-open-siov.cfg -o $@ fnresident_o65_get_close_siov.s

$(RESIDENT_O65_PUT_CONTROL): fnresident_o65_put_control.s fnresident-o65-loader-control.cfg | $(OUT)
	cl65 -t none -C fnresident-o65-loader-control.cfg -o $@ fnresident_o65_put_control.s

$(RESIDENT_O65_PUT_SIOV): fnresident_o65_put_siov.s fnresident-o65-open-siov.cfg | $(OUT)
	cl65 -t none -C fnresident-o65-open-siov.cfg -o $@ fnresident_o65_put_siov.s

# The staged and streamed production controls are exercised together.
test-resident-o65: test-resident-asm

clean:
	rm -rf $(OUT)

.PHONY: test-resident-o65-disk
test-resident-o65-disk: test-resident-asm

# Explicitly provision media and parser before these offline targets.
DOS25_CONFIG_ATR := $(ROOT)/repos/fujinet-nio/distfiles/boot/atari/autorun.atr
DOS25_CONFIG_ESP := $(ROOT)/repos/fujinet-nio/distfiles/esp32-data/boot/atari/autorun.atr
DOS25_PROTECTED := --protect "$(DOS25_CONFIG_ATR)" --protect "$(DOS25_CONFIG_ESP)" --protect "$(APPS)/build/atari/disk/boot/autorun.atr" --protect "$(TBXL_PARSER)"
DOS25_MODULE_FILES := $(RESIDENT_ASM_MODULE) $(RESIDENT_O65_LABELS) $(RESIDENT_ASM_MODULE:.o65=.map) $(RESIDENT_ASM_MODULE:.o65=.o)
DOS25_OUTPUTS := --output "$(OUT)/dos25-clean.atr" --output "$(OUT)/dos25-resident.atr" --output "$(RESIDENT_ASM_DISK_LOADER)" --output "$(RESIDENT_ASM_DISK_LOADER:.xex=.lbl)" --output "$(RESIDENT_O65_DISK_IMAGE)" --output "$(RESIDENT_O65_BASIC_PROGRAM)" --output "$(RESIDENT_O65_BASIC_WRITE)" --output "$(RESIDENT_O65_BASIC_POST)"

.PHONY: clean-dos25 resident-dos25-basic
clean-dos25:
	@test -n "$(DOS25_SOURCE)" || { echo 'Set DOS25_SOURCE to the verified DOS 2.5 source ATR' >&2; exit 1; }
	python3 make-dos25-atr.py clean "$(DOS25_SOURCE)" "$(OUT)" $(DOS25_PROTECTED) $(foreach f,$(RESIDENT_ASM_DISK_LOADER) $(RESIDENT_O65_DISK_IMAGE) $(RESIDENT_O65_BASIC_PROGRAM) $(RESIDENT_O65_BASIC_WRITE) $(RESIDENT_O65_BASIC_POST) $(RESIDENT_ASM_DISK_LOADER:.xex=.lbl) $(OUT)/dos25-resident.atr $(DOS25_MODULE_FILES),--protect "$(f)")

resident-dos25-basic:
	@test -n "$(DOS25_SOURCE)" || { echo 'Set DOS25_SOURCE to the verified DOS 2.5 source ATR' >&2; exit 1; }
	@python3 -c 'import hashlib,os,sys; p=sys.argv[1]; sys.exit(0 if os.access(p,os.X_OK) and hashlib.sha256(open(p,"rb").read()).hexdigest()=="ac65c8308d4c3fd851057aa61bd66a80fce61f54f56da0ef3e378835ce141200" else "BASIC parser missing or checksum mismatch")' "$(TBXL_PARSER)"
	python3 make-dos25-atr.py preflight "$(DOS25_SOURCE)" "$(OUT)" $(DOS25_OUTPUTS) $(foreach f,$(DOS25_MODULE_FILES),--output "$(f)") $(DOS25_PROTECTED)
	$(MAKE) DOS25_OFFLINE=1 $(RESIDENT_ASM_DISK_LOADER) $(RESIDENT_O65_DISK_IMAGE) $(RESIDENT_O65_BASIC_PROGRAM) $(RESIDENT_O65_BASIC_WRITE) $(RESIDENT_O65_BASIC_POST)
	python3 make-dos25-atr.py clean "$(DOS25_SOURCE)" "$(OUT)" $(DOS25_PROTECTED) $(foreach f,$(RESIDENT_ASM_DISK_LOADER) $(RESIDENT_O65_DISK_IMAGE) $(RESIDENT_O65_BASIC_PROGRAM) $(RESIDENT_O65_BASIC_WRITE) $(RESIDENT_O65_BASIC_POST) $(RESIDENT_ASM_DISK_LOADER:.xex=.lbl) $(OUT)/dos25-resident.atr $(DOS25_MODULE_FILES),--protect "$(f)")
	python3 make-dos25-atr.py resident "$(DOS25_SOURCE)" "$(OUT)" $(DOS25_PROTECTED) $(foreach f,$(DOS25_MODULE_FILES),--protect "$(f)")

# SDX cartridge and parser are locally provisioned; no download or DOS binary
# is included in the generated direct-disk fixture.
.PHONY: sdx-fixture
sdx-fixture:
	@test -n "$(SDX_CART)" || { echo 'Set SDX_CART to the verified SDX 4.51 cartridge' >&2; exit 1; }
	python3 ../sdx-parent-child/preflight.py --car "$(SDX_CART)" --parser "$(TBXL_PARSER)" --out "$(OUT)"
	$(MAKE) DOS25_OFFLINE=1 $(RESIDENT_O65_DISK_IMAGE) $(RESIDENT_O65_BASIC_PROGRAM) $(RESIDENT_O65_BASIC_WRITE) $(RESIDENT_O65_BASIC_POST)
	python3 ../sdx-parent-child/build.py "$(OUT)/sdx-fixture.atr" --resident-build "$(OUT)"
