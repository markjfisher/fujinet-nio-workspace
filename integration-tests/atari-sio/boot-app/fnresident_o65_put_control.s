; Execute 128 CIO PUT calls through the relocated HATABS vector.  The peer
; accepts precisely one public fn_write() request after the output fn_open().
        .export _main

HATABS = $031A
IOCB = $0340
CC65_ZP = $82
RESULT = $06D0
.ifndef OPEN_MODE
OPEN_MODE = 8
.endif

.segment "CODE"
_main:
        ldx #$ff
        txs
        lda #0
        sta HATABS
        sta $0080
        sta $0081
        sta failure
        sta step
        sta put_count
        lda #$00
        sta $02e7
        lda #$07
        sta $02e8
        lda #$1f
        sta $02e5
        lda #$9c
        sta $02e6
        lda #$20
        sta $0230
        lda #$9c
        sta $0231
        lda #$40
        sta $0058
        lda #$9c
        sta $0059
        jsr $3f00
        ldx #0
fill_zp:
        txa
        eor #$a5
        sta CC65_ZP,x
        inx
        cpx #26
        bne fill_zp
        ldx #$20
        lda #<uri
        sta IOCB+4,x
        lda #>uri
        sta IOCB+5,x
        lda #OPEN_MODE
        sta IOCB+10,x
        lda #$5a
        jsr call_open
        sty RESULT+1
.ifdef ASM_FAILURE_TEST
        lda $06df
        cmp #9
        bne :+
        ldx #$30
        lda #<uri
        sta IOCB+4,x
        lda #>uri
        sta IOCB+5,x
        lda #8
        sta IOCB+10,x
        jsr call_open
        sty RESULT+11
        ldx #$30
        lda #'B'
        jsr call_put
        sty RESULT+12
:
.endif
put_loop:
        lda #'A'
.ifdef ASM_FAILURE_TEST
        ldx $06df
        cpx #5
        bne :+
        lda put_count
:
.endif
        ldx #$20
        jsr call_put
        cpy #1
        beq :+
        sty RESULT+2
:       inc put_count
        lda put_count
        cmp #128
        bne put_loop
.ifdef ASM_FAILURE_TEST
        lda $06df
        cmp #7
        bne :+
        ldx #$20
        jsr call_status
        sty RESULT+9
        ldx #$20
        jsr call_status
        sty RESULT+10
:
.endif
        ldx #$20
        lda #$7c
        jsr call_close
        sty RESULT+3
.ifdef ASM_FAILURE_TEST
        lda $06df
        cmp #9
        bne :+
        ldx #$30
        lda #'C'
        jsr call_put
        sty RESULT+13
        ldx #$30
        jsr call_close
        sty RESULT+14
:
.endif
.ifdef ASM_FAILURE_TEST
        lda #'B'
        ldx #$20
        jsr call_put
        sty RESULT+7             ; failed CLOSE still retired local owner
        ldx #$20
        jsr call_open
        sty RESULT+8             ; released slot can be reused
.endif
        lda failure
        sta RESULT+4
        lda step
        sta RESULT+5
        ldx #0
check_zp:
        txa
        eor #$a5
        cmp CC65_ZP,x
        bne bad_zp
        inx
        cpx #26
        bne check_zp
        lda #0
        beq save_zp
bad_zp: lda #1
save_zp: sta RESULT+6
        lda #1
        sta RESULT
halt:   jmp halt

call_open:
        ldy #0
        jmp call_vector
call_close:
        ldy #2
        jmp call_vector
call_status:
        ldy #8
        jmp call_vector
call_put:
        ldy #6
call_vector:
        sty vector_offset
        pha
        lda HATABS+1
        sta vector_load_lo+1
        sta vector_load_hi+1
        lda HATABS+2
        sta vector_load_lo+2
        sta vector_load_hi+2
        ldy vector_offset
vector_load_lo:
        lda $ffff,y
        clc
        adc #1
        sta vector_call+1
        iny
vector_load_hi:
        lda $ffff,y
        adc #0
        sta vector_call+2
        pla
vector_call:
        jsr $ffff
        rts

uri: .byte "N1:fixture://a", 0
put_count: .byte 0
vector_offset: .byte 0
failure = $E770
step = $E771
