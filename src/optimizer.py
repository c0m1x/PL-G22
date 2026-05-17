from ir import TACInstr

_FOLD_BIN = {
    "ADD": lambda a, b: a + b,
    "SUB": lambda a, b: a - b,
    "MUL": lambda a, b: a * b,
    "MOD": lambda a, b: int(a) % int(b),
    "GT": lambda a, b: a > b,
    "GE": lambda a, b: a >= b,
    "LT": lambda a, b: a < b,
    "LE": lambda a, b: a <= b,
    "EQ": lambda a, b: a == b,
    "NE": lambda a, b: a != b,
    # Legacy name kept for backwards compatibility with older dumps.
    "EQUAL": lambda a, b: a == b,
}


def _is_num(x):
    return isinstance(x, (int, float))


def _is_number_literal(x):
    # Python bool is a subclass of int; for arithmetic folding we only want
    # genuine numeric literals.
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _replace_arg(arg, aliases):
    if not isinstance(arg, str):
        return arg
    seen = set()
    cur = arg
    while isinstance(cur, str) and cur in aliases and cur not in seen:
        seen.add(cur)
        cur = aliases[cur]
    return cur


def _is_const_bool(value):
    return isinstance(value, bool) or (isinstance(value, (int, float)) and value in {0, 1})


def _const_truth(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return None


def _alias_depends_on(value, target, aliases):
    if not isinstance(value, str):
        return False

    # Alias cycles are unexpected in the current propagation algorithm, but if
    # a malformed map appears we stop once we revisit a name and answer
    # conservatively instead of looping forever.
    seen = set()
    cur = value
    while isinstance(cur, str) and cur not in seen:
        if cur == target:
            return True
        seen.add(cur)
        cur = aliases.get(cur)
    return cur == target


def _simplify_instruction(ins: TACInstr) -> TACInstr:
    if ins.op == "JMPF" and _is_const_bool(ins.arg1):
        truth = _const_truth(ins.arg1)
        if truth is True:
            return TACInstr("NOP")
        return TACInstr("JMP", ins.result)

    if ins.op in {"ADD", "SUB", "MUL", "DIV", "MOD", "POW", "AND", "OR", "EQ", "NE", "LT", "LE", "GT", "GE"}:
        left = ins.arg1
        right = ins.arg2

        if ins.op == "ADD":
            if left == 0:
                return TACInstr("COPY", ins.result, right)
            if right == 0:
                return TACInstr("COPY", ins.result, left)

        elif ins.op == "SUB":
            if right == 0:
                return TACInstr("COPY", ins.result, left)

        elif ins.op == "MUL":
            if left == 0 or right == 0:
                return TACInstr("COPY", ins.result, 0)
            if left == 1:
                return TACInstr("COPY", ins.result, right)
            if right == 1:
                return TACInstr("COPY", ins.result, left)

        elif ins.op == "DIV":
            if right == 1:
                return TACInstr("COPY", ins.result, left)

        elif ins.op == "POW":
            if right == 0:
                return TACInstr("COPY", ins.result, 1)
            if right == 1:
                return TACInstr("COPY", ins.result, left)

        elif ins.op == "AND":
            if left is False or right is False or left == 0 or right == 0:
                return TACInstr("COPY", ins.result, False)
            if left is True or left == 1:
                return TACInstr("COPY", ins.result, right)
            if right is True or right == 1:
                return TACInstr("COPY", ins.result, left)

        elif ins.op == "OR":
            if left is True or right is True or left == 1 or right == 1:
                return TACInstr("COPY", ins.result, True)
            if left is False or left == 0:
                return TACInstr("COPY", ins.result, right)
            if right is False or right == 0:
                return TACInstr("COPY", ins.result, left)

        elif ins.op in {"EQ", "NE", "LT", "LE", "GT", "GE"} and left == right:
            if ins.op in {"EQ", "LE", "GE"}:
                return TACInstr("COPY", ins.result, True)
            return TACInstr("COPY", ins.result, False)

    return ins


def simplify_arithmetic_and_branches(instrs: list[TACInstr]) -> list[TACInstr]:
    return [_simplify_instruction(ins) for ins in instrs]


_PURE_ASSIGNING_OPS = {
    "COPY",
    "ADD",
    "SUB",
    "MUL",
    "DIV",
    "POW",
    "MOD",
    "EQ",
    "NE",
    "LT",
    "LE",
    "GT",
    "GE",
    "AND",
    "OR",
    "NEG",
    "NOT",
    "LOAD_ARR",
}


def _iter_var_uses(value):
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_var_uses(item)


def _instr_uses(ins: TACInstr):
    if ins.op == "LOAD_ARR":
        yield from _iter_var_uses(ins.arg2)
        return

    if ins.op == "STORE_ARR":
        yield from _iter_var_uses(ins.arg1)
        yield from _iter_var_uses(ins.arg2)
        return

    if ins.op == "READ_ARR":
        # READ_ARR stores into ins.result (the array name) and carries the
        # index operands in arg1, matching ir_gen/codegen.
        yield from _iter_var_uses(ins.arg1)
        return

    yield from _iter_var_uses(ins.arg1)
    yield from _iter_var_uses(ins.arg2)


def _instr_def(ins: TACInstr):
    if ins.op in _PURE_ASSIGNING_OPS | {"READ"} and isinstance(ins.result, str):
        return ins.result
    return None


def _build_basic_blocks(instrs: list[TACInstr]):
    if not instrs:
        return [], {}, {}

    label_to_index = {
        ins.result: idx for idx, ins in enumerate(instrs) if ins.op == "LABEL" and isinstance(ins.result, str)
    }

    leaders = {0}
    for idx, ins in enumerate(instrs):
        if ins.op == "LABEL":
            leaders.add(idx)

        if ins.op in {"JMP", "JMPF", "HALT"} and idx + 1 < len(instrs):
            leaders.add(idx + 1)

        if ins.op in {"JMP", "JMPF"}:
            target_idx = label_to_index.get(ins.result)
            if target_idx is not None:
                leaders.add(target_idx)

    ordered = sorted(leaders)
    blocks: list[tuple[int, int]] = []
    instr_to_block: dict[int, int] = {}

    for block_id, start in enumerate(ordered):
        end = ordered[block_id + 1] if block_id + 1 < len(ordered) else len(instrs)
        assert start < end, "basic block construction must not produce empty blocks"
        blocks.append((start, end))
        for idx in range(start, end):
            instr_to_block[idx] = block_id

    return blocks, instr_to_block, label_to_index


def _compute_successors(instrs: list[TACInstr], blocks, instr_to_block, label_to_index):
    succs = [set() for _ in blocks]

    for block_id, (start, end) in enumerate(blocks):
        if end == start:
            continue

        last = instrs[end - 1]
        next_block = block_id + 1 if block_id + 1 < len(blocks) else None

        if last.op == "JMP":
            target_idx = label_to_index.get(last.result)
            if target_idx is not None:
                succs[block_id].add(instr_to_block[target_idx])
        elif last.op == "JMPF":
            target_idx = label_to_index.get(last.result)
            if target_idx is not None:
                succs[block_id].add(instr_to_block[target_idx])
            if next_block is not None:
                succs[block_id].add(next_block)
        elif last.op != "HALT" and next_block is not None:
            succs[block_id].add(next_block)

    return succs


def dead_store_elimination(instrs: list[TACInstr]) -> list[TACInstr]:
    blocks, instr_to_block, label_to_index = _build_basic_blocks(instrs)
    if not blocks:
        return []

    externally_visible = {
        defined
        for ins in instrs
        for defined in [_instr_def(ins)]
        if isinstance(defined, str) and not defined.startswith("_t")
    }

    succs = _compute_successors(instrs, blocks, instr_to_block, label_to_index)
    use = [set() for _ in blocks]
    defs = [set() for _ in blocks]
    exit_live = [set() for _ in blocks]

    for block_id, (start, end) in enumerate(blocks):
        seen_defs: set[str] = set()
        for ins in instrs[start:end]:
            for used in _instr_uses(ins):
                if used not in seen_defs:
                    use[block_id].add(used)

            defined = _instr_def(ins)
            if defined is not None:
                defs[block_id].add(defined)
                seen_defs.add(defined)

        if not succs[block_id]:
            exit_live[block_id] = set(externally_visible)

    live_in = [set() for _ in blocks]
    live_out = [set() for _ in blocks]

    changed = True
    while changed:
        changed = False
        for block_id in range(len(blocks) - 1, -1, -1):
            new_out = set(exit_live[block_id])
            for succ in succs[block_id]:
                new_out.update(live_in[succ])
            new_in = use[block_id] | (new_out - defs[block_id])

            if new_out != live_out[block_id] or new_in != live_in[block_id]:
                live_out[block_id] = new_out
                live_in[block_id] = new_in
                changed = True

    out: list[TACInstr] = []
    for block_id, (start, end) in enumerate(blocks):
        live = set(live_out[block_id])
        kept_rev: list[TACInstr] = []

        for ins in reversed(instrs[start:end]):
            used = set(_instr_uses(ins))
            defined = _instr_def(ins)

            if defined is not None and defined not in live and ins.op in _PURE_ASSIGNING_OPS:
                continue

            if defined is not None:
                live.discard(defined)
            live.update(used)
            kept_rev.append(ins)

        out.extend(reversed(kept_rev))

    return out


def remove_unreachable_code(instrs: list[TACInstr]) -> list[TACInstr]:
    blocks, instr_to_block, label_to_index = _build_basic_blocks(instrs)
    if not blocks:
        return []

    succs = _compute_successors(instrs, blocks, instr_to_block, label_to_index)
    reachable_blocks = set()
    worklist = [0]

    while worklist:
        block_id = worklist.pop()
        if block_id in reachable_blocks:
            continue
        reachable_blocks.add(block_id)
        worklist.extend(succs[block_id] - reachable_blocks)

    out: list[TACInstr] = []
    for block_id, (start, end) in enumerate(blocks):
        if block_id in reachable_blocks:
            out.extend(instrs[start:end])
    return out


def constant_folding(instrs: list[TACInstr]) -> list[TACInstr]:
    out: list[TACInstr] = []
    for ins in instrs:
        if ins.op == "NOT" and _is_num(ins.arg1):
            out.append(TACInstr("COPY", ins.result, 0 if ins.arg1 else 1))
        elif ins.op in _FOLD_BIN and _is_num(ins.arg1) and _is_num(ins.arg2):
            if ins.op in {"DIV", "MOD"} and ins.arg2 == 0:
                out.append(ins)
                continue
            out.append(TACInstr("COPY", ins.result, _FOLD_BIN[ins.op](ins.arg1, ins.arg2)))
        else:
            out.append(ins)
    return out


def copy_propagation(instrs: list[TACInstr]) -> list[TACInstr]:
    blocks, _, _ = _build_basic_blocks(instrs)
    if not blocks:
        return []

    out: list[TACInstr] = []

    for start, end in blocks:
        aliases: dict[str, object] = {}
        for ins in instrs[start:end]:
            result = ins.result
            arg1 = _replace_arg(ins.arg1, aliases)
            arg2 = _replace_arg(ins.arg2, aliases)
            rewritten = TACInstr(ins.op, result, arg1, arg2)

            defined = _instr_def(rewritten)
            if isinstance(defined, str):
                stale_aliases = {
                    name
                    for name, value in aliases.items()
                    if name == defined or _alias_depends_on(value, defined, aliases)
                }
                for name in stale_aliases:
                    aliases.pop(name, None)

            if rewritten.op == "COPY" and isinstance(rewritten.result, str) and rewritten.arg1 != rewritten.result:
                aliases[rewritten.result] = rewritten.arg1

            out.append(rewritten)
    return out


def dead_temp_elimination(instrs: list[TACInstr]) -> list[TACInstr]:
    return dead_store_elimination(instrs)


def peephole(instrs: list[TACInstr]) -> list[TACInstr]:
    out: list[TACInstr] = []
    i = 0
    while i < len(instrs):
        ins = instrs[i]

        if ins.op == "NOP":
            i += 1
            continue

        # Remove x = x copies.
        if ins.op == "COPY" and ins.result == ins.arg1:
            i += 1
            continue

        # Remove unconditional jump to immediately next label.
        if ins.op == "JMP" and i + 1 < len(instrs):
            nxt = instrs[i + 1]
            if nxt.op == "LABEL" and nxt.result == ins.result:
                i += 1
                continue

        out.append(ins)
        i += 1
    return out


def optimize(instrs: list[TACInstr]) -> list[TACInstr]:
    prev = instrs
    while True:
        nxt = constant_folding(prev)
        nxt = copy_propagation(nxt)
        nxt = simplify_arithmetic_and_branches(nxt)
        nxt = remove_unreachable_code(nxt)
        nxt = dead_store_elimination(nxt)
        nxt = peephole(nxt)
        if [str(i) for i in nxt] == [str(i) for i in prev]:
            return nxt
        prev = nxt
