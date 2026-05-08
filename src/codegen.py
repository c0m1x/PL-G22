from ast_nodes import ArrayDeclNode, DeclNode, LiteralNode

_VM_CMP = {
    "EQ": ["EQUAL"],
    "NE": ["EQUAL", "NOT"],
    "LT": ["INF"],
    "LE": ["INFEQ"],
    "GT": ["SUP"],
    "GE": ["SUPEQ"],
}

_VM_BIN = {
    "ADD": "ADD",
    "SUB": "SUB",
    "MUL": "MUL",
    "DIV": "DIV",
    "MOD": "MOD",
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

    for name, info in arrays.items():
        offsets[name] = cursor
        info["base"] = cursor
        cursor += info["size"]

    return offsets, arrays, cursor


def _collect_decl_types(ast):
    var_types = {}
    array_types = {}
    for stmt in ast.body:
        if not isinstance(stmt, DeclNode):
            continue
        for var in stmt.vars:
            if isinstance(var, ArrayDeclNode):
                array_types[var.name] = stmt.type_name
            else:
                var_types[var.name] = stmt.type_name
    return var_types, array_types


def _register_ir_decls(ir, offsets, arrays, mem_size, var_types, array_types):
    cursor = mem_size
    for ins in ir:
        if ins.op == "DECL" and isinstance(ins.result, str):
            var_types[ins.result] = ins.arg1
            if ins.result not in offsets:
                offsets[ins.result] = cursor
                cursor += 1
        elif ins.op == "DECL_ARR" and isinstance(ins.result, str):
            dims = []
            raw_dims = ins.arg1 if isinstance(ins.arg1, list) else []
            for d in raw_dims:
                dims.append(d if isinstance(d, int) and d > 0 else 1)
            size = 1
            for dim in dims:
                size *= dim
            if ins.result not in arrays:
                arrays[ins.result] = {"base": cursor, "size": size, "dims": dims}
                offsets[ins.result] = cursor
                cursor += size
            array_types[ins.result] = ins.arg2
    return cursor


def _infer_ir_types(ir, var_types, array_types):
    types = dict(var_types)

    def _merge_type(current, inferred):
        if inferred is None:
            return current
        if current is None:
            return inferred
        if current == inferred:
            return current
        if {current, inferred} == {"INTEGER", "REAL"}:
            return "REAL"
        # Keep the declared/stable type when in doubt.
        return current

    def _literal_type(value):
        if isinstance(value, bool):
            return "LOGICAL"
        if isinstance(value, int):
            return "INTEGER"
        if isinstance(value, float):
            return "REAL"
        if isinstance(value, tuple) and len(value) == 2 and value[0] == "STR":
            return "CHARACTER"
        return None

    def _resolve_type(value):
        if isinstance(value, str):
            return types.get(value)
        return _literal_type(value)

    changed = True
    while changed:
        changed = False
        for ins in ir:
            if not isinstance(ins.result, str):
                continue

            inferred = None

            if ins.op == "DECL":
                inferred = ins.arg1
            elif ins.op == "DECL_ARR":
                inferred = None
            elif ins.op == "COPY":
                inferred = _resolve_type(ins.arg1)
            elif ins.op == "LOAD_ARR":
                inferred = array_types.get(ins.arg1)
            elif ins.op in {"ADD", "SUB", "MUL", "DIV", "POW", "MOD"}:
                t1 = _resolve_type(ins.arg1)
                t2 = _resolve_type(ins.arg2)
                if t1 == "REAL" or t2 == "REAL":
                    inferred = "REAL"
                elif t1 == "INTEGER" and t2 == "INTEGER":
                    inferred = "INTEGER"
            elif ins.op in {"EQ", "NE", "LT", "LE", "GT", "GE", "AND", "OR", "NOT"}:
                inferred = "LOGICAL"
            elif ins.op in {"NEG"}:
                inferred = _resolve_type(ins.arg1)
            elif ins.op in {"READ", "READ_ARR"}:
                inferred = _resolve_type(ins.result)

            current = types.get(ins.result)
            merged = _merge_type(current, inferred)
            if merged != current:
                types[ins.result] = merged
                changed = True

    return types


def _push_value(lines, operand, _offsets, ensure_offset):
    """Push a value onto the EWVM stack."""
    if isinstance(operand, bool):
        lines.append(f"PUSHI {1 if operand else 0}")
    elif isinstance(operand, tuple) and len(operand) == 2 and operand[0] == "STR":
        lines.append(f'PUSHS "{operand[1]}"')
    elif isinstance(operand, int):
        lines.append(f"PUSHI {operand}")
    elif isinstance(operand, float):
        lines.append(f"PUSHF {operand}")
    elif isinstance(operand, str):
        slot = ensure_offset(operand)
        lines.append(f"PUSHG {slot}")
    else:
        lines.append(f'PUSHS "{operand}"')


def _emit_write(lines, operand, _offsets, ensure_offset, type_of):
    """Push a value and emit the appropriate WRITE instruction."""
    if isinstance(operand, bool):
        lines.append(f"PUSHI {1 if operand else 0}")
        lines.append("WRITEI")
    elif isinstance(operand, tuple) and len(operand) == 2 and operand[0] == "STR":
        lines.append(f'PUSHS "{operand[1]}"')
        lines.append("WRITES")
    elif isinstance(operand, int):
        lines.append(f"PUSHI {operand}")
        lines.append("WRITEI")
    elif isinstance(operand, float):
        lines.append(f"PUSHF {operand}")
        lines.append("WRITEF")
    elif isinstance(operand, str):
        slot = ensure_offset(operand)
        lines.append(f"PUSHG {slot}")
        otype = type_of(operand)
        if otype == "REAL":
            lines.append("WRITEF")
        elif otype == "CHARACTER":
            lines.append("WRITES")
        else:
            lines.append("WRITEI")
    else:
        lines.append(f'PUSHS "{operand}"')
        lines.append("WRITES")


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

    linear = 0
    for axis, dim in enumerate(dims):
        pos = idx_list[axis] - 1  # Fortran 1-based indexing
        if pos < 0 or pos >= dim:
            return None
        stride = 1
        for rem in dims[axis + 1 :]:
            stride *= rem
        linear += pos * stride
    return base + linear


def _emit_runtime_linear_index(lines, idx_list, dims, offsets, ensure_offset):
    """Compute linearized 0-based index and leave it on stack."""
    lines.append("PUSHI 0")
    for axis, idx_operand in enumerate(idx_list):
        _push_value(lines, idx_operand, offsets, ensure_offset)
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
    """Push the address of array element 0 onto the stack."""
    lines.append("PUSHGP")
    lines.append(f"PUSHI {base}")
    lines.append("PADD")


def generate_vm(ir, ast):
    offsets, arrays, mem_size = _collect_vars(ast)
    var_types, array_types = _collect_decl_types(ast)
    mem_size = _register_ir_decls(ir, offsets, arrays, mem_size, var_types, array_types)
    inferred_types = _infer_ir_types(ir, var_types, array_types)
    next_free = mem_size
    lines = [f"PUSHN {mem_size}", "START"]
    pow_count = 0

    def ensure_offset(name):
        nonlocal next_free
        if name not in offsets:
            offsets[name] = next_free
            next_free += 1
            lines[0] = f"PUSHN {next_free}"
        return offsets[name]

    def type_of(name):
        return inferred_types.get(name)

    def emit_pow(base, exponent, result):
        nonlocal pow_count
        result_slot = ensure_offset(result)
        exp_slot = ensure_offset(f"_powexp{pow_count}")
        start_lbl = f"powloop{pow_count}"
        end_lbl = f"powend{pow_count}"
        pow_count += 1

        if type_of(result) == "REAL":
            lines.append("PUSHF 1.0")
        else:
            lines.append("PUSHI 1")
        lines.append(f"STOREG {result_slot}")
        _push_value(lines, exponent, offsets, ensure_offset)
        lines.append(f"STOREG {exp_slot}")
        lines.append(f"{start_lbl}:")
        lines.append(f"PUSHG {exp_slot}")
        lines.append("PUSHI 0")
        lines.append("SUP")
        lines.append(f"JZ {end_lbl}")
        lines.append(f"PUSHG {result_slot}")
        _push_value(lines, base, offsets, ensure_offset)
        lines.append("MUL")
        lines.append(f"STOREG {result_slot}")
        lines.append(f"PUSHG {exp_slot}")
        lines.append("PUSHI 1")
        lines.append("SUB")
        lines.append(f"STOREG {exp_slot}")
        lines.append(f"JUMP {start_lbl}")
        lines.append(f"{end_lbl}:")

    for ins in ir:
        if isinstance(ins.result, str) and ins.result.startswith("_t") and ins.result not in offsets:
            ensure_offset(ins.result)

    for ins in ir:
        op = ins.op

        if op in {"DECL", "DECL_ARR"}:
            continue

        if op == "COPY":
            _push_value(lines, ins.arg1, offsets, ensure_offset)
            lines.append(f"STOREG {ensure_offset(ins.result)}")

        elif op in _VM_BIN:
            _push_value(lines, ins.arg1, offsets, ensure_offset)
            _push_value(lines, ins.arg2, offsets, ensure_offset)
            lines.append(_VM_BIN[op])
            lines.append(f"STOREG {ensure_offset(ins.result)}")

        elif op == "POW":
            emit_pow(ins.arg1, ins.arg2, ins.result)

        elif op in _VM_CMP:
            _push_value(lines, ins.arg1, offsets, ensure_offset)
            _push_value(lines, ins.arg2, offsets, ensure_offset)
            for instr in _VM_CMP[op]:
                lines.append(instr)
            lines.append(f"STOREG {ensure_offset(ins.result)}")

        elif op == "NEG":
            lines.append("PUSHI 0")
            _push_value(lines, ins.arg1, offsets, ensure_offset)
            lines.append("SUB")
            lines.append(f"STOREG {ensure_offset(ins.result)}")

        elif op == "NOT":
            _push_value(lines, ins.arg1, offsets, ensure_offset)
            lines.append("NOT")
            lines.append(f"STOREG {ensure_offset(ins.result)}")

        elif op == "PRINT":
            _emit_write(lines, ins.arg1, offsets, ensure_offset, type_of)

        elif op == "NEWLINE":
            lines.append("WRITELN")

        elif op == "READ":
            lines.append("READ")
            target_type = type_of(ins.result)
            if target_type == "REAL":
                lines.append("ATOF")
            elif target_type != "CHARACTER":
                lines.append("ATOI")
            lines.append(f"STOREG {ensure_offset(ins.result)}")

        elif op == "JMP":
            lines.append(f"JUMP {ins.result}")

        elif op == "JMPF":
            _push_value(lines, ins.arg1, offsets, ensure_offset)
            lines.append(f"JZ {ins.result}")

        elif op == "LABEL":
            lines.append(f"{ins.result}:")

        elif op == "LOAD_ARR":
            elem_off = _resolve_array_offset(ins.arg1, ins.arg2, arrays)
            if elem_off is not None:
                lines.append(f"PUSHG {elem_off}")
                lines.append(f"STOREG {ensure_offset(ins.result)}")
                continue

            arr = arrays.get(ins.arg1)
            if arr is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            _emit_array_base_ptr(lines, arr["base"])
            _emit_runtime_linear_index(
                lines,
                ins.arg2 if isinstance(ins.arg2, list) else [ins.arg2],
                arr.get("dims", []),
                offsets,
                ensure_offset,
            )
            lines.append("LOADN")
            lines.append(f"STOREG {ensure_offset(ins.result)}")

        elif op == "STORE_ARR":
            elem_off = _resolve_array_offset(ins.result, ins.arg1, arrays)
            if elem_off is not None:
                _push_value(lines, ins.arg2, offsets, ensure_offset)
                lines.append(f"STOREG {elem_off}")
                continue

            arr = arrays.get(ins.result)
            if arr is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            _emit_array_base_ptr(lines, arr["base"])
            _emit_runtime_linear_index(
                lines,
                ins.arg1 if isinstance(ins.arg1, list) else [ins.arg1],
                arr.get("dims", []),
                offsets,
                ensure_offset,
            )
            _push_value(lines, ins.arg2, offsets, ensure_offset)
            lines.append("STOREN")

        elif op == "READ_ARR":
            elem_off = _resolve_array_offset(ins.result, ins.arg1, arrays)
            arr_type = array_types.get(ins.result)
            if elem_off is not None:
                lines.append("READ")
                if arr_type == "REAL":
                    lines.append("ATOF")
                elif arr_type != "CHARACTER":
                    lines.append("ATOI")
                lines.append(f"STOREG {elem_off}")
                continue
            arr = arrays.get(ins.result)
            if arr is None:
                lines.append(f"// INSTR NAO SUPORTADA: {ins}")
                continue
            _emit_array_base_ptr(lines, arr["base"])
            _emit_runtime_linear_index(
                lines,
                ins.arg1 if isinstance(ins.arg1, list) else [ins.arg1],
                arr.get("dims", []),
                offsets,
                ensure_offset,
            )
            lines.append("READ")
            if arr_type == "REAL":
                lines.append("ATOF")
            elif arr_type != "CHARACTER":
                lines.append("ATOI")
            lines.append("STOREN")

        elif op == "HALT":
            lines.append("STOP")

        else:
            lines.append(f"// INSTR NAO SUPORTADA: {ins}")

    lines.append("STOP")
    return lines
