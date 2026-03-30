import ply.yacc as yacc

from ast_nodes import (
    ArrayDeclNode,
    ArrayRefNode,
    AssignNode,
    BinOpNode,
    CallNode,
    ContinueNode,
    DeclNode,
    DoNode,
    FuncCallNode,
    FunctionDefNode,
    GotoNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    PrintNode,
    ProgramNode,
    ReadNode,
    ReturnNode,
    StopNode,
    SubroutineDefNode,
    UnaryOpNode,
    VarDeclNode,
)
from lexer import tokens


# Expression and simple-statement parser based on PLY yacc.
# Block statements (IF/DO) and program unit boundaries are handled line-wise.
precedence = (
    ("left", "OR"),
    ("left", "AND"),
    ("nonassoc", "EQ", "NE", "LT", "LE", "GT", "GE"),
    ("left", "PLUS", "MINUS"),
    ("left", "STAR", "SLASH"),
    ("right", "DSTAR"),
    ("right", "UMINUS", "NOT"),
)

_CURRENT_FUNCTION_NAMES: set[str] = set()


class _ListTokenLexer:
    def __init__(self, toks):
        self.toks = toks
        self.pos = 0

    def token(self):
        if self.pos >= len(self.toks):
            return None
        tok = self.toks[self.pos]
        self.pos += 1
        return tok


# ---- Grammar: expression -------------------------------------------------
def p_expr_binop(p):
    """expr : expr PLUS expr
            | expr MINUS expr
            | expr STAR expr
            | expr SLASH expr
            | expr DSTAR expr
            | expr EQ expr
            | expr NE expr
            | expr LT expr
            | expr LE expr
            | expr GT expr
            | expr GE expr
            | expr AND expr
            | expr OR expr"""
    p[0] = BinOpNode(p.slice[2].type, p[1], p[3])


def p_expr_uminus(p):
    "expr : MINUS expr %prec UMINUS"
    p[0] = UnaryOpNode("MINUS", p[2])


def p_expr_not(p):
    "expr : NOT expr"
    p[0] = UnaryOpNode("NOT", p[2])


def p_expr_group(p):
    "expr : LPAREN expr RPAREN"
    p[0] = p[2]


def p_expr_int(p):
    "expr : INT_LIT"
    p[0] = LiteralNode(p[1], "INTEGER")


def p_expr_real(p):
    "expr : REAL_LIT"
    p[0] = LiteralNode(p[1], "REAL")


def p_expr_bool(p):
    "expr : BOOL_LIT"
    p[0] = LiteralNode(p[1], "LOGICAL")


def p_expr_string(p):
    "expr : STRING_LIT"
    p[0] = LiteralNode(p[1], "CHARACTER")


def p_expr_id(p):
    "expr : ID"
    p[0] = IdentifierNode(p[1])


def p_expr_ref_or_call(p):
    "expr : ID LPAREN expr_list RPAREN"
    if p[1] in _CURRENT_FUNCTION_NAMES:
        p[0] = FuncCallNode(p[1], p[3])
    else:
        p[0] = ArrayRefNode(p[1], p[3])


# ---- Grammar: reusable lists ---------------------------------------------
def p_expr_list_one(p):
    "expr_list : expr"
    p[0] = [p[1]]


def p_expr_list_many(p):
    "expr_list : expr_list COMMA expr"
    p[0] = p[1] + [p[3]]


def p_opt_expr_list_empty(p):
    "opt_expr_list : "
    p[0] = []


def p_opt_expr_list_some(p):
    "opt_expr_list : expr_list"
    p[0] = p[1]


# ---- Grammar: declarations and lvalues -----------------------------------
def p_type_name(p):
    """type_name : INTEGER
                 | REAL
                 | LOGICAL
                 | CHARACTER"""
    p[0] = p.slice[1].type


def p_var_spec_scalar(p):
    "var_spec : ID"
    p[0] = VarDeclNode(p[1])


def p_var_spec_array(p):
    "var_spec : ID LPAREN expr_list RPAREN"
    p[0] = ArrayDeclNode(p[1], p[3])


def p_var_list_one(p):
    "var_list : var_spec"
    p[0] = [p[1]]


def p_var_list_many(p):
    "var_list : var_list COMMA var_spec"
    p[0] = p[1] + [p[3]]


def p_lvalue_id(p):
    "lvalue : ID"
    p[0] = IdentifierNode(p[1])


def p_lvalue_array(p):
    "lvalue : ID LPAREN expr_list RPAREN"
    p[0] = ArrayRefNode(p[1], p[3])


def p_lvalue_list_one(p):
    "lvalue_list : lvalue"
    p[0] = [p[1]]


def p_lvalue_list_many(p):
    "lvalue_list : lvalue_list COMMA lvalue"
    p[0] = p[1] + [p[3]]


# ---- Grammar: single-line statements -------------------------------------
def p_stmt_decl(p):
    "stmt : type_name var_list"
    p[0] = DeclNode(p[1], p[2])


def p_stmt_assign(p):
    "stmt : lvalue EQUALS expr"
    p[0] = AssignNode(p[1], p[3])


def p_stmt_print(p):
    "stmt : PRINT STAR COMMA expr_list"
    p[0] = PrintNode(p[4])


def p_stmt_read(p):
    "stmt : READ STAR COMMA lvalue_list"
    p[0] = ReadNode(p[4])


def p_stmt_goto(p):
    "stmt : GOTO INT_LIT"
    p[0] = GotoNode(str(p[2]))


def p_stmt_goto_id(p):
    "stmt : GOTO ID"
    p[0] = GotoNode(str(p[2]))


def p_stmt_continue(p):
    "stmt : CONTINUE"
    p[0] = ContinueNode(None)


def p_stmt_stop(p):
    "stmt : STOP"
    p[0] = StopNode()


def p_stmt_call(p):
    "stmt : CALL ID LPAREN opt_expr_list RPAREN"
    p[0] = CallNode(p[2], p[4])


def p_stmt_return(p):
    "stmt : RETURN"
    p[0] = ReturnNode()


def p_error(p):
    if p is None:
        raise SyntaxError("Fim de linha inesperado")
    raise SyntaxError(f"Token inesperado: {p.type}")


_EXPR_PARSER = yacc.yacc(
    start="expr",
    debug=False,
    write_tables=False,
    optimize=False,
    tabmodule="_fortran_expr_parsetab",
)
_STMT_PARSER = yacc.yacc(
    start="stmt",
    debug=False,
    write_tables=False,
    optimize=False,
    tabmodule="_fortran_stmt_parsetab",
)


def _parse_expr_tokens(toks, function_names):
    global _CURRENT_FUNCTION_NAMES
    _CURRENT_FUNCTION_NAMES = set(function_names)
    return _EXPR_PARSER.parse(lexer=_ListTokenLexer(toks))


def _parse_stmt_tokens(toks, function_names):
    global _CURRENT_FUNCTION_NAMES
    _CURRENT_FUNCTION_NAMES = set(function_names)
    return _STMT_PARSER.parse(lexer=_ListTokenLexer(toks))


def _extract_parenthesized(tokens_in_line, start_idx):
    if start_idx >= len(tokens_in_line) or tokens_in_line[start_idx].type != "LPAREN":
        raise SyntaxError("Esperado LPAREN")
    depth = 0
    for idx in range(start_idx, len(tokens_in_line)):
        t = tokens_in_line[idx].type
        if t == "LPAREN":
            depth += 1
        elif t == "RPAREN":
            depth -= 1
            if depth == 0:
                return tokens_in_line[start_idx + 1 : idx], idx
    raise SyntaxError("Parentesis nao fechado")


def _stmt_with_label(stmt, label):
    if label is not None:
        setattr(stmt, "stmt_label", str(label))
    return stmt


def _parse_stmt_line(line_info, line_iter, function_names):
    lineno, label, toks = line_info
    if not toks:
        return None

    first_t = toks[0].type

    if first_t == "IF":
        if len(toks) < 5 or toks[-1].type != "THEN":
            raise SyntaxError(f"Linha {lineno}: IF mal formado")
        cond_tokens, close_idx = _extract_parenthesized(toks, 1)
        if close_idx != len(toks) - 2:
            raise SyntaxError(f"Linha {lineno}: IF mal formado")
        cond = _parse_expr_tokens(cond_tokens, function_names)

        then_body = []
        else_body = []
        current = then_body
        while True:
            nxt = next(line_iter, None)
            if nxt is None:
                raise SyntaxError(f"Linha {lineno}: IF sem ENDIF")
            nxt_tokens = nxt[2]
            if nxt_tokens and nxt_tokens[0].type == "ENDIF":
                break
            if nxt_tokens and nxt_tokens[0].type == "ELSE":
                current = else_body
                continue
            stmt = _parse_stmt_line(nxt, line_iter, function_names)
            if stmt is not None:
                current.append(stmt)
        return _stmt_with_label(IfNode(cond, then_body, else_body), label)

    if first_t == "DO":
        # DO <label> <var> = <start>, <end> [, <step>]
        if len(toks) < 7:
            raise SyntaxError(f"Linha {lineno}: DO mal formado")
        loop_label_tok = toks[1]
        if loop_label_tok.type not in ("INT_LIT", "ID"):
            raise SyntaxError(f"Linha {lineno}: Label do DO invalido")
        expected_label = str(loop_label_tok.value)

        if toks[2].type != "ID" or toks[3].type != "EQUALS":
            raise SyntaxError(f"Linha {lineno}: DO mal formado")
        var_name = toks[2].value

        # Split start/end/step by top-level commas.
        expr_toks = toks[4:]
        parts = []
        cur = []
        depth = 0
        for tok in expr_toks:
            if tok.type == "LPAREN":
                depth += 1
            elif tok.type == "RPAREN":
                depth -= 1
            if tok.type == "COMMA" and depth == 0:
                parts.append(cur)
                cur = []
                continue
            cur.append(tok)
        if cur:
            parts.append(cur)
        if len(parts) not in (2, 3):
            raise SyntaxError(f"Linha {lineno}: DO mal formado")

        start_expr = _parse_expr_tokens(parts[0], function_names)
        end_expr = _parse_expr_tokens(parts[1], function_names)
        step_expr = _parse_expr_tokens(parts[2], function_names) if len(parts) == 3 else None

        body = []
        while True:
            nxt = next(line_iter, None)
            if nxt is None:
                raise SyntaxError(f"Linha {lineno}: DO sem fecho")
            n_label = str(nxt[1]) if nxt[1] is not None else None
            n_tokens = nxt[2]
            if n_label == expected_label and n_tokens and n_tokens[0].type == "CONTINUE":
                break
            stmt = _parse_stmt_line(nxt, line_iter, function_names)
            if stmt is not None:
                body.append(stmt)

        return _stmt_with_label(DoNode(expected_label, var_name, start_expr, end_expr, step_expr, body), label)

    # Single-line statements handled by yacc grammar.
    stmt = _parse_stmt_tokens(toks, function_names)
    return _stmt_with_label(stmt, label)


def _parse_param_list(toks):
    if not toks:
        return []
    out = []
    for tok in toks:
        if tok.type == "COMMA":
            continue
        if tok.type != "ID":
            raise SyntaxError("Lista de parametros invalida")
        out.append(tok.value)
    return out


def _parse_function_header(tokens_in_line):
    # <TYPE> FUNCTION <ID> ( [params] )
    if len(tokens_in_line) < 5:
        raise SyntaxError("Cabecalho de FUNCTION invalido")
    rtype = tokens_in_line[0].type
    if rtype not in ("INTEGER", "REAL", "LOGICAL", "CHARACTER"):
        raise SyntaxError("Tipo de retorno invalido em FUNCTION")
    if tokens_in_line[1].type != "FUNCTION" or tokens_in_line[2].type != "ID":
        raise SyntaxError("Cabecalho de FUNCTION invalido")
    name = tokens_in_line[2].value
    if tokens_in_line[3].type != "LPAREN" or tokens_in_line[-1].type != "RPAREN":
        raise SyntaxError("Cabecalho de FUNCTION invalido")
    params = _parse_param_list(tokens_in_line[4:-1])
    return rtype, name, params


def _parse_subroutine_header(tokens_in_line):
    # SUBROUTINE <ID> ( [params] )
    if len(tokens_in_line) < 4:
        raise SyntaxError("Cabecalho de SUBROUTINE invalido")
    if tokens_in_line[0].type != "SUBROUTINE" or tokens_in_line[1].type != "ID":
        raise SyntaxError("Cabecalho de SUBROUTINE invalido")
    name = tokens_in_line[1].value
    if tokens_in_line[2].type != "LPAREN" or tokens_in_line[-1].type != "RPAREN":
        raise SyntaxError("Cabecalho de SUBROUTINE invalido")
    params = _parse_param_list(tokens_in_line[3:-1])
    return name, params


def parse(token_lines):
    if not token_lines:
        raise SyntaxError("Programa vazio")

    first = token_lines[0][2]
    if len(first) < 2 or first[0].type != "PROGRAM" or first[1].type != "ID":
        raise SyntaxError("Programa deve iniciar com PROGRAM <ID>")
    program_name = first[1].value

    # Pre-scan subprogram names for call/reference disambiguation in expr grammar.
    function_names = set()
    for _lineno, _label, line_toks in token_lines:
        if len(line_toks) >= 3 and line_toks[0].type in ("INTEGER", "REAL", "LOGICAL", "CHARACTER") and line_toks[1].type == "FUNCTION" and line_toks[2].type == "ID":
            function_names.add(line_toks[2].value)

    # Parse main program body until END.
    body_lines = token_lines[1:]
    it = iter(body_lines)
    body = []
    remainder = []
    ended = False
    for line_info in it:
        toks = line_info[2]
        if toks and toks[0].type == "END":
            ended = True
            remainder = list(it)
            break
        stmt = _parse_stmt_line(line_info, it, function_names)
        if stmt is not None:
            body.append(stmt)

    if not ended:
        raise SyntaxError("Programa deve terminar com END")

    # Parse optional external subprogram units after END PROGRAM.
    subprograms = []
    rem_it = iter(remainder)
    for line_info in rem_it:
        toks = line_info[2]
        if not toks:
            continue

        if len(toks) >= 2 and toks[0].type in ("INTEGER", "REAL", "LOGICAL", "CHARACTER") and toks[1].type == "FUNCTION":
            rtype, name, params = _parse_function_header(toks)
            fn_body = []
            while True:
                nxt = next(rem_it, None)
                if nxt is None:
                    raise SyntaxError(f"FUNCTION {name} sem END")
                nxt_toks = nxt[2]
                if nxt_toks and nxt_toks[0].type == "END":
                    break
                stmt = _parse_stmt_line(nxt, rem_it, function_names)
                if stmt is not None:
                    fn_body.append(stmt)
            subprograms.append(FunctionDefNode(rtype, name, params, fn_body))
            continue

        if toks[0].type == "SUBROUTINE":
            name, params = _parse_subroutine_header(toks)
            sub_body = []
            while True:
                nxt = next(rem_it, None)
                if nxt is None:
                    raise SyntaxError(f"SUBROUTINE {name} sem END")
                nxt_toks = nxt[2]
                if nxt_toks and nxt_toks[0].type == "END":
                    break
                stmt = _parse_stmt_line(nxt, rem_it, function_names)
                if stmt is not None:
                    sub_body.append(stmt)
            subprograms.append(SubroutineDefNode(name, params, sub_body))
            continue

        raise SyntaxError("Codigo apos END do programa deve ser FUNCTION/SUBROUTINE")

    return ProgramNode(program_name, body, subprograms)
