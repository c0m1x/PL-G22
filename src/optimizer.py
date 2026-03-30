from ir import TACInstr


_FOLD_BIN = {
    "ADD": lambda a, b: a + b,
    "SUB": lambda a, b: a - b,
    "MUL": lambda a, b: a * b,
    "DIV": lambda a, b: a / b,
    "POW": lambda a, b: a ** b,
}


def _is_num(x):
    return isinstance(x, (int, float))


def _replace_arg(arg, aliases):
    if not isinstance(arg, str):
        return arg
    seen = set()
    cur = arg
    while isinstance(cur, str) and cur in aliases and cur not in seen:
        seen.add(cur)
        cur = aliases[cur]
    return cur


def constant_folding(instrs: list[TACInstr]) -> list[TACInstr]:
    out: list[TACInstr] = []
    for ins in instrs:
        if ins.op in _FOLD_BIN and _is_num(ins.arg1) and _is_num(ins.arg2):
            out.append(TACInstr("COPY", ins.result, _FOLD_BIN[ins.op](ins.arg1, ins.arg2)))
        else:
            out.append(ins)
    return out


def copy_propagation(instrs: list[TACInstr]) -> list[TACInstr]:
    aliases: dict[str, object] = {}
    out: list[TACInstr] = []

    for ins in instrs:
        result = ins.result
        arg1 = _replace_arg(ins.arg1, aliases)
        arg2 = _replace_arg(ins.arg2, aliases)
        rewritten = TACInstr(ins.op, result, arg1, arg2)

        # Any write invalidates prior alias for that destination.
        if isinstance(result, str) and result in aliases:
            aliases.pop(result, None)

        if rewritten.op == "COPY" and isinstance(rewritten.result, str):
            aliases[rewritten.result] = rewritten.arg1

        out.append(rewritten)
    return out


def dead_temp_elimination(instrs: list[TACInstr]) -> list[TACInstr]:
    live: set[str] = set()
    out_rev: list[TACInstr] = []

    def _mark(arg):
        if isinstance(arg, str):
            live.add(arg)

    for ins in reversed(instrs):
        _mark(ins.arg1)
        _mark(ins.arg2)

        if isinstance(ins.result, str) and ins.result.startswith("_t"):
            if ins.result not in live and ins.op in {
                "COPY",
                "ADD",
                "SUB",
                "MUL",
                "DIV",
                "POW",
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
            }:
                continue
            live.discard(ins.result)

        out_rev.append(ins)

    return list(reversed(out_rev))


def peephole(instrs: list[TACInstr]) -> list[TACInstr]:
    out: list[TACInstr] = []
    i = 0
    while i < len(instrs):
        ins = instrs[i]

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
        nxt = dead_temp_elimination(nxt)
        nxt = peephole(nxt)
        if [str(i) for i in nxt] == [str(i) for i in prev]:
            return nxt
        prev = nxt
