import re

import ply.lex as lex


RESERVED = {
    "PROGRAM",
    "END",
    "INTEGER",
    "REAL",
    "LOGICAL",
    "CHARACTER",
    "IF",
    "THEN",
    "ELSE",
    "ENDIF",
    "DO",
    "CONTINUE",
    "GOTO",
    "READ",
    "PRINT",
    "WRITE",
    "STOP",
    "RETURN",
    "FUNCTION",
    "SUBROUTINE",
    "CALL",
    "AND",
    "OR",
    "NOT",
}

tokens = list(RESERVED) + [
    "ID",
    "INT_LIT",
    "REAL_LIT",
    "BOOL_LIT",
    "STRING_LIT",
    "EQ",
    "NE",
    "LT",
    "LE",
    "GT",
    "GE",
    "PLUS",
    "MINUS",
    "STAR",
    "SLASH",
    "DSTAR",
    "LPAREN",
    "RPAREN",
    "COMMA",
    "EQUALS",
]

t_PLUS = r"\+"
t_MINUS = r"-"
t_SLASH = r"/"
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_COMMA = r","
t_EQUALS = r"="

t_DSTAR = r"\*\*"
t_STAR = r"\*"

t_EQ = r"\.EQ\."
t_NE = r"\.NE\."
t_LT = r"\.LT\."
t_LE = r"\.LE\."
t_GT = r"\.GT\."
t_GE = r"\.GE\."


def t_AND(t):
    r"\.AND\."
    t.value = "AND"
    return t


def t_OR(t):
    r"\.OR\."
    t.value = "OR"
    return t


def t_NOT(t):
    r"\.NOT\."
    t.value = "NOT"
    return t

t_ignore = " \t\r"


def t_BOOL_LIT(t):
    r"\.(TRUE|FALSE)\."
    t.value = t.value.upper() == ".TRUE."
    return t


def t_REAL_LIT(t):
    r"\d+\.\d*([EeDd][+-]?\d+)?|\.\d+([EeDd][+-]?\d+)?"
    t.value = float(t.value.replace("D", "E").replace("d", "e"))
    return t


def t_INT_LIT(t):
    r"\d+"
    t.value = int(t.value)
    return t


def t_ID(t):
    r"[A-Za-z][A-Za-z0-9_]*"
    upper = t.value.upper()
    t.type = upper if upper in RESERVED else "ID"
    t.value = upper
    return t


def t_STRING_LIT(t):
    r"'[^']*'"
    t.value = t.value[1:-1]
    return t


def t_error(t):
    raise SyntaxError(f"Caractere invalido '{t.value[0]}'")


_LEXER = lex.lex(reflags=re.IGNORECASE)


def tokenize_line(line: str):
    _LEXER.input(line)
    out = []
    while True:
        tok = _LEXER.token()
        if not tok:
            break
        out.append(tok)
    return out


def tokenize(lines):
    # Keep (lineno, label, token_stream) per logical source line.
    token_lines = []
    for lineno, label, code in lines:
        token_lines.append((lineno, label, tokenize_line(code)))
    return token_lines
