import os
import re

import pytest

from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize
from optimizer import optimize
from parser import parse
from preprocessor import preprocess
from semantic import analyze

pytest.importorskip("requests")
pytest.importorskip("bs4")

from ewvm import run_code

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_EWVM_TESTS") != "1",
    reason="EWVM integration tests disabled (set RUN_EWVM_TESTS=1 to enable)",
)


def _compile_to_vm(source: str) -> str:
    lines = preprocess(source)
    tokens = tokenize(lines)
    ast = parse(tokens)
    ast, _sym = analyze(ast)
    ir = generate_ir(ast)
    ir = optimize(ir)
    vm = generate_vm(ir, ast)
    return "\n".join(vm)


def test_ewvm_example_hello_output_matches_expected():
    source = (
        "      PROGRAM HELLO\n"
        "      PRINT *, 'Ola, Mundo!'\n"
        "      END\n"
    )

    output = run_code(_compile_to_vm(source))
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

    output = run_code(_compile_to_vm(source), input_data="3\n")

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

    output = run_code(_compile_to_vm(source), input_data="7\n")

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

    output = run_code(_compile_to_vm(source), input_data="2\n5\n")

    assert re.search(r"(^|\D)7(\D|$)", output)
