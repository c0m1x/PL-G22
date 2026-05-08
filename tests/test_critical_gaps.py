import pytest

from conftest import compile_fortran as _compile


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
