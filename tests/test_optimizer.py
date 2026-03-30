from ir import TACInstr
from optimizer import optimize


def test_optimize_applies_copy_propagation_and_dead_temp_elimination():
    instrs = [
        TACInstr("COPY", "_t0", 5),
        TACInstr("COPY", "X", "_t0"),
        TACInstr("COPY", "_t1", "X"),
        TACInstr("COPY", "Y", "_t1"),
    ]

    out = optimize(instrs)

    # _t0 and _t1 become unnecessary after propagation and DCE.
    assert not any(ins.result == "_t0" for ins in out)
    assert not any(ins.result == "_t1" for ins in out)
    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == 5 for ins in out)
    assert any(ins.op == "COPY" and ins.result == "Y" and ins.arg1 == 5 for ins in out)


def test_optimize_removes_redundant_copy_and_jump_to_next_label():
    instrs = [
        TACInstr("COPY", "X", "X"),
        TACInstr("JMP", "L0"),
        TACInstr("LABEL", "L0"),
        TACInstr("COPY", "Y", 1),
    ]

    out = optimize(instrs)

    assert all(not (ins.op == "COPY" and ins.result == "X" and ins.arg1 == "X") for ins in out)
    assert all(not (ins.op == "JMP" and ins.result == "L0") for ins in out)
    assert any(ins.op == "LABEL" and ins.result == "L0" for ins in out)
