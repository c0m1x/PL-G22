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


def test_multidimensional_array_constant_access_codegen():
    source = (
        "      PROGRAM T\n"
        "      INTEGER A(2,3), X\n"
        "      A(2,3) = 7\n"
        "      X = A(2,3)\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "STORE_ARR" for ins in ir)
    assert any(ins.op == "LOAD_ARR" for ins in ir)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)


def test_semantic_rejects_wrong_array_rank():
    source = (
        "      PROGRAM T\n"
        "      INTEGER A(2,3), X\n"
        "      X = A(1)\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Numero de indices incompativel"):
        _compile(source)


def test_semantic_rejects_out_of_bounds_literal_index():
    source = (
        "      PROGRAM T\n"
        "      INTEGER A(2,3), X\n"
        "      X = A(3,1)\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Indice fora dos limites"):
        _compile(source)
