"""Tests the five example programs from the project spec (PL2026-projeto)."""

from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize
from optimizer import optimize
from parser import parse
from preprocessor import preprocess
from semantic import analyze


def _compile(source: str):
    lines = preprocess(source)
    tokens = tokenize(lines)
    ast = parse(tokens)
    ast, _sym = analyze(ast)
    ir = generate_ir(ast)
    ir = optimize(ir)
    vm = generate_vm(ir, ast)
    return ast, ir, vm


# ---- Regression: optimizer must not constant-fold loop variables ----------

def test_optimizer_does_not_collapse_do_loop_body_to_constants():
    """Regression: copy propagation must clear user-var aliases at LABEL
    join points, otherwise loop variables get replaced by their initial
    values and the loop body collapses to constants."""
    source = (
        "      PROGRAM T\n"
        "      INTEGER I, S\n"
        "      S = 0\n"
        "      DO 10 I = 1, 5\n"
        "      S = S + I\n"
        " 10   CONTINUE\n"
        "      PRINT *, S\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    # The loop body (S = S + I) must remain as a dynamic ADD, not a constant.
    assert any(ins.op == "ADD" for ins in ir), "ADD must survive optimizer in loop body"

    # S must be loaded dynamically inside the loop, not inlined as a constant.
    # After the loop DO_10 label, the first ADD should use LOAD for S and I,
    # not PUSHI constants.
    in_loop = False
    has_dynamic_load_in_loop = False
    for line in vm:
        if line == "dolooplbl10:":
            in_loop = True
        if in_loop and line.startswith("endlooplbl10"):
            break
        if in_loop and line.startswith("PUSHG "):
            has_dynamic_load_in_loop = True

    assert has_dynamic_load_in_loop, "Loop body must use LOAD (dynamic), not only PUSHI (constant)"


# ---- Example 1: Hello World -----------------------------------------------

def test_example1_hello_world():
    source = (
        "      PROGRAM HELLO\n"
        "      PRINT *, 'Ola, Mundo!'\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "PRINT" for ins in ir)
    assert any('PUSHS "Ola, Mundo!"' in line for line in vm)
    assert vm[-1] == "STOP"


# ---- Example 2: Factorial -------------------------------------------------

def test_example2_factorial():
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

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "READ" for ins in ir)
    assert any(ins.op == "MUL" for ins in ir), "FAT = FAT * I must produce a MUL"
    assert any(ins.op == "ADD" for ins in ir), "I increment must produce an ADD"
    assert any("dolooplbl10:" in line for line in vm)
    assert any("endlooplbl10:" in line for line in vm)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)

    # Verify loop body is dynamic: MUL must use loaded values, not constants.
    in_loop = False
    has_mul_in_loop = False
    for ins in ir:
        if ins.op == "LABEL" and ins.result == "dolooplbl10":
            in_loop = True
        if ins.op == "LABEL" and ins.result == "endlooplbl10":
            in_loop = False
        if in_loop and ins.op == "MUL":
            has_mul_in_loop = True
    assert has_mul_in_loop, "MUL instruction must be present inside the DO loop"


# ---- Example 3: Is prime? -------------------------------------------------

def test_example3_primo():
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

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "MOD" for ins in ir)
    assert any(ins.op == "AND" for ins in ir)
    assert any(ins.op == "LE" for ins in ir)
    assert any(ins.op == "JMP" and ins.result == "lbl20" for ins in ir), "GOTO 20 must produce JMP lbl20"
    assert any(line == "JUMP lbl20" for line in vm)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)


# ---- Example 4: Array sum -------------------------------------------------

def test_example4_soma_array():
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

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "READ_ARR" for ins in ir)
    assert any(ins.op == "LOAD_ARR" for ins in ir)
    assert any(ins.op == "ADD" for ins in ir)
    assert any("dolooplbl30:" in line for line in vm)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)
    # Dynamic array access must use LOADN / STOREN (runtime index).
    assert any(line in ("LOADN", "STOREN") for line in vm)


# ---- Example 5: Base conversion with FUNCTION ----------------------------

def test_example5_conversor_com_function():
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

    ast, ir, vm = _compile(source)

    assert len(ast.subprograms) == 1
    assert ast.subprograms[0].name == "CONVRT"
    assert any(ins.op == "MOD" for ins in ir)
    assert any(ins.op == "MUL" for ins in ir)
    assert any(ins.op == "DIV" for ins in ir)
    assert any(ins.op == "ADD" for ins in ir)
    # The function must be inlined (no CALL instructions remain in the IR).
    assert not any(ins.op == "CALL" for ins in ir)
    assert not any("INSTR NAO SUPORTADA" in line for line in vm)
    assert vm[-1] == "STOP"
