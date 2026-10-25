; Experimental SDX parent allocation / U_LOAD ownership probe only.
; $0400-$06ff is SDX's documented transient initialization scratch.
.export _main, malloc_ref, install_ref, uload_ref, file_ref, flag_ref
.ifndef PARENT_ALLOC
PARENT_ALLOC = $091f
.endif
.segment "CODE"
_main:
        ; U_LOAD can abort the command without returning here on file error.
        lda #'F'
        sta $06a0
        lda #<PARENT_ALLOC
        sta $0785
        lda #>PARENT_ALLOC
        sta $0786
        ldx #0
        ldy #0
        jsr malloc_call
        bpl :+
        jmp failed
:
        lda $0782
        sta $06a4
        sta $80
        lda $0783
        sta $06a5
        sta $81
.ifndef SDX_RESIDENT_PROTOTYPE
        ldx #9
@page: ldy #0
        lda #$a5
@byte: sta ($80),y
        iny
        bne @byte
        inc $81
        dex
        bne @page
        ldy #0
@tail: sta ($80),y
        iny
        cpy #31
        bne @tail
.endif
        lda $02e7
        sta $06a6
        lda $02e8
        sta $06a7
        lda file_ref
        sta $80
        lda file_ref+1
        sta $81
        ldy #0
        lda #<child_name
        sta ($80),y
        iny
        lda #>child_name
        sta ($80),y
        lda flag_ref
        sta $80
        lda flag_ref+1
        sta $81
        ldy #0
        lda #0
        sta ($80),y
.ifdef SDX_RESIDENT_PROTOTYPE
        ; A failed U_LOAD may never run the child. Invalidate any result left
        ; by an earlier invocation before requesting the load.
        ldx #5
        lda #0
@clear_result:
        sta $06b0,x
        dex
        bpl @clear_result
.endif
        jsr uload_call
.ifdef SDX_RESIDENT_PROTOTYPE
        lda $06b0
        cmp #'N'
        beq :+
        jmp failed
:
        lda $06b1
        cmp #'R'
        beq :+
        jmp failed
:
        lda $06b2
        cmp #'I'
        beq :+
        jmp failed
:
        lda $06b3
        cmp #'!'
        beq :+
        jmp failed
:
        lda $06b4
        cmp #2
        beq :+
        jmp failed
:
        lda $06b5
        beq :+
        jmp failed
:
.endif
        lda $02e7
        sta $06a8
        lda $02e8
        sta $06a9
        lda install_ref
        sta $80
        lda install_ref+1
        sta $81
        ldy #0
        lda #$ff
        sta ($80),y
        lda #'P'
        sta $06a0
        lda #'R'
        sta $06a1
        lda #'O'
        sta $06a2
        lda #'K'
        sta $06a3
        rts
failed: lda #'F'
        sta $06a0
        ; IOCB 0 is the SDX console. Report failure before returning so a
        ; manual installation cannot silently appear to succeed.
        lda #9
        sta $0342
        lda #<failure_message
        sta $0344
        lda #>failure_message
        sta $0345
        lda #failure_end-failure_message
        sta $0348
        lda #0
        sta $0349
        tax
        jsr $e456
        rts
failure_message: .byte "N: INSTALL FAILED", $9b
failure_end:
malloc_call: jmp (malloc_ref)
uload_call: jmp (uload_ref)
malloc_ref: .word 0
install_ref: .word 0
uload_ref: .word 0
file_ref: .word 0
flag_ref: .word 0
child_name: .byte "D1:CHILD.COM",$9b
.assert * <= $0600, error, "parent exceeded documented scratch"
.segment "INIT"
.word _main
