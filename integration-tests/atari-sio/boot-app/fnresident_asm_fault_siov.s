; Independent packet/SIO fault peer: a PUT may have executed even when W/R
; completion is lost. The handler must drain, never replay, then close once.
        .export _main
        .macpack longbranch
CASE=$06df
WCOUNT=$06c0
COMMITS=$06c1
CLOSES=$06c2
FAULTED=$06c3
RECOVERIES=$06c4
POLLCOUNT=$06c5
BAD_BODY=$06c7
ptr=$b0
        .segment "SIOV"
_main:
        lda $0304
        sta ptr
        lda $0305
        sta ptr+1
        lda $0302
        cmp #'W'
        beq write
        cmp #'P'
        jeq poll
        cmp #'R'
        jeq read
bad:    lda #$8b
        sta $0303
        rts
write:
        inc WCOUNT
        ldy #1
        lda (ptr),y
        sta command
        cmp #4
        bne :+
        inc CLOSES
:       cmp #3
        jne ok
        lda CASE
        cmp #5
        beq partial_write
        ldy #13
        lda (ptr),y
        bne :+
        inc COMMITS
:       lda FAULTED
        jne ok
        lda CASE
        cmp #2
        jne ok
        inc FAULTED              ; accepted W with lost terminal completion
        jmp bad
partial_write:
        ldy #9
        lda (ptr),y
        sta offset
        ldy #13
        lda (ptr),y
        sta length
        bne @body
        inc COMMITS
        lda offset
        cmp #128
        beq ok
        inc BAD_BODY
        bne ok
@body:  lda offset
        ldy #15
        ldx #0
@check: cmp (ptr),y
        beq :+
        inc BAD_BODY
:       clc
        adc #1
        iny
        inx
        cpx length
        bne @check
        lda length
        clc
        adc offset
        cmp #128
        beq ok
        inc BAD_BODY
ok:     lda #1
        sta $0303
        rts
poll:
        lda command
        cmp #3
        bne @ready
        lda CASE
        cmp #3
        bne @ready
        inc POLLCOUNT
        lda POLLCOUNT
        cmp #61
        bcs @ready
        ldy #0
        lda #1                  ; busy for the complete bounded first wait
        sta (ptr),y
        jmp ok
@ready: ldy #0
        lda #2
        sta (ptr),y
        iny
        lda #6
        ldx command
        cpx #4
        beq :+
        lda #13
        cpx #1
        beq :+
        lda #18
:       sta (ptr),y
        iny
        lda #0
        sta (ptr),y
        jmp ok
read:
        lda command
        cmp #3
        bne @copy
        lda CASE
        cmp #4
        bne @copy
        lda FAULTED
        bne @recovered
        inc FAULTED
        jmp bad                 ; retained response after failed R
@recovered:
        inc RECOVERIES
@copy:  lda #<reply_open
        ldx #>reply_open
        ldy command
        cpy #1
        beq @source
        lda #<reply_write
        ldx #>reply_write
        cpy #3
        beq @source
        lda #<reply_close
        ldx #>reply_close
@source:
        sta load+1
        stx load+2
        ldy #0
load:   lda $ffff,y
        sta (ptr),y
        iny
        cpy $0308
        bne load
        lda command
        cmp #3
        jne ok
        lda CASE
        cmp #1
        beq corrupt
        cmp #5
        jne ok
        jmp partial_reply
corrupt:
        ldy #4
        lda #0
        sta (ptr),y             ; executed body, malformed response checksum
        jmp ok
partial_reply:
        ldy #12
        lda offset
        sta (ptr),y
        ldy #16
        lda length
        beq :+
        lda #64
:       sta (ptr),y
        lda #0
        ldy #0
@sum:   cpy #4
        beq :+
        clc
        adc (ptr),y
        adc #0
:       iny
        cpy #18
        bne @sum
        ldy #4
        sta (ptr),y
        jmp ok
offset: .byte 0
length: .byte 0
command:.byte 0
reply_open: .byte $fd,1,13,0,$53,0,1,0,0,0,$34,$12,0
reply_write:.byte $fd,3,18,0,$da,0,1,0,0,0,$34,$12,0,0,0,0,$80,0
reply_close:.byte $fd,4,6,0,$08,0
