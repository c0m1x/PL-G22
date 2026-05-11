from optimize import optimize_ir_text, parse_ir_line, parse_ir_text


def test_parse_ir_line_handles_lists_and_tuples():
    ins = parse_ir_line("LOAD_ARR _t7 NUMS ['I']")

    assert ins.op == "LOAD_ARR"
    assert ins.result == "_t7"
    assert ins.arg1 == "NUMS"
    assert ins.arg2 == ["I"]


def test_optimize_ir_text_optimizes_dump_ir_output():
    text = "\n".join(
        [
            "COPY _t0 5",
            "COPY X _t0",
            "COPY _t1 X",
            "COPY Y _t1",
        ]
    )

    optimized = optimize_ir_text(text)

    assert "COPY X 5" in optimized
    assert "COPY Y 5" in optimized
    assert "_t0" not in optimized
    assert "_t1" not in optimized


def test_parse_ir_text_ignores_blank_lines():
    instrs = parse_ir_text("\nPRINT ('STR', 'Ola')\n\nNEWLINE\n")

    assert [ins.op for ins in instrs] == ["PRINT", "NEWLINE"]