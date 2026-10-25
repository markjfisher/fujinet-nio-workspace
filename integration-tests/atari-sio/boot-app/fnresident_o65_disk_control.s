; Real-6502 streamed installer control. The CIO stand-in exposes a file at
; $9500, outside every installer/resident write range. $0681 selects a fault.
        .export _main
.segment "CODE"
_main:
        ldx #$ff
        txs
        lda #$e8
        sta $02e7
        lda #$1e
        sta $02e8
        lda #$1f
        sta $02e5
        lda #$9c
        sta $02e6
        sta $0231
        sta $0059
        lda #$20
        sta $0230
        lda #$40
        sta $0058
        lda #$ff
        sta $03b0
        lda $0681
        cmp #3
        bne :+
        lda #$70
        sta $02e8
:       lda $0681
        cmp #4
        bne :+
        lda #$80
        sta $02e6
:
        lda #$4c
        sta $e456
        lda #<cio
        sta $e457
        lda #>cio
        sta $e458
        jsr $6000
        lda $9385
        sta $0682
        lda $0681
        cmp #1
        bne done
        ; Repeat only after the first successful installation.
        ; Keep the file's first 48 bytes available, replace its remaining
        ; content with a full resident snapshot. Any second payload read
        ; would now fail parsing; a valid own-handler path reads only header.
        lda #$e8
        sta $b0
        lda #$1e
        sta $b1
        lda #$30
        sta $b2
        lda #$95
        sta $b3
        lda #$8a
        sta $b4
        lda #$37
        sta $b5
snapshot:
        ldy #0
        lda ($b0),y
        sta ($b2),y
        jsr advance
        bne snapshot
        jsr $6000
        lda #$e8
        sta $b0
        lda #$1e
        sta $b1
        lda #$30
        sta $b2
        lda #$95
        sta $b3
        lda #$8a
        sta $b4
        lda #$37
        sta $b5
compare:
        ldy #0
        lda ($b0),y
        cmp ($b2),y
        bne done
        jsr advance
        bne compare
        inc $0685
done:   lda #1
        sta $0680
halt:   jmp halt
cio:
        lda $0342,x
        cmp #3
        beq open
        cmp #12
        beq close
        lda $0344,x
        sta $b2
        lda $0345,x
        sta $b3
        lda $0348,x
        sta $b4
        lda $0349,x
        sta $b5
loop:
        lda $0681
        cmp #2
        bne copy
        lda $b1
        cmp #$96                 ; simulated early EOF after initial copy
        bcs eof
copy:   ldy #0
        lda ($b0),y
        sta ($b2),y
        jsr advance
        bne loop
ok:     ldy #1
        rts
advance:
        inc $b0
        bne :+
        inc $b1
:       inc $b2
        bne :+
        inc $b3
:       lda $b4
        bne :+
        dec $b5
:       dec $b4
        lda $b4
        ora $b5
        rts
eof:    ldy #136
        rts
open:   inc $0683
        lda #0
        sta $b0
        lda #$95
        sta $b1
        jmp ok
close:  inc $0684
        jmp ok
