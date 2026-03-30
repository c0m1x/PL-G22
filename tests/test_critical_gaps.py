"""Tests que devem falhar hoje para destacar riscos criticos do compilador."""

import pytest

from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize
from parser import parse
from preprocessor import preprocess
from semantic import analyze


def _compile(source: str):
    lines = preprocess(source)
    tokens = tokenize(lines)
    ast = parse(tokens)
    ast, _sym = analyze(ast)
    ir = generate_ir(ast)
    vm = generate_vm(ir, ast)
    return ast, ir, vm


def test_critical_goto_to_missing_label_should_be_semantic_error():
    """Critico: o semantico devia rejeitar GOTO para label inexistente."""
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = 1\n"
        "      GOTO 999\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="GOTO para label inexistente: 999"):
        _compile(source)


def test_critical_array_codegen_should_not_emit_placeholder_comments():
    """Critico: codegen de arrays ainda gera comentarios placeholder."""
    source = (
        "      PROGRAM T\n"
        "      INTEGER A(5), X\n"
        "      X = A(1)\n"
        "      END\n"
    )

    _ast, _ir, vm = _compile(source)

    assert not any("ainda nao implementado" in line for line in vm)
