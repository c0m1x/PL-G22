import pytest

from conftest import compile_fortran as _compile


def test_external_function_call_is_parsed_and_lowered():
    source = (
        "      PROGRAM T\n"
        "      INTEGER A, B, R\n"
        "      A = 2\n"
        "      B = 3\n"
        "      R = SUM2(A, B)\n"
        "      PRINT *, R\n"
        "      END\n"
        "      INTEGER FUNCTION SUM2(X, Y)\n"
        "      INTEGER X, Y\n"
        "      SUM2 = X + Y\n"
        "      RETURN\n"
        "      END\n"
    )

    ast, ir, vm = _compile(source)

    assert len(ast.subprograms) == 1
    assert any(ins.op == "ADD" for ins in ir)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)


def test_function_without_arguments_is_parsed_and_inlined():
    source = (
        "      PROGRAM T\n"
        "      INTEGER R, FIVE\n"
        "      R = FIVE()\n"
        "      PRINT *, R\n"
        "      END\n"
        "      INTEGER FUNCTION FIVE()\n"
        "      FIVE = 5\n"
        "      RETURN\n"
        "      END\n"
    )

    ast, ir, vm = _compile(source)

    assert len(ast.subprograms) == 1
    assert any(ins.op == "COPY" and ins.arg1 == 5 for ins in ir)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)


def test_function_local_variables_are_renamed_during_inlining():
    source = (
        "      PROGRAM T\n"
        "      INTEGER TMP, R, A, F\n"
        "      TMP = 100\n"
        "      A = 0\n"
        "      R = F(A)\n"
        "      PRINT *, TMP, R\n"
        "      END\n"
        "      INTEGER FUNCTION F(N)\n"
        "      INTEGER N, TMP\n"
        "      TMP = 1\n"
        "      F = TMP\n"
        "      RETURN\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "COPY" and isinstance(ins.result, str) and ins.result.startswith("f0l") for ins in ir)
    assert not any(ins.op == "COPY" and ins.result == "TMP" and ins.arg1 == 1 for ins in ir)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)


def test_subroutine_call_compiles_and_updates_identifier_argument():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = 1\n"
        "      CALL INC(X)\n"
        "      PRINT *, X\n"
        "      END\n"
        "      SUBROUTINE INC(N)\n"
        "      INTEGER N\n"
        "      N = N + 1\n"
        "      RETURN\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "CALL" for ins in ir) is False
    assert any(ins.op == "ADD" for ins in ir)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)


def test_dynamic_array_index_no_longer_emits_placeholder():
    source = (
        "      PROGRAM T\n"
        "      INTEGER A(5), I, X\n"
        "      I = 3\n"
        "      READ *, A(I)\n"
        "      X = A(I)\n"
        "      PRINT *, X\n"
        "      END\n"
    )

    _ast, _ir, vm = _compile(source)

    assert not any("INSTR NAO SUPORTADA" in line for line in vm)
    assert any(line in ("LOADN", "STOREN") for line in vm)


def test_function_call_rejects_type_mismatch_argument():
    source = (
        "      PROGRAM T\n"
        "      INTEGER A, R\n"
        "      REAL X\n"
        "      A = 2\n"
        "      X = 3.5\n"
        "      R = SUM2(A, X)\n"
        "      END\n"
        "      INTEGER FUNCTION SUM2(U, V)\n"
        "      INTEGER U, V\n"
        "      SUM2 = U + V\n"
        "      RETURN\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Tipo de argumento incompativel em FUNCTION SUM2"):
        _compile(source)


def test_subroutine_call_rejects_type_mismatch_argument():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      REAL Y\n"
        "      X = 1\n"
        "      Y = 1.5\n"
        "      CALL INC(Y)\n"
        "      END\n"
        "      SUBROUTINE INC(N)\n"
        "      INTEGER N\n"
        "      N = N + 1\n"
        "      RETURN\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Tipo de argumento incompativel em SUBROUTINE INC"):
        _compile(source)


def test_subroutine_call_rejects_scalar_when_array_parameter_expected():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = 1\n"
        "      CALL FILL(X)\n"
        "      END\n"
        "      SUBROUTINE FILL(A)\n"
        "      INTEGER A(5)\n"
        "      A(1) = 7\n"
        "      RETURN\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Argumento 1 de SUBROUTINE FILL deve ser array"):
        _compile(source)
