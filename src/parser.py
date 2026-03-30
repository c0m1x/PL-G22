from ast_nodes import (
    ArrayDeclNode,
    ArrayRefNode,
    AssignNode,
    BinOpNode,
    ContinueNode,
    DeclNode,
    DoNode,
    GotoNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    PrintNode,
    ProgramNode,
    ReadNode,
    StopNode,
    UnaryOpNode,
    VarDeclNode,
)


class TokenStream:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def match(self, *types):
        tok = self.peek()
        if tok and tok.type in types:
            self.pos += 1
            return tok
        return None

    def expect(self, *types):
        tok = self.match(*types)
        if tok:
            return tok
        expected = "/".join(types)
        got = self.peek().type if self.peek() else "EOF"
        raise SyntaxError(f"Esperado {expected}, obtido {got}")


def parse_expr(ts: TokenStream):
    return parse_or(ts)


def parse_or(ts: TokenStream):
    node = parse_and(ts)
    while ts.match("OR"):
        node = BinOpNode("OR", node, parse_and(ts))
    return node


def parse_and(ts: TokenStream):
    node = parse_rel(ts)
    while ts.match("AND"):
        node = BinOpNode("AND", node, parse_rel(ts))
    return node


def parse_rel(ts: TokenStream):
    node = parse_add(ts)
    tok = ts.match("EQ", "NE", "LT", "LE", "GT", "GE")
    if tok:
        return BinOpNode(tok.type, node, parse_add(ts))
    return node


def parse_add(ts: TokenStream):
    node = parse_mul(ts)
    while True:
        tok = ts.match("PLUS", "MINUS")
        if not tok:
            break
        node = BinOpNode(tok.type, node, parse_mul(ts))
    return node


def parse_mul(ts: TokenStream):
    node = parse_pow(ts)
    while True:
        tok = ts.match("STAR", "SLASH")
        if not tok:
            break
        node = BinOpNode(tok.type, node, parse_pow(ts))
    return node


def parse_pow(ts: TokenStream):
    node = parse_unary(ts)
    tok = ts.match("DSTAR")
    if tok:
        return BinOpNode(tok.type, node, parse_pow(ts))
    return node


def parse_unary(ts: TokenStream):
    tok = ts.match("MINUS", "NOT")
    if tok:
        return UnaryOpNode(tok.type, parse_unary(ts))
    return parse_primary(ts)


def parse_primary(ts: TokenStream):
    tok = ts.peek()
    if not tok:
        raise SyntaxError("Expressao incompleta")

    if ts.match("LPAREN"):
        node = parse_expr(ts)
        ts.expect("RPAREN")
        return node

    if tok.type == "INT_LIT":
        ts.pos += 1
        return LiteralNode(tok.value, "INTEGER")

    if tok.type == "REAL_LIT":
        ts.pos += 1
        return LiteralNode(tok.value, "REAL")

    if tok.type == "BOOL_LIT":
        ts.pos += 1
        return LiteralNode(tok.value, "LOGICAL")

    if tok.type == "STRING_LIT":
        ts.pos += 1
        return LiteralNode(tok.value, "CHARACTER")

    if tok.type == "ID":
        ts.pos += 1
        name = tok.value
        if ts.match("LPAREN"):
            idx = [parse_expr(ts)]
            while ts.match("COMMA"):
                idx.append(parse_expr(ts))
            ts.expect("RPAREN")
            return ArrayRefNode(name, idx)
        return IdentifierNode(name)

    raise SyntaxError(f"Token inesperado: {tok.type}")


def _parse_decl(ts: TokenStream):
    type_tok = ts.expect("INTEGER", "REAL", "LOGICAL", "CHARACTER")
    vars_out = []
    while True:
        name = ts.expect("ID").value
        if ts.match("LPAREN"):
            dims = [parse_expr(ts)]
            while ts.match("COMMA"):
                dims.append(parse_expr(ts))
            ts.expect("RPAREN")
            vars_out.append(ArrayDeclNode(name, dims))
        else:
            vars_out.append(VarDeclNode(name))
        if not ts.match("COMMA"):
            break
    return DeclNode(type_tok.type, vars_out)


def _parse_lvalue(ts: TokenStream):
    name = ts.expect("ID").value
    if ts.match("LPAREN"):
        idx = [parse_expr(ts)]
        while ts.match("COMMA"):
            idx.append(parse_expr(ts))
        ts.expect("RPAREN")
        return ArrayRefNode(name, idx)
    return IdentifierNode(name)


def _parse_stmt(line_info, line_iter):
    lineno, label, tokens = line_info
    ts = TokenStream(tokens)
    first = ts.peek()

    if not first:
        return None

    if first.type in ("INTEGER", "REAL", "LOGICAL", "CHARACTER"):
        return _parse_decl(ts)

    if first.type == "PRINT":
        ts.expect("PRINT")
        ts.expect("STAR")
        ts.expect("COMMA")
        values = [parse_expr(ts)]
        while ts.match("COMMA"):
            values.append(parse_expr(ts))
        return PrintNode(values)

    if first.type == "READ":
        ts.expect("READ")
        ts.expect("STAR")
        ts.expect("COMMA")
        targets = [_parse_lvalue(ts)]
        while ts.match("COMMA"):
            targets.append(_parse_lvalue(ts))
        return ReadNode(targets)

    if first.type == "GOTO":
        ts.expect("GOTO")
        lbl = ts.expect("INT_LIT", "ID").value
        return GotoNode(str(lbl))

    if first.type == "CONTINUE":
        ts.expect("CONTINUE")
        return ContinueNode(label)

    if first.type == "STOP":
        ts.expect("STOP")
        return StopNode()

    if first.type == "IF":
        ts.expect("IF")
        ts.expect("LPAREN")
        cond = parse_expr(ts)
        ts.expect("RPAREN")
        ts.expect("THEN")

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
            stmt = _parse_stmt(nxt, line_iter)
            if stmt is not None:
                current.append(stmt)
        return IfNode(cond, then_body, else_body)

    if first.type == "DO":
        ts.expect("DO")
        loop_label = ts.expect("INT_LIT", "ID").value
        var = ts.expect("ID").value
        ts.expect("EQUALS")
        start = parse_expr(ts)
        ts.expect("COMMA")
        end = parse_expr(ts)
        step = None
        if ts.match("COMMA"):
            step = parse_expr(ts)

        body = []
        expected_label = str(loop_label)
        while True:
            nxt = next(line_iter, None)
            if nxt is None:
                raise SyntaxError(f"Linha {lineno}: DO sem fecho")
            n_label = str(nxt[1]) if nxt[1] is not None else None
            n_tokens = nxt[2]
            if n_label == expected_label and n_tokens and n_tokens[0].type == "CONTINUE":
                break
            stmt = _parse_stmt(nxt, line_iter)
            if stmt is not None:
                body.append(stmt)
        return DoNode(expected_label, var, start, end, step, body)

    target = _parse_lvalue(ts)
    ts.expect("EQUALS")
    value = parse_expr(ts)
    return AssignNode(target, value)


def parse(token_lines):
    if not token_lines:
        raise SyntaxError("Programa vazio")

    first = token_lines[0][2]
    if len(first) < 2 or first[0].type != "PROGRAM" or first[1].type != "ID":
        raise SyntaxError("Programa deve iniciar com PROGRAM <ID>")
    program_name = first[1].value

    if not token_lines[-1][2] or token_lines[-1][2][0].type != "END":
        raise SyntaxError("Programa deve terminar com END")

    body_lines = token_lines[1:-1]
    it = iter(body_lines)
    body = []
    for line_info in it:
        stmt = _parse_stmt(line_info, it)
        if stmt is not None:
            body.append(stmt)

    return ProgramNode(program_name, body)
