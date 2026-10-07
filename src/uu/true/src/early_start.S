/* This file is part of the uutils coreutils package.
 * For copyright and license information, see the distributed LICENSE file.
 *
 * Experimental Linux x86-64 ELF entry for silent true invocations.
 * The initial stack holds argc, argv[0], argv[1], ... in eight-byte slots.
 * Every string byte is tested before reading the next, so short arguments
 * never cause a read past their terminating NUL. The original stack and rdx
 * are preserved for the original CRT entry on the help/version path.
 * No absolute addresses or runtime-initialized data are used here.
 */
.section .text.uutils_true_start,"ax",@progbits
.global uutils_true_start
.type uutils_true_start,@function
.p2align 4
uutils_true_start:
    endbr64
    cmp qword ptr [rsp], 2
    jne .Ltrue_exit
    mov r10, qword ptr [rsp + 16]
    cmp byte ptr [r10], 45 /* - */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 1], 45 /* - */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 2], 104 /* h */
    je .Ltrue_help
    cmp byte ptr [r10 + 2], 118 /* v */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 3], 101 /* e */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 4], 114 /* r */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 5], 115 /* s */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 6], 105 /* i */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 7], 111 /* o */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 8], 110 /* n */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 9], 0
    je .Ltrue_full
    jmp .Ltrue_exit
.Ltrue_help:
    cmp byte ptr [r10 + 3], 101 /* e */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 4], 108 /* l */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 5], 112 /* p */
    jne .Ltrue_exit
    cmp byte ptr [r10 + 6], 0
    je .Ltrue_full
.Ltrue_exit:
    xor edi, edi
    mov eax, 231 /* Linux x86-64 exit_group(0). */
    syscall
    /* A policy rejecting exit_group can fall back to normal CRT handling. */
.Ltrue_full:
    jmp _start
.size uutils_true_start, .-uutils_true_start
.section .note.GNU-stack,"",@progbits
