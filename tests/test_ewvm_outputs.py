import re

import pytest

from conftest import compile_fortran_optimized
from vm import run as vm_run


def _compile_to_vm(source: str) -> str:
    _, _, vm = compile_fortran_optimized(source)
    return "\n".join(vm)


def test_ewvm_example_hello_output_matches_expected():
    source = (
        "      PROGRAM HELLO\n"
        "      PRINT *, 'Ola, Mundo!'\n"
        "      END\n"
    )

    output = vm_run(_compile_to_vm(source))
    assert "Ola, Mundo!" in output


def test_ewvm_example_factorial_with_input_3_matches_expected_output():
    source = (
        "      PROGRAM FATORIAL\n"
        "      INTEGER N, I, FAT\n"
        "      PRINT *, 'Introduza um numero inteiro positivo:'\n"
        "      READ *, N\n"
        "      FAT = 1\n"
        "      DO 10 I = 1, N\n"
        "      FAT = FAT * I\n"
        " 10   CONTINUE\n"
        "      PRINT *, 'Fatorial de ', N, ': ', FAT\n"
        "      END\n"
    )

    output = vm_run(_compile_to_vm(source), input_data="3\n")

    assert "Introduza um numero inteiro positivo:" in output
    assert re.search(r"Fatorial\s+de\s+3\s*:\s*6", output)


def test_ewvm_read_then_print_echoes_integer_input():
    source = (
        "      PROGRAM ECHO\n"
        "      INTEGER N\n"
        "      READ *, N\n"
        "      PRINT *, N\n"
        "      END\n"
    )

    output = vm_run(_compile_to_vm(source), input_data="7\n")

    assert re.search(r"(^|\D)7(\D|$)", output)


def test_ewvm_two_reads_are_consumed_in_order_and_summed():
    source = (
        "      PROGRAM SUM2\n"
        "      INTEGER A, B\n"
        "      READ *, A\n"
        "      READ *, B\n"
        "      PRINT *, A + B\n"
        "      END\n"
    )

    output = vm_run(_compile_to_vm(source), input_data="2\n5\n")

    assert re.search(r"(^|\D)7(\D|$)", output)


def test_ewvm_example_primo_with_input_7_matches_expected_output():
    source = (
        "      PROGRAM PRIMO\n"
        "      INTEGER NUM, I\n"
        "      LOGICAL ISPRIM\n"
        "      PRINT *, 'Introduza um numero inteiro positivo:'\n"
        "      READ *, NUM\n"
        "      ISPRIM = .TRUE.\n"
        "      I = 2\n"
        " 20   IF (I .LE. (NUM/2) .AND. ISPRIM) THEN\n"
        "      IF (MOD(NUM, I) .EQ. 0) THEN\n"
        "      ISPRIM = .FALSE.\n"
        "      ENDIF\n"
        "      I = I + 1\n"
        "      GOTO 20\n"
        "      ENDIF\n"
        "      IF (ISPRIM) THEN\n"
        "      PRINT *, NUM, ' e um numero primo'\n"
        "      ELSE\n"
        "      PRINT *, NUM, ' nao e um numero primo'\n"
        "      ENDIF\n"
        "      END\n"
    )

    output = vm_run(_compile_to_vm(source), input_data="7\n")

    assert re.search(r"7\s+e\s+um\s+numero\s+primo", output)


def test_ewvm_example_somaarr_with_inputs_1_to_5_matches_expected_output():
    source = (
        "      PROGRAM SOMAARR\n"
        "      INTEGER NUMS(5)\n"
        "      INTEGER I, SOMA\n"
        "      SOMA = 0\n"
        "      PRINT *, 'Introduza 5 numeros inteiros:'\n"
        "      DO 30 I = 1, 5\n"
        "      READ *, NUMS(I)\n"
        "      SOMA = SOMA + NUMS(I)\n"
        " 30   CONTINUE\n"
        "      PRINT *, 'A soma dos numeros e: ', SOMA\n"
        "      END\n"
    )

    output = vm_run(_compile_to_vm(source), input_data="1\n2\n3\n4\n5\n")

    assert re.search(r"A\s+soma\s+dos\s+numeros\s+e:\s*15", output)


def test_ewvm_example_conversor_with_input_10_matches_expected_output():
    source = (
        "      PROGRAM CONVERSOR\n"
        "      INTEGER NUM, BASE, RESULT, CONVRT\n"
        "      PRINT *, 'INTRODUZA UM NUMERO DECIMAL INTEIRO:'\n"
        "      READ *, NUM\n"
        "      DO 10 BASE = 2, 9\n"
        "      RESULT = CONVRT(NUM, BASE)\n"
        "      PRINT *, 'BASE ', BASE, ': ', RESULT\n"
        " 10   CONTINUE\n"
        "      END\n"
        "      INTEGER FUNCTION CONVRT(N, B)\n"
        "      INTEGER N, B, QUOT, REM, POT, VAL\n"
        "      VAL = 0\n"
        "      POT = 1\n"
        "      QUOT = N\n"
        " 20   IF (QUOT .GT. 0) THEN\n"
        "      REM = MOD(QUOT, B)\n"
        "      VAL = VAL + (REM * POT)\n"
        "      QUOT = QUOT / B\n"
        "      POT = POT * 10\n"
        "      GOTO 20\n"
        "      ENDIF\n"
        "      CONVRT = VAL\n"
        "      RETURN\n"
        "      END\n"
    )

    output = vm_run(_compile_to_vm(source), input_data="10\n")

    assert re.search(r"BASE\s+2\s*:\s*1010", output)
    assert re.search(r"BASE\s+8\s*:\s*12", output)
    assert re.search(r"BASE\s+9\s*:\s*11", output)
