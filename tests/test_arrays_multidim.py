import pytest

from conftest import compile_fortran as _compile


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
