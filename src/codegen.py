from ast_nodes import ArrayDeclNode, DeclNode, LiteralNode


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
    scalars = []
    arrays = {}
    cursor = 0

    for stmt in ast.body:
        if isinstance(stmt, DeclNode):
            for var in stmt.vars:
                if isinstance(var, ArrayDeclNode):
                    dims = []
                    for d in var.dims:
                        if isinstance(d, LiteralNode) and isinstance(d.value, int) and d.value > 0:
                            dims.append(d.value)
                        else:
                            dims.append(1)
                    size = 1
                    for dim in dims:
                        size *= dim
                    arrays[var.name] = {"base": cursor, "size": size, "dims": dims}
                    cursor += size
                else:
                    scalars.append(var.name)

    # Preserve first declaration order and dedupe for scalars.
    seen = set()
    ordered = []
    for name in scalars:
        if name not in seen:
            ordered.append(name)
            seen.add(name)

    offsets = {}
    cursor = 0
    for name in ordered:
        offsets[name] = cursor
        cursor += 1

    # Place arrays after scalar variables.
    for name, info in arrays.items():
        offsets[name] = cursor
        info["base"] = cursor
        cursor += info["size"]

    return offsets, arrays, cursor


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


def _resolve_array_offset(arr_name, idx, arrays):
    if arr_name not in arrays:
        return None
    dims = arrays[arr_name].get("dims", [])
    idx_list = idx if isinstance(idx, list) else [idx]
    if not all(isinstance(v, int) for v in idx_list):
        return None
    if dims and len(idx_list) != len(dims):
        return None

    base = arrays[arr_name]["base"]
    if not dims:
        dims = [arrays[arr_name]["size"]]

    # Row-major linearization for MVP layout in VM memory.
    linear = 0
    for axis, dim in enumerate(dims):
        pos = idx_list[axis] - 1  # Fortran source indexing is 1-based.
        if pos < 0 or pos >= dim:
            return None
        stride = 1
        for rem in dims[axis + 1 :]:
            stride *= rem
        linear += pos * stride
    return base + linear


def generate_vm(ir, ast):
    offsets, arrays, mem_size = _collect_vars(ast)
    next_free = mem_size
    lines = [f"ALLOC {mem_size}"]

    # Ensure temporaries also get stack slots.
    for ins in ir:
        if isinstance(ins.result, str) and ins.result.startswith("_t") and ins.result not in offsets:
            offsets[ins.result] = next_free
            next_free += 1
            lines[0] = f"ALLOC {next_free}"

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
        elif op == "LOAD_ARR":
            elem_off = _resolve_array_offset(ins.arg1, ins.arg2, arrays)
            if elem_off is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            lines.append(f"LOAD {elem_off}")
            lines.append(f"STORE {offsets[ins.result]}")
        elif op == "STORE_ARR":
            elem_off = _resolve_array_offset(ins.result, ins.arg1, arrays)
            if elem_off is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            _emit_load(lines, ins.arg2, offsets)
            lines.append(f"STORE {elem_off}")
        elif op == "READ_ARR":
            elem_off = _resolve_array_offset(ins.result, ins.arg1, arrays)
            if elem_off is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            lines.append("READ")
            lines.append(f"STORE {elem_off}")
        elif op == "HALT":
            lines.append("HALT")
        else:
            lines.append(f"// INSTR NAO SUPORTADA: {ins}")

    lines.append("HALT")
    return lines
