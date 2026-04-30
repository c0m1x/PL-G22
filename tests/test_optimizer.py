from ir import TACInstr
from optimizer import _alias_depends_on, _build_basic_blocks, _instr_uses, optimize


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


def test_optimize_simplifies_algebraic_identities():
    instrs = [
        TACInstr("ADD", "_t0", "X", 0),
        TACInstr("MUL", "_t1", 1, "_t0"),
        TACInstr("COPY", "Y", "_t1"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "Y" and ins.arg1 == "X" for ins in out)
    assert not any(ins.result in {"_t0", "_t1"} for ins in out)


def test_optimize_removes_unreachable_code_after_jump():
    instrs = [
        TACInstr("JMP", "L1"),
        TACInstr("COPY", "X", 99),
        TACInstr("COPY", "Y", 100),
        TACInstr("LABEL", "L1"),
        TACInstr("COPY", "Z", 1),
    ]

    out = optimize(instrs)

    assert all(not (ins.op == "COPY" and ins.result in {"X", "Y"}) for ins in out)
    assert any(ins.op == "LABEL" and ins.result == "L1" for ins in out)
    assert any(ins.op == "COPY" and ins.result == "Z" and ins.arg1 == 1 for ins in out)


def test_optimize_does_not_crash_on_division_by_zero_constant_folding():
    instrs = [TACInstr("DIV", "_t0", 4, 0), TACInstr("COPY", "X", "_t0")]

    out = optimize(instrs)

    assert any(ins.op == "DIV" and ins.result == "_t0" for ins in out)
    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == "_t0" for ins in out)


def test_optimize_simplifies_power_zero_to_one():
    instrs = [TACInstr("POW", "_t0", "X", 0), TACInstr("COPY", "Y", "_t0")]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "Y" and ins.arg1 == 1 for ins in out)


def test_optimize_eliminates_dead_overwritten_scalar_store():
    instrs = [
        TACInstr("COPY", "X", 1),
        TACInstr("COPY", "X", 2),
        TACInstr("PRINT", None, "X"),
    ]

    out = optimize(instrs)

    assert not any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == 1 for ins in out)
    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == 2 for ins in out)


def test_optimize_keeps_store_live_on_fallthrough_branch():
    instrs = [
        TACInstr("COPY", "X", 1),
        TACInstr("JMPF", "L1", "COND"),
        TACInstr("COPY", "X", 2),
        TACInstr("LABEL", "L1"),
        TACInstr("PRINT", None, "X"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == 1 for ins in out)
    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == 2 for ins in out)


def test_optimize_invalidates_alias_when_source_variable_is_redefined():
    instrs = [
        TACInstr("COPY", "Y", "X"),
        TACInstr("COPY", "X", 1),
        TACInstr("PRINT", None, "Y"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "PRINT" and ins.arg1 == "Y" for ins in out)
    assert all(not (ins.op == "PRINT" and ins.arg1 == 1) for ins in out)


def test_optimize_invalidates_alias_when_source_variable_is_read():
    instrs = [
        TACInstr("COPY", "Y", "X"),
        TACInstr("READ", "X"),
        TACInstr("PRINT", None, "Y"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "PRINT" and ins.arg1 == "Y" for ins in out)
    assert all(not (ins.op == "PRINT" and ins.arg1 == "X") for ins in out)


def test_optimize_does_not_propagate_temp_across_join_point():
    instrs = [
        TACInstr("COPY", "_t0", 1),
        TACInstr("JMPF", "L1", "COND"),
        TACInstr("COPY", "_t0", 2),
        TACInstr("LABEL", "L1"),
        TACInstr("COPY", "X", "_t0"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == "_t0" for ins in out)
    assert all(not (ins.op == "COPY" and ins.result == "X" and ins.arg1 == 2) for ins in out)


def test_optimize_keeps_loop_carried_temp_live_on_back_edge():
    instrs = [
        TACInstr("COPY", "_t0", 1),
        TACInstr("LABEL", "L0"),
        TACInstr("PRINT", None, "_t0"),
        TACInstr("COPY", "_t0", 2),
        TACInstr("JMP", "L0"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "_t0" and ins.arg1 == 1 for ins in out)
    assert any(ins.op == "COPY" and ins.result == "_t0" and ins.arg1 == 2 for ins in out)


def test_optimize_removes_block_unreachable_after_halt_even_with_label():
    instrs = [
        TACInstr("HALT"),
        TACInstr("LABEL", "L1"),
        TACInstr("COPY", "X", 1),
    ]

    out = optimize(instrs)

    assert [(ins.op, ins.result, ins.arg1, ins.arg2) for ins in out] == [("HALT", None, None, None)]


def test_optimize_simplifies_zero_times_value_to_zero():
    instrs = [
        TACInstr("MUL", "_t0", 0, "Y"),
        TACInstr("COPY", "X", "_t0"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == 0 for ins in out)


def test_optimize_preserves_external_scalar_store_at_program_exit():
    instrs = [TACInstr("COPY", "X", 1)]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "X" and ins.arg1 == 1 for ins in out)


def test_optimize_keeps_array_store_side_effect_and_index_use():
    instrs = [
        TACInstr("COPY", "_t0", 1),
        TACInstr("STORE_ARR", "A", ["_t0"], 7),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "_t0" and ins.arg1 == 1 for ins in out)
    assert any(ins.op == "STORE_ARR" and ins.result == "A" for ins in out)


def test_optimize_keeps_temp_used_in_load_arr_index():
    instrs = [
        TACInstr("COPY", "_t0", 1),
        TACInstr("LOAD_ARR", "_t1", "A", ["_t0"]),
        TACInstr("PRINT", None, "_t1"),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "_t0" and ins.arg1 == 1 for ins in out)
    assert any(ins.op == "LOAD_ARR" and ins.result == "_t1" for ins in out)


def test_optimize_keeps_temp_used_in_read_arr_index():
    instrs = [
        TACInstr("COPY", "_t0", 1),
        TACInstr("READ_ARR", "A", ["_t0"]),
    ]

    out = optimize(instrs)

    assert any(ins.op == "COPY" and ins.result == "_t0" and ins.arg1 == 1 for ins in out)
    assert any(ins.op == "READ_ARR" and ins.result == "A" for ins in out)


def test_optimize_simplifies_jmpf_using_arg1_condition():
    instrs = [
        TACInstr("JMPF", "L1", 0, 1),
        TACInstr("COPY", "X", 99),
        TACInstr("LABEL", "L1"),
        TACInstr("COPY", "Y", 1),
    ]

    out = optimize(instrs)

    assert all(not (ins.op == "COPY" and ins.result == "X") for ins in out)
    assert any(ins.op == "LABEL" and ins.result == "L1" for ins in out)
    assert any(ins.op == "COPY" and ins.result == "Y" and ins.arg1 == 1 for ins in out)


def test_alias_depends_on_handles_cycles_without_infinite_loop():
    aliases = {"A": "B", "B": "A"}

    assert _alias_depends_on("A", "B", aliases) is True
    assert _alias_depends_on("A", "A", aliases) is True
    assert _alias_depends_on("A", "Z", aliases) is False


def test_instr_uses_reads_read_arr_indexes_from_arg1():
    ins = TACInstr("READ_ARR", "A", ["I", "J"])

    assert list(_instr_uses(ins)) == ["I", "J"]


def test_build_basic_blocks_produces_non_empty_ranges():
    instrs = [
        TACInstr("JMP", "L1"),
        TACInstr("LABEL", "L0"),
        TACInstr("COPY", "X", 1),
        TACInstr("LABEL", "L1"),
        TACInstr("HALT"),
    ]

    blocks, _instr_to_block, _labels = _build_basic_blocks(instrs)

    assert all(start < end for start, end in blocks)
