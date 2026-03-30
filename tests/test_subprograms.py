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
