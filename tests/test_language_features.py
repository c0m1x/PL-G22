from ast_nodes import BinOpNode
from codegen import generate_vm
from ir import TACInstr
from ir_gen import generate_ir
from lexer import tokenize
from optimizer import constant_folding
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


def test_expression_precedence_and_associativity_on_ast():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = 2 + 3 * 4 ** 2\n"
        "      END\n"
    )

    ast, _ir, _vm = _compile(source)
    expr = ast.body[1].value

    # Expect: 2 + (3 * (4 ** 2))
    assert isinstance(expr, BinOpNode)
    assert expr.op == "PLUS"
    assert isinstance(expr.right, BinOpNode)
    assert expr.right.op == "STAR"
    assert isinstance(expr.right.right, BinOpNode)
    assert expr.right.right.op == "DSTAR"


def test_if_else_generates_conditional_control_flow():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = 1\n"
        "      IF (X .EQ. 1) THEN\n"
        "      PRINT *, X\n"
        "      ELSE\n"
        "      X = 2\n"
        "      ENDIF\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "JMPF" for ins in ir)
    assert any(ins.op == "LABEL" and str(ins.result).startswith("else") for ins in ir)
    assert any(ins.op == "LABEL" and str(ins.result).startswith("endif") for ins in ir)
    assert any(ins.op == "PRINT" for ins in ir)
    assert any(line.startswith("JZ else") for line in vm)


def test_do_loop_with_step_generates_loop_structure():
    source = (
        "      PROGRAM T\n"
        "      INTEGER I, S\n"
        "      S = 0\n"
        "      DO 100 I = 1, 5, 2\n"
        "      S = S + I\n"
        " 100  CONTINUE\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "LABEL" and ins.result == "dolooplbl100" for ins in ir)
    assert any(ins.op == "LABEL" and ins.result == "endlooplbl100" for ins in ir)
    assert any(ins.op == "LE" for ins in ir)
    assert any(ins.op == "ADD" for ins in ir)
    assert any(line == "dolooplbl100:" for line in vm)
    assert any(line == "endlooplbl100:" for line in vm)


def test_read_and_print_support_scalar_and_array_element():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X, A(3)\n"
        "      READ *, X, A(2)\n"
        "      PRINT *, X, A(2)\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "READ" for ins in ir)
    assert any(ins.op == "READ_ARR" for ins in ir)
    assert len([ins for ins in ir if ins.op == "PRINT"]) == 2
    assert vm.count("READ") == 2


def test_constant_folding_rewrites_pure_numeric_binop():
    instrs = [TACInstr("ADD", "_t0", 2, 3), TACInstr("COPY", "X", "_t0")]

    optimized = constant_folding(instrs)

    assert optimized[0].op == "COPY"
    assert optimized[0].result == "_t0"
    assert optimized[0].arg1 == 5


def test_stop_statement_emits_explicit_halt_instruction():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X, Y\n"
        "      X = 1\n"
        "      STOP\n"
        "      Y = 2\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "HALT" for ins in ir)
    assert vm.count("STOP") >= 2
    first_halt = vm.index("STOP")
    last_halt = len(vm) - 1 - vm[::-1].index("STOP")
    assert first_halt < last_halt
