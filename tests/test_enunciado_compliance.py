import pytest

from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize, tokenize_line
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


def test_lexer_recognizes_dotted_logical_operators():
    toks = tokenize_line("L = .NOT. A .AND. B .OR. C")
    types = [tok.type for tok in toks]

    assert "NOT" in types
    assert "AND" in types
    assert "OR" in types


def test_program_with_decl_types_and_logical_expression_compiles():
    source = (
        "      PROGRAM T\n"
        "      INTEGER I\n"
        "      REAL R\n"
        "      LOGICAL L\n"
        "      CHARACTER C\n"
        "      I = 2\n"
        "      R = 3.5\n"
        "      C = 'A'\n"
        "      L = .NOT. (I .EQ. 3) .AND. .TRUE.\n"
        "      IF (L .OR. .FALSE.) THEN\n"
        "      PRINT *, I, R, C\n"
        "      ENDIF\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "NOT" for ins in ir)
    assert any(ins.op == "AND" for ins in ir)
    assert any(ins.op == "OR" for ins in ir)
    assert any(ins.op == "PRINT" for ins in ir)
    assert vm[-1] == "STOP"


def test_semantic_rejects_non_integer_do_control_and_bounds():
    source = (
        "      PROGRAM T\n"
        "      REAL I\n"
        "      INTEGER S\n"
        "      S = 0\n"
        "      DO 10 I = 1.0, 3.0\n"
        "      S = S + 1\n"
        " 10   CONTINUE\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Variavel de controlo do DO deve ser INTEGER"):
        _compile(source)


@pytest.mark.parametrize(
    "decl_line, expected_error",
    [
        ("      INTEGER A(0)\n", "Dimensao de array deve ser > 0"),
        ("      INTEGER A(2.5)\n", "Dimensao de array deve ser literal INTEGER"),
    ],
)
def test_semantic_validates_array_declaration_dimensions(decl_line: str, expected_error: str):
    source = "      PROGRAM T\n" + decl_line + "      END\n"

    with pytest.raises(ValueError, match=expected_error):
        _compile(source)


def test_goto_to_existing_label_is_accepted_and_emitted():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = 1\n"
        "      GOTO 100\n"
        "      X = 2\n"
        " 100  CONTINUE\n"
        "      PRINT *, X\n"
        "      END\n"
    )

    _ast, ir, vm = _compile(source)

    assert any(ins.op == "JMP" and ins.result == "lbl100" for ins in ir)
    assert any(ins.op == "LABEL" and ins.result == "lbl100" for ins in ir)
    assert any(line == "JUMP lbl100" for line in vm)
    assert any(line == "lbl100:" for line in vm)
