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


def test_mod_intrinsic_in_if_condition_compiles():
    source = (
        "      PROGRAM PRIMO\n"
        "      INTEGER NUM, I\n"
        "      LOGICAL ISPRIM\n"
        "      NUM = 7\n"
        "      ISPRIM = .TRUE.\n"
        "      I = 2\n"
        " 20   IF (I .LE. (NUM/2) .AND. ISPRIM) THEN\n"
        "      IF (MOD(NUM, I) .EQ. 0) THEN\n"
        "      ISPRIM = .FALSE.\n"
        "      ENDIF\n"
        "      I = I + 1\n"
        "      GOTO 20\n"
        "      ENDIF\n"
        "      PRINT *, ISPRIM\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "MOD" for ins in ir)
    assert any(line == "MOD" for line in vm)


def test_external_function_name_type_declaration_is_accepted():
    source = (
        "      PROGRAM CONVERSOR\n"
        "      INTEGER NUM, BASE, RESULT, CONVRT\n"
        "      NUM = 10\n"
        "      BASE = 2\n"
        "      RESULT = CONVRT(NUM, BASE)\n"
        "      PRINT *, RESULT\n"
        "      END\n"
        "      INTEGER FUNCTION CONVRT(N, B)\n"
        "      INTEGER N, B, V\n"
        "      V = N + B\n"
        "      CONVRT = V\n"
        "      RETURN\n"
        "      END\n"
    )

    ast, ir, vm = _compile(source)

    assert len(ast.subprograms) == 1
    assert any(ins.op == "ADD" for ins in ir)
    assert vm[-1] == "HALT"
