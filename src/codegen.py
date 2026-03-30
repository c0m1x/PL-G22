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


def _emit_load(lines, operand, offsets, ensure_offset):
    if isinstance(operand, bool):
        lines.append(f"PUSHI {1 if operand else 0}")
    elif isinstance(operand, tuple) and len(operand) == 2 and operand[0] == "STR":
        lines.append(f"PUSHS '{operand[1]}'")
    elif _is_number(operand):
        if isinstance(operand, int):
            lines.append(f"PUSHI {operand}")
        else:
            lines.append(f"PUSHF {operand}")
    elif isinstance(operand, str):
        slot = ensure_offset(operand)
        lines.append(f"LOAD {slot}")
    else:
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


def _emit_runtime_linear_index(lines, idx_list, dims, offsets, ensure_offset):
    # Stack result: linearized 0-based index.
    lines.append("PUSHI 0")
    for axis, idx_operand in enumerate(idx_list):
        _emit_load(lines, idx_operand, offsets, ensure_offset)
        lines.append("PUSHI 1")
        lines.append("SUB")
        stride = 1
        for rem in dims[axis + 1 :]:
            stride *= rem
        if stride != 1:
            lines.append(f"PUSHI {stride}")
            lines.append("MUL")
        lines.append("ADD")


def _emit_array_base_ptr(lines, base):
    lines.append("PUSHGP")
    lines.append(f"PUSHI {base}")
    lines.append("PADD")


def generate_vm(ir, ast):
    offsets, arrays, mem_size = _collect_vars(ast)
    next_free = mem_size
    lines = [f"ALLOC {mem_size}"]

    def ensure_offset(name):
        nonlocal next_free
        if name not in offsets:
            offsets[name] = next_free
            next_free += 1
            lines[0] = f"ALLOC {next_free}"
        return offsets[name]

    # Ensure temporaries also get stack slots.
    for ins in ir:
        if isinstance(ins.result, str) and ins.result.startswith("_t") and ins.result not in offsets:
            ensure_offset(ins.result)

    for ins in ir:
        op = ins.op
        if op == "COPY":
            _emit_load(lines, ins.arg1, offsets, ensure_offset)
            lines.append(f"STORE {ensure_offset(ins.result)}")
        elif op in _VM_BIN:
            _emit_load(lines, ins.arg1, offsets, ensure_offset)
            _emit_load(lines, ins.arg2, offsets, ensure_offset)
            lines.append(_VM_BIN[op])
            lines.append(f"STORE {ensure_offset(ins.result)}")
        elif op == "NEG":
            _emit_load(lines, 0, offsets, ensure_offset)
            _emit_load(lines, ins.arg1, offsets, ensure_offset)
            lines.append("SUB")
            lines.append(f"STORE {ensure_offset(ins.result)}")
        elif op == "NOT":
            _emit_load(lines, ins.arg1, offsets, ensure_offset)
            lines.append("NOT")
            lines.append(f"STORE {ensure_offset(ins.result)}")
        elif op == "PRINT":
            _emit_load(lines, ins.arg1, offsets, ensure_offset)
            lines.append("PRINT")
        elif op == "READ":
            lines.append("READ")
            lines.append(f"STORE {ensure_offset(ins.result)}")
        elif op == "JMP":
            lines.append(f"JUMP {ins.result}")
        elif op == "JMPF":
            _emit_load(lines, ins.arg1, offsets, ensure_offset)
            lines.append(f"JZ {ins.result}")
        elif op == "LABEL":
            lines.append(f"{ins.result}:")
        elif op == "LOAD_ARR":
            elem_off = _resolve_array_offset(ins.arg1, ins.arg2, arrays)
            if elem_off is not None:
                lines.append(f"LOAD {elem_off}")
                lines.append(f"STORE {ensure_offset(ins.result)}")
                continue

            arr = arrays.get(ins.arg1)
            if arr is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            _emit_array_base_ptr(lines, arr["base"])
            _emit_runtime_linear_index(lines, ins.arg2 if isinstance(ins.arg2, list) else [ins.arg2], arr.get("dims", []), offsets, ensure_offset)
            lines.append("LOADN")
            lines.append(f"STORE {ensure_offset(ins.result)}")
        elif op == "STORE_ARR":
            elem_off = _resolve_array_offset(ins.result, ins.arg1, arrays)
            if elem_off is not None:
                _emit_load(lines, ins.arg2, offsets, ensure_offset)
                lines.append(f"STORE {elem_off}")
                continue

            arr = arrays.get(ins.result)
            if arr is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            _emit_array_base_ptr(lines, arr["base"])
            _emit_runtime_linear_index(lines, ins.arg1 if isinstance(ins.arg1, list) else [ins.arg1], arr.get("dims", []), offsets, ensure_offset)
            _emit_load(lines, ins.arg2, offsets, ensure_offset)
            lines.append("STOREN")
        elif op == "READ_ARR":
            elem_off = _resolve_array_offset(ins.result, ins.arg1, arrays)
            if elem_off is not None:
                lines.append("READ")
                lines.append(f"STORE {elem_off}")
                continue

            arr = arrays.get(ins.result)
            if arr is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            _emit_array_base_ptr(lines, arr["base"])
            _emit_runtime_linear_index(lines, ins.arg1 if isinstance(ins.arg1, list) else [ins.arg1], arr.get("dims", []), offsets, ensure_offset)
            lines.append("READ")
            lines.append("STOREN")
        elif op == "HALT":
            lines.append("HALT")
        else:
            lines.append(f"// INSTR NAO SUPORTADA: {ins}")

    lines.append("HALT")
    return lines
