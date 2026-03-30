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


def constant_folding(instrs: list[TACInstr]) -> list[TACInstr]:
    out: list[TACInstr] = []
    for ins in instrs:
        if ins.op in _FOLD_BIN and _is_num(ins.arg1) and _is_num(ins.arg2):
            out.append(TACInstr("COPY", ins.result, _FOLD_BIN[ins.op](ins.arg1, ins.arg2)))
        else:
            out.append(ins)
    return out


def optimize(instrs: list[TACInstr]) -> list[TACInstr]:
    prev = instrs
    while True:
        nxt = constant_folding(prev)
        if [str(i) for i in nxt] == [str(i) for i in prev]:
            return nxt
        prev = nxt
