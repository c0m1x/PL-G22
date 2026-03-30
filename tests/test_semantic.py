import pytest

from lexer import tokenize
from parser import parse
from preprocessor import preprocess
from semantic import analyze


def _analyze(source: str):
    lines = preprocess(source)
    tokens = tokenize(lines)
    ast = parse(tokens)
    return analyze(ast)


def test_semantic_detects_undeclared_identifier():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = Y\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Identificador nao declarado: Y"):
        _analyze(source)


def test_semantic_detects_redeclaration():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      INTEGER X\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Redeclaracao de simbolo: X"):
        _analyze(source)


def test_semantic_requires_logical_if_condition():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      IF (X) THEN\n"
        "      X = 1\n"
        "      ENDIF\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Condicao de IF deve ser LOGICAL"):
        _analyze(source)


def test_semantic_rejects_non_logical_not_operand():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      X = .NOT. 1\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Operador NOT exige operando LOGICAL"):
        _analyze(source)


def test_semantic_rejects_non_logical_and_operands():
    source = (
        "      PROGRAM T\n"
        "      INTEGER X\n"
        "      LOGICAL L\n"
        "      L = X .AND. .TRUE.\n"
        "      END\n"
    )

    with pytest.raises(ValueError, match="Operador AND exige operandos LOGICAL"):
        _analyze(source)
