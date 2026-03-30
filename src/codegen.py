from ast_nodes import DeclNode


_VM_BIN = {
    "ADD": "ADD",
    "SUB": "SUB",
    "MUL": "MUL",
    "DIV": "DIV",
    "POW": "POW",
    "EQ": "EQ",
    "NE": "NE",
    "LT": "LT",
    "LE": "LE",
    "GT": "GT",
    "GE": "GE",
    "AND": "AND",
    "OR": "OR",
}


def _collect_vars(ast):
    out = []
    for stmt in ast.body:
        if isinstance(stmt, DeclNode):
            for var in stmt.vars:
                out.append(var.name)
    # Preserve first declaration order and dedupe.
    seen = set()
    ordered = []
    for name in out:
        if name not in seen:
            ordered.append(name)
            seen.add(name)
    return ordered


def _is_number(x):
    return isinstance(x, (int, float))


def _emit_load(lines, operand, offsets):
    if isinstance(operand, bool):
        lines.append(f"PUSHI {1 if operand else 0}")
    elif _is_number(operand):
        if isinstance(operand, int):
            lines.append(f"PUSHI {operand}")
        else:
            lines.append(f"PUSHF {operand}")
    elif isinstance(operand, str) and operand in offsets:
        lines.append(f"LOAD {offsets[operand]}")
    else:
        # String literal or fallback immediate.
        lines.append(f"PUSHS '{operand}'")


def generate_vm(ir, ast):
    vars_ = _collect_vars(ast)
    offsets = {name: i for i, name in enumerate(vars_)}
    lines = [f"ALLOC {len(vars_)}"]

    # Ensure temporaries also get stack slots.
    for ins in ir:
        if isinstance(ins.result, str) and ins.result.startswith("_t") and ins.result not in offsets:
            offsets[ins.result] = len(offsets)
            lines[0] = f"ALLOC {len(offsets)}"

    for ins in ir:
        op = ins.op
        if op == "COPY":
            _emit_load(lines, ins.arg1, offsets)
            lines.append(f"STORE {offsets[ins.result]}")
        elif op in _VM_BIN:
            _emit_load(lines, ins.arg1, offsets)
            _emit_load(lines, ins.arg2, offsets)
            lines.append(_VM_BIN[op])
            lines.append(f"STORE {offsets[ins.result]}")
        elif op == "NEG":
            _emit_load(lines, 0, offsets)
            _emit_load(lines, ins.arg1, offsets)
            lines.append("SUB")
            lines.append(f"STORE {offsets[ins.result]}")
        elif op == "NOT":
            _emit_load(lines, ins.arg1, offsets)
            lines.append("NOT")
            lines.append(f"STORE {offsets[ins.result]}")
        elif op == "PRINT":
            _emit_load(lines, ins.arg1, offsets)
            lines.append("PRINT")
        elif op == "READ":
            lines.append("READ")
            lines.append(f"STORE {offsets[ins.result]}")
        elif op == "JMP":
            lines.append(f"JUMP {ins.result}")
        elif op == "JMPF":
            _emit_load(lines, ins.arg1, offsets)
            lines.append(f"JZ {ins.result}")
        elif op == "LABEL":
            lines.append(f"{ins.result}:")
        elif op in ("LOAD_ARR", "STORE_ARR", "READ_ARR"):
            lines.append(f"// {op} ainda nao implementado: {ins}")
        else:
            lines.append(f"// INSTR NAO SUPORTADA: {ins}")

    lines.append("HALT")
    return lines
