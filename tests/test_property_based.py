"""Testes baseados em propriedades (Hypothesis) para o compilador Fortran 77."""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from conftest import compile_fortran_optimized, compile_fortran
from vm import run as vm_run


def _run(source: str, inp: str = "") -> str:
    _, _, vm = compile_fortran_optimized(source)
    return vm_run("\n".join(vm), inp)


# ---------------------------------------------------------------------------
# Propriedade 1: o compilador nunca crasha em programas válidos
# ---------------------------------------------------------------------------

@given(
    x=st.integers(min_value=-1000, max_value=1000),
    y=st.integers(min_value=-1000, max_value=1000),
)
@settings(max_examples=200)
def test_integer_arithmetic_never_crashes(x, y):
    source = (
        f"      PROGRAM T\n"
        f"      INTEGER A, B, C\n"
        f"      A = {x}\n"
        f"      B = {y}\n"
        f"      C = A + B\n"
        f"      PRINT *, C\n"
        f"      END\n"
    )
    output = _run(source)
    assert str(x + y) in output


@given(
    x=st.integers(min_value=-100, max_value=100),
    y=st.integers(min_value=-100, max_value=100),
)
@settings(max_examples=200)
def test_integer_multiplication_never_crashes(x, y):
    source = (
        f"      PROGRAM T\n"
        f"      INTEGER A, B, C\n"
        f"      A = {x}\n"
        f"      B = {y}\n"
        f"      C = A * B\n"
        f"      PRINT *, C\n"
        f"      END\n"
    )
    output = _run(source)
    assert str(x * y) in output


# ---------------------------------------------------------------------------
# Propriedade 2: o otimizador não altera o output do programa
# ---------------------------------------------------------------------------

@given(
    x=st.integers(min_value=-500, max_value=500),
    y=st.integers(min_value=-500, max_value=500),
)
@settings(max_examples=100)
def test_optimizer_preserves_output(x, y):
    source = (
        f"      PROGRAM T\n"
        f"      INTEGER A, B, C\n"
        f"      A = {x}\n"
        f"      B = {y}\n"
        f"      C = A + B\n"
        f"      PRINT *, C\n"
        f"      END\n"
    )
    _, _, vm_unopt = compile_fortran(source)
    _, _, vm_opt = compile_fortran_optimized(source)

    out_unopt = vm_run("\n".join(vm_unopt))
    out_opt = vm_run("\n".join(vm_opt))

    assert out_unopt == out_opt


# ---------------------------------------------------------------------------
# Propriedade 3: DO loops produzem o número correto de iterações
# ---------------------------------------------------------------------------

@given(
    start=st.integers(min_value=1, max_value=10),
    end=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=100)
def test_do_loop_iteration_count(start, end):
    assume(end >= start)
    expected = end - start + 1
    source = (
        f"      PROGRAM T\n"
        f"      INTEGER I, C\n"
        f"      C = 0\n"
        f"      DO 10 I = {start}, {end}\n"
        f"      C = C + 1\n"
        f" 10   CONTINUE\n"
        f"      PRINT *, C\n"
        f"      END\n"
    )
    output = _run(source)
    assert str(expected) in output


# ---------------------------------------------------------------------------
# Propriedade 4: divisão inteira é consistente com Python //
# ---------------------------------------------------------------------------

@given(
    x=st.integers(min_value=-200, max_value=200),
    y=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100)
def test_integer_division_matches_python(x, y):
    source = (
        f"      PROGRAM T\n"
        f"      INTEGER A, B, C\n"
        f"      A = {x}\n"
        f"      B = {y}\n"
        f"      C = A / B\n"
        f"      PRINT *, C\n"
        f"      END\n"
    )
    output = _run(source)
    assert str(x // y) in output


# ---------------------------------------------------------------------------
# Propriedade 5: MOD é consistente com Python %
# ---------------------------------------------------------------------------

@given(
    x=st.integers(min_value=0, max_value=1000),
    y=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100)
def test_mod_matches_python(x, y):
    source = (
        f"      PROGRAM T\n"
        f"      INTEGER A, B, C\n"
        f"      A = {x}\n"
        f"      B = {y}\n"
        f"      C = MOD(A, B)\n"
        f"      PRINT *, C\n"
        f"      END\n"
    )
    output = _run(source)
    assert str(x % y) in output
